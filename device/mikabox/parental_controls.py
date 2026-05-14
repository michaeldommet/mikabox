"""
MikaBox Parental Controls
=========================

Local enforcement of parental rules on the device.
Rules are synced from the server but enforced locally so
the device works even when offline.
"""

import logging
import time
from datetime import datetime, time as dtime
from typing import Optional

from .config import config
from .utils import load_json, save_json

logger = logging.getLogger("mikabox.parental")

_RULES_FILE = "parental_rules.json"


class ParentalControls:
    """
    Enforces parental control rules on the device.

    Rules
    -----
    - Daily listening time limit (per profile).
    - Bedtime / quiet hours schedule.
    - Maximum volume cap.
    - Content allowlist / blocklist.
    """

    def __init__(self):
        self._rules: dict = {
            "daily_limit_minutes": config.daily_time_limit_minutes,
            "bedtime_start": config.bedtime_start,
            "bedtime_end": config.bedtime_end,
            "volume_cap": config.volume_cap,
            "blocked_content_ids": [],
            "allowed_categories": [],   # empty = allow all
        }

        # Usage tracking for today
        self._today_key: str = ""
        self._usage_seconds: float = 0.0
        self._session_start: Optional[float] = None

        # Load persisted rules and usage
        rules_path = config.content_dir / _RULES_FILE
        saved = load_json(rules_path, {})
        if saved.get("rules"):
            self._rules.update(saved["rules"])

        self._usage_data: dict = load_json(
            config.content_dir / "daily_usage.json", {}
        )
        self._refresh_today()

    # ── Rule Queries ──────────────────────────────────────────────────

    def is_playback_allowed(self) -> tuple[bool, str]:
        """
        Check whether playback is currently allowed.

        Returns (allowed: bool, reason: str).
        """
        # Check bedtime
        if self._is_bedtime():
            return False, "It's bedtime! Time to rest. 🌙"

        # Check daily time limit
        self._refresh_today()
        limit = self._rules["daily_limit_minutes"] * 60
        if self._usage_seconds >= limit:
            return False, "You've reached your listening limit for today! 🎧"

        return True, ""

    def is_content_allowed(self, content_id: str, category: str = "") -> bool:
        """Check if a specific content item is allowed."""
        blocked = self._rules.get("blocked_content_ids", [])
        if content_id in blocked:
            return False

        allowed_cats = self._rules.get("allowed_categories", [])
        if allowed_cats and category and category not in allowed_cats:
            return False

        return True

    @property
    def volume_cap(self) -> int:
        return self._rules.get("volume_cap", config.max_volume)

    @property
    def remaining_minutes(self) -> float:
        """Minutes of listening time remaining today."""
        self._refresh_today()
        limit = self._rules["daily_limit_minutes"] * 60
        remaining = max(0, limit - self._usage_seconds)
        return remaining / 60

    # ── Session Tracking ──────────────────────────────────────────────

    def start_session(self) -> None:
        """Mark the start of a listening session."""
        self._session_start = time.monotonic()
        logger.debug("Listening session started.")

    def end_session(self) -> None:
        """Mark the end of a listening session and accumulate time."""
        if self._session_start is not None:
            elapsed = time.monotonic() - self._session_start
            self._usage_seconds += elapsed
            self._session_start = None
            self._save_usage()
            logger.debug("Session ended. Today total: %.0fs", self._usage_seconds)

    def get_today_usage_minutes(self) -> float:
        """Get total listening time today in minutes."""
        self._refresh_today()
        current = self._usage_seconds
        if self._session_start is not None:
            current += time.monotonic() - self._session_start
        return current / 60

    # ── Rule Updates (from server sync) ───────────────────────────────

    def update_rules(self, rules: dict) -> None:
        """Update rules from server sync."""
        self._rules.update(rules)
        save_json(config.content_dir / _RULES_FILE, {"rules": self._rules})
        logger.info("Parental rules updated: %s", rules)

    def get_rules(self) -> dict:
        return dict(self._rules)

    # ── Internals ─────────────────────────────────────────────────────

    def _is_bedtime(self) -> bool:
        """Check if the current time falls within bedtime hours."""
        now = datetime.now().time()
        try:
            start = dtime.fromisoformat(self._rules["bedtime_start"])
            end = dtime.fromisoformat(self._rules["bedtime_end"])
        except (ValueError, KeyError):
            return False

        if start <= end:
            return start <= now <= end
        else:
            # Overnight bedtime (e.g., 20:00 → 07:00)
            return now >= start or now <= end

    def _refresh_today(self) -> None:
        """Reset usage counter if it's a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._today_key:
            self._today_key = today
            self._usage_seconds = self._usage_data.get(today, 0.0)

    def _save_usage(self) -> None:
        """Persist today's usage to disk."""
        self._usage_data[self._today_key] = self._usage_seconds
        # Keep only last 30 days
        keys = sorted(self._usage_data.keys())
        if len(keys) > 30:
            for old_key in keys[:-30]:
                del self._usage_data[old_key]
        save_json(config.content_dir / "daily_usage.json", self._usage_data)

    def shutdown(self) -> None:
        self.end_session()
        logger.info("ParentalControls shut down.")
