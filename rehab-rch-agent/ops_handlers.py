"""Agent v3 operations handlers — Rehab_Operations_Master_v2 sheet.

Commands (all require ops-sheet connection + staff auth):
    /briefing     — morning ops briefing (deterministic, computed numbers)
    /daily        — guided daily STAFF report → Daily_Staff_Reports
    /supervisor   — guided daily SUPERVISOR report → Daily_Supervisor_Reports
    /actions      — list open actions (+ guided add)
    /equipment    — list open equipment issues (+ guided log)
    /dashboard    — sheet Dashboard KPIs
    /staff [name] — staff directory lookup
    /units        — units + supervisors
    /datahealth   — data-quality findings (missing roles, chat IDs, ...)
    /setup        — create missing tabs + headers (admins only)
    /leave        — my leave requests (+ pending approvals for managers)
    /leave_add    — request leave (guided, → Leave_Tracker as Pending)
    /leave_approve— approve leave (supervisor/head, own unit only)
    /incidents    — open incidents, metadata only (details live in sheet)
    /incident_add — log an incident (guided, metadata only, PHI-screened)
    /capability   — my/team capability & competency status
    /policies     — policy register + overdue reviews
    /status       — my staff record, license, leave, capabilities
    /whoison      — who is on approved leave today (+ cover status)
    /coverage     — today's coverage vs minimum staffing

Registered into the bot via :func:`register_ops_handlers` (called from
bot.py). Number formatting is deterministic — Gemini is never asked to
compute or restate metrics, so figures can't be hallucinated.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from audit import audit
from auth import is_admin, staff_auth
from safety import contains_phi
from sheets_ops import OpsDB, get_ops_db

log = logging.getLogger("ops")

# Conversation states (module-local ranges to avoid clashes with bot.py)
(D_UNIT, D_SEEN, D_NEW, D_FOLLOW, D_DOC, D_ISSUES, D_TOMORROW) = range(100, 107)
(S_UNIT, S_READY, S_STAFF, S_ATTEND, S_DOC, S_EQUIP, S_URGENT) = range(110, 117)
(A_TITLE, A_OWNER, A_DUE, A_PRIORITY) = range(120, 124)
(E_UNIT, E_EQUIP, E_ISSUE, E_SEV) = range(130, 134)
(L_TYPE, L_START, L_END, L_NOTES) = range(140, 144)
(I_UNIT, I_TYPE, I_SEV, I_ACTION) = range(150, 154)


# ----------------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------------
async def _me(update: Update):
    """Authorized staff member or None (private staff chats only)."""
    from auth import is_private_chat  # local: staff-only gate

    if not is_private_chat(update):
        audit.log("group_blocked", getattr(update.effective_user, "id", "?"),
                  "", "flow=ops")
        return None  # silent in groups/channels: no data, no hints
    user = update.effective_user
    if user is None or not staff_auth.is_authorized(user.id):
        audit.log("auth_denied", getattr(user, "id", "?"),
                  getattr(user, "full_name", ""), "flow=ops")
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔒 Access denied.\n\nContact Rehabilitation Section Head.")
        return None
    return staff_auth.get_staff(user.id)


async def _db_or_msg(update: Update) -> Optional[OpsDB]:
    db = get_ops_db()
    if db is None and update.effective_message:
        await update.effective_message.reply_text(
            "📊 Operations sheet not connected.\n\n"
            "Set OPS_SHEET_ID in .env (the Rehab_Operations_Master_v2 Google "
            "Sheet ID), share it with the service account as Editor, restart, "
            "then run /setup.\nSee docs/SHEETS_OPS.md")
    return db


async def _send_long(update: Update, text: str, chunk: int = 3500) -> None:
    assert update.message is not None
    for i in range(0, max(len(text), 1), chunk):
        await update.message.reply_text(text[i:i + chunk])


def _staff_name(update: Update) -> str:
    try:
        staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
        return staff.display() if staff else ""
    except Exception:
        return ""


async def _phi_block(update: Update, text: str, flow: str) -> None:
    result = contains_phi(text)
    audit.log("phi_blocked", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update),
              f"flow={flow} reasons={'; '.join(result.reasons)[:200]}")
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ This request can't be processed.\n\n"
            "Operational counts only — no patient information in reports. "
            "Please resubmit without patient details.")


def _none(text: str) -> bool:
    return text.strip().lower() in {"", "none", "no", "nil", "-", "n/a", "skip"}


def _parse_ints(text: str, count: int) -> Optional[list[int]]:
    parts = text.replace(",", " ").split()
    if len(parts) != count:
        return None
    try:
        return [int(float(p)) for p in parts]
    except ValueError:
        return None


# ----------------------------------------------------------------------------
# Pure briefing / formatting builders (reused by demo_ops.py)
# ----------------------------------------------------------------------------
def build_briefing_text(db: OpsDB, day: Optional[date] = None) -> str:
    """Deterministic morning briefing — computed numbers only, no AI."""
    day = day or date.today()
    kpis = db.dashboard()
    sup_reports = {str(r.get("Unit")).upper(): r for r in db.supervisor_reports(day)}
    staff_reports = db.staff_reports(day)
    missing_units = db.missing_supervisor_reports(day)
    missing_staff = db.missing_staff_reports(day)
    actions = db.open_actions()
    overdue = db.overdue_actions(day)
    issues = db.open_equipment_issues()
    expiring = db.training_expiring(30)
    expired = db.training_expired()
    coverage = db.coverage_on(day)

    lines = [f"🌅 *Morning Briefing — {day.strftime('%A %d %b %Y')}*", ""]
    lines.append("📊 *Dashboard*")
    for kpi in ("Reports Received Today", "Weekly Attendance %",
                "Documentation Compliance %", "Open Issues", "Pending Actions"):
        if kpis.get(kpi):
            lines.append(f"• {kpi}: {kpis[kpi]}")
    if not any(kpis.get(k) for k in ("Reports Received Today",)):
        lines.append(f"• Staff reports filed today: {len(staff_reports)}")
    lines.append("")

    lines.append("🏥 *Unit readiness*")
    any_reports = False
    for unit in db.units():
        uid = str(unit.get("Unit_ID")).upper()
        if uid == "U08":
            continue
        rep = sup_reports.get(uid) or sup_reports.get(str(unit.get("Unit_Name")).upper())
        if not rep:
            continue
        any_reports = True
        ready = str(rep.get("Readiness") or "?")
        icon = {"ready": "✅", "partial": "⚠️"}.get(ready.lower(), "❌")
        present = rep.get("Present", "?")
        lines.append(f"{icon} {uid} {unit.get('Unit_Name')} — {ready} (present {present})")
        urgent = str(rep.get("Urgent_Decision") or "").strip()
        if urgent and urgent.lower() != "none":
            lines.append(f"   🚨 Urgent: {urgent[:120]}")
    if not any_reports:
        lines.append("No supervisor reports filed yet today.")
    if missing_units:
        lines.append(f"❌ Missing supervisor reports: {', '.join(missing_units)}")
    lines.append("")

    if missing_staff:
        shown = "; ".join(missing_staff[:8])
        extra = f" (+{len(missing_staff) - 8} more)" if len(missing_staff) > 8 else ""
        lines.append(f"📝 *Staff reports missing ({len(missing_staff)}):* {shown}{extra}")
    else:
        lines.append("📝 All expected staff reports received. ✅")
    lines.append("")

    if overdue:
        lines.append(f"🔴 *Overdue actions ({len(overdue)}):*")
        for r in overdue[:5]:
            lines.append(f"• {r.get('Action_ID')} — {r.get('Title')} "
                         f"(owner: {r.get('Owner')}, due {r.get('Due_Date')})")
    if actions:
        rest = [r for r in actions if r not in overdue]
        if rest:
            lines.append(f"📌 *Open actions ({len(actions)}):*")
            for r in rest[:5]:
                lines.append(f"• {r.get('Action_ID')} — {r.get('Title')} "
                             f"(owner: {r.get('Owner')}, due {r.get('Due_Date')})")
    else:
        lines.append("📌 No open actions. ✅")
    lines.append("")

    if issues:
        lines.append(f"🔧 *Open equipment issues ({len(issues)}):*")
        for r in issues[:5]:
            lines.append(f"• {r.get('Issue_ID')} [{r.get('Unit')}] {r.get('Equipment')}: "
                         f"{r.get('Issue')} ({r.get('Severity')})")
    else:
        lines.append("🔧 No open equipment issues. ✅")
    lines.append("")

    for row in coverage:
        if str(row.get("Coverage_Status")).lower() != "covered":
            lines.append(f"👥 Coverage {row.get('Unit')}: {row.get('Coverage_Status')} "
                         f"— absent: {row.get('Absent_Staff')}; "
                         f"covering: {row.get('Covering_Staff')}")
    for r in expired:
        lines.append(f"🎓 EXPIRED: {r.get('Course')} — {r.get('Staff_Name')} "
                     f"(expired {r.get('Expiry_Date')})")
    for r in expiring:
        lines.append(f"🎓 Expiring ≤30d: {r.get('Course')} — {r.get('Staff_Name')} "
                     f"(expires {r.get('Expiry_Date')})")
    lines.append("")
    lines.append("_Figures computed from Rehab_Operations_Master_v2. Draft for review._")
    return "\n".join(lines)


def format_units(db: OpsDB) -> str:
    lines = ["🏥 *Rehabilitation Units*"]
    for u in db.units():
        lines.append(f"• {u.get('Unit_ID')} — {u.get('Unit_Name')} "
                     f"(supervisor: {u.get('Supervisor') or '—'})")
    return "\n".join(lines)


def format_dashboard(db: OpsDB) -> str:
    kpis = db.dashboard()
    if not kpis:
        return "📊 Dashboard sheet is empty."
    lines = ["📊 *Dashboard KPIs*"]
    for kpi, val in kpis.items():
        lines.append(f"• {kpi}: {val}")
    return "\n".join(lines)


def format_actions(db: OpsDB) -> str:
    actions = db.open_actions()
    if not actions:
        return "📌 No open actions. ✅"
    overdue_ids = {r.get("Action_ID") for r in db.overdue_actions()}
    lines = [f"📌 *Open actions ({len(actions)})*"]
    for r in actions[:15]:
        flag = "🔴 OVERDUE " if r.get("Action_ID") in overdue_ids else ""
        lines.append(f"• {flag}{r.get('Action_ID')} — {r.get('Title')}\n"
                     f"  Owner: {r.get('Owner')} | Due: {r.get('Due_Date')} | "
                     f"{r.get('Priority')} | {r.get('Status')}")
    if len(actions) > 15:
        lines.append(f"_+{len(actions) - 15} more_")
    lines.append("\n_Add: /actions_add_")
    return "\n".join(lines)


def format_equipment(db: OpsDB) -> str:
    issues = db.open_equipment_issues()
    if not issues:
        return "🔧 No open equipment issues. ✅"
    lines = [f"🔧 *Open equipment issues ({len(issues)})*"]
    for r in issues[:15]:
        lines.append(f"• {r.get('Issue_ID')} [{r.get('Unit')}] {r.get('Equipment')}: "
                     f"{r.get('Issue')} — {r.get('Severity')} "
                     f"(reported by {r.get('Reported_By')})")
    if len(issues) > 15:
        lines.append(f"_+{len(issues) - 15} more_")
    lines.append("\n_Log: /equipment_add_")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Read commands
# ----------------------------------------------------------------------------
async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    await _send_long(update, build_briefing_text(db))
    audit.log("briefing_viewed", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update), f"date={date.today().isoformat()}")


async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    await update.message.reply_text(format_dashboard(db))  # type: ignore[union-attr]


async def cmd_units(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    await update.message.reply_text(format_units(db))  # type: ignore[union-attr]


async def cmd_staff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    query = " ".join(context.args or []).strip()
    if not query:
        counts: dict[str, int] = {}
        for s in db.staff():
            counts[s.get("Unit", "?")] = counts.get(s.get("Unit", "?"), 0) + 1
        lines = [f"👥 *Staff register ({len(db.staff())})*"]
        for unit, n in sorted(counts.items()):
            lines.append(f"• {unit}: {n}")
        lines.append("\n_Search: /staff <name>_")
        await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]
        return
    hits = db.find_staff(query)
    if not hits:
        await update.message.reply_text(f"No staff matching '{query}'.")  # type: ignore[union-attr]
        return
    lines = [f"👥 *{len(hits)} match(es)*"]
    for s in hits[:10]:
        role = s.get("Role") or "⚠️ role missing"
        lines.append(f"• {s.get('Name')} — {s.get('Unit')} ({role})")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def cmd_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    await _send_long(update, format_actions(db))


async def cmd_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    await _send_long(update, format_equipment(db))


async def cmd_datahealth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    h = db.datahealth()
    lines = ["🩺 *Data health — Rehab_Operations_Master_v2*",
             f"Staff: {h['staff_count']} | Units: {len(db.units())}"]
    if h["missing_roles"]:
        lines.append(f"\n⚠️ Missing roles ({len(h['missing_roles'])}):")
        for item in h["missing_roles"][:12]:
            lines.append(f"• {item}")
        if len(h["missing_roles"]) > 12:
            lines.append(f"_+{len(h['missing_roles']) - 12} more_")
    else:
        lines.append("\n✅ All staff have roles.")
    if h["units_without_supervisor"]:
        lines.append(f"⚠️ Units without supervisor: {', '.join(h['units_without_supervisor'])}")
    if h["telegram_active_without_chat_id"]:
        lines.append(f"⚠️ Telegram_Users active without Chat ID "
                     f"({len(h['telegram_active_without_chat_id'])}): "
                     + ", ".join(h["telegram_active_without_chat_id"][:8]))
    lines.append(f"\nCapability matrix: {h['capability_rows']} rows, "
                 f"{h['capability_unverified']} unverified.")
    await _send_long(update, "\n".join(lines))


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    if not is_admin(update.effective_user.id):  # type: ignore[union-attr]
        await update.message.reply_text("🔒 Admins only.")  # type: ignore[union-attr]
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    status = db.ensure_schema()
    created = [t for t, s in status.items() if s == "created"]
    fixed = [t for t, s in status.items() if s == "header-fixed"]
    await update.message.reply_text(  # type: ignore[union-attr]
        f"🧩 Ops sheet schema: {len(status)} tabs checked.\n"
        f"Created: {', '.join(created) or '—'}\n"
        f"Headers fixed: {', '.join(fixed) or '—'}\n"
        f"Existing: {len(status) - len(created) - len(fixed)}")
    audit.log("ops_setup", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update), f"created={len(created)} fixed={len(fixed)}")


async def ops_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Type /help for commands.")  # type: ignore[union-attr]
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# /daily — staff report flow
# ----------------------------------------------------------------------------
async def daily_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await _me(update) is None:
        return ConversationHandler.END
    db = await _db_or_msg(update)
    if db is None:
        return ConversationHandler.END
    context.user_data["ops_report"] = {}
    units = ", ".join(f"{u.get('Unit_ID')}" for u in db.units() if u.get("Unit_ID") != "U08")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"📝 *Daily staff report — {date.today():%d %b %Y}*\n\n"
        f"Which unit? ({units}, or unit name)\n(/cancel to stop)")
    return D_UNIT


async def _daily_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = get_ops_db()
    assert db is not None
    unit = db.resolve_unit(update.message.text or "")  # type: ignore[union-attr]
    if unit is None or unit.get("Unit_ID") == "U08":
        await update.message.reply_text("Unknown unit — reply like U01, or the unit name.")  # type: ignore[union-attr]
        return D_UNIT
    context.user_data["ops_report"]["Unit"] = unit["Unit_ID"]
    await update.message.reply_text("Patients seen today? (number)")  # type: ignore[union-attr]
    return D_SEEN


async def _daily_number(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        field: str, prompt: str) -> int:
    nums = _parse_ints(update.message.text or "", 1)  # type: ignore[union-attr]
    if nums is None or nums[0] < 0:
        await update.message.reply_text("Please reply with a number (0 or more).")  # type: ignore[union-attr]
        return _state_of(field)
    context.user_data["ops_report"][field] = str(nums[0])
    await update.message.reply_text(prompt)  # type: ignore[union-attr]
    return _next_of(field)


def _state_of(field: str) -> int:
    return {"Patients_Seen": D_SEEN, "New_Cases": D_NEW,
            "Follow_Up_Cases": D_FOLLOW}[field]


def _next_of(field: str) -> int:
    return {"Patients_Seen": D_NEW, "New_Cases": D_FOLLOW,
            "Follow_Up_Cases": D_DOC}[field]


async def daily_seen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _daily_number(update, context, "Patients_Seen",
                               "New cases today? (number)")


async def daily_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _daily_number(update, context, "New_Cases",
                               "Follow-up cases today? (number)")


async def daily_follow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _daily_number(update, context, "Follow_Up_Cases",
                               "Documentation status? (Complete, or Incomplete + note)")


async def daily_doc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "daily_doc")
        return ConversationHandler.END
    context.user_data["ops_report"]["Documentation_Status"] = text[:200]
    await update.message.reply_text("Any issues? (or 'none' — counts only, no patient details)")  # type: ignore[union-attr]
    return D_ISSUES


async def daily_issues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "daily_issues")
        return ConversationHandler.END
    context.user_data["ops_report"]["Issues"] = "" if _none(text) else text[:300]
    await update.message.reply_text("Follow-up for tomorrow? (or 'none')")  # type: ignore[union-attr]
    return D_TOMORROW


async def daily_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "daily_tomorrow")
        return ConversationHandler.END
    db = get_ops_db()
    assert db is not None
    staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
    row = dict(context.user_data.get("ops_report", {}))
    row.update({
        "Report_Date": date.today().isoformat(),
        "Staff_Name": staff.name if staff else "?",
        "Follow_Up_Tomorrow": "" if _none(text) else text[:300],
        "Submitted_Time": datetime.now().strftime("%H:%M"),
    })
    db.add_staff_report(row)
    audit.log("daily_report", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update),
              f"unit={row.get('Unit')} seen={row.get('Patients_Seen')}")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ Daily report saved to Daily_Staff_Reports.\n"
        f"Unit {row.get('Unit')} | Seen {row.get('Patients_Seen')} "
        f"(new {row.get('New_Cases')}, follow-up {row.get('Follow_Up_Cases')}) | "
        f"Docs: {row.get('Documentation_Status')}")
    context.user_data.clear()
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# /supervisor — supervisor report flow
# ----------------------------------------------------------------------------
async def sup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await _me(update) is None:
        return ConversationHandler.END
    db = await _db_or_msg(update)
    if db is None:
        return ConversationHandler.END
    context.user_data["ops_report"] = {}
    await update.message.reply_text(  # type: ignore[union-attr]
        f"🧑‍⚕️ *Daily supervisor report — {date.today():%d %b %Y}*\n\nWhich unit? (U01–U07)")
    return S_UNIT


async def sup_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = get_ops_db()
    assert db is not None
    unit = db.resolve_unit(update.message.text or "")  # type: ignore[union-attr]
    if unit is None or unit.get("Unit_ID") not in {"U01", "U02", "U03", "U04", "U05", "U06", "U07"}:
        await update.message.reply_text("Unknown unit — reply U01 to U07.")  # type: ignore[union-attr]
        return S_UNIT
    context.user_data["ops_report"]["Unit"] = unit["Unit_ID"]
    await update.message.reply_text("Readiness? (Ready / Partial / Not Ready)")  # type: ignore[union-attr]
    return S_READY


async def sup_ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip().capitalize()  # type: ignore[union-attr]
    if text not in {"Ready", "Partial", "Not ready"}:
        await update.message.reply_text("Reply: Ready / Partial / Not Ready")  # type: ignore[union-attr]
        return S_READY
    context.user_data["ops_report"]["Readiness"] = text
    await update.message.reply_text("Staffing — 4 numbers: present leave sick_leave absent\n(e.g. 6 1 0 0)")  # type: ignore[union-attr]
    return S_STAFF


async def sup_staff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nums = _parse_ints(update.message.text or "", 4)  # type: ignore[union-attr]
    if nums is None or any(n < 0 for n in nums):
        await update.message.reply_text("Send 4 numbers: present leave sick_leave absent")  # type: ignore[union-attr]
        return S_STAFF
    for key, val in zip(("Present", "Leave", "Sick_Leave", "Absent"), nums):
        context.user_data["ops_report"][key] = str(val)
    await update.message.reply_text("Attendance — 3 numbers: scheduled attended no_show\n(e.g. 42 39 3)")  # type: ignore[union-attr]
    return S_ATTEND


async def sup_attend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nums = _parse_ints(update.message.text or "", 3)  # type: ignore[union-attr]
    if nums is None or any(n < 0 for n in nums):
        await update.message.reply_text("Send 3 numbers: scheduled attended no_show")  # type: ignore[union-attr]
        return S_ATTEND
    sched, att, _ = nums
    for key, val in zip(("Scheduled", "Attended", "No_Show"), nums):
        context.user_data["ops_report"][key] = str(val)
    context.user_data["ops_report"]["Attendance_Rate"] = str(round(att / sched * 100)) if sched else "0"
    await update.message.reply_text("Documentation — 2 numbers: complete incomplete\n(e.g. 39 0)")  # type: ignore[union-attr]
    return S_DOC


async def sup_doc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nums = _parse_ints(update.message.text or "", 2)  # type: ignore[union-attr]
    if nums is None or any(n < 0 for n in nums):
        await update.message.reply_text("Send 2 numbers: doc_complete doc_incomplete")  # type: ignore[union-attr]
        return S_DOC
    context.user_data["ops_report"]["Doc_Complete"] = str(nums[0])
    context.user_data["ops_report"]["Doc_Incomplete"] = str(nums[1])
    await update.message.reply_text("Equipment? (OK, or describe the issue — no patient details)")  # type: ignore[union-attr]
    return S_EQUIP


async def sup_equip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "sup_equip")
        return ConversationHandler.END
    context.user_data["ops_report"]["Equipment"] = text[:300]
    await update.message.reply_text("Urgent decision needed? (or 'none')")  # type: ignore[union-attr]
    return S_URGENT


async def sup_urgent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "sup_urgent")
        return ConversationHandler.END
    db = get_ops_db()
    assert db is not None
    staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
    row = dict(context.user_data.get("ops_report", {}))
    row.update({
        "Date": date.today().isoformat(),
        "Supervisor": staff.name if staff else "?",
        "Urgent_Decision": "" if _none(text) else text[:300],
    })
    db.add_supervisor_report(row)
    audit.log("supervisor_report", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update),
              f"unit={row.get('Unit')} readiness={row.get('Readiness')}")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ Supervisor report saved.\nUnit {row.get('Unit')} | {row.get('Readiness')} | "
        f"Attendance {row.get('Attendance_Rate')}% | Docs {row.get('Doc_Complete')}/"
        f"{int(row.get('Doc_Complete', 0)) + int(row.get('Doc_Incomplete', 0))} complete")
    context.user_data.clear()
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# /actions_add and /equipment_add flows
# ----------------------------------------------------------------------------
async def actions_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await _me(update) is None:
        return ConversationHandler.END
    if await _db_or_msg(update) is None:
        return ConversationHandler.END
    context.user_data["ops_new"] = {"Source": "Telegram"}
    await update.message.reply_text("📌 New action — title?")  # type: ignore[union-attr]
    return A_TITLE


async def actions_add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "action_title")
        return ConversationHandler.END
    context.user_data["ops_new"]["Title"] = text[:200]
    await update.message.reply_text("Owner? (staff name)")  # type: ignore[union-attr]
    return A_OWNER


async def actions_add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    context.user_data["ops_new"]["Owner"] = text[:100]
    await update.message.reply_text("Due date? (YYYY-MM-DD)")  # type: ignore[union-attr]
    return A_DUE


async def actions_add_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Use YYYY-MM-DD, e.g. 2026-09-20")  # type: ignore[union-attr]
        return A_DUE
    context.user_data["ops_new"]["Due_Date"] = text
    await update.message.reply_text("Priority? (High / Medium / Low)")  # type: ignore[union-attr]
    return A_PRIORITY


async def actions_add_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip().capitalize()  # type: ignore[union-attr]
    if text not in {"High", "Medium", "Low"}:
        await update.message.reply_text("Reply: High / Medium / Low")  # type: ignore[union-attr]
        return A_PRIORITY
    db = get_ops_db()
    assert db is not None
    row = dict(context.user_data.get("ops_new", {}))
    row["Priority"] = text
    action_id = db.add_action(row)
    audit.log("action_added", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update), f"{action_id} {row.get('Title', '')[:80]}")
    await update.message.reply_text(f"✅ Action {action_id} saved (owner: {row.get('Owner')}, due {row.get('Due_Date')}).")  # type: ignore[union-attr]
    context.user_data.clear()
    return ConversationHandler.END


async def equip_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await _me(update) is None:
        return ConversationHandler.END
    if await _db_or_msg(update) is None:
        return ConversationHandler.END
    context.user_data["ops_new"] = {}
    await update.message.reply_text("🔧 New equipment issue — which unit? (U01–U07)")  # type: ignore[union-attr]
    return E_UNIT


async def equip_add_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = get_ops_db()
    assert db is not None
    unit = db.resolve_unit(update.message.text or "")  # type: ignore[union-attr]
    if unit is None or unit.get("Unit_ID") == "U08":
        await update.message.reply_text("Unknown unit — reply U01 to U07.")  # type: ignore[union-attr]
        return E_UNIT
    context.user_data["ops_new"]["Unit"] = unit["Unit_ID"]
    await update.message.reply_text("Equipment name? (e.g. Ultrasound probe)")  # type: ignore[union-attr]
    return E_EQUIP


async def equip_add_equip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "equip_name")
        return ConversationHandler.END
    context.user_data["ops_new"]["Equipment"] = text[:150]
    await update.message.reply_text("Describe the issue (no patient details)?")  # type: ignore[union-attr]
    return E_ISSUE


async def equip_add_issue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "equip_issue")
        return ConversationHandler.END
    context.user_data["ops_new"]["Issue"] = text[:300]
    await update.message.reply_text("Severity? (Low / Medium / High / Critical)")  # type: ignore[union-attr]
    return E_SEV


async def equip_add_sev(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip().capitalize()  # type: ignore[union-attr]
    if text not in {"Low", "Medium", "High", "Critical"}:
        await update.message.reply_text("Reply: Low / Medium / High / Critical")  # type: ignore[union-attr]
        return E_SEV
    db = get_ops_db()
    assert db is not None
    staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
    row = dict(context.user_data.get("ops_new", {}))
    row.update({"Severity": text, "Reported_By": staff.name if staff else "?"})
    issue_id = db.add_equipment_issue(row)
    audit.log("equipment_issue", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update), f"{issue_id} [{row.get('Unit')}] {text}")
    await update.message.reply_text(f"✅ Issue {issue_id} logged ({row.get('Unit')} — {row.get('Equipment')}, {text}).")  # type: ignore[union-attr]
    context.user_data.clear()
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# /register — self-provisioning (+ admin /approve)
# ----------------------------------------------------------------------------
(R_NAME, R_UNIT) = range(140, 142)


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/register <code> — code-gated self-enrollment (no prior auth needed)."""
    from auth import check_enroll_code, is_private_chat  # local: staff-only gates

    if not is_private_chat(update):
        return ConversationHandler.END  # silent outside private chats
    code = " ".join(context.args or []).strip()
    if not check_enroll_code(code):
        audit.log("enroll_denied", getattr(update.effective_user, "id", "?"),
                  getattr(update.effective_user, "full_name", ""))
        await update.message.reply_text(  # type: ignore[union-attr]
            "🔒 Registration requires a staff enrollment code.\n\n"
            "Ask your supervisor for the code, then send:\n/register <code>")
        return ConversationHandler.END
    db = await _db_or_msg(update)
    if db is None:
        return ConversationHandler.END
    await update.message.reply_text(  # type: ignore[union-attr]
        "📲 *Register for Rehab RCH alerts*\n\n"
        "Full name exactly as in Staff_Register?\n(/cancel to stop)")
    return R_NAME


