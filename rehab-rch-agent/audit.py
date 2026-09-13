"""Audit logging for Rehab RCH Agent v2 (Phase 2 safety rails).

Every security-relevant event is recorded:

* auth_granted / auth_denied — who tried to use the bot, when
* phi_blocked — blocked patient-data attempts (content NOT stored,
  only the matched reason labels + message length)
* question_asked / sop_asked — Q&A with knowledge-coverage level
* needs_review — out-of-scope questions flagged for human review
* report_generated / announcement_saved / meeting_saved / drive_upload
* kb_reload

Storage:
  1. Local JSONL ``output/audit/audit-YYYY-MM.jsonl`` (always on).
  2. Google Sheet tab (``AUDIT_SHEET_TAB``, default ``AuditLog``) in the
     staff spreadsheet — best-effort, same service account needs
     **Editor** on the Sheet for this. Disable with
     ``AUDIT_SHEET_ENABLED=false``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from config import settings

log = logging.getLogger(__name__)

AUDIT_HEADER = ["Timestamp (UTC)", "Event", "Telegram ID", "Name", "Details"]


class AuditLogger:
    """Append-only audit trail: local JSONL + optional Google Sheet."""

    def __init__(self, audit_dir: Optional[Path] = None) -> None:
        self.dir = audit_dir or (settings.output_dir / "audit")
        self.dir.mkdir(parents=True, exist_ok=True)

    # -- public API ------------------------------------------------------
    def log(
        self,
        event: str,
        telegram_id: int | str = "",
        name: str = "",
        details: str = "",
    ) -> dict[str, Any]:
        """Record one audit event. Never raises (logging must not break flows)."""
        entry = {
            "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            "telegram_id": str(telegram_id),
            "name": name,
            "details": details[:500],
        }
        try:
            month_file = self.dir / f"audit-{datetime.now(timezone.utc):%Y-%m}.jsonl"
            with month_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            log.warning("Local audit write failed: %s", exc)
        self._append_to_sheet(entry)
        return entry

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent local entries (newest last)."""
        files = sorted(self.dir.glob("audit-*.jsonl"))
        entries: list[dict[str, Any]] = []
        for path in files:
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            except Exception as exc:
                log.warning("Audit read failed for %s: %s", path.name, exc)
        return entries[-limit:]

    # -- Google Sheet mirror (best-effort) --------------------------------
    def _append_to_sheet(self, entry: dict[str, Any]) -> None:
        if not settings.audit_sheet_enabled:
            return
        if not settings.staff_sheet_id or not settings.has_google_credentials:
            return
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_file(
                str(settings.credentials_path), scopes=scopes
            )
            client = gspread.authorize(creds)
            workbook = client.open_by_key(settings.staff_sheet_id)
            try:
                sheet = workbook.worksheet(settings.audit_sheet_tab)
            except Exception:
                sheet = workbook.add_worksheet(
                    title=settings.audit_sheet_tab, rows=2000, cols=len(AUDIT_HEADER)
                )
            if not sheet.get_values("A1:A1"):
                sheet.append_row(AUDIT_HEADER)
            sheet.append_row(
                [
                    entry["ts_utc"],
                    entry["event"],
                    entry["telegram_id"],
                    entry["name"],
                    entry["details"],
                ]
            )
        except Exception as exc:
            # Sheet mirroring is optional — local JSONL is the source of truth.
            log.debug("Audit sheet append skipped: %s", exc)


# Singleton
audit = AuditLogger()
