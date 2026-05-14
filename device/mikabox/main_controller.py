"""
MikaBox Main Controller
=======================

Central state machine that orchestrates all device subsystems:
audio playback, NFC detection, voice input, LED feedback,
parental controls, and server communication.
"""

import logging
import signal
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional

from .config import config
from .audio_player import AudioPlayer
from .nfc_manager import NFCManager
from .led_controller import LEDController, LEDPattern
from .voice_manager import VoiceManager
from .server_client import ServerClient
from .parental_controls import ParentalControls

logger = logging.getLogger("mikabox.controller")


class DeviceState(str, Enum):
    """Device state machine states."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    LISTENING = "listening"      # Wake word detected, recording voice
    PROCESSING = "processing"    # Voice sent to server, awaiting response
    SLEEP = "sleep"


class MainController:
    """
    The brain of the MikaBox device.

    Wires together all subsystems and manages state transitions.
    Runs until SIGINT/SIGTERM or explicit shutdown.
    """

    def __init__(self):
        self._state = DeviceState.IDLE
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._last_activity_time = time.monotonic()
        self._current_profile_id: str = "default"

        # ── Subsystems ────────────────────────────────────────────────
        self._audio = AudioPlayer(
            on_track_changed=self._on_track_changed,
            on_playback_ended=self._on_playback_ended,
        )
        self._nfc = NFCManager(
            on_tag_placed=self._on_nfc_tag_placed,
            on_tag_removed=self._on_nfc_tag_removed,
        )
        self._leds = LEDController()
        self._voice = VoiceManager(
            on_wake_word=self._on_wake_word,
            on_voice_captured=self._on_voice_captured,
        )
        self._server = ServerClient(
            on_command=self._on_server_command,
            on_connection_change=self._on_connection_change,
        )
        self._parental = ParentalControls()

        # Apply parental volume cap
        self._audio.set_volume_cap(self._parental.volume_cap)

    # ── Public API ────────────────────────────────────────────────────

    def run(self) -> None:
        """Start all subsystems and block until shutdown."""
        logger.info("╔══════════════════════════════════════╗")
        logger.info("║       🎵 MikaBox Starting Up 🎵      ║")
        logger.info("╚══════════════════════════════════════╝")

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start subsystems
        self._leds.start()
        self._leds.set_pattern(LEDPattern.IDLE)

        self._nfc.start()
        self._server.start()
        self._voice.start()

        # Sync parental rules from server
        self._sync_parental_rules()

        logger.info("All subsystems started. Device is ready.")
        logger.info("State: %s | Server: %s",
                     self._state.value,
                     "connected" if self._server.is_connected else "offline")

        # Main loop — check inactivity + parental time limits
        self._main_loop()

    def shutdown(self) -> None:
        """Gracefully shut down all subsystems."""
        logger.info("Shutting down MikaBox...")
        self._shutdown_event.set()

        self._voice.shutdown()
        self._audio.shutdown()
        self._nfc.shutdown()
        self._leds.shutdown()
        self._server.shutdown()
        self._parental.shutdown()

        logger.info("MikaBox shut down complete. Goodbye! 👋")

    @property
    def state(self) -> DeviceState:
        return self._state

    def get_device_status(self) -> dict:
        """Get current device status for server reporting."""
        return {
            "device_id": config.device_id,
            "state": self._state.value,
            "server_connected": self._server.is_connected,
            "current_track": self._audio.current_track,
            "volume": self._audio.volume,
            "nfc_tag": self._nfc.current_tag,
            "profile_id": self._current_profile_id,
            "usage_today_minutes": self._parental.get_today_usage_minutes(),
            "remaining_minutes": self._parental.remaining_minutes,
        }

    # ── Main Loop ─────────────────────────────────────────────────────

    def _main_loop(self) -> None:
        """Main loop: monitors inactivity and parental time limits."""
        while not self._shutdown_event.is_set():
            # Check parental time limit
            if self._state == DeviceState.PLAYING:
                allowed, reason = self._parental.is_playback_allowed()
                if not allowed:
                    logger.info("Parental control: %s", reason)
                    self._audio.stop()
                    self._transition_to(DeviceState.IDLE)
                    # TODO: TTS announcement of the reason

            # Check inactivity timeout
            if self._state == DeviceState.IDLE:
                idle_time = time.monotonic() - self._last_activity_time
                if idle_time > config.inactivity_timeout:
                    self._transition_to(DeviceState.SLEEP)

            # Report state to server periodically
            if self._server.is_connected:
                self._server.send_state(self.get_device_status())

            self._shutdown_event.wait(timeout=5.0)

    # ── State Transitions ─────────────────────────────────────────────

    def _transition_to(self, new_state: DeviceState) -> None:
        with self._lock:
            old_state = self._state
            if old_state == new_state:
                return

            self._state = new_state
            self._last_activity_time = time.monotonic()

            # LED feedback
            led_map = {
                DeviceState.IDLE: LEDPattern.IDLE,
                DeviceState.PLAYING: LEDPattern.PLAYING,
                DeviceState.PAUSED: LEDPattern.PLAYING,
                DeviceState.LISTENING: LEDPattern.LISTENING,
                DeviceState.PROCESSING: LEDPattern.PROCESSING,
                DeviceState.SLEEP: LEDPattern.OFF,
            }
            self._leds.set_pattern(led_map.get(new_state, LEDPattern.IDLE))

            # Session tracking
            if old_state == DeviceState.PLAYING and new_state != DeviceState.PAUSED:
                self._parental.end_session()
            if new_state == DeviceState.PLAYING and old_state != DeviceState.PAUSED:
                self._parental.start_session()

            logger.info("State: %s → %s", old_state.value, new_state.value)

    # ── NFC Event Handlers ────────────────────────────────────────────

    def _on_nfc_tag_placed(self, tag_uid: str, content_id: Optional[str]) -> None:
        """Handle NFC sticker placed on the device."""
        self._last_activity_time = time.monotonic()

        if not content_id:
            logger.info("Unknown tag %s — no content mapped.", tag_uid)
            self._leds.set_pattern(LEDPattern.ERROR)
            threading.Timer(2.0, lambda: self._leds.set_pattern(
                LEDPattern.IDLE if self._state == DeviceState.IDLE else LEDPattern.PLAYING
            )).start()
            return

        # Check parental controls
        allowed, reason = self._parental.is_playback_allowed()
        if not allowed:
            logger.info("Playback blocked: %s", reason)
            return

        if not self._parental.is_content_allowed(content_id):
            logger.info("Content blocked by parental controls: %s", content_id)
            return

        # Find content and play
        if not self._play_content_with_download(content_id):
            logger.warning("Failed to play or download content locally: %s", content_id)
            self._leds.set_pattern(LEDPattern.ERROR)
            return

        self._transition_to(DeviceState.PLAYING)

        # Log usage
        self._server.send_usage_event({
            "event": "play_start",
            "content_id": content_id,
            "trigger": "nfc",
            "tag_uid": tag_uid,
            "profile_id": self._current_profile_id,
        })

    def _on_nfc_tag_removed(self, tag_uid: str) -> None:
        """Handle NFC sticker removed — pause playback."""
        if self._state in (DeviceState.PLAYING, DeviceState.PAUSED):
            self._audio.pause()
            self._transition_to(DeviceState.PAUSED)

    # ── Voice Event Handlers ──────────────────────────────────────────

    def _on_wake_word(self) -> None:
        """Handle wake word detection."""
        self._last_activity_time = time.monotonic()

        # Duck audio if playing
        if self._state == DeviceState.PLAYING:
            self._audio.duck_audio()

        self._transition_to(DeviceState.LISTENING)

    def _on_voice_captured(self, audio_bytes: Optional[bytes]) -> None:
        """Handle captured voice command — send to server for processing."""
        if not audio_bytes:
            # Aborted listening (e.g., child didn't speak during auto-listen)
            if self._audio.is_playing:
                self._transition_to(DeviceState.PLAYING)
            else:
                self._transition_to(DeviceState.IDLE)
            return

        self._transition_to(DeviceState.PROCESSING)

        # Send to server in background thread
        def process():
            result = self._server.send_voice_audio(
                audio_bytes, self._current_profile_id
            )
            self._audio.unduck_audio()

            if result:
                self._execute_ai_command(result)
            else:
                logger.warning("No response from server AI.")
                self._leds.set_pattern(LEDPattern.ERROR)
                time.sleep(1)
                # Return to previous state
                if self._audio.is_playing:
                    self._transition_to(DeviceState.PLAYING)
                else:
                    self._transition_to(DeviceState.IDLE)

        threading.Thread(target=process, name="voice-process", daemon=True).start()

    def _execute_ai_command(self, result: dict) -> None:
        """Execute a command returned by the AI service."""
        action = result.get("action", "none")
        message = result.get("message", "")
        expect_reply = result.get("expect_reply", False)
        language = result.get("language", "en")
        logger.info("AI command: %s — %s (expect_reply=%s, lang=%s)", action, message, expect_reply, language)

        # Speak the AI response aloud through the speaker (this blocks until done)
        if message:
            self._speak_response(message, language=language)

        if action == "play":
            content_id = result.get("content_id")
            if content_id and self._play_content_with_download(content_id):
                self._transition_to(DeviceState.PLAYING)
            else:
                self._transition_to(DeviceState.IDLE)

        elif action == "pause":
            self._audio.pause()
            self._transition_to(DeviceState.PAUSED)

        elif action == "resume":
            self._audio.resume()
            self._transition_to(DeviceState.PLAYING)

        elif action == "stop":
            self._audio.stop()
            self._transition_to(DeviceState.IDLE)

        elif action == "skip_forward":
            self._audio.skip_forward()

        elif action == "skip_back":
            self._audio.skip_back()

        elif action == "set_volume":
            level = result.get("level", self._audio.volume)
            self._audio.set_volume(level)

        elif action == "tell_story":
            if expect_reply:
                self._transition_to(DeviceState.LISTENING)
                self._voice.trigger_listening()
            else:
                self._transition_to(DeviceState.IDLE)

        elif action == "none":
            # Informational/conversational response
            if expect_reply:
                self._transition_to(DeviceState.LISTENING)
                self._voice.trigger_listening()
            else:
                if self._audio.is_playing:
                    self._transition_to(DeviceState.PLAYING)
                else:
                    self._transition_to(DeviceState.IDLE)

        else:
            logger.warning("Unknown AI action: %s", action)
            self._transition_to(DeviceState.IDLE)

    def _speak_response(self, text: str, language: str = "en") -> None:
        """Speak text aloud using edge-tts (natural Microsoft neural voice)."""
        import subprocess
        import tempfile
        import os

        # Clean text for speech (remove emojis, special chars)
        clean_text = text.encode("ascii", errors="ignore").decode("ascii").strip()
        if not clean_text:
            return

        logger.info("🔊 Speaking: '%s' (lang: %s)", clean_text[:80], language)
        
        # We use a single Multilingual neural voice so Mika sounds identical across all languages!
        # Emma is a friendly, young-sounding voice that supports auto-detecting language pronunciation.
        voice = "en-US-EmmaMultilingualNeural"

        # Try edge-tts (Microsoft neural voice — very natural)
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            # Make the file readable by everyone (in case PulseAudio daemon needs to read it directly)
            try:
                os.chmod(tmp_path, 0o644)
            except OSError:
                pass

            import sys
            # Find the edge-tts binary in the same directory as the current python executable (the virtualenv)
            edge_tts_bin = os.path.join(os.path.dirname(sys.executable), "edge-tts")

            # Generate speech with edge-tts CLI
            result = subprocess.run(
                [
                    edge_tts_bin,
                    "--voice", voice,
                    "--text", clean_text,
                    "--write-media", tmp_path,
                ],
                timeout=30,
                capture_output=True,
            )

            file_size = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
            logger.info("edge-tts generated %d bytes (exit %d)", file_size, result.returncode)

            if result.returncode == 0 and file_size > 1000:
                # Play using the existing AudioPlayer (which we know works with Bluetooth)
                logger.info("Playing TTS audio using AudioPlayer...")
                self._audio.play_file(Path(tmp_path), content_id="tts")

                import time
                # Wait for TTS to finish (AudioPlayer runs in a background thread)
                time.sleep(0.5)
                while self._audio.is_playing:
                    time.sleep(0.1)

                os.unlink(tmp_path)
                return

            os.unlink(tmp_path)

        except FileNotFoundError:
            logger.info("edge-tts not installed or not found. Run: pip install edge-tts")
        except Exception as exc:
            logger.warning("edge-tts failed: %s", exc)

        # Fallback: espeak (robotic but works)
        try:
            espeak_lang = language[:2] if language else "en"
            subprocess.run(
                ["espeak", "-v", f"{espeak_lang}+f3", "-s", "150", "-p", "70", clean_text],
                timeout=30, capture_output=True,
            )
        except FileNotFoundError:
            logger.warning("No TTS engine available. Install: pip install edge-tts")
        except Exception as exc:
            logger.error("TTS failed: %s", exc)

    def _play_wav(self, wav_path: str) -> None:
        """Play a WAV file through the speaker (Bluetooth-compatible)."""
        import subprocess
        import os

        # Make the temp file readable by the PulseAudio daemon (which runs as normal user, not root)
        try:
            os.chmod(wav_path, 0o644)
        except OSError as exc:
            logger.warning("Failed to chmod %s: %s", wav_path, exc)

        # Try paplay (PulseAudio) — works with Bluetooth speakers
        try:
            result = subprocess.run(
                ["paplay", wav_path],
                timeout=60,
                capture_output=True,
            )
            if result.returncode == 0:
                return
            logger.warning("paplay failed (code %d): %s", result.returncode, result.stderr.decode(errors="ignore").strip())
        except FileNotFoundError:
            pass

        # Try cvlc (VLC command line) — also works with PulseAudio
        try:
            result = subprocess.run(
                ["cvlc", "--play-and-exit", "--no-repeat", wav_path],
                timeout=60,
                capture_output=True,
            )
            if result.returncode == 0:
                return
            logger.warning("cvlc failed (code %d): %s", result.returncode, result.stderr.decode(errors="ignore").strip())
        except FileNotFoundError:
            pass

        # Fallback: aplay (ALSA only — won't reach Bluetooth)
        try:
            result = subprocess.run(
                ["aplay", wav_path],
                timeout=60,
                capture_output=True,
            )
            if result.returncode != 0:
                logger.warning("aplay failed (code %d): %s", result.returncode, result.stderr.decode(errors="ignore").strip())
        except FileNotFoundError:
            pass

    # ── Server Command Handlers ───────────────────────────────────────

    def _on_server_command(self, command: str, payload: dict) -> None:
        """Handle commands received from the companion app via server."""
        self._last_activity_time = time.monotonic()
        logger.info("Remote command: %s %s", command, payload)

        if command == "play":
            content_id = payload.get("content_id")
            if content_id:
                self._on_nfc_tag_placed("REMOTE", content_id)
        elif command == "pause":
            self._audio.pause()
            self._transition_to(DeviceState.PAUSED)
        elif command == "resume":
            self._audio.resume()
            self._transition_to(DeviceState.PLAYING)
        elif command == "stop":
            self._audio.stop()
            self._transition_to(DeviceState.IDLE)
        elif command == "skip_forward":
            self._audio.skip_forward()
        elif command == "skip_back":
            self._audio.skip_back()
        elif command == "set_volume":
            self._audio.set_volume(payload.get("level", 50))
        elif command == "update_rules":
            self._parental.update_rules(payload)
            self._audio.set_volume_cap(self._parental.volume_cap)
        elif command == "set_profile":
            self._current_profile_id = payload.get("profile_id", "default")

    def _on_connection_change(self, connected: bool) -> None:
        """Handle server connection status change."""
        status = "connected" if connected else "disconnected"
        logger.info("Server %s.", status)
        if connected:
            self._sync_parental_rules()

    # ── Audio Event Handlers ──────────────────────────────────────────

    def _on_track_changed(self, track_info: dict) -> None:
        logger.info("Track: %s (%d/%d)",
                     track_info.get("name", "?"),
                     track_info.get("index", 0) + 1,
                     track_info.get("total_tracks", 0))

    def _on_playback_ended(self) -> None:
        logger.info("Playback finished.")
        self._transition_to(DeviceState.IDLE)

    # ── Helpers ───────────────────────────────────────────────────────

    def _sync_parental_rules(self) -> None:
        """Fetch latest parental rules from server."""
        rules = self._server.fetch_parental_rules()
        if rules:
            self._parental.update_rules(rules)
            self._audio.set_volume_cap(self._parental.volume_cap)
            logger.info("Parental rules synced from server.")

    def _play_content_with_download(self, content_id: str) -> bool:
        """Play content, automatically downloading it from the server if missing."""
        content_path = config.content_dir / content_id
        
        # 1. Direct path check (could be a directory or exactly named file)
        if content_path.is_dir():
            self._audio.play_folder(content_path, content_id=content_id)
            return True
        if content_path.is_file():
            self._audio.play_file(content_path, content_id=content_id)
            return True
            
        # 2. Check for extensions (e.g. content_id.mp3)
        existing_files = list(config.content_dir.glob(f"{content_id}.*"))
        if existing_files:
            self._audio.play_file(existing_files[0], content_id=content_id)
            return True
            
        # 3. Not found — Download it!
        logger.info("Content %s not found locally. Downloading...", content_id)
        # Give visual feedback while downloading
        self._leds.set_pattern(LEDPattern.PROCESSING)
        
        dest_path = str(config.content_dir / f"{content_id}.mp3")
        if self._server.download_content(content_id, dest_path):
            self._audio.play_file(Path(dest_path), content_id=content_id)
            return True
            
        return False

    def _signal_handler(self, signum: int, frame: object) -> None:
        logger.info("Signal %d received — shutting down.", signum)
        self.shutdown()
