"""
MikaBox LED Controller
======================

NeoPixel / WS2812B LED ring animations for device state feedback.

Hardware: WS2812B LED ring on GPIO 18 (default).
Install: ``sudo pip install adafruit-circuitpython-neopixel``
"""

import logging
import math
import threading
import time
from enum import Enum
from typing import Optional

from .config import config

logger = logging.getLogger("mikabox.led")

try:
    import neopixel  # type: ignore[import-untyped]
    import board      # type: ignore[import-untyped]

    _HAS_NEOPIXEL = True
except ImportError:
    _HAS_NEOPIXEL = False
    logger.info("NeoPixel library not found — LED animations will be simulated.")


class LEDPattern(str, Enum):
    OFF = "off"
    IDLE = "idle"                 # Gentle breathing glow (soft blue)
    LISTENING = "listening"       # Pulsing green ring
    PROCESSING = "processing"    # Spinning animation
    PLAYING = "playing"          # Soft pulsing teal
    ERROR = "error"              # Red flash
    LOW_BATTERY = "low_battery"  # Orange pulse
    CHARGING = "charging"        # Green fill animation
    BEDTIME = "bedtime"          # Warm dim glow
    SUCCESS = "success"          # Brief green flash


# ── Color Palette (R, G, B) ──────────────────────────────────────────
COLORS = {
    "soft_blue": (30, 80, 180),
    "teal": (0, 180, 160),
    "green": (0, 200, 80),
    "coral": (249, 112, 102),
    "orange": (255, 140, 0),
    "red": (220, 40, 40),
    "warm_white": (255, 180, 80),
    "purple": (120, 60, 200),
}


class LEDController:
    """
    Manages LED ring animations in a background thread.

    Call ``set_pattern(LEDPattern.IDLE)`` to change the animation.
    The animation loop runs continuously, updating LEDs at ~30 FPS.
    """

    def __init__(self):
        self._pattern: LEDPattern = LEDPattern.OFF
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Hardware
        self._pixels = None
        self._count = config.led_count
        if _HAS_NEOPIXEL:
            try:
                pin = getattr(board, f"D{config.led_pin}")
                self._pixels = neopixel.NeoPixel(
                    pin, self._count,
                    brightness=config.led_brightness,
                    auto_write=False,
                )
                self._pixels.fill((0, 0, 0))
                self._pixels.show()
            except Exception as exc:
                logger.error("Failed to initialize NeoPixel: %s", exc)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._animation_loop, name="led-anim", daemon=True
        )
        self._thread.start()
        logger.info("LED controller started (%d LEDs).", self._count)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._fill((0, 0, 0))
        logger.info("LED controller stopped.")

    def set_pattern(self, pattern: LEDPattern) -> None:
        with self._lock:
            if pattern != self._pattern:
                self._pattern = pattern
                logger.debug("LED pattern → %s", pattern.value)

    @property
    def current_pattern(self) -> LEDPattern:
        return self._pattern

    # ── Animation Loop ────────────────────────────────────────────────

    def _animation_loop(self) -> None:
        tick = 0
        while self._running:
            with self._lock:
                pattern = self._pattern

            if pattern == LEDPattern.OFF:
                self._fill((0, 0, 0))
            elif pattern == LEDPattern.IDLE:
                self._breathe(COLORS["soft_blue"], tick, speed=0.02)
            elif pattern == LEDPattern.LISTENING:
                self._pulse(COLORS["green"], tick, speed=0.06)
            elif pattern == LEDPattern.PROCESSING:
                self._spin(COLORS["purple"], tick)
            elif pattern == LEDPattern.PLAYING:
                self._breathe(COLORS["teal"], tick, speed=0.03)
            elif pattern == LEDPattern.ERROR:
                self._flash(COLORS["red"], tick)
            elif pattern == LEDPattern.LOW_BATTERY:
                self._pulse(COLORS["orange"], tick, speed=0.04)
            elif pattern == LEDPattern.CHARGING:
                self._fill_progress(COLORS["green"], tick)
            elif pattern == LEDPattern.BEDTIME:
                self._breathe(COLORS["warm_white"], tick, speed=0.01)
            elif pattern == LEDPattern.SUCCESS:
                self._flash(COLORS["green"], tick, duration=10)

            tick += 1
            time.sleep(1 / 30)  # ~30 FPS

    # ── Animation Primitives ──────────────────────────────────────────

    def _breathe(self, color: tuple, tick: int, speed: float = 0.02) -> None:
        """Gentle breathing glow — sinusoidal brightness modulation."""
        brightness = (math.sin(tick * speed) + 1) / 2  # 0.0 to 1.0
        brightness = 0.1 + brightness * 0.9             # min 10% brightness
        r, g, b = color
        c = (int(r * brightness), int(g * brightness), int(b * brightness))
        self._fill(c)

    def _pulse(self, color: tuple, tick: int, speed: float = 0.06) -> None:
        """Faster pulse for active states."""
        brightness = (math.sin(tick * speed) + 1) / 2
        brightness = 0.2 + brightness * 0.8
        r, g, b = color
        c = (int(r * brightness), int(g * brightness), int(b * brightness))
        self._fill(c)

    def _spin(self, color: tuple, tick: int) -> None:
        """Single LED chasing around the ring."""
        pos = tick % self._count
        for i in range(self._count):
            dist = min(abs(i - pos), self._count - abs(i - pos))
            brightness = max(0.0, 1.0 - dist / 3.0)
            r, g, b = color
            self._set_pixel(i, (int(r * brightness), int(g * brightness), int(b * brightness)))
        self._show()

    def _flash(self, color: tuple, tick: int, duration: int = 15) -> None:
        """Quick on/off flash."""
        if (tick // duration) % 2 == 0:
            self._fill(color)
        else:
            self._fill((0, 0, 0))

    def _fill_progress(self, color: tuple, tick: int) -> None:
        """LEDs fill up progressively like a charging bar."""
        filled = (tick // 8) % (self._count + 1)
        for i in range(self._count):
            if i < filled:
                self._set_pixel(i, color)
            else:
                self._set_pixel(i, (0, 0, 0))
        self._show()

    # ── Hardware Abstraction ──────────────────────────────────────────

    def _fill(self, color: tuple) -> None:
        if self._pixels:
            self._pixels.fill(color)
            self._pixels.show()

    def _set_pixel(self, index: int, color: tuple) -> None:
        if self._pixels and 0 <= index < self._count:
            self._pixels[index] = color

    def _show(self) -> None:
        if self._pixels:
            self._pixels.show()

    def shutdown(self) -> None:
        self.stop()
        logger.info("LEDController shut down.")
