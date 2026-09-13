"""Agent v4.2 Google Calendar client — service account, demo-mode fallback.

Reuses the Drive service-account credentials. Disabled unless
GOOGLE_CALENDAR_ID is set (and the calendar is shared with the service
account email). All calls are fail-soft: they return "" instead of raising.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from config import settings

log = logging.getLogger("calendar")


def calendar_configured() -> bool:
    return bool(settings.calendar_enabled and settings.calendar_id
                and settings.has_google_credentials)


def build_event_body(title: str, day: date | str,
                     description: str = "") -> dict:
    """Pure event payload builder (all-day event, schedule tz)."""
    day_s = day.isoformat() if isinstance(day, date) else str(day).strip()
    body: dict = {
        "summary": f"[Rehab] {title}"[:200],
        "start": {"date": day_s, "timeZone": settings.sched_tz},
        "end": {"date": day_s, "timeZone": settings.sched_tz},
    }
    if description.strip():
        body["description"] = description.strip()[:2000]
    return body


class CalendarClient:
    """Thin Calendar wrapper with demo-mode fallback."""

    def __init__(self) -> None:
        self._service = None
        self.demo_mode = True
        if not calendar_configured():
            log.debug("Calendar not configured — demo mode.")
            return
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_service_account_file(
                str(settings.credentials_path),
                scopes=["https://www.googleapis.com/auth/calendar"],
            )
            self._service = build("calendar", "v3", credentials=creds,
                                  cache_discovery=False)
            self.demo_mode = False
            log.info("Google Calendar client initialised.")
        except Exception as exc:
            log.warning("Calendar init failed (%s); demo mode.", exc)
            self._service = None
            self.demo_mode = True

    def create_event(self, title: str, day: date | str,
                     description: str = "") -> str:
        """Create an all-day event. Returns event ID or "" (demo/failure)."""
        from audit import audit  # lazy: avoid import cycles

        if self.demo_mode or self._service is None:
            return ""
        try:
            created = self._service.events().insert(
                calendarId=settings.calendar_id,
                body=build_event_body(title, day, description)).execute()
            eid = str(created.get("id", ""))
            audit.log("calendar_event", "", "system",
                      f"event={eid} title={title[:100]}")
            return eid
        except Exception as exc:
            log.warning("Calendar event failed (%s).", exc)
            audit.log("calendar_failed", "", "system",
                      f"title={title[:100]} err={exc!r}"[:300])
            return ""


_client: Optional[CalendarClient] = None


def get_calendar() -> CalendarClient:
    """Module-level lazy singleton (rebuilt once per process)."""
    global _client
    if _client is None:
        _client = CalendarClient()
    return _client


def create_calendar_event(title: str, day: date | str,
                          description: str = "") -> str:
    """Convenience: "" when calendar is not connected."""
    if not calendar_configured():
        return ""
    return get_calendar().create_event(title, day, description)
