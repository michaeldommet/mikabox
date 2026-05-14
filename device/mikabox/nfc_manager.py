"""
MikaBox NFC Manager
===================

Detects NFC stickers/cards via a PN532 reader on I2C or SPI,
maps tag UIDs to content IDs, and emits events on tag
placement and removal.

Hardware: PN532 NFC module connected to Raspberry Pi GPIO.
Install: ``pip install adafruit-circuitpython-pn532``
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, Callable

from .config import config
from .utils import load_json, save_json

logger = logging.getLogger("mikabox.nfc")

# PN532 is only available on Pi — graceful fallback for dev machines.
try:
    import board  # type: ignore[import-untyped]
    import busio  # type: ignore[import-untyped]
    from adafruit_pn532.i2c import PN532_I2C  # type: ignore[import-untyped]

    _HAS_NFC = True
except ImportError:
    _HAS_NFC = False
    logger.info("NFC hardware libraries not found — running in simulation mode.")


class NFCManager:
    """
    Manages NFC tag detection and content mapping.

    Events
    ------
    on_tag_placed(tag_uid: str, content_id: str | None)
        Fired when a new tag is detected on the reader.
    on_tag_removed(tag_uid: str)
        Fired when a previously detected tag is removed.
    """

    def __init__(
        self,
        on_tag_placed: Optional[Callable[[str, Optional[str]], None]] = None,
        on_tag_removed: Optional[Callable[[str], None]] = None,
    ):
        self._on_tag_placed = on_tag_placed
        self._on_tag_removed = on_tag_removed

        # Tag state
        self._current_tag: Optional[str] = None
        self._last_seen_time: float = 0.0
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None

        # Tag → content mapping
        self._tag_map: dict[str, dict] = load_json(config.tag_map_path, {})

        # Hardware
        self._pn532: Optional["PN532_I2C"] = None
        if _HAS_NFC:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self._pn532 = PN532_I2C(i2c, debug=False)
                ic, ver, rev, support = self._pn532.firmware_version
                logger.info("PN532 found — firmware v%d.%d (IC: 0x%02X)", ver, rev, ic)
                self._pn532.SAM_configuration()
            except Exception as exc:
                logger.error("Failed to initialize PN532: %s", exc)
                self._pn532 = None

    # ── Tag Map Management ────────────────────────────────────────────

    def register_tag(self, tag_uid: str, content_id: str, label: str = "") -> None:
        """Map a tag UID to a content ID."""
        self._tag_map[tag_uid] = {
            "content_id": content_id,
            "label": label,
        }
        save_json(config.tag_map_path, self._tag_map)
        logger.info("Registered tag %s → content '%s' (%s)", tag_uid, content_id, label)

    def unregister_tag(self, tag_uid: str) -> None:
        """Remove a tag mapping."""
        self._tag_map.pop(tag_uid, None)
        save_json(config.tag_map_path, self._tag_map)
        logger.info("Unregistered tag %s", tag_uid)

    def get_content_id(self, tag_uid: str) -> Optional[str]:
        """Look up the content ID for a tag UID."""
        entry = self._tag_map.get(tag_uid)
        return entry["content_id"] if entry else None

    def get_all_mappings(self) -> dict[str, dict]:
        """Return all tag → content mappings."""
        return dict(self._tag_map)

    # ── Polling Loop ──────────────────────────────────────────────────

    def start(self) -> None:
        """Start the NFC polling loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, name="nfc-poll", daemon=True
        )
        self._poll_thread.start()
        logger.info("NFC polling started (interval=%.1fs).", config.nfc_poll_interval)

    def stop(self) -> None:
        """Stop the NFC polling loop."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=3.0)
        logger.info("NFC polling stopped.")

    def _poll_loop(self) -> None:
        """Continuously poll for NFC tags."""
        while self._running:
            try:
                tag_uid = self._read_tag()

                if tag_uid:
                    self._last_seen_time = time.monotonic()

                    if tag_uid != self._current_tag:
                        # New tag placed
                        self._current_tag = tag_uid
                        content_id = self.get_content_id(tag_uid)
                        logger.info(
                            "Tag detected: %s → content: %s",
                            tag_uid,
                            content_id or "(unmapped)",
                        )
                        if self._on_tag_placed:
                            self._on_tag_placed(tag_uid, content_id)

                elif self._current_tag:
                    # Check for tag removal (no tag seen for removal_timeout)
                    elapsed = time.monotonic() - self._last_seen_time
                    if elapsed > config.nfc_removal_timeout:
                        removed_tag = self._current_tag
                        self._current_tag = None
                        logger.info("Tag removed: %s", removed_tag)
                        if self._on_tag_removed:
                            self._on_tag_removed(removed_tag)

            except Exception as exc:
                logger.error("NFC poll error: %s", exc)

            time.sleep(config.nfc_poll_interval)

    def _read_tag(self) -> Optional[str]:
        """Read a tag UID from the PN532, or None if no tag is present."""
        if self._pn532:
            uid = self._pn532.read_passive_target(timeout=0.3)
            if uid is not None:
                return self._uid_to_hex(uid)
            return None

        # Simulation mode — no hardware
        return None

    @staticmethod
    def _uid_to_hex(uid: bytes) -> str:
        """Convert raw UID bytes to a hex string (e.g., '04:A3:2B:C1')."""
        return ":".join(f"{b:02X}" for b in uid)

    # ── Simulation Helpers (for dev/testing) ──────────────────────────

    def simulate_tag_placed(self, tag_uid: str) -> None:
        """Simulate placing an NFC sticker (for dev/testing without hardware)."""
        self._current_tag = tag_uid
        self._last_seen_time = time.monotonic()
        content_id = self.get_content_id(tag_uid)
        logger.info("[SIM] Tag placed: %s → %s", tag_uid, content_id or "(unmapped)")
        if self._on_tag_placed:
            self._on_tag_placed(tag_uid, content_id)

    def simulate_tag_removed(self) -> None:
        """Simulate removing an NFC sticker."""
        if self._current_tag:
            removed = self._current_tag
            self._current_tag = None
            logger.info("[SIM] Tag removed: %s", removed)
            if self._on_tag_removed:
                self._on_tag_removed(removed)

    @property
    def current_tag(self) -> Optional[str]:
        return self._current_tag

    def shutdown(self) -> None:
        """Clean shutdown."""
        self.stop()
        logger.info("NFCManager shut down.")
