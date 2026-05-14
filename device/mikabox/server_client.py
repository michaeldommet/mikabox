"""
MikaBox Server Client
=====================

WiFi communication between the Pi 4 device and the home server.
Handles WebSocket state sync, HTTP content downloads, and voice
audio streaming to the AI service.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Optional

from .config import config

logger = logging.getLogger("mikabox.server")

try:
    import websockets  # type: ignore[import-untyped]
    import aiohttp      # type: ignore[import-untyped]

    _HAS_WS = True
except ImportError:
    _HAS_WS = False
    logger.warning("websockets/aiohttp not found — server communication disabled.")

try:
    import requests  # type: ignore[import-untyped]

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


class ServerClient:
    """
    Manages the WiFi link between the MikaBox device and the home server.

    Responsibilities
    ----------------
    - WebSocket: real-time state sync (now playing, volume, battery, etc.)
    - HTTP: content downloads, settings sync, voice audio upload
    - Auto-reconnect with exponential backoff
    - Offline detection for fallback mode
    """

    def __init__(
        self,
        on_command: Optional[Callable[[str, dict], None]] = None,
        on_connection_change: Optional[Callable[[bool], None]] = None,
    ):
        self._on_command = on_command
        self._on_connection_change = on_connection_change

        self._connected = False
        self._running = False
        self._ws_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._reconnect_delay = config.server_reconnect_delay

    # ── Connection Lifecycle ──────────────────────────────────────────

    def start(self) -> None:
        """Start the WebSocket connection in a background thread."""
        if self._running:
            return
        self._running = True
        self._ws_thread = threading.Thread(
            target=self._run_event_loop, name="server-ws", daemon=True
        )
        self._ws_thread.start()
        logger.info("Server client started (target: %s).", config.server_ws_url)

    def stop(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._ws_thread:
            self._ws_thread.join(timeout=5.0)
        logger.info("Server client stopped.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── WebSocket Event Loop ──────────────────────────────────────────

    def _run_event_loop(self) -> None:
        """Run the async WebSocket loop in a dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._ws_connect_loop())

    async def _ws_connect_loop(self) -> None:
        """Connect to the server with exponential backoff on failure."""
        while self._running:
            try:
                if not _HAS_WS:
                    logger.info("[SIM] Server connection simulated.")
                    self._set_connected(True)
                    while self._running:
                        await asyncio.sleep(1)
                    return

                async with websockets.connect(
                    f"{config.server_ws_url}?device_id={config.device_id}",
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._set_connected(True)
                    self._reconnect_delay = config.server_reconnect_delay
                    logger.info("Connected to server.")

                    async for raw_message in ws:
                        try:
                            msg = json.loads(raw_message)
                            cmd = msg.get("command", "")
                            payload = msg.get("payload", {})
                            logger.debug("Server → device: %s %s", cmd, payload)
                            if self._on_command:
                                self._on_command(cmd, payload)
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON from server: %s", raw_message[:100])

            except Exception as exc:
                self._set_connected(False)
                logger.warning(
                    "Server connection lost: %s. Retrying in %.0fs...",
                    exc, self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    config.server_reconnect_max_delay,
                )

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            if self._on_connection_change:
                self._on_connection_change(connected)

    # ── HTTP API Calls ────────────────────────────────────────────────

    def send_state(self, state: dict) -> bool:
        """Send device state to the server via HTTP POST."""
        return self._post("/api/devices/state", state)

    def send_usage_event(self, event: dict) -> bool:
        """Log a usage event on the server."""
        return self._post("/api/usage/log", event)

    def send_voice_audio(self, audio_bytes: bytes, profile_id: str) -> Optional[dict]:
        """
        Send captured voice audio to the server's AI service for processing.

        Returns the parsed command result from Gemma 4, or None on failure.
        """
        if not _HAS_REQUESTS:
            logger.warning("[SIM] Voice audio send simulated.")
            return {"action": "none", "message": "Simulated response."}

        try:
            resp = requests.post(
                f"{config.server_http_url}/api/voice/process",
                files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
                data={"device_id": config.device_id, "profile_id": profile_id},
                timeout=config.server_timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("Voice audio send failed: %s", exc)
            return None

    def fetch_parental_rules(self) -> Optional[dict]:
        """Fetch the latest parental control rules from the server."""
        return self._get("/api/controls/rules")

    def fetch_content_catalog(self) -> Optional[list]:
        """Fetch the content catalog from the server."""
        return self._get("/api/content/catalog")

    def download_content(self, content_id: str, dest: str) -> bool:
        """Download an audio file from the server to local storage."""
        if not _HAS_REQUESTS:
            logger.warning("[SIM] Content download simulated: %s", content_id)
            return False

        try:
            resp = requests.get(
                f"{config.server_http_url}/api/content/{content_id}/download",
                stream=True,
                timeout=60,
            )
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Downloaded content %s → %s", content_id, dest)
            return True
        except Exception as exc:
            logger.error("Content download failed: %s", exc)
            return False

    # ── HTTP Helpers ──────────────────────────────────────────────────

    def _post(self, path: str, data: Any) -> bool:
        if not _HAS_REQUESTS:
            return False
        try:
            resp = requests.post(
                f"{config.server_http_url}{path}",
                json=data,
                timeout=config.server_timeout,
            )
            return resp.ok
        except Exception as exc:
            logger.debug("POST %s failed: %s", path, exc)
            return False

    def _get(self, path: str) -> Optional[Any]:
        if not _HAS_REQUESTS:
            return None
        try:
            resp = requests.get(
                f"{config.server_http_url}{path}",
                timeout=config.server_timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.debug("GET %s failed: %s", path, exc)
            return None

    def shutdown(self) -> None:
        self.stop()
        logger.info("ServerClient shut down.")
