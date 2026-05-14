"""
MikaBox Voice Pipeline
======================

End-to-end voice processing on the home server:
1. Receive WAV audio from the Pi 4 device
2. Speech-to-Text (Gemma 4 native audio or Whisper fallback)
3. NLU via Gemma 4 tool-calling
4. Text-to-Speech for response (Piper TTS)
5. Return command result + optional TTS audio to device
"""

import io
import logging
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional

from .config import ai_config
from .engine import AIEngine, CommandResult

logger = logging.getLogger("mikabox.ai.pipeline")

# Optional: Whisper for STT fallback
try:
    import whisper  # type: ignore[import-untyped]

    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False

# Optional: Piper TTS
_PIPER_AVAILABLE = False
try:
    result = subprocess.run(["piper", "--version"], capture_output=True, timeout=5)
    _PIPER_AVAILABLE = result.returncode == 0
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass


class VoicePipeline:
    """
    Processes voice audio from the MikaBox device:
    WAV audio → Text (STT) → Command (NLU) → Response (TTS)
    """

    def __init__(self, ai_engine: AIEngine):
        self._engine = ai_engine
        self._whisper_model = None

        if _HAS_WHISPER:
            try:
                self._whisper_model = whisper.load_model("base")
                logger.info("Whisper STT model loaded.")
            except Exception as exc:
                logger.warning("Whisper model load failed: %s", exc)

        logger.info(
            "Voice pipeline ready (STT: %s, TTS: %s)",
            "whisper" if self._whisper_model else "simulation",
            "piper" if _PIPER_AVAILABLE else "simulation",
        )

    async def process_audio(
        self,
        audio_bytes: bytes,
        profile: dict,
        available_content: str = "",
        memory_facts: str = "",
    ) -> dict:
        """
        Full voice pipeline: audio → command → response.

        Uses Gemma 4 E2B's native audio input when available.
        Falls back to Whisper STT → text pipeline otherwise.

        Parameters
        ----------
        audio_bytes : bytes
            WAV-encoded audio from the device.
        profile : dict
            Child profile with 'name', 'age', 'id' keys.
        available_content : str
            Comma-separated list of available content titles.

        Returns
        -------
        dict with keys: action, content_id, level, minutes, message, tts_audio
        """
        child_name = profile.get("name", "buddy")
        age = profile.get("age", 5)

        # Check for simulation marker first
        sim_marker = b"__SIM_TEXT__"
        if sim_marker in audio_bytes:
            idx = audio_bytes.index(sim_marker)
            text = audio_bytes[idx + len(sim_marker):].decode("utf-8", errors="ignore")
            logger.info("Simulated STT: '%s'", text)
            result: CommandResult = self._engine.process_command(
                text=text,
                child_name=child_name,
                age=age,
                available_content=available_content,
                memory_facts=memory_facts,
            )
        elif self._engine._has_audio:
            # Native audio path — send WAV directly to Gemma 4 E2B
            logger.info("Using Gemma 4 native audio processing (%d bytes)", len(audio_bytes))
            audio_path = self._save_temp_wav(audio_bytes)
            try:
                result = self._engine.process_command(
                    text="",
                    child_name=child_name,
                    age=age,
                    available_content=available_content,
                    audio_path=audio_path,
                    memory_facts=memory_facts,
                )
            finally:
                # Clean up temp file
                import os
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass
        else:
            # Fallback: STT (Whisper) → text → Gemma 4
            text = self._speech_to_text(audio_bytes)
            if not text:
                return {
                    "action": "none",
                    "message": "I couldn't hear you. Could you say that again?",
                }
            logger.info("STT result: '%s'", text)
            result = self._engine.process_command(
                text=text,
                child_name=child_name,
                age=age,
                available_content=available_content,
                memory_facts=memory_facts,
            )

        # Text-to-Speech for the response message
        tts_audio = None
        lang_code = "en"
        if result.message:
            # Detect language of the LLM response to pick the right TTS voice
            try:
                from langdetect import detect
                lang_code = detect(result.message)
            except Exception as e:
                logger.warning("Language detection failed, defaulting to 'en': %s", e)
                
            tts_audio = self._text_to_speech(result.message)

        return {
            "action": result.action,
            "content_id": result.content_id,
            "level": result.level,
            "minutes": result.minutes,
            "message": result.message,
            "tts_audio": tts_audio,
            "expect_reply": getattr(result, "expect_reply", False),
            "searched_query": getattr(result, "searched_query", None),
            "safety_alert": getattr(result, "safety_alert", None),
            "remembered_fact": getattr(result, "remembered_fact", None),
            "language": lang_code,
        }

    # ── Audio File Helpers ─────────────────────────────────────────────

    def _save_temp_wav(self, audio_bytes: bytes) -> str:
        """Save audio bytes to a temporary WAV file for Gemma 4 processing."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(audio_bytes)
        tmp.flush()
        tmp.close()
        logger.debug("Saved temp audio: %s (%d bytes)", tmp.name, len(audio_bytes))
        return tmp.name

    # ── Speech-to-Text ────────────────────────────────────────────────

    def _speech_to_text(self, audio_bytes: bytes) -> Optional[str]:
        """Convert WAV audio to text."""
        # Check for simulation marker
        sim_marker = b"__SIM_TEXT__"
        if sim_marker in audio_bytes:
            idx = audio_bytes.index(sim_marker)
            text = audio_bytes[idx + len(sim_marker):].decode("utf-8", errors="ignore")
            logger.debug("Simulated STT: '%s'", text)
            return text

        # Whisper STT
        if self._whisper_model:
            return self._stt_whisper(audio_bytes)

        logger.warning("No STT engine available — returning None.")
        return None

    def _stt_whisper(self, audio_bytes: bytes) -> Optional[str]:
        """Run Whisper STT on audio bytes."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                result = self._whisper_model.transcribe(
                    tmp.name,
                    fp16=False,
                )
                text = result.get("text", "").strip()
                return text if text else None
        except Exception as exc:
            logger.error("Whisper STT failed: %s", exc)
            return None

    # ── Text-to-Speech ────────────────────────────────────────────────

    def _text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to WAV audio using Piper TTS."""
        if _PIPER_AVAILABLE:
            return self._tts_piper(text)

        # Fallback: return None (device will not play TTS)
        logger.debug("TTS not available — skipping audio response.")
        return None

    def _tts_piper(self, text: str) -> Optional[bytes]:
        """Generate speech using Piper TTS."""
        try:
            result = subprocess.run(
                [
                    "piper",
                    "--model", ai_config.tts_model,
                    "--output-raw",
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("Piper TTS error: %s", result.stderr.decode())
                return None

            # Wrap raw PCM in WAV header
            raw_audio = result.stdout
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(ai_config.tts_rate)
                wf.writeframes(raw_audio)
            return buf.getvalue()

        except Exception as exc:
            logger.error("Piper TTS failed: %s", exc)
            return None

    def shutdown(self) -> None:
        logger.info("VoicePipeline shut down.")