async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = get_ops_db()
    assert db is not None
    name = (update.message.text or "").strip()  # type: ignore[union-attr]
    if not db.find_staff(name) and not any(
            _s2(s.get("Name")) == _s2(name) for s in db.staff()):
        await update.message.reply_text(  # type: ignore[union-attr]
            f"'{name}' is not in Staff_Register. Check spelling or ask your "
            f"supervisor to add you, then try again.")
        return ConversationHandler.END
    context.user_data["reg_name"] = next(
        _s2(s.get("Name")) for s in db.staff()
        if _s2(s.get("Name")) == _s2(name) or _s2(name) in _s2(s.get("Name")))
    await update.message.reply_text("Your unit? (U01–U08 or name)")  # type: ignore[union-attr]
    return R_UNIT


def _s2(value) -> str:
    return str(value or "").strip()


async def register_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = get_ops_db()
    assert db is not None
    unit = db.resolve_unit(update.message.text or "")  # type: ignore[union-attr]
    if unit is None:
        await update.message.reply_text("Unknown unit — reply U01–U08 or the unit name.")  # type: ignore[union-attr]
        return R_UNIT
    user = update.effective_user
    assert user is not None
    name = context.user_data.get("reg_name", "")
    existing = [r for r in db.telegram_users(active_only=False)
                if _s2(r.get("Staff_Name")).lower() == name.lower()]
    already_active = existing and _s2(existing[0].get("Active")).lower() in {
        "true", "yes", "active", "1", "y"}
    db.upsert_telegram_user(
        name, unit["Unit_ID"], f"@{user.username}" if user.username else "",
        str(user.id), active="TRUE" if already_active else "FALSE")
    from auth import staff_auth as _auth
    _auth.reload()  # pick up chat-id changes immediately
    if already_active:
        audit.log("user_reregistered", user.id, name,
                  f"unit={unit['Unit_ID']} chat updated")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"✅ {name}, your Telegram chat is updated — alerts will reach you here.")
    else:
        audit.log("user_registered", user.id, name, f"unit={unit['Unit_ID']} pending")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"✅ Registered, {name} — *pending admin approval*.\n"
            f"You'll get a message once approved. (Your chat ID: `{user.id}`)")
        # Nudge configured bot admins (best-effort).
        try:
            from config import settings as _settings
            for admin_id in _settings.telegram_admin_ids:
                await context.bot.send_message(
                    chat_id=int(admin_id),
                    text=f"📲 Approval needed: {name} ({unit['Unit_ID']}) "
                         f"registered. Approve: /approve {name}")
        except Exception as exc:
            log.debug("Admin nudge skipped: %s", exc)
    context.user_data.clear()
    return ConversationHandler.END


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    if not is_admin(update.effective_user.id):  # type: ignore[union-attr]
        await update.message.reply_text("🔒 Admins only.")  # type: ignore[union-attr]
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    name = " ".join(context.args or []).strip()
    if not name:
        pending = db.pending_telegram_users()
        if not pending:
            await update.message.reply_text("No pending registrations. ✅")  # type: ignore[union-attr]
            return
        lines = ["📲 *Pending approvals:*"]
        for r in pending:
            lines.append(f"• {r.get('Staff_Name')} ({r.get('Unit')}) — "
                         f"/approve {r.get('Staff_Name')}")
        await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]
        return
    if not db.set_user_active(name, True):
        await update.message.reply_text(f"No Telegram_Users row for '{name}'.")  # type: ignore[union-attr]
        return
    from auth import staff_auth as _auth
    _auth.reload()
    audit.log("user_approved", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update), f"approved={name}")
    await update.message.reply_text(f"✅ {name} approved.")  # type: ignore[union-attr]
    try:  # tell the user they're live
        chat = db.chat_id_for(name)
        if chat:
            await context.bot.send_message(
                chat_id=int(chat),
                text=f"✅ {name}, you're approved! Send /briefing to start, "
                     f"/help for all commands.")
    except Exception as exc:
        log.debug("Approval DM skipped: %s", exc)


