"""
MikaBox Utilities
=================

Shared helpers for the device firmware.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("mikabox")


def load_json(path: Path, default: Any = None) -> Any:
    """Load a JSON file, returning `default` if it doesn't exist or is invalid."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load %s: %s", path, exc)
    return default if default is not None else {}


def save_json(path: Path, data: Any) -> None:
    """Atomically save data as JSON (write to tmp then rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.rename(path)
    except OSError as exc:
        logger.error("Failed to save %s: %s", path, exc)
        if tmp.exists():
            tmp.unlink()


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration (e.g., '1h 23m')."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining = minutes % 60
    return f"{hours}h {remaining}m" if remaining else f"{hours}h"


class RateLimiter:
    """Simple token-bucket rate limiter for event flooding prevention."""

    def __init__(self, max_events: int, window_seconds: float):
        self._max = max_events
        self._window = window_seconds
        self._events: list[float] = []

    def allow(self) -> bool:
        now = time.monotonic()
        self._events = [t for t in self._events if now - t < self._window]
        if len(self._events) < self._max:
            self._events.append(now)
            return True
        return False
