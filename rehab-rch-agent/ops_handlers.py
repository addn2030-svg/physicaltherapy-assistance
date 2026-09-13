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


# ----------------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------------
async def _me(update: Update):
    """Authorized staff member or None (with denial reply + audit)."""
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
    app.add_handler(daily_conv)
    app.add_handler(sup_conv)
    app.add_handler(action_conv)
    app.add_handler(equip_conv)
