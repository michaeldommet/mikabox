"""
MikaBox Backend Configuration
==============================
"""

import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Backend settings — override via environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = field(default_factory=lambda: int(os.getenv("MIKABOX_PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("MIKABOX_DEBUG", "false").lower() == "true")

    # Database
    database_url: str = field(default_factory=lambda: os.getenv(
        "MIKABOX_DATABASE_URL",
        f"sqlite+aiosqlite:///{Path.home() / 'mikabox' / 'mikabox.db'}"
    ))

    # Security
    secret_key: str = field(default_factory=lambda: os.getenv(
        "MIKABOX_SECRET_KEY", "mikabox-dev-secret-change-in-production"
    ))
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"

    # Content storage
    content_dir: Path = field(default_factory=lambda: Path(os.getenv(
        "MIKABOX_CONTENT_DIR", str(Path.home() / "mikabox" / "content")
    )))

    # CORS
    allowed_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ])

    def __post_init__(self):
        self.content_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
