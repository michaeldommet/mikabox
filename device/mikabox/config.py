"""
MikaBox Device Configuration
=============================

All tunable constants for the MikaBox device firmware.
Override via environment variables or a local `.env` file.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeviceConfig:
    """Immutable device configuration."""

    # ── Identity ──────────────────────────────────────────────────────
    device_name: str = "MikaBox"
    device_id: str = field(default_factory=lambda: os.getenv("MIKABOX_DEVICE_ID", "mikabox-001"))

    # ── Home Server Connection ────────────────────────────────────────
    server_host: str = field(default_factory=lambda: os.getenv("MIKABOX_SERVER_HOST", "192.168.1.100"))
    server_port: int = field(default_factory=lambda: int(os.getenv("MIKABOX_SERVER_PORT", "8000")))
    server_ws_path: str = "/ws/device"
    server_reconnect_delay: float = 2.0        # seconds, initial backoff
    server_reconnect_max_delay: float = 30.0   # seconds, max backoff
    server_timeout: float = 60.0               # seconds, HTTP request timeout

    # ── Audio ─────────────────────────────────────────────────────────
    audio_device: str = field(default_factory=lambda: os.getenv("MIKABOX_AUDIO_DEVICE", "default"))
    default_volume: int = 50                    # 0-100
    max_volume: int = 80                        # parental cap, overridden by server
    content_dir: Path = field(default_factory=lambda: Path(os.getenv(
        "MIKABOX_CONTENT_DIR", str(Path.home() / "mikabox" / "content")
    )))
    supported_formats: tuple = (".mp3", ".flac", ".ogg", ".m4a", ".wav")
    resume_positions_file: str = "resume_positions.json"

    # ── NFC Reader (PN532) ────────────────────────────────────────────
    nfc_interface: str = field(default_factory=lambda: os.getenv("MIKABOX_NFC_INTERFACE", "i2c"))  # "i2c" or "spi"
    nfc_i2c_bus: int = 1
    nfc_poll_interval: float = 0.5              # seconds between tag polls
    nfc_tag_map_file: str = "tag_map.json"
    nfc_removal_timeout: float = 2.0            # seconds before "tag removed" fires

    # ── Wake Word / Voice ─────────────────────────────────────────────
    wake_word: str = "hey mika"
    wake_word_sensitivity: float = 0.5          # 0.0 to 1.0
    vad_silence_duration: float = 1.5           # seconds of silence to end recording
    voice_sample_rate: int = 16000
    voice_channels: int = 1
    voice_chunk_size: int = 1024

    # ── LED Ring (NeoPixel / WS2812B) ─────────────────────────────────
    led_pin: int = 18                           # GPIO pin (BCM numbering)
    led_count: int = 16                         # number of LEDs in ring
    led_brightness: float = 0.3                 # 0.0 to 1.0

    # ── Parental Controls (defaults, overridden by server) ────────────
    daily_time_limit_minutes: int = 120         # 2 hours default
    bedtime_start: str = "20:00"                # 8 PM
    bedtime_end: str = "07:00"                  # 7 AM
    volume_cap: int = 80                        # same as max_volume initially

    # ── Power / System ────────────────────────────────────────────────
    inactivity_timeout: int = 300               # seconds before sleep (5 min)
    log_level: str = field(default_factory=lambda: os.getenv("MIKABOX_LOG_LEVEL", "INFO"))

    @property
    def server_http_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}"

    @property
    def server_ws_url(self) -> str:
        return f"ws://{self.server_host}:{self.server_port}{self.server_ws_path}"

    @property
    def tag_map_path(self) -> Path:
        return self.content_dir / self.nfc_tag_map_file

    @property
    def resume_positions_path(self) -> Path:
        return self.content_dir / self.resume_positions_file


# Global singleton
config = DeviceConfig()