# ----------------------------------------------------------------------------
# /digest — personal ops slice · /watchdog — run tick now · /schedule
# ----------------------------------------------------------------------------
async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    from datetime import date as _date
    today = _date.today()
    my = [s for s in db.staff() if _s2(s.get("Name")).lower() == staff.name.lower()]
    my_unit = db.resolve_unit(my[0].get("Unit", "")) if my else None
    uid = str(my_unit.get("Unit_ID")).upper() if my_unit else ""
    lines = [f"📌 *Your digest — {today:%d %b %Y}*"]
    if my_unit:
        reps = [r for r in db.supervisor_reports(today)
                if (db.resolve_unit(str(r.get("Unit", ""))) or {}).get("Unit_ID") == uid]
        if reps:
            r = reps[0]
            lines.append(f"🏥 {uid}: {r.get('Readiness')} | present {r.get('Present')} | "
                         f"attendance {r.get('Attendance_Rate')}%")
        else:
            lines.append(f"🏥 {uid}: no supervisor report filed yet today.")
    filed = any(_s2(r.get("Staff_Name")).lower() == staff.name.lower()
                for r in db.staff_reports(today))
    lines.append(f"📝 Your /daily report: {'filed ✅' if filed else 'MISSING ❌ — file with /daily'}")
    mine = [r for r in db.open_actions()
            if staff.name.lower() in _s2(r.get("Owner")).lower()]
    if mine:
        lines.append(f"📌 Your open actions ({len(mine)}):")
        for r in mine[:5]:
            lines.append(f"• {r.get('Action_ID')} — {r.get('Title')} (due {r.get('Due_Date')})")
    if my_unit:
        issues = [r for r in db.open_equipment_issues()
                  if str(r.get("Unit", "")).upper() == uid]
        if issues:
            lines.append(f"🔧 {uid} open equipment ({len(issues)}):")
            for r in issues[:4]:
                lines.append(f"• {r.get('Equipment')}: {r.get('Issue')} ({r.get('Severity')})")
    await _send_long(update, "\n".join(lines))


