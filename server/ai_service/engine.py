"""
MikaBox AI Engine
=================

Gemma 4 E2B inference via LiteRT-LM on the home server.
Processes voice commands using tool-calling for device control.

This runs on your desktop/laptop/NAS — NOT on the Pi 4.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Literal
from duckduckgo_search import DDGS

from .config import ai_config

logger = logging.getLogger("mikabox.ai.engine")

# LiteRT-LM is the production runtime — fallback to simulation for dev
try:
    from litert_lm import Engine as LiteRtLmEngine  # type: ignore[import-untyped]

    _HAS_LITERT = True
except ImportError:
    _HAS_LITERT = False
    logger.info("LiteRT-LM not found — AI engine will run in simulation mode.")


@dataclass
class CommandResult:
    """Result of processing a voice command."""
    action: str          # play, pause, resume, stop, skip_forward, skip_back,
                         # set_volume, set_timer, tell_story, none
    content_id: Optional[str] = None
    level: Optional[int] = None
    minutes: Optional[int] = None
    message: str = ""
    tts_audio: Optional[bytes] = None  # Pre-rendered TTS response
    expect_reply: bool = False         # True if the device should listen immediately after speaking
    searched_query: Optional[str] = None  # Query used for web search
    safety_alert: Optional[str] = None    # Reason for safety alert
    remembered_fact: Optional[str] = None # Fact learned about the child


class AIEngine:
    """
    Gemma 4 E2B inference engine using the stateless per-request pattern.

    Each voice command gets a fresh conversation context.
    KV cache is freed after every request to prevent memory accumulation.
    """

    def __init__(self):
        self._engine = None
        self._has_audio = False
        self._history: list[dict] = []  # Maintain conversation context
        if _HAS_LITERT:
            try:
                import litert_lm
                # Enable native audio processing in Gemma 4 E2B
                self._engine = LiteRtLmEngine(
                    model_path=ai_config.model_path,
                    audio_backend=litert_lm.Backend.CPU,
                )
                self._has_audio = True
                logger.info("Gemma 4 E2B loaded from %s (with native audio)", ai_config.model_path)
            except Exception:
                # Fallback: try without audio backend
                try:
                    self._engine = LiteRtLmEngine(
                        model_path=ai_config.model_path,
                    )
                    logger.info("Gemma 4 E2B loaded from %s (text only)", ai_config.model_path)
                except Exception as exc:
                    logger.error("Failed to load Gemma 4: %s", exc)
        self._last_tool_result: Optional[dict] = None
        self._last_search_query: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        return self._engine is not None or not _HAS_LITERT

    # ── Tool Definitions ──────────────────────────────────────────────

    def play_content(self, content_id: str) -> dict:
        """Play a specific audiobook or music track.

        Args:
            content_id: The unique identifier of the content to play.

        Returns:
            Confirmation of the play command.
        """
        # LiteRT-LM sometimes passes string arguments wrapped in <|"|> tags
        clean_id = content_id.replace('<|"|>', '').replace('<|', '').replace('|>', '').strip()
        result = {"action": "play", "content_id": clean_id}
        self._last_tool_result = result
        return result

    def control_playback(self, action: Literal["pause", "resume", "stop", "skip_forward", "skip_back"]) -> dict:
        """Control audio playback.

        Args:
            action: One of 'pause', 'resume', 'stop', 'skip_forward', 'skip_back'.

        Returns:
            Confirmation of the playback control command.
        """
        result = {"action": action}
        self._last_tool_result = result
        return result

    def set_volume(self, level: int) -> dict:
        """Set the speaker volume.

        Args:
            level: Volume level from 0 (silent) to 100 (maximum).

        Returns:
            Confirmation of the volume change.
        """
        result = {"action": "set_volume", "level": max(0, min(100, level))}
        self._last_tool_result = result
        return result

    def set_timer(self, minutes: int) -> dict:
        """Set a sleep timer that will pause playback after the given minutes.

        Args:
            minutes: Number of minutes before auto-pause.

        Returns:
            Confirmation of the timer.
        """
        result = {"action": "set_timer", "minutes": max(1, min(120, minutes))}
        self._last_tool_result = result
        return result

    def search_web(self, query: str) -> str:
        """Search the internet for safe, up-to-date information.

        Args:
            query: The search query to look up on the web.

        Returns:
            Concatenated text snippets from the top search results.
        """
        # LiteRT-LM sometimes passes string arguments wrapped in <|"|> tags
        clean_query = query.replace('<|"|>', '').replace('<|', '').replace('|>', '').strip()
        
        logger.info("Executing web search for: %s", clean_query)
        self._last_search_query = clean_query
        try:
            with DDGS() as ddgs:
                results = ddgs.text(clean_query, max_results=3, safesearch="moderate")
            
            if not results:
                return "I couldn't find any information about that."
                
            snippets = []
            for i, res in enumerate(results):
                snippets.append(f"Source {i+1}: {res.get('body', '')}")
            
            return "\n\n".join(snippets)
        except Exception as e:
            logger.error("Web search failed: %s", e)
            return "Sorry, I had trouble searching the web right now."

    def trigger_safety_alert(self, reason: str) -> dict:
        """Trigger an emergency alert to the parents' dashboard if the child is in danger.

        Args:
            reason: A short description of the dangerous behavior.

        Returns:
            Confirmation of the alert.
        """
        logger.warning("SAFETY ALERT TRIGGERED: %s", reason)
        result = {"action": "none", "safety_alert": reason}
        self._last_tool_result = result
        return result

    def remember_fact(self, fact: str) -> dict:
        """Save a personal fact about the child to persistent memory.

        Args:
            fact: The fact to remember (e.g. "Favorite color is blue").

        Returns:
            Confirmation.
        """
        logger.info("Remembering fact: %s", fact)
        result = {"action": "none", "remembered_fact": fact}
        self._last_tool_result = result
        return result

    def get_weather(self, location: str) -> str:
        """Get the current weather for a specific city or location.

        Args:
            location: The name of the city or location (e.g. 'Berlin', 'New York').

        Returns:
            The current weather conditions.
        """
        import urllib.request
        import urllib.parse
        
        # Clean the location string just in case
        clean_location = location.replace('<|"|>', '').replace('<|', '').replace('|>', '').strip()
        logger.info("Executing weather search for: %s", clean_location)
        
        # Log this as a search query so it shows up in Parental Controls
        self._last_search_query = f"Weather in {clean_location}"
        
        try:
            url = f"https://wttr.in/{urllib.parse.quote(clean_location)}?format=%l:+%C+%t+(feels+like+%f).+Wind:+%w.+Humidity:+%h"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.read().decode('utf-8').strip()
        except Exception as e:
            logger.error("Weather search failed: %s", e)
            return "Sorry, I couldn't check the weather right now."

    # ── Inference ─────────────────────────────────────────────────────

    def process_command(
        self,
        text: str,
        child_name: str = "buddy",
        age: int = 5,
        available_content: str = "",
        audio_path: str | None = None,
        memory_facts: str = "",
    ) -> CommandResult:
        """
        Process a voice command through Gemma 4.

        Can accept either text or an audio file path.
        Uses stateless per-request pattern: fresh context → infer → free KV cache.
        """
        logger.info("Processing command: text='%s', audio=%s (child=%s, age=%d)",
                    text or '(from audio)', bool(audio_path), child_name, age)

        from datetime import datetime
        current_time = datetime.now().strftime("%I:%M %p")

        system_prompt = ai_config.system_prompt.format(
            child_name=child_name,
            age=age,
            current_time=current_time,
            available_content=available_content or "various audiobooks and music",
            memory_facts=memory_facts or "None yet.",
        )

        if self._engine:
            return self._inference_litert(text, system_prompt, audio_path=audio_path)
        else:
            return self._inference_simulated(text or '', available_content=available_content)

    def _inference_litert(self, text: str, system_prompt: str, audio_path: str | None = None) -> CommandResult:
        """Run inference with LiteRT-LM (production path)."""
        tools = [
            self.play_content,
            self.control_playback,
            self.set_volume,
            self.set_timer,
            self.search_web,
            self.get_weather,
            self.trigger_safety_alert,
            self.remember_fact,
        ]

        try:
            # Build conversation with history
            messages = [{"role": "system", "content": system_prompt}] + self._history
            
            with self._engine.create_conversation(
                messages=messages,
                tools=tools,
            ) as ctx:
                self._last_tool_result = None
                self._last_search_query = None
                
                # If we have audio and the engine supports it, send audio directly
                if audio_path and self._has_audio:
                    message = {
                        "role": "user",
                        "content": [
                            {"type": "audio", "path": audio_path},
                            {"type": "text", "text": text or "What did the user say? Process their voice command."},
                        ],
                    }
                    logger.info("Sending audio directly to Gemma 4 E2B...")
                    response = ctx.send_message(message)
                    # We store just the text transcript in history
                    self._history.append({"role": "user", "content": text or "(audio command)"})
                else:
                    response = ctx.send_message(text)
                    self._history.append({"role": "user", "content": text})

            # Append the assistant's text response to history
            resp_text = self._extract_text(response)
            if resp_text:
                self._history.append({"role": "assistant", "content": resp_text})
            
            # Keep history capped at 10 turns (20 messages)
            if len(self._history) > 20:
                self._history = self._history[-20:]

            return self._parse_response(response)

        except Exception as exc:
            logger.error("LiteRT-LM inference failed: %s", exc)
            return CommandResult(action="none", message="Sorry, I didn't understand that.")

    def _inference_simulated(self, text: str, available_content: str = "") -> CommandResult:
        """Simulated inference for development without Gemma 4."""
        text_lower = text.lower()

        # Simple keyword matching for simulation
        if any(w in text_lower for w in ["play", "listen to", "put on"]):
            # Try to extract content reference
            return CommandResult(
                action="play",
                message=f"Playing what you asked for!",
                content_id=self._extract_content_ref(text_lower, available_content),
            )
        elif "pause" in text_lower:
            return CommandResult(action="pause", message="Paused!")
        elif "resume" in text_lower or "continue" in text_lower:
            return CommandResult(action="resume", message="Resuming!")
        elif "stop" in text_lower:
            return CommandResult(action="stop", message="Stopped!")
        elif "skip" in text_lower and "back" in text_lower:
            return CommandResult(action="skip_back", message="Going back!")
        elif "skip" in text_lower or "next" in text_lower:
            return CommandResult(action="skip_forward", message="Skipping!")
        elif "volume" in text_lower:
            if "up" in text_lower or "louder" in text_lower:
                return CommandResult(action="set_volume", level=70, message="Turning it up!")
            elif "down" in text_lower or "quieter" in text_lower:
                return CommandResult(action="set_volume", level=30, message="Turning it down!")
        elif "timer" in text_lower or "sleep" in text_lower:
            return CommandResult(action="set_timer", minutes=30, message="Sleep timer set for 30 minutes!")

        return CommandResult(action="none", message="I'm here! How can I help?", expect_reply=True)

    def _parse_response(self, response: Any) -> CommandResult:
        """Parse a LiteRT-LM response into a CommandResult."""
        logger.debug("Raw response type=%s: %s", type(response).__name__, response)

        # Extract text from various response formats
        text = self._extract_text(response)

        # Check if a tool was executed during this turn
        if self._last_tool_result:
            result = self._last_tool_result
            action = result.get("action", "none")
            
            # Clear history if taking a non-conversational action
            if action in ["play", "pause", "resume", "stop", "skip_forward", "skip_back", "set_volume", "set_timer"]:
                self._history.clear()
                text = ""  # Suppress the LLM's internal monologue for control actions
                
            self._last_tool_result = None
            return CommandResult(
                action=action,
                content_id=result.get("content_id"),
                level=result.get("level"),
                minutes=result.get("minutes"),
                message=text,
                expect_reply=False,
                searched_query=self._last_search_query,
                safety_alert=result.get("safety_alert"),
                remembered_fact=result.get("remembered_fact"),
            )

        # Handle tool call responses directly (if litert_lm didn't consume them)
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_call = response.tool_calls[0]
            result = tool_call.result
            if isinstance(result, dict):
                action = result.get("action", "none")
                
                # Clear history if taking a non-conversational action
                if action in ["play_content", "control_playback", "set_volume", "set_timer"]:
                    self._history.clear()
                    text = ""  # Suppress the LLM's internal monologue for control actions
                    
                return CommandResult(
                    action=action,
                    content_id=result.get("content_id"),
                    level=result.get("level"),
                    minutes=result.get("minutes"),
                    message=text,
                    expect_reply=False,
                    searched_query=self._last_search_query,
                    safety_alert=result.get("safety_alert"),
                    remembered_fact=result.get("remembered_fact"),
                )

        # Plain text response (conversational)
        return CommandResult(
            action="none", 
            message=text, 
            expect_reply=True,
            searched_query=self._last_search_query,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract clean text from a LiteRT-LM response object."""
        # Dict format: {'content': [{'text': '...', 'type': 'text'}], 'role': 'assistant'}
        if isinstance(response, dict):
            content = response.get("content", [])
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                if parts:
                    return " ".join(parts).strip()
            # Simple {'text': '...'} format
            if "text" in response:
                return str(response["text"])
            return str(response)

        # Object with .text attribute
        if hasattr(response, "text"):
            return str(response.text)

        # Object with .content attribute (list of parts)
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif hasattr(item, "text"):
                        parts.append(str(item.text))
                if parts:
                    return " ".join(parts).strip()

        # Fallback
        return str(response)

    @staticmethod
    def _extract_content_ref(text: str, available_content: str = "") -> Optional[str]:
        """Extract a content reference from natural language (best effort)."""
        import re
        # Try to match from available_content dynamically first
        if available_content:
            matches = re.findall(r"'([^']+)' \(ID: ([^)]+)\)", available_content)
            for title, c_id in matches:
                # Basic string inclusion matching
                if title.lower() in text:
                    return c_id

        # In production, Gemma 4 handles this via tool calling.
        # This is a rough simulation fallback.
        for word in ["jungle book", "little prince", "peter pan"]:
            if word in text:
                return word.replace(" ", "_")
        return None

    def shutdown(self) -> None:
        if self._engine:
            del self._engine
        logger.info("AIEngine shut down.")
