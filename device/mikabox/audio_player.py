"""
MikaBox Audio Player
====================

VLC-based audio playback engine with playlist management,
chapter navigation, volume control, and resume-from-position.

On the Pi 4, install VLC: ``sudo apt install vlc``
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, Callable

from .config import config
from .utils import load_json, save_json

logger = logging.getLogger("mikabox.audio")

# VLC is only available on the Pi — graceful fallback for dev machines.
try:
    import vlc  # type: ignore[import-untyped]

    _HAS_VLC = True
except ImportError:
    _HAS_VLC = False
    logger.warning("python-vlc not found — audio playback will be simulated.")


class AudioPlayer:
    """
    Manages audio playback with VLC as the backend.

    Features
    --------
    - Play single files or playlists (folder-based).
    - Chapter / track skip forward / back.
    - Volume control with parental max-volume cap.
    - Persist and resume playback position across restarts.
    - Audio ducking for voice interactions.
    - Thread-safe controls.
    """

    def __init__(
        self,
        on_track_changed: Optional[Callable[[dict], None]] = None,
        on_playback_ended: Optional[Callable[[], None]] = None,
    ):
        self._lock = threading.Lock()
        self._on_track_changed = on_track_changed
        self._on_playback_ended = on_playback_ended

        # Playlist state
        self._playlist: list[Path] = []
        self._current_index: int = 0
        self._current_content_id: Optional[str] = None

        # Volume
        self._volume: int = config.default_volume
        self._volume_cap: int = config.max_volume
        self._ducked: bool = False
        self._pre_duck_volume: int = self._volume

        # Resume positions: {content_id: {track_index: int, position_ms: int}}
        self._resume_data: dict = load_json(config.resume_positions_path, {})

        # VLC instance
        self._instance: Optional["vlc.Instance"] = None
        self._player: Optional["vlc.MediaPlayer"] = None
        if _HAS_VLC:
            self._instance = vlc.Instance("--no-video", "--quiet")
            self._player = self._instance.media_player_new()
            self._player.audio_set_volume(self._volume)

            # Event manager for end-of-track
            em = self._player.event_manager()
            em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

        self._playing = False
        self._monitor_thread: Optional[threading.Thread] = None

    # ── Public API ────────────────────────────────────────────────────

    def play_file(self, file_path: Path, content_id: Optional[str] = None) -> bool:
        """Play a single audio file."""
        if not file_path.exists():
            logger.error("File not found: %s", file_path)
            return False
        return self._play_playlist([file_path], content_id=content_id)

    def play_folder(self, folder: Path, content_id: Optional[str] = None) -> bool:
        """Play all supported audio files in a folder, sorted by name."""
        if not folder.is_dir():
            logger.error("Folder not found: %s", folder)
            return False
        files = sorted(
            f for f in folder.iterdir()
            if f.suffix.lower() in config.supported_formats
        )
        if not files:
            logger.warning("No audio files found in %s", folder)
            return False
        return self._play_playlist(files, content_id=content_id)

    def pause(self) -> None:
        """Toggle pause/resume."""
        with self._lock:
            if self._player and self._playing:
                self._player.pause()
                logger.info("Playback paused.")

    def resume(self) -> None:
        """Resume from pause."""
        with self._lock:
            if self._player and self._playing:
                self._player.play()
                logger.info("Playback resumed.")

    def stop(self) -> None:
        """Stop playback and save position."""
        with self._lock:
            self._save_position()
            if self._player:
                self._player.stop()
            self._playing = False
            self._playlist.clear()
            logger.info("Playback stopped.")

    def skip_forward(self) -> None:
        """Skip to the next track in the playlist."""
        with self._lock:
            if self._current_index < len(self._playlist) - 1:
                self._current_index += 1
                self._load_and_play(self._playlist[self._current_index])

    def skip_back(self) -> None:
        """Skip to the previous track, or restart current if > 3s in."""
        with self._lock:
            if self._player and self._player.get_time() > 3000:
                self._player.set_time(0)
            elif self._current_index > 0:
                self._current_index -= 1
                self._load_and_play(self._playlist[self._current_index])

    def set_volume(self, level: int) -> int:
        """Set volume (0-100), clamped by parental cap. Returns actual level."""
        with self._lock:
            self._volume = max(0, min(level, self._volume_cap))
            if self._player:
                self._player.audio_set_volume(self._volume)
            logger.debug("Volume set to %d (cap: %d)", self._volume, self._volume_cap)
            return self._volume

    def set_volume_cap(self, cap: int) -> None:
        """Update the parental volume cap."""
        self._volume_cap = max(0, min(cap, 100))
        if self._volume > self._volume_cap:
            self.set_volume(self._volume_cap)

    def duck_audio(self) -> None:
        """Reduce volume for voice interaction."""
        if not self._ducked:
            self._ducked = True
            self._pre_duck_volume = self._volume
            self.set_volume(max(10, self._volume // 3))
            logger.debug("Audio ducked for voice interaction.")

    def unduck_audio(self) -> None:
        """Restore volume after voice interaction."""
        if self._ducked:
            self._ducked = False
            self.set_volume(self._pre_duck_volume)
            logger.debug("Audio unducked.")

    # ── State Queries ─────────────────────────────────────────────────

    @property
    def is_playing(self) -> bool:
        if not self._player:
            return self._playing
        return self._player.is_playing() == 1

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def current_track(self) -> Optional[dict]:
        if not self._playlist or self._current_index >= len(self._playlist):
            return None
        track = self._playlist[self._current_index]
        position_ms = self._player.get_time() if self._player else 0
        duration_ms = self._player.get_length() if self._player else 0
        return {
            "file": str(track),
            "name": track.stem,
            "index": self._current_index,
            "total_tracks": len(self._playlist),
            "position_ms": max(0, position_ms),
            "duration_ms": max(0, duration_ms),
            "content_id": self._current_content_id,
        }

    # ── Internal ──────────────────────────────────────────────────────

    def _play_playlist(self, files: list[Path], content_id: Optional[str] = None) -> bool:
        with self._lock:
            self._save_position()
            self._playlist = files
            self._current_content_id = content_id
            self._current_index = 0

            # Resume from saved position
            if content_id and content_id in self._resume_data:
                saved = self._resume_data[content_id]
                idx = saved.get("track_index", 0)
                if 0 <= idx < len(files):
                    self._current_index = idx

            self._load_and_play(self._playlist[self._current_index])
            self._playing = True

            # Resume time position
            if content_id and content_id in self._resume_data:
                pos = self._resume_data[content_id].get("position_ms", 0)
                if pos > 0 and self._player:
                    # Small delay for VLC to start
                    threading.Timer(0.3, lambda: self._player.set_time(pos)).start()

            return True

    def _load_and_play(self, file_path: Path) -> None:
        if not self._player or not self._instance:
            logger.info("[SIM] Playing: %s", file_path.name)
            return
        media = self._instance.media_new(str(file_path))
        self._player.set_media(media)
        self._player.play()
        self._player.audio_set_volume(self._volume)
        logger.info("Now playing: %s (%d/%d)", file_path.name,
                     self._current_index + 1, len(self._playlist))
        if self._on_track_changed:
            self._on_track_changed(self.current_track or {})

    def _on_end_reached(self, event: object) -> None:
        """Called by VLC when a track finishes."""
        # Clear resume position for completed track
        if self._current_content_id and self._current_content_id in self._resume_data:
            if self._current_index >= len(self._playlist) - 1:
                self._resume_data.pop(self._current_content_id, None)

        if self._current_index < len(self._playlist) - 1:
            self._current_index += 1
            # VLC events fire from a non-main thread — schedule playback
            threading.Timer(0.1, lambda: self._load_and_play(
                self._playlist[self._current_index]
            )).start()
        else:
            self._playing = False
            logger.info("Playlist finished.")
            if self._on_playback_ended:
                self._on_playback_ended()

    def _save_position(self) -> None:
        """Persist current playback position for resume."""
        if self._current_content_id and self._player and self._playing:
            self._resume_data[self._current_content_id] = {
                "track_index": self._current_index,
                "position_ms": max(0, self._player.get_time()),
            }
            save_json(config.resume_positions_path, self._resume_data)

    def shutdown(self) -> None:
        """Clean shutdown — save position and release VLC resources."""
        self.stop()
        if self._player:
            self._player.release()
        if self._instance:
            self._instance.release()
        logger.info("AudioPlayer shut down.")
