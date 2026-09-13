"""24/7 proactive scheduler — Agent v4 orchestra driver.

Every 60s the tick checks the timetable (in SCHED_TZ, default
Asia/Riyadh) and runs due jobs through the orchestrator:

  07:30 (BRIEFING_TIME)  briefing → head + supervisors push
  09:00/12:00/15:00      gaps → gap scan + cutoff nudges
  17:00 (ROLLUP_TIME)    rollup → evening rollup + Drive archive
  SUN 08:00              weekly → auto-fill Weekly_Summary + Drive + admin
  every 30 min           watchdog → critical lens

Also writes output/heartbeat.txt each tick (Docker HEALTHCHECK + admin
monitoring). Started from bot.py post_init; no-ops cleanly when the ops
sheet is not connected or SCHED_ENABLED=false.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from config import settings

log = logging.getLogger(__name__)

WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def tz_now() -> datetime:
    """Timezone-aware now in the schedule timezone (naive fallback UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(settings.sched_tz)).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


def _at_time(day: datetime, hhmm: str) -> Optional[datetime]:
    try:
        h, m = (int(x) for x in hhmm.split(":"))
        return day.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, AttributeError):
        return None


def _due_since(last: dict[str, datetime], key: str, target: datetime,
               now: datetime) -> bool:
    """Due when target passed and we haven't run since target."""
    if now < target:
        return False
    prev = last.get(key)
    return prev is None or prev < target


def due_jobs(now: datetime, last: dict[str, datetime]) -> list[str]:
    """Pure timetable check. Returns job names due at `now`.

    `last` maps job key → last run datetime (naive, schedule tz).
    """
    jobs: list[str] = []
    target = _at_time(now, settings.briefing_time)
    if target and _due_since(last, "briefing", target, now):
        jobs.append("briefing")
    for slot in settings.gap_scan_times:
        target = _at_time(now, slot)
        key = f"gaps:{slot}"
        if target and _due_since(last, key, target, now):
            jobs.append("gaps")
            break
    target = _at_time(now, settings.rollup_time)
    if target and _due_since(last, "rollup", target, now):
        jobs.append("rollup")
    want_wd = WEEKDAYS.get(settings.weekly_day.upper(), 6)
    days_back = (now.weekday() - want_wd) % 7
    week_target = _at_time(now - timedelta(days=days_back), settings.weekly_time)
    if week_target and _due_since(last, "weekly", week_target, now):
        jobs.append("weekly")
    prev_wd = last.get("watchdog")
    if prev_wd is None or (now - prev_wd) >= timedelta(minutes=settings.watchdog_minutes):
        jobs.append("watchdog")
    return jobs


def mark_ran(last: dict[str, datetime], jobs: list[str], now: datetime) -> None:
    for job in jobs:
        if job == "gaps":
            for slot in settings.gap_scan_times:
                target = _at_time(now, slot)
                if target and target <= now:
                    last[f"gaps:{slot}"] = now
        else:
            last[job] = now


def describe_schedule() -> str:
    return (
        f"🗓️ *Proactive schedule* ({settings.sched_tz})\n"
        f"Status: {'ENABLED ✅' if settings.sched_enabled else 'DISABLED ⏸️'}\n"
        f"• Briefing push: daily {settings.briefing_time} → head + supervisors\n"
        f"• Gap scans: daily {', '.join(settings.gap_scan_times)}\n"
        f"• Report cutoff nudges: from {settings.report_cutoff} → therapists\n"
        f"• Evening rollup: daily {settings.rollup_time} → head (+ Drive archive)\n"
        f"• Weekly auto-draft: {settings.weekly_day} {settings.weekly_time} → head + higher admin\n"
        f"• Watchdog: every {settings.watchdog_minutes} min (critical equipment, coverage, due-today)\n"
        f"• Quiet hours: {settings.quiet_hours} (critical only)\n"
        f"• Higher admin: {len(settings.higher_admin_chat_ids)} chat(s) configured")


def write_heartbeat() -> None:
    try:
        hb = settings.output_dir / "heartbeat.txt"
        hb.write_text(f"alive {datetime.utcnow().isoformat(timespec='seconds')}Z\n",
                      encoding="utf-8")
    except Exception as exc:
        log.debug("Heartbeat skipped: %s", exc)


async def _tick(app, last: dict[str, datetime]) -> None:
    from agents import Orchestrator  # lazy: keep import graph clean
    from messenger import TelegramMessenger
    from sheets_ops import get_ops_db

    db = get_ops_db()
    if db is None:
        return
    now = tz_now()
    jobs = due_jobs(now, last)
    if not jobs:
        return
    log.info("Scheduler running jobs: %s", jobs)
    orch = Orchestrator(db)
    outbox = await asyncio.to_thread(orch.tick, now, jobs)
    mark_ran(last, jobs, now)
    messenger = TelegramMessenger(app.bot)
    sent = 0
    for msg in outbox:
        if await messenger.send(msg):
            sent += 1
    log.info("Scheduler delivered %d/%d messages.", sent, len(outbox))


async def _loop(app) -> None:
    last: dict[str, datetime] = {}
    log.info("Proactive scheduler started (tz=%s).", settings.sched_tz)
    while True:
        try:
            write_heartbeat()
            await _tick(app, last)
        except Exception as exc:
            log.exception("Scheduler tick failed: %s", exc)
        await asyncio.sleep(60)


async def start_scheduler(app) -> None:
    """Bot post_init hook — starts the background scheduler task."""
    if not settings.sched_enabled:
        log.info("Scheduler disabled (SCHED_ENABLED=false).")
        return
    from sheets_ops import get_ops_db

    if get_ops_db() is None:
        log.warning("Scheduler idle: ops sheet not connected (set OPS_SHEET_ID).")
        return
    app.create_task(_loop(app), name="orchestra-scheduler")
