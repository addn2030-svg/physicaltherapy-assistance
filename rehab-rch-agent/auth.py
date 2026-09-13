"""Staff authentication for Rehab RCH Agent v2.

Source of truth: a Google Sheet with columns::

    Telegram ID | Name | Role

Example row::

    123456789 | Abdulrahman | Section Head

Fallbacks (in order) when Google Sheets is unavailable:
  1. ``ALLOWED_TELEGRAM_IDS`` env var (comma separated)
  2. Local ``staff_allowlist.json`` file::

        [
          {"telegram_id": "123456789", "name": "Abdulrahman", "role": "Section Head"}
        ]

Unauthorized users receive: "Access denied. Contact Rehabilitation Section Head."
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config import settings

log = logging.getLogger(__name__)

ACCESS_DENIED_MESSAGE = (
    "🔒 *Access denied.*\n\n"
    "Only approved Rehabilitation Department staff can use this bot.\n"
    "Contact Rehabilitation Section Head."
)


@dataclass
class StaffMember:
    telegram_id: str
    name: str
    role: str = "Staff"

    def display(self) -> str:
        return f"{self.name} ({self.role})"


class StaffAuth:
    """Loads and caches the staff allowlist."""

    def __init__(self) -> None:
        self._cache: dict[str, StaffMember] = {}
        self._source: str = "none"
        self.reload()

    # -- public API ------------------------------------------------------
    @property
    def source(self) -> str:
        return self._source

    def reload(self) -> int:
        """Reload staff list. Returns number of entries loaded."""
        self._cache = {}

        # 1) Google Sheets (preferred)
        loaded = self._load_from_google_sheets()
        if loaded:
            self._source = "google-sheets"
            return len(self._cache)

        # 2) Env var
        for tid in settings.allowed_telegram_ids:
            self._cache[str(tid)] = StaffMember(telegram_id=str(tid), name=f"Staff {tid}")
        if self._cache:
            self._source = "env"
            return len(self._cache)

        # 3) Local JSON file
        if self._load_from_json_file():
            self._source = "json"
            return len(self._cache)

        self._source = "none"
        log.warning("No staff allowlist configured — all users will be denied.")
        return 0

    def is_authorized(self, telegram_id: int | str) -> bool:
        return str(telegram_id) in self._cache

    def get_staff(self, telegram_id: int | str) -> Optional[StaffMember]:
        return self._cache.get(str(telegram_id))

    def count(self) -> int:
        return len(self._cache)

    # -- loaders ---------------------------------------------------------
    def _load_from_google_sheets(self) -> bool:
        sheet_id = settings.staff_sheet_id
        if not sheet_id or not settings.has_google_credentials:
            return False
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_file(
                str(settings.credentials_path), scopes=scopes
            )
            client = gspread.authorize(creds)
            sheet = client.open_by_key(sheet_id).worksheet(settings.staff_sheet_tab)
            rows = sheet.get_all_records()
            for row in rows:
                tid = str(
                    row.get("Telegram ID", row.get("telegram_id", row.get("ID", "")))
                ).strip()
                if not tid or tid.lower() == "none":
                    continue
                # gspread may return numbers as int/float
                tid = str(int(float(tid))) if tid.replace(".", "", 1).isdigit() else tid
                name = str(row.get("Name", row.get("name", "Staff"))).strip() or "Staff"
                role = str(row.get("Role", row.get("role", "Staff"))).strip() or "Staff"
                self._cache[tid] = StaffMember(telegram_id=tid, name=name, role=role)
            log.info("Loaded %d staff from Google Sheets.", len(self._cache))
            return bool(self._cache)
        except Exception as exc:  # pragma: no cover - needs live creds
            log.warning("Google Sheets staff load failed: %s", exc)
            return False

    def _load_from_json_file(self) -> bool:
        path = Path(settings.staff_allowlist_file)
        if not path.is_absolute():
            path = settings.base_dir / path
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("staff", [])
            for item in items:
                tid = str(item.get("telegram_id", "")).strip()
                if not tid:
                    continue
                self._cache[tid] = StaffMember(
                    telegram_id=tid,
                    name=str(item.get("name", "Staff")),
                    role=str(item.get("role", "Staff")),
                )
            log.info("Loaded %d staff from %s.", len(self._cache), path.name)
            return bool(self._cache)
        except Exception as exc:
            log.warning("Staff JSON load failed: %s", exc)
            return False


# Singleton used by bot.py
staff_auth = StaffAuth()


def is_admin(telegram_id: int | str) -> bool:
    return str(telegram_id) in (settings.telegram_admin_ids or [])
