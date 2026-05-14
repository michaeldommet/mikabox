"""
MikaBox Voice Manager
=====================

Handles wake word detection, voice activity detection (VAD),
and audio capture for streaming to the home server's AI service.

The Pi 4 does NOT run Gemma 4 — it captures audio and sends it
to the server for STT + NLU processing.

Install: ``pip install pyaudio openwakeword``
"""

import io
import logging
import struct
import threading
import time
import wave
from typing import Callable, Optional

from .config import config

logger = logging.getLogger("mikabox.voice")

try:
    import pyaudio  # type: ignore[import-untyped]

    _HAS_AUDIO = True
except ImportError:
    _HAS_AUDIO = False
    logger.info("PyAudio not found — voice input will be simulated via terminal.")

try:
    from openwakeword.model import Model as WakeWordModel  # type: ignore[import-untyped]

    _HAS_WAKEWORD = True
except ImportError:
    _HAS_WAKEWORD = False
    logger.info("openWakeWord not found — wake word detection disabled.")


class VoiceManager:
    """
    Manages the voice input pipeline:

    1. **Always-on wake word detection** ("Hey Mika") — lightweight, low CPU.
    2. **VAD-based recording** — once wake word fires, record until silence.
    3. **Audio packaging** — produce a WAV byte buffer for server upload.

    The heavy lifting (STT + Gemma 4 NLU) happens on the home server.
    """

    def __init__(
        self,
        on_wake_word: Optional[Callable[[], None]] = None,
        on_voice_captured: Optional[Callable[[bytes], None]] = None,
    ):
        self._on_wake_word = on_wake_word
        self._on_voice_captured = on_voice_captured

        self._running = False
        self._listening_for_command = False
        self._listen_thread: Optional[threading.Thread] = None

        # PyAudio
        self._pa: Optional["pyaudio.PyAudio"] = None
        self._stream: Optional["pyaudio.Stream"] = None

        # Wake word model
        self._wakeword_model: Optional["WakeWordModel"] = None

        if _HAS_AUDIO:
            self._pa = pyaudio.PyAudio()

        if _HAS_WAKEWORD:
            try:
                # Use the bare constructor — openwakeword API changes
                # frequently between versions. No custom wake word yet;
                # the built-in models will be loaded automatically.
                self._wakeword_model = WakeWordModel()
                logger.info(
                    "Wake word models loaded: %s",
                    list(self._wakeword_model.models.keys()) if hasattr(self._wakeword_model, 'models') else "default",
                )
            except Exception as exc:
                logger.warning("Wake word model init failed: %s. Using fallback.", exc)
                self._wakeword_model = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the always-on wake word listening loop."""
        if self._running:
            return
        self._running = True
        self._listen_thread = threading.Thread(
            target=self._wake_word_loop, name="voice-wake", daemon=True
        )
        self._listen_thread.start()
        logger.info("Voice manager started (wake word: '%s').", config.wake_word)

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._listen_thread:
            self._listen_thread.join(timeout=3.0)
        logger.info("Voice manager stopped.")

    # ── Wake Word Loop ────────────────────────────────────────────────

    def _wake_word_loop(self) -> None:
        """
        Continuously listen for voice activity.

        Strategy:
        - If openwakeword has loaded models, use them.
        - Otherwise, use energy-based detection: when sustained loud
          speech is detected (RMS above threshold for several consecutive
          chunks), treat it as a wake trigger and record the command.
        """
        if not _HAS_AUDIO:
            self._terminal_fallback_loop()
            return

        # Find the right input device
        mic_index, mic_rate = self._find_input_device()
        if mic_index is None:
            logger.error("No input device found. Falling back to terminal.")
            self._terminal_fallback_loop()
            return

        try:
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=config.voice_channels,
                rate=mic_rate,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=config.voice_chunk_size,
            )
            # Store actual rate for WAV encoding
            self._actual_sample_rate = mic_rate
        except Exception as exc:
            logger.error("Failed to open audio stream: %s. Falling back to terminal.", exc)
            self._terminal_fallback_loop()
            return

        # Check if our configured wake word is in the loaded models.
        # openwakeword ships with 'alexa', 'hey_jarvis', etc. but NOT 'hey_mika'.
        # If our wake word isn't available, fall back to energy-based detection.
        use_energy_detection = True
        if self._wakeword_model and hasattr(self._wakeword_model, 'models'):
            loaded = list(self._wakeword_model.models.keys())
            wake_key = config.wake_word.replace(" ", "_")
            if wake_key in loaded:
                use_energy_detection = False
                logger.info("Listening for wake word '%s'...", config.wake_word)
            else:
                logger.info(
                    "Wake word '%s' not in loaded models %s — using energy-based voice trigger.",
                    config.wake_word, loaded,
                )
                # Disable the model so the detection loop uses energy path
                self._wakeword_model = None
        
        if use_energy_detection:
            logger.info("🎤 Speak near the mic to activate. Recording starts on sustained speech.")

        # Energy detection state
        SPEECH_THRESHOLD = 1200    # RMS level to consider as speech
        TRIGGER_CHUNKS = 3        # Consecutive loud chunks needed to trigger
        COOLDOWN_SECONDS = 3.0    # Minimum time between triggers
        loud_count = 0
        last_trigger_time = 0.0

        while self._running:
            try:
                # Check for manual trigger (e.g., continuous conversation)
                if getattr(self, "_force_trigger", False):
                    self._force_trigger = False
                    logger.info("Manual listening trigger activated.")
                    
                    # Clear out the current stream buffer so we don't catch the TTS tail
                    try:
                        while self._stream.get_read_available() > 0:
                            self._stream.read(self._stream.get_read_available(), exception_on_overflow=False)
                    except Exception:
                        pass
                        
                    self._handle_wake_word()
                    last_trigger_time = time.monotonic()
                    continue

                audio_chunk = self._stream.read(
                    config.voice_chunk_size, exception_on_overflow=False
                )

                if self._wakeword_model:
                    prediction = self._wakeword_model.predict(audio_chunk)
                    scores = list(prediction.values()) if isinstance(prediction, dict) else []
                    if any(s > config.wake_word_sensitivity for s in scores):
                        logger.info("Wake word detected!")
                        self._handle_wake_word()
                else:
                    # Energy-based voice trigger
                    rms = self._calculate_rms(audio_chunk)
                    # Log every 20th chunk to show the mic is alive
                    if not hasattr(self, '_dbg_count'):
                        self._dbg_count = 0
                    self._dbg_count += 1
                    if self._dbg_count % 20 == 0:
                        logger.debug("Audio chunk #%d — RMS: %.0f (threshold: %d, loud_streak: %d)",
                                     self._dbg_count, rms, SPEECH_THRESHOLD, loud_count)
                    if rms > SPEECH_THRESHOLD:
                        loud_count += 1
                        if loud_count == 1:  # Only log first loud chunk in a streak to avoid spam
                            logger.debug("Loud chunk! RMS=%.0f, streak=%d/%d", rms, loud_count, TRIGGER_CHUNKS)
                        if loud_count >= TRIGGER_CHUNKS:
                            now = time.monotonic()
                            if now - last_trigger_time > COOLDOWN_SECONDS:
                                logger.info("🎤 Voice detected! (RMS=%d, sustained %d chunks)", rms, loud_count)
                                last_trigger_time = now
                                loud_count = 0
                                self._handle_wake_word()
                            else:
                                loud_count = 0
                    else:
                        loud_count = 0

            except Exception as exc:
                logger.error("Audio read error: %s", exc)
                time.sleep(0.1)

    def trigger_listening(self) -> None:
        """Manually trigger the listening state (bypassing wake word/energy check)."""
        self._force_trigger = True

    def _terminal_fallback_loop(self) -> None:
        """Fallback for dev machines without a microphone."""
        logger.info("Terminal fallback mode — type 'hey mika' to activate.")
        while self._running:
            try:
                user_input = input("\n🎤 [MikaBox Voice] Type command (or 'hey mika'): ").strip()
                if not user_input:
                    continue

                if config.wake_word in user_input.lower():
                    logger.info("[SIM] Wake word detected!")
                    if self._on_wake_word:
                        self._on_wake_word()

                    # Get the actual command
                    command = user_input.lower().replace(config.wake_word, "").strip()
                    if not command:
                        command = input("🎤 [MikaBox Voice] Say your command: ").strip()

                    if command:
                        # Package as WAV (dummy for simulation)
                        wav_bytes = self._text_to_dummy_wav(command)
                        if self._on_voice_captured:
                            self._on_voice_captured(wav_bytes)
                else:
                    # Treat as direct command
                    wav_bytes = self._text_to_dummy_wav(user_input)
                    if self._on_voice_captured:
                        self._on_voice_captured(wav_bytes)

            except (EOFError, KeyboardInterrupt):
                break

    # ── Voice Command Capture ─────────────────────────────────────────

    def _handle_wake_word(self) -> None:
        """Handle wake word detection: notify + capture command audio."""
        if self._on_wake_word:
            self._on_wake_word()

        # Record until silence (VAD)
        audio_data = self._record_until_silence()
        if self._on_voice_captured:
            self._on_voice_captured(audio_data)

    def _record_until_silence(self) -> Optional[bytes]:
        """
        Record audio after wake word until silence is detected.
        Returns WAV-encoded bytes.
        """
        if not self._stream:
            return None

        logger.info("Recording voice command...")
        frames: list[bytes] = []
        silence_start: Optional[float] = None
        max_duration = 10.0  # Max recording length
        start_time = time.monotonic()
        has_spoken = False

        while self._running:
            elapsed = time.monotonic() - start_time
            if elapsed > max_duration:
                logger.warning("Max recording duration reached.")
                break

            audio_chunk = self._stream.read(
                config.voice_chunk_size, exception_on_overflow=False
            )
            frames.append(audio_chunk)

            rms = self._calculate_rms(audio_chunk)
            
            # 800 is a conservative threshold for "has started speaking"
            if rms > 800:
                has_spoken = True
                silence_start = None
            elif rms < 500:  # Silence threshold
                if silence_start is None:
                    silence_start = time.monotonic()
                elif time.monotonic() - silence_start > config.vad_silence_duration:
                    if not has_spoken and elapsed < 4.0:
                        # Give the child up to 4 seconds to start speaking
                        continue
                    elif not has_spoken:
                        logger.info("No speech detected — aborting recording.")
                        return None
                        
                    logger.info("Silence detected — recording stopped (%.1fs).", elapsed)
                    break
            else:
                silence_start = None

        if not frames:
            return None

        return self._frames_to_wav(frames)

    def _find_input_device(self) -> tuple:
        """
        Enumerate all PyAudio input devices, log them, and pick the best one.
        Prefers USB devices over built-in ones.

        Returns (device_index, sample_rate) or (None, None).
        """
        if not self._pa:
            return None, None

        device_count = self._pa.get_device_count()
        logger.info("--- Available audio devices (%d) ---", device_count)

        usb_device = None
        any_input = None

        for i in range(device_count):
            try:
                info = self._pa.get_device_info_by_index(i)
            except Exception:
                continue

            name = info.get("name", "Unknown")
            max_in = info.get("maxInputChannels", 0)
            rate = int(info.get("defaultSampleRate", 16000))

            if max_in > 0:
                logger.info("  [%d] INPUT: '%s' (channels=%d, rate=%d)", i, name, max_in, rate)
                if any_input is None:
                    any_input = (i, rate)
                # Prefer USB devices
                name_lower = name.lower()
                if "usb" in name_lower or "mic" in name_lower:
                    usb_device = (i, rate)
                    logger.info("       ^^^ Selected as USB mic")

        if usb_device:
            idx, rate = usb_device
            logger.info("Using USB mic: device %d at %d Hz", idx, rate)
            return idx, rate
        elif any_input:
            idx, rate = any_input
            logger.info("Using input device: device %d at %d Hz", idx, rate)
            return idx, rate
        else:
            logger.error("No input devices found!")
            return None, None

    # ── Audio Utilities ───────────────────────────────────────────────

    @staticmethod
    def _calculate_rms(audio_chunk: bytes) -> float:
        """Calculate root-mean-square energy of a PCM16 audio chunk."""
        count = len(audio_chunk) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"<{count}h", audio_chunk)
        sum_sq = sum(s * s for s in shorts)
        return (sum_sq / count) ** 0.5

    def _frames_to_wav(self, frames: list[bytes]) -> bytes:
        """Package raw PCM frames into a WAV byte buffer."""
        rate = getattr(self, '_actual_sample_rate', config.voice_sample_rate)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(config.voice_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    @staticmethod
    def _text_to_dummy_wav(text: str) -> bytes:
        """
        Create a minimal WAV with the text embedded as metadata.
        Used for simulation mode — the server will extract the text.
        """
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            # Write a tiny amount of silence
            wf.writeframes(b"\x00\x00" * 1600)
        # Append text marker for simulation
        result = buf.getvalue()
        # In sim mode, the server checks for this marker
        return result + b"__SIM_TEXT__" + text.encode("utf-8")

    def shutdown(self) -> None:
        self.stop()
        # Give the audio stream a moment to fully close before
        # terminating PyAudio — prevents PulseAudio assertion crash.
        import time
        time.sleep(0.3)
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass  # Suppress PulseAudio teardown errors
        logger.info("VoiceManager shut down.")