async def cmd_watchdog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: run gap scan + watchdog tick immediately and deliver here."""
    staff = await _me(update)
    if staff is None:
        return
    if not is_admin(update.effective_user.id):  # type: ignore[union-attr]
        await update.message.reply_text("🔒 Admins only.")  # type: ignore[union-attr]
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    from agents import Orchestrator  # lazy
    from scheduler import tz_now  # lazy

    await update.message.reply_text("🛰️ Running gap scan + watchdog…")  # type: ignore[union-attr]
    outbox = Orchestrator(db).tick(tz_now(), ["gaps", "watchdog"])
    if not outbox:
        await update.message.reply_text("✅ No findings — all quiet.")  # type: ignore[union-attr]
        return
    lines = [f"🛰️ *{len(outbox)} routed alert(s)* (also sent to owners):"]
    for m in outbox[:12]:
        first = m.text.splitlines()[0][:90]
        lines.append(f"• [{m.level}/{m.meta.get('severity')}] → {m.meta.get('to')}: {first}")
    if len(outbox) > 12:
        lines.append(f"_+{len(outbox) - 12} more_")
    await _send_long(update, "\n".join(lines))
    from messenger import TelegramMessenger  # lazy
    messenger = TelegramMessenger(context.bot)
    for m in outbox:
        await messenger.send(m)


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    from scheduler import describe_schedule  # lazy
    await update.message.reply_text(describe_schedule())  # type: ignore[union-attr]


# ----------------------------------------------------------------------------
# v4.1: leave, incidents, capability, policies, status, coverage
# ----------------------------------------------------------------------------
def _raw_name(update: Update) -> str:
    """Plain staff name (no role suffix) for sheet lookups."""
    try:
        staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
        return staff.name if staff else ""
    except Exception:
        return ""


def _manages_any(db: OpsDB, staff_name: str) -> bool:
    """Head or supervisor of at least one unit."""
    if db.is_head(staff_name):
        return True
    return any(db.supervises(staff_name, str(u.get("Unit_ID", "")))
               for u in db.units())


def _requester_unit_id(db: OpsDB, staff_name: str) -> str:
    want = staff_name.strip().lower()
    for s in db.staff():
        if str(s.get("Name", "")).strip().lower() == want:
            u = db.resolve_unit(str(s.get("Unit", "")))
            return str(u.get("Unit_ID", "")).upper() if u else ""
    return ""


def _staff_unit_name(db: OpsDB, staff_name: str) -> str:
    want = staff_name.strip().lower()
    for s in db.staff():
        if str(s.get("Name", "")).strip().lower() == want:
            return str(s.get("Unit", "")) or "—"
    return "—"


async def cmd_leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    me = staff.name
    mine = db.leave_for_staff(me)
    if not mine:
        lines = ["🏖️ You have no leave requests on file.",
                 "", "Request one: /leave_add"]
    else:
        lines = [f"🏖️ *Your leave ({len(mine)})*"]
        for r in mine[-10:]:
            cover = ""
            if str(r.get("Status", "")).lower() == "approved":
                cover = f", cover: {r.get('Coverage_Staff') or '⚠️ none'}"
            lines.append(f"• {r.get('Leave_ID')} {r.get('Leave_Type')} "
                         f"{r.get('Start_Date')}→{r.get('End_Date')} — "
                         f"*{r.get('Status')}*{cover}")
        lines.append("\n_Request: /leave_add_")
    if _manages_any(db, me):
        pend = db.pending_leaves()
        if pend:
            lines.append(f"\n⏳ *Pending approvals ({len(pend)})*")
            for r in pend[:10]:
                lines.append(f"• {r.get('Leave_ID')} {r.get('Staff_Name')} "
                             f"{r.get('Leave_Type')} "
                             f"{r.get('Start_Date')}→{r.get('End_Date')}\n"
                             f"  /leave_approve {r.get('Leave_ID')} "
                             f"<cover staff name>")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def leave_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await _me(update) is None:
        return ConversationHandler.END
    if await _db_or_msg(update) is None:
        return ConversationHandler.END
    context.user_data["ops_leave"] = {}
    await update.message.reply_text(  # type: ignore[union-attr]
        "🏖️ New leave request — type?\n(Annual / Sick / Emergency / Unpaid)")
    return L_TYPE


async def leave_add_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ops_leave"]["Leave_Type"] = \
        (update.message.text or "").strip()[:30]  # type: ignore[union-attr]
    await update.message.reply_text("Start date? (YYYY-MM-DD)")  # type: ignore[union-attr]
    return L_START


def _parse_ymd(text: str):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


async def leave_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    day = _parse_ymd(update.message.text or "")  # type: ignore[union-attr]
    if day is None:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Use YYYY-MM-DD please (e.g. 2026-09-20). Start date?")
        return L_START
    context.user_data["ops_leave"]["Start_Date"] = day.isoformat()  # type: ignore[index]
    await update.message.reply_text("End date? (YYYY-MM-DD)")  # type: ignore[union-attr]
    return L_END


async def leave_add_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    day = _parse_ymd(update.message.text or "")  # type: ignore[union-attr]
    start = context.user_data["ops_leave"].get("Start_Date", "")  # type: ignore[index]
    if day is None or day.isoformat() < start:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"End must be a valid date on/after {start}. End date?")
        return L_END
    context.user_data["ops_leave"]["End_Date"] = day.isoformat()  # type: ignore[index]
    await update.message.reply_text(  # type: ignore[union-attr]
        "Notes? (suggested cover, handover — or 'skip')")
    return L_NOTES


async def leave_add_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "leave_notes")
        return ConversationHandler.END
    db = await _db_or_msg(update)
    if db is None:
        return ConversationHandler.END
    data = context.user_data.get("ops_leave", {})
    data["Staff_Name"] = _raw_name(update)
    if not _none(text):
        data["Notes"] = text[:300]
    leave_id = db.add_leave_request(data)
    audit.log("leave_requested", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update), f"id={leave_id} {data.get('Start_Date')}→"
              f"{data.get('End_Date')}")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ Leave request *{leave_id}* recorded as Pending.\n"
        f"{data.get('Leave_Type')} {data.get('Start_Date')}→"
        f"{data.get('End_Date')} ({data.get('Duration_Days', '?')} days).\n"
        f"Your supervisor will approve in the Leave_Tracker tab or via "
        f"/leave_approve.")
    return ConversationHandler.END


async def cmd_leave_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    me = staff.name
    args = context.args or []
    if not args:
        if not _manages_any(db, me):
            await update.message.reply_text("🔒 Supervisors/head only.")  # type: ignore[union-attr]
            return
        pend = [r for r in db.pending_leaves()
                if db.can_manage(me, _requester_unit_id(db, str(r.get("Staff_Name", ""))))]
        if not pend:
            await update.message.reply_text(  # type: ignore[union-attr]
                "No pending leave requests in your scope. ✅")
            return
        lines = ["⏳ *Pending in your scope:*"]
        for r in pend[:10]:
            lines.append(f"• {r.get('Leave_ID')} {r.get('Staff_Name')} "
                         f"{r.get('Leave_Type')} "
                         f"{r.get('Start_Date')}→{r.get('End_Date')}\n"
                         f"  /leave_approve {r.get('Leave_ID')} <cover name>")
        await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]
        return
    leave_id = args[0].strip().upper()
    coverage = " ".join(args[1:]).strip()[:100]
    if contains_phi(coverage).blocked:
        await _phi_block(update, coverage, "leave_approve")
        return
    want = leave_id.lower()
    row = next((r for r in db.b.read_tab("Leave_Tracker")
                if str(r.get("Leave_ID", "")).strip().lower() == want), None)
    if row is None:
        await update.message.reply_text(f"No leave request '{leave_id}'.")  # type: ignore[union-attr]
        return
    if str(row.get("Status", "")).lower() != "pending":
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{leave_id} is already {row.get('Status')}.")
        return
    unit_id = _requester_unit_id(db, str(row.get("Staff_Name", "")))
    if not db.can_manage(me, unit_id):
        audit.log("leave_approve_denied", update.effective_user.id,  # type: ignore[union-attr]
                  _staff_name(update), f"id={leave_id}")
        await update.message.reply_text(  # type: ignore[union-attr]
            "🔒 You can only approve leave for your own unit.")
        return
    db.approve_leave(leave_id, me, coverage)
    audit.log("leave_approved", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update),
              f"id={leave_id} staff={row.get('Staff_Name')} cover={coverage or 'none'}")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ {leave_id} approved for {row.get('Staff_Name')}.\n"
        f"Cover: {coverage or '⚠️ none named — arrange cover in Leave_Tracker'}.")
    try:  # tell the requester they're approved
        chat = db.chat_id_for(str(row.get("Staff_Name", "")))
        if chat:
            await context.bot.send_message(
                chat_id=int(chat),
                text=f"✅ Your leave {leave_id} "
                     f"({row.get('Start_Date')}→{row.get('End_Date')}) was "
                     f"approved by {me}.")
    except Exception as exc:
        log.debug("Leave-approval DM skipped: %s", exc)


async def cmd_incidents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    open_ = db.open_incidents()
    if not open_:
        await update.message.reply_text("🚨 No open incidents. ✅")  # type: ignore[union-attr]
        return
    lines = [f"🚨 *Open incidents ({len(open_)}) — metadata only*"]
    for r in open_[:15]:
        m = OpsDB.incident_public(r)
        icon = "🔴" if m["Severity"].lower() in {"serious", "critical"} else "🟡"
        lines.append(f"{icon} {m['Incident_ID']} [{m['Severity']}] "
                     f"{m['Incident_Type']} — {m['Unit']}\n"
                     f"  {m['Date']} | {m['Status']} | reported by "
                     f"{m['Reported_By']}")
    if len(open_) > 15:
        lines.append(f"_+{len(open_) - 15} more_")
    lines.append("\n_Details live in the Incident_Reports tab only — "
                 "never in chat._\n_Log: /incident_add_")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def incident_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await _me(update) is None:
        return ConversationHandler.END
    if await _db_or_msg(update) is None:
        return ConversationHandler.END
    context.user_data["ops_inc"] = {}
    await update.message.reply_text(  # type: ignore[union-attr]
        "🚨 New incident — which unit? (U01–U08 or unit name)")
    return I_UNIT


async def incident_add_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = await _db_or_msg(update)
    if db is None:
        return ConversationHandler.END
    unit = db.resolve_unit((update.message.text or "").strip())  # type: ignore[union-attr]
    if unit is None:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Unknown unit — use U01–U08 or the unit name. Which unit?")
        return I_UNIT
    context.user_data["ops_inc"]["Unit"] = unit.get("Unit_ID")  # type: ignore[index]
    await update.message.reply_text(  # type: ignore[union-attr]
        "Type? (Fall / Medication / Equipment / Behavioural / Near-miss / Other)")
    return I_TYPE


async def incident_add_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "incident_type")
        return ConversationHandler.END
    context.user_data["ops_inc"]["Incident_Type"] = text[:60]  # type: ignore[index]
    await update.message.reply_text(  # type: ignore[union-attr]
        "Severity? (Minor / Moderate / Serious / Critical)")
    return I_SEV


_SEV_MAP = {"minor": "Minor", "moderate": "Moderate", "serious": "Serious",
            "critical": "Critical"}


async def incident_add_sev(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sev = _SEV_MAP.get((update.message.text or "").strip().lower())  # type: ignore[union-attr]
    if sev is None:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Choose: Minor / Moderate / Serious / Critical.")
        return I_SEV
    context.user_data["ops_inc"]["Severity"] = sev  # type: ignore[index]
    extra = ("\n⚠️ Serious/Critical pages the supervisor + head automatically."
             if sev in {"Serious", "Critical"} else "")
    await update.message.reply_text(  # type: ignore[union-attr]
        "Immediate action taken? (operational only — no patient details)" + extra)
    return I_ACTION


async def incident_add_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if contains_phi(text).blocked:
        await _phi_block(update, text, "incident_action")
        return ConversationHandler.END
    db = await _db_or_msg(update)
    if db is None:
        return ConversationHandler.END
    data = context.user_data.get("ops_inc", {})
    if not _none(text):
        data["Immediate_Action"] = text[:300]
    data["Reported_By"] = _raw_name(update)
    data["Supervisor_Notified"] = ("Auto" if data.get("Severity")
                                    in {"Serious", "Critical"} else "No")
    if "Time" not in data:
        data["Time"] = datetime.now().strftime("%H:%M")
    inc_id = db.add_incident(data)
    audit.log("incident_logged", update.effective_user.id,  # type: ignore[union-attr]
              _staff_name(update),
              f"id={inc_id} sev={data.get('Severity')} unit={data.get('Unit')}")
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ Incident *{inc_id}* logged ({data.get('Severity')}).\n"
        f"A supervisor must complete the Description + follow-up directly in "
        f"the Incident_Reports tab — full details are never kept in chat.")
    return ConversationHandler.END


async def cmd_capability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    name = " ".join(context.args or []).strip() or staff.name
    rows = db.capabilities_for(name)
    if not rows:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"No capability rows for '{name}'.\n"
            f"Rows are added by supervisors in the Capability_Matrix tab.")
        return
    lines = [f"🎓 *Capabilities — {name}*"]
    for r in rows[:10]:
        flag = " ⏳ UNVERIFIED" if str(r.get("Verification_Status", "")).lower() \
            in {"pending_verification", "pending"} else ""
        lines.append(f"• {r.get('Primary_Capability')} "
                     f"({r.get('Competency_Level') or 'no level'}){flag}\n"
                     f"  2nd: {r.get('Secondary_Capability') or '—'} | "
                     f"assessed: {r.get('Assessment_Date') or '—'} | "
                     f"expires: {r.get('Expiry_Date') or '—'}")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def cmd_policies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    rows = db.policies()
    if not rows:
        await update.message.reply_text("📜 No policies registered.")  # type: ignore[union-attr]
        return
    overdue = {r.get("Policy_ID") for r in db.policies_overdue()}
    lines = [f"📜 *Policies ({len(rows)})*"]
    for r in rows[:15]:
        flag = " 🔴 OVERDUE" if r.get("Policy_ID") in overdue else ""
        lines.append(f"• {r.get('Policy_ID')} v{r.get('Version')} — "
                     f"{r.get('Title')}\n"
                     f"  review due: {r.get('Review_Date') or '—'}{flag} | "
                     f"owner: {r.get('Owner') or '—'} | {r.get('Status')}")
    if len(rows) > 15:
        lines.append(f"_+{len(rows) - 15} more_")
    lines.append("\n_Full text lives in the Policy_Registry tab._")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    staff = await _me(update)
    if staff is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    me = staff.name
    want = me.lower()
    row = next((s for s in db.staff()
                if str(s.get("Name", "")).strip().lower() == want), {})
    today = date.today()
    on_leave_today = any(str(r.get("Staff_Name", "")).strip().lower() == want
                         for r in db.on_leave(today))
    upcoming = [r for r in db.leave_for_staff(me)
                if str(r.get("Status", "")).lower() == "approved"
                and str(r.get("End_Date", "")) >= today.isoformat()]
    caps = db.capabilities_for(me)
    lines = [f"👤 *{me}*",
             f"Unit: {_staff_unit_name(db, me)} | "
             f"Role: {row.get('Role', '—')}",
             f"Status: {row.get('Status', 'Active') or 'Active'} | "
             f"Contract: {row.get('Contract_Type', '—') or '—'}",
             f"License expires: {row.get('License_Expiry', '—') or '—'}",
             f"On leave today: {'Yes 🏖️' if on_leave_today else 'No'}",
             f"Upcoming approved leave: {len(upcoming)}",
             f"Capabilities on file: {len(caps)}"]
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def cmd_whoison(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    rows = db.on_leave(date.today())
    if not rows:
        await update.message.reply_text(  # type: ignore[union-attr]
            "🏖️ Nobody on approved leave today. ✅")
        return
    lines = [f"🏖️ *On leave today ({len(rows)})*"]
    for r in rows:
        name = str(r.get("Staff_Name", ""))
        cover = (r.get("Coverage_Staff") or "").strip()
        cover_txt = f"cover: {cover}" if cover else "⚠️ NO COVER"
        lines.append(f"• {name} ({_staff_unit_name(db, name)}) — "
                     f"{r.get('Leave_Type')} ({cover_txt})")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


async def cmd_coverage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _me(update) is None:
        return
    db = await _db_or_msg(update)
    if db is None:
        return
    today = date.today()
    lines = [f"🛡️ *Coverage — {today.isoformat()}*"]
    cov = db.coverage_on(today)
    if cov:
        for r in cov[:8]:
            st = str(r.get("Coverage_Status", "")).lower()
            icon = "🔴" if st == "uncovered" else ("🟡" if st == "partial"
                                                  else "🟢")
            lines.append(f"{icon} {r.get('Unit')}: {r.get('Coverage_Status')} "
                         f"(absent: {r.get('Absent_Staff') or '—'}; "
                         f"covering: {r.get('Covering_Staff') or '—'})")
    else:
        lines.append("No Coverage_Log rows for today.")
    under: list[str] = []
    for r in db.supervisor_reports(today):
        unit = db.resolve_unit(str(r.get("Unit", "")))
        if not unit:
            continue
        uid = str(unit.get("Unit_ID")).upper()
        try:
            present = int(float(str(r.get("Present", "0")).strip()))
        except ValueError:
            continue
        minimum = db.unit_min_staff(uid)
        if minimum and present < minimum:
            under.append(f"• {uid}: {present}/{minimum} present ⚠️")
    if under:
        lines.append("\n*Below minimum staffing:*")
        lines.extend(under[:8])
    uncovered = db.uncovered_leaves(today)
    if uncovered:
        lines.append(f"\n*Approved leave without cover ({len(uncovered)}):*")
        for r in uncovered[:8]:
            lines.append(f"• {r.get('Staff_Name')} ({r.get('Leave_ID')})")
    await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]


# ----------------------------------------------------------------------------
# Registration (called from bot.py — keeps bot.py diff to 2 lines)
# ----------------------------------------------------------------------------
def register_ops_handlers(app) -> None:
    """Add all Agent v3 ops commands + conversations to the application."""
    daily_conv = ConversationHandler(
        entry_points=[CommandHandler("daily", daily_start)],
        states={
            D_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _daily_unit)],
            D_SEEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, daily_seen)],
            D_NEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, daily_new)],
            D_FOLLOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, daily_follow)],
            D_DOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, daily_doc)],
            D_ISSUES: [MessageHandler(filters.TEXT & ~filters.COMMAND, daily_issues)],
            D_TOMORROW: [MessageHandler(filters.TEXT & ~filters.COMMAND, daily_tomorrow)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )
    sup_conv = ConversationHandler(
        entry_points=[CommandHandler("supervisor", sup_start)],
        states={
            S_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_unit)],
            S_READY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_ready)],
            S_STAFF: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_staff)],
            S_ATTEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_attend)],
            S_DOC: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_doc)],
            S_EQUIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_equip)],
            S_URGENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_urgent)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )
    action_conv = ConversationHandler(
        entry_points=[CommandHandler("actions_add", actions_add_start)],
        states={
            A_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, actions_add_title)],
            A_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, actions_add_owner)],
            A_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, actions_add_due)],
            A_PRIORITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, actions_add_priority)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )
    equip_conv = ConversationHandler(
        entry_points=[CommandHandler("equipment_add", equip_add_start)],
        states={
            E_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, equip_add_unit)],
            E_EQUIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, equip_add_equip)],
            E_ISSUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, equip_add_issue)],
            E_SEV: [MessageHandler(filters.TEXT & ~filters.COMMAND, equip_add_sev)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )

    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("dashboard", cmd_dashboard))
    app.add_handler(CommandHandler("units", cmd_units))
    app.add_handler(CommandHandler("staff", cmd_staff))
    app.add_handler(CommandHandler("actions", cmd_actions))
    app.add_handler(CommandHandler("equipment", cmd_equipment))
    app.add_handler(CommandHandler("datahealth", cmd_datahealth))
    app.add_handler(CommandHandler("setup", cmd_setup))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("watchdog", cmd_watchdog))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("leave", cmd_leave))
    app.add_handler(CommandHandler("leave_approve", cmd_leave_approve))
    app.add_handler(CommandHandler("incidents", cmd_incidents))
    app.add_handler(CommandHandler("capability", cmd_capability))
    app.add_handler(CommandHandler("policies", cmd_policies))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("whoison", cmd_whoison))
    app.add_handler(CommandHandler("coverage", cmd_coverage))
    leave_conv = ConversationHandler(
        entry_points=[CommandHandler("leave_add", leave_add_start)],
        states={
            L_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_add_type)],
            L_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_add_start)],
            L_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_add_end)],
            L_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_add_notes)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )
    incident_conv = ConversationHandler(
        entry_points=[CommandHandler("incident_add", incident_add_start)],
        states={
            I_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, incident_add_unit)],
            I_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, incident_add_type)],
            I_SEV: [MessageHandler(filters.TEXT & ~filters.COMMAND, incident_add_sev)],
            I_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, incident_add_action)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )
    register_conv = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            R_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            R_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_unit)],
        },
        fallbacks=[CommandHandler("cancel", ops_cancel)],
    )
    app.add_handler(register_conv)
    app.add_handler(daily_conv)
    app.add_handler(sup_conv)
    app.add_handler(action_conv)
    app.add_handler(equip_conv)
    app.add_handler(leave_conv)
    app.add_handler(incident_conv)
