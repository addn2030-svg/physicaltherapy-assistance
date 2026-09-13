"""Central configuration for Rehab RCH Agent v2.

All settings are loaded from environment variables (see `.env.example`).
The bot runs in a graceful *demo mode* when optional keys are missing so
staff can test commands without Google credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # Load .env automatically when present (no-op if missing)
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except ValueError:
        return default


def _env_list(key: str) -> list[str]:
    raw = os.getenv(key, "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]


@dataclass
class Settings:
    """Typed application settings."""

    # -- Telegram ---------------------------------------------------------
    telegram_bot_token: str = field(default_factory=lambda: _env("TELEGRAM_BOT_TOKEN"))
    telegram_admin_ids: list[str] = field(default_factory=lambda: _env_list("TELEGRAM_ADMIN_IDS"))

    # -- Gemini -----------------------------------------------------------
    gemini_api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _env("GEMINI_MODEL", "gemini-2.0-flash"))
    gemini_temperature: float = 0.4
    gemini_max_tokens: int = 2048

    # -- Google -----------------------------------------------------------
    google_credentials_file: str = field(
        default_factory=lambda: _env("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    )
    drive_root_folder_name: str = field(
        default_factory=lambda: _env("DRIVE_ROOT_FOLDER_NAME", "Rehab RCH Agent")
    )
    drive_root_folder_id: str = field(default_factory=lambda: _env("DRIVE_ROOT_FOLDER_ID"))
    staff_sheet_id: str = field(default_factory=lambda: _env("STAFF_SHEET_ID"))
    staff_sheet_tab: str = field(default_factory=lambda: _env("STAFF_SHEET_TAB", "Staff"))
    audit_sheet_tab: str = field(default_factory=lambda: _env("AUDIT_SHEET_TAB", "AuditLog"))
    audit_sheet_enabled: bool = field(
        default_factory=lambda: _env("AUDIT_SHEET_ENABLED", "true").lower() not in {"0", "false", "no"}
    )

    # -- Retention / compliance -------------------------------------------
    retention_days: int = field(default_factory=lambda: _env_int("RETENTION_DAYS", 365))
    manifest_file: str = field(
        default_factory=lambda: _env("KB_MANIFEST_FILE", "manifest.json")
    )

    # -- Local allowlist fallback (comma separated telegram ids) ----------
    allowed_telegram_ids: list[str] = field(
        default_factory=lambda: _env_list("ALLOWED_TELEGRAM_IDS")
    )
    staff_allowlist_file: str = field(
        default_factory=lambda: _env("STAFF_ALLOWLIST_FILE", "staff_allowlist.json")
    )

    # -- Department branding ----------------------------------------------
    department_name: str = field(
        default_factory=lambda: _env("DEPARTMENT_NAME", "Rehabilitation Department — RCH")
    )
    section_head_name: str = field(
        default_factory=lambda: _env("SECTION_HEAD_NAME", "Abdulrahman Bakor Howsawy")
    )
    section_head_title: str = field(
        default_factory=lambda: _env("SECTION_HEAD_TITLE", "Rehabilitation Section Head")
    )

    # -- Paths ------------------------------------------------------------
    base_dir: Path = BASE_DIR
    knowledge_dir: Path = field(default_factory=lambda: BASE_DIR / _env("KNOWLEDGE_DIR", "knowledge"))
    output_dir: Path = field(default_factory=lambda: BASE_DIR / _env("OUTPUT_DIR", "output"))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO").upper())

    def __post_init__(self) -> None:
        # Optional numeric overrides
        try:
            self.gemini_temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.4"))
        except ValueError:
            self.gemini_temperature = 0.4
        self.gemini_max_tokens = _env_int("GEMINI_MAX_TOKENS", 2048)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -- Helpers ----------------------------------------------------------
    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def credentials_path(self) -> Path:
        p = Path(self.google_credentials_file)
        if not p.is_absolute():
            p = self.base_dir / p
        return p

    @property
    def has_google_credentials(self) -> bool:
        return self.credentials_path.exists()

    @property
    def demo_mode(self) -> bool:
        """True when running without Gemini and/or Google credentials."""
        return not (self.has_gemini and self.has_google_credentials)


settings = Settings()
