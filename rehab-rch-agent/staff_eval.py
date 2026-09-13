"""Agent v4.2 staff evaluation — transparent computed metrics (no AI).

Formulas (also shown in /evaluate output so staff can verify):
  expected days   = working days in month (minus EVAL_WEEKEND, default
                    Fri/Sat) minus approved leave days
  working-days %  = distinct days with a Daily_Staff_Reports row ÷ expected
  patients        = Σ Patients_Seen for the month
  patient share % = staff patients ÷ unit total patients
  load index      = staff patients ÷ unit average (over staff who filed ≥1
                    report); 100% = exactly average
  doc rate %      = reports with Documentation_Status=Complete ÷ all reports
  flags           = working-days <80% · doc rate <90% · load <60% · load >150%

There is deliberately NO single composite score — supervisors see the
components and the flags, then judge with context the sheet can't hold
(case complexity, part-time rosters, new starters).
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date

from config import settings
from sheets_ops import STAFF_REPORT_EXCLUDED_ROLES

_WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5,
             "SUN": 6}

FLAG_WORKING = "low reporting (<80% working days)"
FLAG_DOC = "documentation <90%"
FLAG_LOAD_LOW = "load <60% of unit average"
FLAG_LOAD_HIGH = "load >150% of unit average"


def _to_int(value) -> int:
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError, AttributeError):
        return 0


def _pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 1) if den > 0 else 0.0


def weekend_days() -> set[int]:
    out = set()
    for token in settings.eval_weekend.replace(";", ",").split(","):
        day = _WEEKDAYS.get(token.strip().upper())
        if day is not None:
            out.add(day)
    return out or {4, 5}


def working_days(year: int, month: int) -> list[date]:
    off = weekend_days()
    days_in = monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, days_in + 1)
            if date(year, month, d).weekday() not in off]


def month_label(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    return start, date(year, month, monthrange(year, month)[1])


def previous_month(today: date) -> tuple[int, int]:
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def staff_unit_name(db, staff_name: str) -> str:
    want = staff_name.strip().lower()
    for s in db.staff():
        if str(s.get("Name", "")).strip().lower() == want:
            return str(s.get("Unit", "")) or "—"
    return "—"


def evaluate_staff(db, staff_name: str, year: int,
                   month: int) -> dict[str, str]:
    """Compute one snapshot row (string values, sheet-ready)."""
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    reports = db.staff_reports_between(start, end, staff_name)
    reported_days = {_r_date(r) for r in reports}
    reported_days.discard("")
    leave_days = db.approved_leave_days_between(staff_name, start, end)
    expected = max(len(working_days(year, month)) - leave_days, 0)

    patients = sum(_to_int(r.get("Patients_Seen")) for r in reports)
    new_cases = sum(_to_int(r.get("New_Cases")) for r in reports)
    followups = sum(_to_int(r.get("Follow_Up_Cases")) for r in reports)
    complete = sum(1 for r in reports
                   if str(r.get("Documentation_Status", "")).strip().lower()
                   == "complete")

    unit = staff_unit_name(db, staff_name)
    peers = [n for n in db.resolve_audience(unit)] if unit != "—" else []
    if staff_name not in peers:
        peers.append(staff_name)
    peer_totals = {n: sum(_to_int(r.get("Patients_Seen"))
                          for r in db.staff_reports_between(start, end, n))
                   for n in peers}
    unit_total = sum(peer_totals.values())
    reporters = [t for t in peer_totals.values() if t > 0]
    avg = sum(reporters) / len(reporters) if reporters else 0.0

    working_pct = _pct(len(reported_days), expected) if expected else 0.0
    working_pct = min(working_pct, 100.0)
    share = _pct(patients, unit_total)
    load = round(100.0 * patients / avg, 1) if avg > 0 else 0.0
    doc_rate = _pct(complete, len(reports))

    flags = []
    if expected and working_pct < 80:
        flags.append(FLAG_WORKING)
    if reports and doc_rate < 90:
        flags.append(FLAG_DOC)
    if avg > 0 and load < 60:
        flags.append(FLAG_LOAD_LOW)
    if load > 150:
        flags.append(FLAG_LOAD_HIGH)

    return {
        "Eval_Month": month_label(year, month),
        "Staff_Name": staff_name,
        "Unit": unit,
        "Working_Days_Pct": str(working_pct),
        "Patients_Seen": str(patients),
        "Patient_Share_Pct": str(share),
        "Load_Index": str(load),
        "Doc_Rate_Pct": str(doc_rate),
        "Leave_Days": str(leave_days),
        "Flags": "; ".join(flags),
        "_New_Cases": str(new_cases),       # card-only, not sheeted
        "_Follow_Ups": str(followups),      # card-only, not sheeted
        "_Reported_Days": str(len(reported_days)),
        "_Expected_Days": str(expected),
    }


def _r_date(r: dict) -> str:
    return str(r.get("Report_Date", "")).strip().split()[0]


def evaluate_all(db, year: int, month: int) -> list[dict[str, str]]:
    """Snapshots for report-filing clinical staff (heads, supervisors and
    secretaries are excluded — they file supervisor reports, not /daily)."""
    rows = []
    for s in db.active_staff():
        name = str(s.get("Name", "")).strip()
        if not name or not str(s.get("Unit", "")).strip():
            continue
        if STAFF_REPORT_EXCLUDED_ROLES.search(str(s.get("Role", ""))):
            continue
        rows.append(evaluate_staff(db, name, year, month))
    return rows


_SHEET_COLS = ["Eval_Month", "Staff_Name", "Unit", "Working_Days_Pct",
               "Patients_Seen", "Patient_Share_Pct", "Load_Index",
               "Doc_Rate_Pct", "Leave_Days", "Flags"]


def run_monthly_evaluation(db, today: date):
    """Evaluate the previous month, save snapshots, return (label, rows).

    Idempotent: if snapshots already exist for the month, returns them
    without rewriting (scheduler `last` is in-memory, so restarts refire).
    """
    year, month = previous_month(today)
    label = month_label(year, month)
    existing = db.evaluations_for(label)
    if existing:
        return label, existing
    rows = evaluate_all(db, year, month)
    for r in rows:
        db.save_evaluation({k: r[k] for k in _SHEET_COLS})
    return label, rows


def format_eval_card(row: dict) -> str:
    flags = row.get("Flags", "").strip() or "none ✅"
    return (
        f"📊 *Evaluation — {row.get('Staff_Name')} ({row.get('Eval_Month')})*\n"
        f"Unit: {row.get('Unit')}\n"
        f"Working days: {row.get('_Reported_Days', '?')}/"
        f"{row.get('_Expected_Days', '?')} "
        f"({row.get('Working_Days_Pct')}%)\n"
        f"Patients seen: {row.get('Patients_Seen')} "
        f"(share {row.get('Patient_Share_Pct')}% of unit)\n"
        f"New: {row.get('_New_Cases', '?')} | "
        f"Follow-up: {row.get('_Follow_Ups', '?')}\n"
        f"Load vs unit avg: {row.get('Load_Index')}%\n"
        f"Documentation complete: {row.get('Doc_Rate_Pct')}%\n"
        f"Leave days: {row.get('Leave_Days')}\n"
        f"Flags: {flags}\n"
        f"_Formulas: share = my patients ÷ unit total; load 100% = unit "
        f"average; working % excludes weekends + approved leave._")


def format_unit_digest(unit_id: str, rows: list[dict]) -> str:
    month = rows[0].get("Eval_Month", "") if rows else ""
    lines = [f"📊 *Monthly evaluation — {unit_id} ({month})*"]
    for r in sorted(rows, key=lambda x: -float(x.get("Patients_Seen") or 0)):
        flag = f" ⚠️ {r['Flags']}" if r.get("Flags") else ""
        lines.append(f"• {r.get('Staff_Name')}: {r.get('Patients_Seen')} pts "
                     f"(share {r.get('Patient_Share_Pct')}%, load "
                     f"{r.get('Load_Index')}%), work "
                     f"{r.get('Working_Days_Pct')}%, doc "
                     f"{r.get('Doc_Rate_Pct')}%{flag}")
    if not rows:
        lines.append("No snapshots.")
    return "\n".join(lines)


def format_head_summary(rows: list[dict]) -> str:
    month = rows[0].get("Eval_Month", "") if rows else ""
    flagged = [r for r in rows if r.get("Flags")]
    total_pts = sum(_to_int(r.get("Patients_Seen")) for r in rows)
    lines = [f"📊 *Monthly evaluation summary ({month})*",
             f"Staff evaluated: {len(rows)} | "
             f"Total patients: {total_pts} | Flagged: {len(flagged)}"]
    for r in flagged[:15]:
        lines.append(f"• {r.get('Staff_Name')} ({r.get('Unit')}): "
                     f"{r.get('Flags')}")
    if len(flagged) > 15:
        lines.append(f"_+{len(flagged) - 15} more_")
    lines.append("\n_Full detail: Staff_Evaluations tab + /evaluate <name>_")
    return "\n".join(lines)
