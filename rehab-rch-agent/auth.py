"""Staff authentication for Rehab RCH Agent v2.

Source of truth: a Google Sheet with columns::

    Telegram ID | Name | Role | Status | Valid Until

Example row::

    123456789 | Abdulrahman | Section Head | Active | 2027-09-01

``Status`` / ``Valid Until`` are optional (Phase 2 access review):
Status != Active, or a past Valid Until (YYYY-MM-DD), denies access.
Use them for monthly access reviews and offboarding without deleting rows.

Second source: the ``Telegram_Users`` tab of the operations workbook
(``OPS_SHEET_ID``) — rows with an ``Active`` flag and matching
``Telegram_Chat_ID`` grant access, with roles resolved from
``Staff_Register`` by name.

Further fallbacks (in order) when Google Sheets is unavailable:
  1. ``ALLOWED_TELEGRAM_IDS`` env var (comma separated)
  2. Local ``staff_allowlist.json`` file::

        [
          {"telegram_id": "123456789", "name": "Abdulrahman", "role": "Section Head",
           "status": "Active", "valid_until": "2027-09-01"}
        ]

Unauthorized users receive: "Access denied. Contact Rehabilitation Section Head."
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from config import settings

log = logging.getLogger(__name__)

ACCESS_DENIED_MESSAGE = (
    "🔒 *Access denied.*\n\n"
    "Only approved Rehabilitation Department staff can use this bot.\n"
    "Contact Rehabilitation Section Head."
)


def _parse_valid_until(raw: str) -> Optional[date]:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    log.warning("Unparseable Valid Until %r — treating as no expiry.", raw)
    return None


@dataclass
class StaffMember:
    telegram_id: str
    name: str
    role: str = "Staff"
    status: str = "Active"
    valid_until: Optional[date] = field(default=None)

    def display(self) -> str:
        return f"{self.name} ({self.role})"

    @property
    def access_ok(self) -> bool:
        """Active status and not past Valid Until (periodic re-auth)."""
        if self.status.strip().lower() != "active":
            return False
        if self.valid_until and self.valid_until < date.today():
            return False
        return True


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

        # 1) Google Sheets staff tab (preferred)
        loaded = self._load_from_google_sheets()
        if loaded:
            self._source = "google-sheets"
            return len(self._cache)

        # 2) Ops workbook Telegram_Users tab
        if self._load_from_ops_sheet():
            self._source = "ops-telegram-users"
            return len(self._cache)

        # 3) Env var
        for tid in settings.allowed_telegram_ids:
            self._cache[str(tid)] = StaffMember(telegram_id=str(tid), name=f"Staff {tid}")
        if self._cache:
            self._source = "env"
            return len(self._cache)

        # 4) Local JSON file
        if self._load_from_json_file():
            self._source = "json"
            return len(self._cache)

        self._source = "none"
        log.warning("No staff allowlist configured — all users will be denied.")
        return 0

    def is_authorized(self, telegram_id: int | str) -> bool:
        member = self._cache.get(str(telegram_id))
        return bool(member and member.access_ok)

    def get_staff(self, telegram_id: int | str) -> Optional[StaffMember]:
        return self._cache.get(str(telegram_id))

    def count(self) -> int:
        return len(self._cache)

    def active_count(self) -> int:
        """Staff with current access (Active + not expired)."""
        return sum(1 for m in self._cache.values() if m.access_ok)

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
                status = str(row.get("Status", row.get("status", "Active"))).strip() or "Active"
                valid_until = _parse_valid_until(
                    str(row.get("Valid Until", row.get("valid_until", "")))
                )
                self._cache[tid] = StaffMember(
                    telegram_id=tid, name=name, role=role,
                    status=status, valid_until=valid_until,
                )
            log.info("Loaded %d staff from Google Sheets.", len(self._cache))
            return bool(self._cache)
        except Exception as exc:  # pragma: no cover - needs live creds
            log.warning("Google Sheets staff load failed: %s", exc)
            return False

    def _load_from_ops_sheet(self) -> bool:
        """Auth from the ops workbook Telegram_Users tab (Agent v3)."""
        if not settings.ops_sheet_id or not settings.has_google_credentials:
            return False
        try:
            from sheets_ops import OpsDB, GSpreadBackend  # lazy: avoid import cycles

            db = OpsDB(GSpreadBackend(settings.ops_sheet_id))
            for user in db.telegram_users(active_only=True):
                chat_id = str(user.get("Telegram_Chat_ID", "")).strip()
                if not chat_id or not chat_id.lstrip("-").isdigit():
                    continue
                name = str(user.get("Staff_Name", "")).strip() or "Staff"
                self._cache[chat_id] = StaffMember(
                    telegram_id=chat_id, name=name, role=db.staff_role(name),
                )
            log.info("Loaded %d staff from ops Telegram_Users.", len(self._cache))
            return bool(self._cache)
        except Exception as exc:
            log.warning("Ops Telegram_Users load failed: %s", exc)
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
                    status=str(item.get("status", "Active")),
                    valid_until=_parse_valid_until(str(item.get("valid_until", ""))),
                )
            log.info("Loaded %d staff from %s.", len(self._cache), path.name)
            return bool(self._cache)
        except Exception as exc:
            log.warning("Staff JSON load failed: %s", exc)
            return False


def is_private_chat(update) -> bool:
    """True only for one-to-one private chats (staff-only policy).

    Groups, supergroups, channels, and missing chats are all rejected —
    department data must never render where non-staff can see it.
    """
    chat = getattr(update, "effective_chat", None)
    return getattr(chat, "type", "") == "private"


def check_enroll_code(provided: str) -> bool:
    """Validate the staff enrollment code for /register.

    Fail-closed: when ENROLL_CODE is not configured, registration is
    closed (returns False) until the Section Head sets a code.
    """
    expected = (settings.enroll_code or "").strip()
    if not expected:
        return False
    return (provided or "").strip() == expected


# Singleton used by bot.py
staff_auth = StaffAuth()


def is_admin(telegram_id: int | str) -> bool:
    return str(telegram_id) in (settings.telegram_admin_ids or [])
