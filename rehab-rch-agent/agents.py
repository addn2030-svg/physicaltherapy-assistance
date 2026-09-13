"""Agent v4 orchestra — proactive support agents + escalation.

Six specialist agents run on a schedule inside the bot process:

  GapAgent        — finds gaps (missing reports, missing roles, stale items)
  WatchdogAgent   — critical lens (critical equipment, uncovered coverage,
                    due-today actions, expired training)
  EscalationAgent — cutoff nudges (therapist → supervisor summaries)
  BriefingAgent   — morning briefing push (head + supervisors)
  ReportAgent     — evening rollup + weekly auto-fill (sheet rows + Drive .docx)
  InsightAgent    — Gemini narrative over pre-computed numbers (AI polish only)
  ReminderAgent   — v4.2 reminders cadence + HIGH task nudges + agenda nudges
  EvaluationAgent — v4.2 monthly staff evaluation digests

The :class:`Orchestrator` runs agents per job, routes every finding up the
ladder (therapist → supervisor → head → admin) via :mod:`messenger`,
applies quiet hours + dedup windows, audits, and returns an outbox the
scheduler delivers. Numbers are ALWAYS computed here — Gemini only
narrates, so metrics can't be hallucinated.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from config import settings
from messenger import Directory, OutboxMessage
from sheets_ops import OpsDB

log = logging.getLogger(__name__)

SEV_ICON = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
SEV_DEDUP_HOURS = {"critical": 2, "warning": 6, "info": 24}


def _to_int(value) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (ValueError, TypeError):
        return 0


@dataclass
class Alert:
    """One routable finding from a support agent."""

    key: str           # stable dedup key, e.g. "gap:sup:2026-09-13:U02"
    severity: str      # critical | warning | info
    level: str         # therapist | supervisor | head | admin
    title: str
    body: str
    staff_name: str = ""
    unit_id: str = ""
    dedup_hours: Optional[int] = None

    def dedup_window(self) -> int:
        if self.dedup_hours is not None:
            return self.dedup_hours
        if self.severity == "warning":
            return settings.alert_dedup_hours
        return SEV_DEDUP_HOURS.get(self.severity, 6)


@dataclass
class Ctx:
    db: OpsDB
    now: datetime
    directory: Directory

    @property
    def today(self) -> date:
        return self.now.date()

    @property
    def day(self) -> str:
        return self.now.date().isoformat()


def in_quiet_hours(now: datetime) -> bool:
    """True when non-critical alerts must be held (env QUIET_HOURS)."""
    try:
        start_s, end_s = settings.quiet_hours.split("-")
        sh, sm = (int(x) for x in start_s.split(":"))
        eh, em = (int(x) for x in end_s.split(":"))
    except (ValueError, AttributeError):
        return False
    cur = now.hour * 60 + now.minute
    start, end = sh * 60 + sm, eh * 60 + em
    if start <= end:
        return start <= cur < end
    return cur >= start or cur < end  # overnight window


# ----------------------------------------------------------------------------
# Support agents
# ----------------------------------------------------------------------------
class GapAgent:
    """Finds operational + data gaps. Runs on every gap scan."""

    name = "gap"

    def run(self, ctx: Ctx) -> list[Alert]:
        alerts: list[Alert] = []
        day, today = ctx.day, ctx.today

        for label in ctx.db.missing_supervisor_reports(today):
            uid = label.split()[0]
            alerts.append(Alert(
                key=f"gap:sup:{day}:{uid}", severity="warning",
                level="supervisor", unit_id=uid,
                title=f"Missing supervisor report — {label}",
                body=f"No Daily_Supervisor_Reports row for {label} today ({day}). "
                     f"File it with /supervisor."))

        missing_staff = ctx.db.missing_staff_reports(today)
        if missing_staff:
            per_unit: dict[str, list[str]] = {}
            for item in missing_staff:
                name, _, unit = item.partition(" (")
                unit = unit.rstrip(")").strip()
                u = ctx.db.resolve_unit(unit)
                uid = str(u.get("Unit_ID")).upper() if u else "?"
                per_unit.setdefault(uid, []).append(name)
            for uid, names in sorted(per_unit.items()):
                shown = ", ".join(names[:6]) + (f" +{len(names) - 6} more" if len(names) > 6 else "")
                alerts.append(Alert(
                    key=f"gap:staff:{day}:{uid}", severity="info",
                    level="supervisor", unit_id=uid if uid != "?" else "",
                    title=f"Staff reports missing — {uid} ({len(names)})",
                    body=f"Not filed yet: {shown}.\nTherapists file with /daily."))

        health = ctx.db.datahealth()
        if health["missing_roles"]:
            alerts.append(Alert(
                key=f"gap:roles:{day}", severity="info", level="head",
                title=f"Staff register: {len(health['missing_roles'])} roles missing",
                body="; ".join(health["missing_roles"][:10]) +
                     "\nFix in Staff_Register (see /datahealth)."))
        if health["telegram_active_without_chat_id"]:
            alerts.append(Alert(
                key=f"gap:chatids:{day}", severity="warning", level="head",
                title="Telegram_Users: active staff without Chat ID",
                body=", ".join(health["telegram_active_without_chat_id"][:10]) +
                     "\nThey cannot receive alerts. Staff get IDs from @userinfobot."))
        if health["capability_unverified"]:
            alerts.append(Alert(
                key=f"gap:cap:{day}", severity="info", level="head",
                title=f"Capability matrix: {health['capability_unverified']} unverified",
                body="Review Capability_Matrix verification statuses."))

        for r in ctx.db.open_actions():
            if not str(r.get("Owner", "")).strip() or not str(r.get("Due_Date", "")).strip():
                alerts.append(Alert(
                    key=f"gap:action:{r.get('Action_ID')}", severity="warning",
                    level="head",
                    title=f"Action {r.get('Action_ID')} has no owner/due date",
                    body=f"{r.get('Title')} — assign it in Operational_Actions."))

        for r in ctx.db.open_equipment_issues():
            opened = r.get("Date", "")
            try:
                age = (today - date.fromisoformat(opened)).days
            except ValueError:
                age = 0
            if age >= 7:
                uid = str(r.get("Unit", "")).upper()
                alerts.append(Alert(
                    key=f"gap:stale:{r.get('Issue_ID')}:{day}", severity="warning",
                    level="supervisor", unit_id=uid,
                    title=f"Equipment issue {r.get('Issue_ID')} stale ({age}d open)",
                    body=f"{r.get('Equipment')}: {r.get('Issue')} [{r.get('Severity')}]"))

        for r in ctx.db.overdue_actions(today):
            owner = str(r.get("Owner", "")).strip()
            alerts.append(Alert(
                key=f"gap:overdue:{r.get('Action_ID')}:{day}", severity="warning",
                level="therapist" if owner else "head", staff_name=owner,
                title=f"Overdue action {r.get('Action_ID')}",
                body=f"{r.get('Title')} — owner: {owner or 'unassigned'}, "
                     f"due {r.get('Due_Date')}."))
        alerts.extend(self.run_v41(ctx))
        return alerts

    def run_v41(self, ctx: Ctx) -> list[Alert]:
        """v4.1 findings: licenses, competency, leave cover, readiness, policy."""
        alerts: list[Alert] = []
        day, today = ctx.day, ctx.today

        expiring = ctx.db.licenses_expiring(30)
        if expiring:
            alerts.append(Alert(
                key=f"gap:lic:{day}", severity="info", level="head",
                title=f"Licenses expiring ≤30d ({len(expiring)})",
                body="; ".join(f"{s.get('Name')} ({s.get('License_Expiry')})"
                               for s in expiring[:8])))
        expired = ctx.db.licenses_expired()
        if expired:
            alerts.append(Alert(
                key=f"gap:licexp:{day}", severity="warning", level="head",
                title=f"EXPIRED licenses ({len(expired)})",
                body="; ".join(f"{s.get('Name')} (expired {s.get('License_Expiry')})"
                               for s in expired[:8]) + "\nRenew immediately."))

        comp = ctx.db.competency_expiring(30)
        if comp:
            alerts.append(Alert(
                key=f"gap:comp:{day}", severity="info", level="head",
                title=f"Competency assessments expiring ≤30d ({len(comp)})",
                body="; ".join(f"{r.get('Staff_Name')} ({r.get('Expiry_Date')})"
                               for r in comp[:8])))

        for r in ctx.db.uncovered_leaves(today):
            name = str(r.get("Staff_Name", ""))
            unit = next((s for s in ctx.db.staff()
                         if str(s.get("Name", "")).lower() == name.lower()), {})
            u = ctx.db.resolve_unit(str(unit.get("Unit", ""))) if unit else None
            uid = str(u.get("Unit_ID")).upper() if u else ""
            alerts.append(Alert(
                key=f"gap:cover:{day}:{r.get('Leave_ID')}", severity="warning",
                level="supervisor", unit_id=uid,
                title=f"Leave with no cover — {name}",
                body=f"{r.get('Leave_Type')} leave {r.get('Start_Date')}→"
                     f"{r.get('End_Date')} approved but Coverage_Arranged=No. "
                     f"Arrange cover in Leave_Tracker."))

        for r in ctx.db.supervisor_reports(today):
            if str(r.get("Readiness", "")).strip().lower() not in {"not ready", "red"}:
                continue
            unit = ctx.db.resolve_unit(str(r.get("Unit", "")))
            uid = str(unit.get("Unit_ID")).upper() if unit else str(r.get("Unit"))
            alerts.append(Alert(
                key=f"gap:notready:{day}:{uid}", severity="warning", level="head",
                unit_id=uid,
                title=f"Unit NOT READY — {uid}",
                body=f"{r.get('Supervisor')}: present {r.get('Present')}, "
                     f"equipment: {str(r.get('Equipment', ''))[:150]}. "
                     f"Urgent: {str(r.get('Urgent_Decision', ''))[:150]}"))

        for r in ctx.db.supervisor_reports(today):
            unit = ctx.db.resolve_unit(str(r.get("Unit", "")))
            if not unit:
                continue
            uid = str(unit.get("Unit_ID")).upper()
            minimum = ctx.db.unit_min_staff(uid)
            try:
                present = int(float(str(r.get("Present", "0")).strip()))
            except ValueError:
                continue
            if minimum and present < minimum:
                alerts.append(Alert(
                    key=f"gap:understaff:{day}:{uid}", severity="warning",
                    level="supervisor", unit_id=uid,
                    title=f"Understaffed — {uid} ({present}/{minimum} present)",
                    body="Below Min_Staff_Required. Arrange cover or escalate."))

        overdue = ctx.db.policies_overdue(today)
        if overdue:
            alerts.append(Alert(
                key=f"gap:policy:{day}", severity="info", level="head",
                title=f"Policies overdue for review ({len(overdue)})",
                body="; ".join(f"{r.get('Policy_ID')} {r.get('Title')} "
                               f"(due {r.get('Review_Date')})" for r in overdue[:8])))
        return alerts


class WatchdogAgent:
    """Critical lens. Runs every WATCHDOG_MINUTES."""

    name = "watchdog"

    def run(self, ctx: Ctx) -> list[Alert]:
        alerts: list[Alert] = []
        day, today = ctx.day, ctx.today

        for r in ctx.db.open_equipment_issues():
            if str(r.get("Severity", "")).strip().lower() == "critical":
                uid = str(r.get("Unit", "")).upper()
                for level in ("supervisor", "head"):
                    alerts.append(Alert(
                        key=f"wd:crit:{r.get('Issue_ID')}:{level}", severity="critical",
                        level=level, unit_id=uid,
                        title=f"CRITICAL equipment — {r.get('Equipment')} ({uid})",
                        body=f"{r.get('Issue')} — reported by {r.get('Reported_By')} "
                             f"on {r.get('Date')}.",
                        dedup_hours=2))

        for r in ctx.db.coverage_on(today):
            if str(r.get("Coverage_Status", "")).strip().lower() in {"uncovered", "partial"}:
                uid = str(r.get("Unit", "")).upper()
                sev = "critical" if "uncover" in str(r.get("Coverage_Status")).lower() else "warning"
                alerts.append(Alert(
                    key=f"wd:cov:{day}:{uid}", severity=sev,
                    level="supervisor", unit_id=uid,
                    title=f"Coverage {str(r.get('Coverage_Status')).lower()} — {uid}",
                    body=f"Absent: {r.get('Absent_Staff')}; covering: {r.get('Covering_Staff')}. "
                         f"{r.get('Notes', '')}".strip()))

        for r in ctx.db.open_actions():
            if str(r.get("Due_Date", "")).strip() == day:
                owner = str(r.get("Owner", "")).strip()
                alerts.append(Alert(
                    key=f"wd:due:{r.get('Action_ID')}:{day}", severity="warning",
                    level="therapist" if owner else "head", staff_name=owner,
                    title=f"Action due TODAY — {r.get('Action_ID')}",
                    body=f"{r.get('Title')} (owner: {owner or 'unassigned'})."))

        for r in ctx.db.training_expired():
            alerts.append(Alert(
                key=f"wd:exp:{r.get('Staff_Name')}:{r.get('Course')}",
                severity="warning", level="head",
                title=f"EXPIRED training — {r.get('Course')}",
                body=f"{r.get('Staff_Name')} expired {r.get('Expiry_Date')}. "
                     f"Renew immediately (Training_Tracker).",
                dedup_hours=24))

        for r in ctx.db.serious_incidents():
            u = ctx.db.resolve_unit(str(r.get("Unit", "")))
            uid = str(u.get("Unit_ID")).upper() if u else str(r.get("Unit", ""))
            meta = OpsDB.incident_public(r)
            alerts.append(Alert(
                key=f"watch:inc:{day}:{meta['Incident_ID']}", severity="critical",
                level="supervisor", unit_id=uid,
                title=f"{meta['Severity']} incident {meta['Incident_ID']}",
                body=f"{meta['Incident_Type']} in {meta['Unit']} "
                     f"({meta['Date']}, status: {meta['Status']}). "
                     f"Full details in Incident_Reports tab only — "
                     f"acknowledge and update Status there."))
        return alerts


class EscalationAgent:
    """Cutoff nudges: therapists first, supervisor summaries alongside."""

    name = "escalation"

    def run(self, ctx: Ctx) -> list[Alert]:
        alerts: list[Alert] = []
        cutoff = settings.report_cutoff
        try:
            ch, cm = (int(x) for x in cutoff.split(":"))
            past_cutoff = (ctx.now.hour, ctx.now.minute) >= (ch, cm)
        except ValueError:
            past_cutoff = True
        if not past_cutoff:
            return alerts
        day = ctx.day
        for item in ctx.db.missing_staff_reports(ctx.today):
            name, _, unit = item.partition(" (")
            unit = unit.rstrip(")").strip()
            u = ctx.db.resolve_unit(unit)
            uid = str(u.get("Unit_ID")).upper() if u else ""
            alerts.append(Alert(
                key=f"esc:nudge:{day}:{name}", severity="info",
                level="therapist", staff_name=name, unit_id=uid,
                title="Reminder: file your daily report",
                body=f"Assalamu alaikum {name.split()[0]}, your /daily report for "
                     f"{day} is still missing. It takes ~1 minute.",
                dedup_hours=24))
        return alerts


class BriefingAgent:
    """Morning briefing push (head + all supervisors with Chat IDs)."""

    name = "briefing"

    def run(self, ctx: Ctx) -> list[Alert]:
        from ops_handlers import build_briefing_text  # lazy: avoid import cycles

        text = build_briefing_text(ctx.db, ctx.today)
        alerts = [Alert(key=f"brief:{ctx.day}:head", severity="info",
                        level="head", title="Morning briefing", body=text,
                        dedup_hours=20)]
        _, head_chat = ctx.directory.section_head()
        for name, chat in ctx.directory.all_supervisor_chats().items():
            if head_chat and chat == head_chat:
                continue  # head already receives the head copy
            alerts.append(Alert(
                key=f"brief:{ctx.day}:sup:{name}", severity="info",
                level="therapist", staff_name=name,
                title="Morning briefing", body=text, dedup_hours=20))
        return alerts


class ReportAgent:
    """Automates the reports: evening rollup + weekly auto-fill + Drive archive."""

    name = "report"

    # -- evening rollup ---------------------------------------------------
    def evening_rollup(self, ctx: Ctx) -> list[Alert]:
        from report_generator import build_operational_report  # lazy
        from google_drive import drive  # lazy

        day, today = ctx.day, ctx.today
        reps = ctx.db.supervisor_reports(day)
        total_seen = sum(_to_int(r.get("Attended")) for r in reps)
        total_sched = sum(_to_int(r.get("Scheduled")) for r in reps)
        rate = round(total_seen / total_sched * 100) if total_sched else 0
        urgents = [f"{r.get('Unit')}: {r.get('Urgent_Decision')}" for r in reps
                   if str(r.get("Urgent_Decision", "")).strip()]

        for r in reps:
            unit = ctx.db.resolve_unit(str(r.get("Unit", "")))
            uid = str(unit.get("Unit_ID")).upper() if unit else str(r.get("Unit"))
            summary = (f"Auto-rollup: readiness {r.get('Readiness')}, present "
                       f"{r.get('Present')}, attendance {r.get('Attended')}/"
                       f"{r.get('Scheduled')} ({r.get('Attendance_Rate')}%), docs "
                       f"{r.get('Doc_Complete')} complete / {r.get('Doc_Incomplete')} "
                       f"incomplete, no-show {r.get('No_Show')}.")
            ctx.db.add_briefing({
                "Date": day, "Supervisor": str(r.get("Supervisor", "")),
                "Unit": uid, "Summary": summary,
                "Risks": str(r.get("Equipment", "")),
                "Decisions_Required": str(r.get("Urgent_Decision", "")),
            })

        staff_n = len(ctx.db.staff_reports(today))
        body = (f"Day {day}: {len(reps)} supervisor reports, {staff_n} staff reports.\n"
                f"Attendance {total_seen}/{total_sched} ({rate}%).\n" +
                ("Urgent decisions:\n• " + "\n• ".join(urgents) if urgents
                 else "No urgent decisions logged."))
        try:
            path = build_operational_report(
                f"## Daily Operations Rollup\n\n{body}",
                title="Daily Operations Rollup", prepared_by="Orchestra (auto)")
            res = drive.upload_file(path, folder_key="Reports", dated_subfolders=False)
            body += f"\n\nArchived: {res.get('filename')}"
        except Exception as exc:
            log.warning("Rollup archive failed: %s", exc)

        return [Alert(key=f"rollup:{day}:head", severity="info", level="head",
                      title=f"Evening rollup — {day}", body=body, dedup_hours=20)]

    # -- weekly auto-fill ----------------------------------------------------
    def weekly(self, ctx: Ctx) -> list[Alert]:
        from report_generator import build_weekly_report  # lazy
        from google_drive import drive  # lazy

        end = ctx.today - timedelta(days=1)
        start = end - timedelta(days=6)
        week_tag = f"{start.isoformat()}..{end.isoformat()}"
        lines = [f"Week {week_tag} (auto-aggregated, review required):"]
        for unit in ctx.db.units():
            uid = str(unit.get("Unit_ID", "")).upper()
            if uid == "U08":
                continue
            rows = ctx.db.supervisor_reports_between(uid, start, end)
            sched = sum(_to_int(r.get("Scheduled")) for r in rows)
            att = sum(_to_int(r.get("Attended")) for r in rows)
            rate = round(att / sched * 100) if sched else 0
            doc_c = sum(_to_int(r.get("Doc_Complete")) for r in rows)
            doc_i = sum(_to_int(r.get("Doc_Incomplete")) for r in rows)
            doc_rate = round(doc_c / (doc_c + doc_i) * 100) if (doc_c + doc_i) else 0
            ctx.db.b.append_row("Weekly_Summary", {
                "Week_Start": start.isoformat(), "Week_End": end.isoformat(),
                "Supervisor": str(unit.get("Supervisor", "")),
                "Unit": uid, "Total_Appointments": str(sched),
                "Total_Attendance": str(att), "Attendance_Rate": str(rate),
                "Documentation_Rate": str(doc_rate),
                "Completed_Actions": "", "Pending_Actions": "",
                "Risks": "Auto-filled — review required",
                "Decisions_Required": "Review auto-filled weekly draft",
            })
            lines.append(f"• {uid}: {len(rows)}/7 reports, attendance {att}/{sched} "
                         f"({rate}%), docs {doc_rate}%.")

        body = "\n".join(lines)
        try:
            path = build_weekly_report(f"## Auto Weekly Draft\n\n{body}\n\n"
                                       f"_Auto-aggregated from Daily_Supervisor_Reports. "
                                       f"Risks/decisions need human review._",
                                       prepared_by="Orchestra (auto)")
            res = drive.upload_file(path, folder_key="Reports/Weekly")
            body += f"\n\nArchived: {res.get('filename')}"
        except Exception as exc:
            log.warning("Weekly archive failed: %s", exc)

        return [
            Alert(key=f"weekly:{week_tag}:head", severity="info", level="head",
                  title="Weekly auto-draft ready", body=body, dedup_hours=72),
            Alert(key=f"weekly:{week_tag}:admin", severity="info", level="admin",
                  title="Rehab weekly summary (auto)",
                  body=body[:1200], dedup_hours=72),
        ]


class InsightAgent:
    """Gemini narrative over pre-computed stats (AI polish, numbers fixed)."""

    name = "insight"

    def run(self, ctx: Ctx, stats_text: str) -> str:
        try:
            from gemini_client import gemini  # lazy
        except Exception:
            return ""
        if gemini.demo_mode:
            return ""
        prompt = ("You are given PRE-COMPUTED department stats. Write exactly 3 "
                  "short bullets: top risk, top win, one recommended action for "
                  "tomorrow. Use ONLY these numbers — never invent figures.\n\n"
                  f"Stats:\n{stats_text}")
        out = gemini.generate(prompt)
        return out if "can't process" not in out else ""


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------
def _parse_day(value) -> Optional[date]:
    try:
        return date.fromisoformat(str(value).strip().split()[0])
    except ValueError:
        return None


class ReminderAgent:
    """Reminders + task cadence + agenda nudges. Runs on the reminders job."""

    name = "reminder"

    def run(self, ctx: Ctx) -> list[Alert]:
        alerts: list[Alert] = []
        day, today = ctx.day, ctx.today

        for r in ctx.db.due_reminders(today):
            rid = str(r.get("Reminder_ID", ""))
            title = str(r.get("Title", "")).strip()
            audience = str(r.get("Audience", "")).strip() or "All"
            notes = str(r.get("Notes", "")).strip()
            body = f"{title}\nAudience: {audience}"
            if notes:
                body += f"\n{notes[:300]}"
            self._email(ctx, audience, f"Reminder: {title}", body)
            names = ctx.db.resolve_audience(audience)
            for name in names:
                alerts.append(Alert(
                    key=f"rem:{rid}:{day}:{name}", severity="info",
                    level="therapist", staff_name=name,
                    title=f"⏰ Reminder: {title}",
                    body=f"{notes[:300]}\n_(Reminder {rid} · {audience})_"
                    if notes else f"_(Reminder {rid} · {audience})_",
                    dedup_hours=20))
            if not names:
                alerts.append(Alert(
                    key=f"rem:{rid}:{day}:unroutable", severity="warning",
                    level="head", title=f"Reminder has no audience: {rid}",
                    body=f"'{title}' (audience '{audience}') matched nobody. "
                         f"Fix the Audience in the Reminders tab."))
            once = str(r.get("Cadence", "")).strip().lower() == "once"
            ctx.db.mark_reminder_sent(rid, today, done=once)

        high_due = [r for r in ctx.db.actions_due_within(3, today)
                    if str(r.get("Priority", "")).strip().lower() == "high"]
        high_over = [r for r in ctx.db.overdue_actions(today)
                     if str(r.get("Priority", "")).strip().lower() == "high"]
        for r in high_over:
            owner = str(r.get("Owner", "")).strip()
            alerts.append(Alert(
                key=f"rem:task:{day}:{r.get('Action_ID')}", severity="warning",
                level="therapist" if owner else "head", staff_name=owner,
                title=f"🔴 HIGH task OVERDUE — {r.get('Action_ID')}",
                body=f"{r.get('Title')} (owner: {owner or 'unassigned'}, "
                     f"was due {r.get('Due_Date')}). Update status today."))
        for r in high_due:
            if r in high_over:
                continue
            owner = str(r.get("Owner", "")).strip()
            alerts.append(Alert(
                key=f"rem:task:{day}:{r.get('Action_ID')}", severity="info",
                level="therapist" if owner else "head", staff_name=owner,
                title=f"⏰ HIGH task due {r.get('Due_Date')} — "
                     f"{r.get('Action_ID')}",
                body=f"{r.get('Title')} (owner: {owner or 'unassigned'}).",
                dedup_hours=20))

        if today.strftime("%a").upper() == settings.weekly_day.upper():
            alerts += self._weekly_task_digest(ctx)

        tomorrow = today + timedelta(days=1)
        for a in ctx.db.upcoming_agendas(today, days=1):
            if _parse_day(a.get("Date")) != tomorrow:
                continue
            mid = str(a.get("Meeting_ID", ""))
            names = ctx.db.resolve_audience(str(a.get("Attendees", "")))
            for name in names:
                alerts.append(Alert(
                    key=f"agenda:{mid}:{day}:{name}", severity="info",
                    level="therapist", staff_name=name,
                    title=f"📅 Meeting tomorrow: {a.get('Title')}",
                    body=f"{str(a.get('Agenda_Items', ''))[:400]}\n_({mid})_",
                    dedup_hours=20))
        return alerts

    @staticmethod
    def _email(ctx: Ctx, audience: str, subject: str, body: str) -> int:
        try:
            from mailer import send_staff_email  # lazy
            return send_staff_email(ctx.db, audience, subject, body)
        except Exception as exc:
            log.debug("Reminder email skipped: %s", exc)
            return 0

    def _weekly_task_digest(self, ctx: Ctx) -> list[Alert]:
        by_unit: dict[str, list[dict]] = {}
        for r in ctx.db.open_actions():
            owner = str(r.get("Owner", "")).strip()
            uid = ""
            for s in ctx.db.staff():
                if str(s.get("Name", "")).strip().lower() == owner.lower():
                    u = ctx.db.resolve_unit(str(s.get("Unit", "")))
                    uid = str(u.get("Unit_ID")).upper() if u else ""
                    break
            by_unit.setdefault(uid or "UNASSIGNED", []).append(r)
        alerts = []
        for uid, rows in sorted(by_unit.items()):
            lines = [f"• {r.get('Action_ID')} [{r.get('Priority')}] "
                     f"{r.get('Title')} — {r.get('Owner')} "
                     f"(due {r.get('Due_Date')})" for r in rows[:12]]
            if len(rows) > 12:
                lines.append(f"_+{len(rows) - 12} more_")
            alerts.append(Alert(
                key=f"taskdigest:{ctx.day}:{uid}", severity="info",
                level="supervisor" if uid != "UNASSIGNED" else "head",
                unit_id=uid if uid != "UNASSIGNED" else "",
                title=f"🗂️ Weekly task digest — {uid} ({len(rows)} open)",
                body="\n".join(lines), dedup_hours=24 * 6))
        return alerts


class EvaluationAgent:
    """Monthly staff evaluation. Runs on the evaluation job (EVAL_DAY)."""

    name = "evaluation"

    def run(self, ctx: Ctx) -> list[Alert]:
        from staff_eval import (format_head_summary, format_unit_digest,
                                month_label, month_range, previous_month,
                                run_monthly_evaluation)
        year, month = previous_month(ctx.today)
        label = month_label(year, month)
        if ctx.db.evaluations_for(label):
            return []  # already computed + announced (restart-safe)
        start, end = month_range(year, month)
        if not ctx.db.staff_reports_between(start, end):
            log.info("Evaluation %s skipped: no reports filed that month.",
                     label)
            return []
        _, rows = run_monthly_evaluation(ctx.db, ctx.today)
        if not rows:
            return []
        try:
            from mailer import send_staff_email  # lazy
        except Exception:
            send_staff_email = None  # type: ignore[assignment]

        alerts: list[Alert] = []
        by_unit: dict[str, list[dict]] = {}
        for r in rows:
            by_unit.setdefault(str(r.get("Unit", "—")), []).append(r)
        for unit_name, urows in sorted(by_unit.items()):
            digest = format_unit_digest(unit_name, urows)
            unit = ctx.db.resolve_unit(unit_name)
            uid = str(unit.get("Unit_ID")).upper() if unit else ""
            alerts.append(Alert(
                key=f"eval:{label}:{uid or unit_name}", severity="info",
                level="supervisor" if uid else "head", unit_id=uid,
                title=f"Monthly evaluation — {unit_name} ({label})",
                body=digest, dedup_hours=24 * 32))
            if send_staff_email:
                try:
                    send_staff_email(ctx.db, unit_name,
                                     f"Monthly evaluation {label}", digest)
                except Exception as exc:
                    log.debug("Eval email skipped: %s", exc)
        summary = format_head_summary(rows)
        alerts.append(Alert(
            key=f"eval:{label}:head", severity="info", level="head",
            title=f"Monthly evaluation summary ({label})",
            body=summary, dedup_hours=24 * 32))
        if send_staff_email:
            try:
                head_name, _ = ctx.directory.section_head()
                if head_name:
                    send_staff_email(ctx.db, head_name,
                                     f"Monthly evaluation summary {label}",
                                     summary)
            except Exception as exc:
                log.debug("Eval head email skipped: %s", exc)
        return alerts


class Orchestrator:
    """Runs agents per job, routes alerts, dedups, audits."""

    def __init__(self, db: OpsDB, state_path: Optional[Path] = None) -> None:
        self.db = db
        self.directory = Directory(db)
        self.state_path = state_path or (settings.output_dir / "orchestra_state.json")
        self.state: dict[str, str] = self._load_state()
        self.gap = GapAgent()
        self.watchdog = WatchdogAgent()
        self.escalation = EscalationAgent()
        self.briefing = BriefingAgent()
        self.report = ReportAgent()
        self.insight = InsightAgent()
        self.reminder = ReminderAgent()
        self.evaluation = EvaluationAgent()

    # -- state -------------------------------------------------------------
    def _load_state(self) -> dict[str, str]:
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            log.debug("Orchestra state load skipped: %s", exc)
        return {}

    def _save_state(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            # prune entries older than 7 days
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            self.state = {k: v for k, v in self.state.items() if v > cutoff}
            self.state_path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")
        except Exception as exc:
            log.debug("Orchestra state save skipped: %s", exc)

    def _suppressed(self, alert: Alert, now: datetime) -> bool:
        last = self.state.get(alert.key)
        if not last:
            return False
        try:
            sent = datetime.fromisoformat(last)
        except ValueError:
            return False
        window = alert.dedup_window() * 3600
        return (now - sent.replace(tzinfo=None)).total_seconds() < window

    # -- tick ---------------------------------------------------------------
    def tick(self, now: datetime, jobs: list[str]) -> list[OutboxMessage]:
        """Run jobs, return deliverable outbox. Never raises."""
        from audit import audit  # lazy: avoid import cycles

        ctx = Ctx(self.db, now.replace(tzinfo=None), self.directory)
        alerts: list[Alert] = []
        try:
            if "briefing" in jobs:
                alerts += self.briefing.run(ctx)
            if "gaps" in jobs:
                alerts += self.gap.run(ctx)
                alerts += self.escalation.run(ctx)
            if "watchdog" in jobs:
                alerts += self.watchdog.run(ctx)
            if "rollup" in jobs:
                alerts += self.report.evening_rollup(ctx)
            if "weekly" in jobs:
                alerts += self.report.weekly(ctx)
            if "reminders" in jobs:
                alerts += self.reminder.run(ctx)
            if "evaluation" in jobs:
                alerts += self.evaluation.run(ctx)
        except Exception as exc:
            log.exception("Orchestrator job failed: %s", exc)

        outbox: list[OutboxMessage] = []
        skipped_quiet = skipped_dup = unroutable = 0
        quiet = in_quiet_hours(ctx.now)
        for alert in alerts:
            if quiet and alert.severity != "critical":
                skipped_quiet += 1
                continue
            if self._suppressed(alert, ctx.now):
                skipped_dup += 1
                continue
            rcpt = self.directory.resolve(alert.level, alert.staff_name, alert.unit_id)
            if not rcpt.chat_id:
                unroutable += 1
                audit.log("alert_unroutable", "", "",
                          f"{alert.key} target={rcpt.note[:150]}")
                continue
            icon = SEV_ICON.get(alert.severity, "ℹ️")
            text = f"{icon} *{alert.title}*\n\n{alert.body}"
            if rcpt.note:
                text += f"\n\n_{rcpt.note}_"
            outbox.append(OutboxMessage(chat_id=rcpt.chat_id, text=text,
                                       level=rcpt.level, key=alert.key,
                                       meta={"severity": alert.severity,
                                             "to": rcpt.label}))
            self.state[alert.key] = ctx.now.isoformat()
            if alert.severity == "critical":
                audit.log("alert_critical", rcpt.chat_id, rcpt.label,
                          f"{alert.key} {alert.title[:120]}")
        self._save_state()
        audit.log("orchestra_tick", "", "",
                  f"jobs={','.join(jobs)} alerts={len(alerts)} "
                  f"send={len(outbox)} dup={skipped_dup} quiet={skipped_quiet} "
                  f"unroutable={unroutable}")
        return outbox
