"""Operations workbook layer — Rehab_Operations_Master_v2 (Agent v3).

Typed access to the department's Google Sheet mirror of
``Rehab_Operations_Master_v2.xlsx``: units, staff, daily staff +
supervisor reports, weekly summaries, dashboard KPIs, actions, equipment
issues, training, coverage, briefings, announcements, FAQ, and the agent
audit log.

Backends:
  * :class:`GSpreadBackend` — live Google Sheet (``OPS_SHEET_ID``).
  * :class:`MemoryBackend` — in-memory tabs, seeded with the real
    department structure for tests and ``demo_ops.py``.

Use :func:`get_ops_db` inside bot handlers (cached, None when the ops
sheet is not connected). All date comparisons accept ``YYYY-MM-DD``
(cells in ``DD/MM/YYYY`` are normalized automatically).

Privacy: this workbook's reporting tabs hold operational counts only
(no patient names/MRNs). Free-text fields (Issues, Equipment,
Urgent_Decision, ...) are PHI-screened by callers before append.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Optional

from config import settings

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Schemas — 11 core tabs + 8 Agent v3 tabs (headers must match the Sheet)
# ----------------------------------------------------------------------------
SCHEMAS: dict[str, list[str]] = {
    # -- core workbook ---------------------------------------------------
    "Units": ["Unit_ID", "Unit_Name", "Supervisor",
              "Min_Staff_Required", "Capacity_Daily"],
    "Supervisors": ["Supervisor", "Area"],
    "Staff_Register": ["Name", "Unit", "Role",
                       # v4.1 additions (all optional, backward compatible):
                       "Status", "Contract_Type", "License_Expiry",
                       # v4.2: staff email for agent email reminders (optional)
                       "Email"],
    "Daily_Staff_Reports": [
        "Report_Date", "Staff_Name", "Unit", "Patients_Seen", "New_Cases",
        "Follow_Up_Cases", "Documentation_Status", "Issues",
        "Follow_Up_Tomorrow", "Submitted_Time",
    ],
    "Daily_Supervisor_Reports": [
        "Date", "Supervisor", "Unit", "Readiness", "Present", "Leave",
        "Sick_Leave", "Absent", "Scheduled", "Attended", "No_Show",
        "Attendance_Rate", "Doc_Complete", "Doc_Incomplete", "Equipment",
        "Urgent_Decision",
    ],
    "Weekly_Summary": [
        "Week_Start", "Week_End", "Supervisor", "Unit", "Total_Appointments",
        "Total_Attendance", "Attendance_Rate", "Documentation_Rate",
        "Completed_Actions", "Pending_Actions", "Risks", "Decisions_Required",
    ],
    "Dashboard": ["KPI", "Value"],
    "Capability_Matrix": [
        "Staff_Name", "Primary_Capability", "Secondary_Capability",
        "Verification_Status",
        # v4.1 additions:
        "Competency_Level", "Assessment_Date", "Assessor", "Expiry_Date",
    ],
    "Data_Dictionary": ["Key", "Value"],
    "Telegram_Users": [
        "Staff_Name", "Unit", "Telegram_Username", "Telegram_Chat_ID", "Active",
    ],
    "API_Configuration": ["Service", "Value", "Notes"],
    # -- Agent v3 tabs ----------------------------------------------------
    "Announcements_Log": ["Date", "Title", "Body", "Audience", "Author", "Status"],
    "Operational_Actions": [
        "Action_ID", "Date_Raised", "Title", "Owner", "Due_Date", "Status",
        "Priority", "Source", "Notes",
    ],
    "Training_Tracker": [
        "Staff_Name", "Course", "Provider", "Date", "Status",
        "Expiry_Date", "Hours",
    ],
    "Equipment_Issues": [
        "Issue_ID", "Date", "Unit", "Equipment", "Issue", "Severity",
        "Status", "Reported_By", "Resolved_Date",
    ],
    "Coverage_Tracker": [
        "Date", "Unit", "Absent_Staff", "Covering_Staff",
        "Coverage_Status", "Notes",
    ],
    "Supervisor_Briefings": [
        "Date", "Supervisor", "Unit", "Summary", "Risks", "Decisions_Required",
    ],
    "Agent_Audit_Log": ["Timestamp", "Event", "Telegram_ID", "Name", "Details"],
    "Knowledge_FAQ": ["Question", "Answer", "Source", "Updated"],
    # -- v4.1 tabs (from gap-analysis feedback) ------------------------------
    "Leave_Tracker": [
        "Leave_ID", "Staff_Name", "Leave_Type", "Start_Date", "End_Date",
        "Duration_Days", "Status", "Approved_By", "Requested_Date",
        "Approved_Date", "Coverage_Arranged", "Coverage_Staff", "Notes",
    ],
    "Incident_Reports": [
        # Privacy: bot reads metadata only (never Description/Patient fields).
        "Incident_ID", "Date", "Time", "Unit", "Reported_By", "Incident_Type",
        "Severity", "Description", "Immediate_Action", "Supervisor_Notified",
        "Status", "Resolution_Date", "Closed_By",
    ],
    "Policy_Registry": [
        "Policy_ID", "Title", "Version", "Effective_Date", "Review_Date",
        "Owner", "Status", "Last_Reviewed_By", "Notes",
    ],
    # -- v4.2 tabs (reminders, memos, agendas, evaluations) ---------------
    "Reminders": [
        "Reminder_ID", "Title", "Audience", "Start_Date", "End_Date",
        "Cadence", "Priority", "Status", "Created_By", "Last_Sent",
        "Calendar_Event_ID", "Notes",
    ],
    "Memo_Log": [
        "Memo_ID", "Date", "Title", "Body", "Audience", "Author", "Status",
    ],
    "Meeting_Agenda": [
        "Meeting_ID", "Date", "Title", "Agenda_Items", "Attendees",
        "Status", "Calendar_Event_ID", "Minutes_Ref",
    ],
    "Staff_Evaluations": [
        "Eval_Month", "Staff_Name", "Unit", "Working_Days_Pct",
        "Patients_Seen", "Patient_Share_Pct", "Load_Index", "Doc_Rate_Pct",
        "Leave_Days", "Flags",
    ],
}

# Units expected to file a daily supervisor report (U08 = section office).
EXPECTED_SUP_UNITS = ["U01", "U02", "U03", "U04", "U05", "U06", "U07"]

# Staff_Register roles that file SUPERVISOR reports (or none) instead of
# daily STAFF reports. Everyone else (incl. empty role = data gap) is
# expected to file a daily staff report.
STAFF_REPORT_EXCLUDED_ROLES = re.compile(r"supervisor|section head|secretary", re.IGNORECASE)

# Cell values that mean "not provided".
MISSING_MARKERS = {"", "-", "n/a", "na", "none", "missing in the department register."}

ACTIVE_MARKERS = {"true", "yes", "active", "1", "y"}


# ----------------------------------------------------------------------------
# Value helpers
# ----------------------------------------------------------------------------
def _s(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _num(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0


def _missing(value: Any) -> bool:
    return _s(value).lower() in MISSING_MARKERS


def _norm_date(value: Any) -> str:
    """Normalize common cell formats to YYYY-MM-DD (best-effort)."""
    raw = _s(value)
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw.split()[0], fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _datestr(day: date | str) -> str:
    return day.isoformat() if isinstance(day, date) else _norm_date(day)


def _parse_date(value: Any) -> Optional[date]:
    norm = _norm_date(value)
    try:
        return date.fromisoformat(norm)
    except ValueError:
        return None


# ----------------------------------------------------------------------------
# Backends
# ----------------------------------------------------------------------------
class SheetBackend(ABC):
    @abstractmethod
    def read_tab(self, tab: str) -> list[dict[str, str]]:
        """Return all data rows as dicts (empty list when tab is missing)."""

    @abstractmethod
    def append_row(self, tab: str, row: dict[str, str]) -> None:
        """Append one row (creates the tab + header from SCHEMAS if needed)."""

    @abstractmethod
    def update_rows(self, tab: str, key_col: str, key_val: str,
                    updates: dict[str, str]) -> int:
        """Update rows where key_col == key_val. Returns rows updated."""

    @abstractmethod
    def ensure_tabs(self, schemas: dict[str, list[str]]) -> dict[str, str]:
        """Create missing tabs + headers. Returns {tab: created|exists}."""


class GSpreadBackend(SheetBackend):
    """Live Google Sheets backend via service account."""

    def __init__(self, sheet_id: str) -> None:
        self.sheet_id = sheet_id
        self._book = None

    def _open(self):
        if self._book is None:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.readonly",
            ]
            creds = Credentials.from_service_account_file(
                str(settings.credentials_path), scopes=scopes
            )
            self._book = gspread.authorize(creds).open_by_key(self.sheet_id)
        return self._book

    def _ws(self, tab: str):
        try:
            return self._open().worksheet(tab)
        except Exception:
            return None

    def read_tab(self, tab: str) -> list[dict[str, str]]:
        ws = self._ws(tab)
        if ws is None:
            return []
        try:
            values = ws.get_all_values()
        except Exception as exc:
            log.warning("Read failed for tab %s: %s", tab, exc)
            return []
        if not values:
            return []
        headers = [_s(h) for h in values[0]]
        rows: list[dict[str, str]] = []
        for record in values[1:]:
            cells = [_s(c) for c in record]
            if not any(cells):
                continue
            rows.append(
                {h: (cells[i] if i < len(cells) else "")
                 for i, h in enumerate(headers) if h}
            )
        return rows

    def append_row(self, tab: str, row: dict[str, str]) -> None:
        headers = SCHEMAS.get(tab)
        if not headers:
            raise ValueError(f"Unknown tab: {tab}")
        book = self._open()
        ws = self._ws(tab)
        if ws is None:
            ws = book.add_worksheet(title=tab, rows=1000, cols=max(len(headers), 5))
            ws.update("A1", [headers])
        elif not ws.get_values("A1:A1"):
            ws.update("A1", [headers])
        ws.append_row([_s(row.get(h, "")) for h in headers])

    def update_rows(self, tab: str, key_col: str, key_val: str,
                    updates: dict[str, str]) -> int:
        ws = self._ws(tab)
        if ws is None:
            return 0
        values = ws.get_all_values()
        if not values:
            return 0
        headers = [_s(h) for h in values[0]]
        if key_col not in headers:
            return 0
        key_idx = headers.index(key_col)
        targets = {h: headers.index(h) for h in updates if h in headers}
        if not targets:
            return 0
        want = _s(key_val).lower()
        updated = 0
        for i, record in enumerate(values[1:], start=2):
            cells = [_s(c) for c in record]
            current = cells[key_idx] if key_idx < len(cells) else ""
            if current.lower() != want:
                continue
            for header, col_idx in targets.items():
                ws.update_cell(i, col_idx + 1, _s(updates[header]))
            updated += 1
        return updated

    def ensure_tabs(self, schemas: dict[str, list[str]]) -> dict[str, str]:
        book = self._open()
        existing = {ws.title for ws in book.worksheets()}
        status: dict[str, str] = {}
        for tab, headers in schemas.items():
            if tab not in existing:
                ws = book.add_worksheet(title=tab, rows=1000, cols=max(len(headers), 5))
                ws.update("A1", [headers])
                status[tab] = "created"
            else:
                ws = book.worksheet(tab)
                if not ws.get_values("A1:A1"):
                    ws.update("A1", [headers])
                    status[tab] = "header-fixed"
                else:
                    status[tab] = "exists"
        return status


class MemoryBackend(SheetBackend):
    """In-memory backend for tests and demos."""

    def __init__(self, tabs: Optional[dict[str, list[dict[str, str]]]] = None) -> None:
        self.tabs: dict[str, list[dict[str, str]]] = tabs or {}

    def read_tab(self, tab: str) -> list[dict[str, str]]:
        return [dict(r) for r in self.tabs.get(tab, [])]

    def append_row(self, tab: str, row: dict[str, str]) -> None:
        headers = SCHEMAS.get(tab)
        if not headers:
            raise ValueError(f"Unknown tab: {tab}")
        self.tabs.setdefault(tab, []).append({h: _s(row.get(h, "")) for h in headers})

    def update_rows(self, tab: str, key_col: str, key_val: str,
                    updates: dict[str, str]) -> int:
        want = _s(key_val).lower()
        updated = 0
        for row in self.tabs.get(tab, []):
            if _s(row.get(key_col)).lower() != want:
                continue
            for header, value in updates.items():
                if header in SCHEMAS.get(tab, []):
                    row[header] = _s(value)
            updated += 1
        return updated

    def ensure_tabs(self, schemas: dict[str, list[str]]) -> dict[str, str]:
        status: dict[str, str] = {}
        for tab in schemas:
            if tab in self.tabs:
                status[tab] = "exists"
            else:
                self.tabs[tab] = []
                status[tab] = "created"
        return status


# ----------------------------------------------------------------------------
# Demo seed — real department structure + sample operational rows
# ----------------------------------------------------------------------------
def seed_demo_tabs(today: Optional[date] = None) -> dict[str, list[dict[str, str]]]:
    """Seed data mirroring the user's Rehab_Operations_Master_v2 content."""
    day = (today or date.today()).isoformat()
    now = datetime.now().strftime("%H:%M")

    units = [
        ("U01", "Physiotherapy Male", "Abdulmajeed Mohammed AlJuraid"),
        ("U02", "Physiotherapy Female", "Shahad Abdullah Albalawi"),
        ("U03", "Inpatient", "Sumaya Abdullah Al Batook"),
        ("U04", "Speech Therapy", "Shahad Abdullah Albalawi"),
        ("U05", "Occupational Therapy", "Shahad Abdullah Albalawi"),
        ("U06", "Cast Technician", "Shahad Abdullah Albalawi"),
        ("U07", "Home Visit", "Abdulmajeed Mohammed AlJuraid"),
        ("U08", "Rehabilitation Section", "Abdulrahman Hawsawi"),
    ]
    supervisors = [
        ("Abdulrahman Hawsawi", "Section Head"),
        ("Abdulmajeed Mohammed AlJuraid", "PT Male & Home Visit"),
        ("Shahad Abdullah Albalawi", "PT Female, Speech, OT, Cast"),
        ("Sumaya Abdullah Al Batook", "Inpatient"),
    ]
    staff = [
        ("Abdulrahman Hawsawi", "Rehabilitation Section", "Section Head"),
        ("Ahmed Mohammed Bakri", "Physiotherapy Male", ""),
        ("Abdulmajeed Mohammed AlJuraid", "Physiotherapy Male", "OPD Male Supervisor"),
        ("Khaled Sultan Al-Otaibi", "Physiotherapy Male", ""),
        ("Sayfaleslam Salem Alenzi", "Physiotherapy Male", ""),
        ("Mosab Saleh AlSheikh", "Physiotherapy Male", ""),
        ("Ayish AlShahrani", "Physiotherapy Male", ""),
        ("Abdulelah Faleh Alharbi", "Physiotherapy Male", ""),
        ("Shahad Abdullah Albalawi", "Physiotherapy Female", "OPD Female Supervisor"),
        ("Anwar Al Shammari", "Physiotherapy Female", ""),
        ("Nouf Mohammed Abduldaim", "Physiotherapy Female", ""),
        ("Maryam Eyadh Al Shammari", "Physiotherapy Female", ""),
        ("Nada Omar Al Amoudi", "Physiotherapy Female", ""),
        ("Sumaya Abdullah Al Batook", "Inpatient", "Inpatient Supervisor"),
        ("Reem Abdulrazeq", "Speech Therapy", ""),
        ("Maryam Naji Ali", "Occupational Therapy", ""),
        ("Shoug Atallah Alanazi", "Cast Technician", "Cast Technician"),
        ("Hanin", "PT Secretary", "PT Secretary"),
    ]

    tabs: dict[str, list[dict[str, str]]] = {
        "Units": [
            {"Unit_ID": i, "Unit_Name": n, "Supervisor": s} for i, n, s in units
        ],
        "Supervisors": [
            {"Supervisor": n, "Area": a} for n, a in supervisors
        ],
        "Staff_Register": [
            {"Name": n, "Unit": u, "Role": r} for n, u, r in staff
        ],
        "Daily_Supervisor_Reports": [
            {"Date": day, "Supervisor": "Abdulmajeed Mohammed AlJuraid",
             "Unit": "U01", "Readiness": "Ready", "Present": "6",
             "Leave": "1", "Sick_Leave": "0", "Absent": "0", "Scheduled": "42",
             "Attended": "39", "No_Show": "3", "Attendance_Rate": "93",
             "Doc_Complete": "39", "Doc_Incomplete": "0",
             "Equipment": "OK", "Urgent_Decision": ""},
            {"Date": day, "Supervisor": "Sumaya Abdullah Al Batook",
             "Unit": "U03", "Readiness": "Partial", "Present": "4",
             "Leave": "0", "Sick_Leave": "1", "Absent": "0", "Scheduled": "18",
             "Attended": "16", "No_Show": "2", "Attendance_Rate": "89",
             "Doc_Complete": "15", "Doc_Incomplete": "1",
             "Equipment": "Ultrasound probe intermittent — reported",
             "Urgent_Decision": "Approve Thursday coverage swap"},
        ],
        "Daily_Staff_Reports": [
            {"Report_Date": day, "Staff_Name": "Khaled Sultan Al-Otaibi",
             "Unit": "U01", "Patients_Seen": "9", "New_Cases": "2",
             "Follow_Up_Cases": "7", "Documentation_Status": "Complete",
             "Issues": "", "Follow_Up_Tomorrow": "6 booked", "Submitted_Time": now},
            {"Report_Date": day, "Staff_Name": "Anwar Al Shammari",
             "Unit": "U02", "Patients_Seen": "8", "New_Cases": "1",
             "Follow_Up_Cases": "7", "Documentation_Status": "Complete",
             "Issues": "", "Follow_Up_Tomorrow": "5 booked", "Submitted_Time": now},
            {"Report_Date": day, "Staff_Name": "Shoug Atallah Alanazi",
             "Unit": "U06", "Patients_Seen": "5", "New_Cases": "3",
             "Follow_Up_Cases": "2", "Documentation_Status": "Complete",
             "Issues": "Cast room stock low on 4-inch rolls",
             "Follow_Up_Tomorrow": "3 booked", "Submitted_Time": now},
            {"Report_Date": day, "Staff_Name": "Reem Abdulrazeq",
             "Unit": "U04", "Patients_Seen": "6", "New_Cases": "0",
             "Follow_Up_Cases": "6", "Documentation_Status": "Incomplete: 1 note pending",
             "Issues": "", "Follow_Up_Tomorrow": "4 booked", "Submitted_Time": now},
        ],
        "Weekly_Summary": [
            {"Week_Start": day, "Week_End": day, "Supervisor": "Abdulmajeed Mohammed AlJuraid",
             "Unit": "U01", "Total_Appointments": "210", "Total_Attendance": "196",
             "Attendance_Rate": "93", "Documentation_Rate": "100",
             "Completed_Actions": "4", "Pending_Actions": "1",
             "Risks": "None", "Decisions_Required": "None"},
        ],
        "Dashboard": [
            {"KPI": "Reports Received Today", "Value": "6"},
            {"KPI": "Weekly Attendance %", "Value": "93"},
            {"KPI": "Documentation Compliance %", "Value": "88"},
            {"KPI": "Open Issues", "Value": "2"},
            {"KPI": "Pending Actions", "Value": "3"},
        ],
        "Capability_Matrix": [
            {"Staff_Name": "Abdulmajeed Mohammed AlJuraid",
             "Primary_Capability": "Musculoskeletal PT",
             "Secondary_Capability": "Home Visit Assessment",
             "Verification_Status": "Pending_Verification",
             "Competency_Level": "P3", "Assessment_Date": "",
             "Assessor": "", "Expiry_Date": ""},
            {"Staff_Name": "Shahad Abdullah Albalawi",
             "Primary_Capability": "Neuro PT",
             "Secondary_Capability": "Paediatric OT",
             "Verification_Status": "Pending_Verification",
             "Competency_Level": "P3", "Assessment_Date": "",
             "Assessor": "", "Expiry_Date": ""},
            {"Staff_Name": "Sumaya Abdullah Al Batook",
             "Primary_Capability": "Inpatient Rehab",
             "Secondary_Capability": "Early Mobilization",
             "Verification_Status": "Pending_Verification",
             "Competency_Level": "P3", "Assessment_Date": "",
             "Assessor": "", "Expiry_Date": ""},
            {"Staff_Name": "Reem Abdulrazeq",
             "Primary_Capability": "Speech-Language Therapy",
             "Secondary_Capability": "Dysphagia Management",
             "Verification_Status": "Pending_Verification",
             "Competency_Level": "P2", "Assessment_Date": "",
             "Assessor": "", "Expiry_Date": ""},
            {"Staff_Name": "Maryam Naji Ali",
             "Primary_Capability": "Occupational Therapy",
             "Secondary_Capability": "ADL Training",
             "Verification_Status": "Pending_Verification",
             "Competency_Level": "P2", "Assessment_Date": "",
             "Assessor": "", "Expiry_Date": ""},
            {"Staff_Name": "Shoug Atallah Alanazi",
             "Primary_Capability": "Cast Application",
             "Secondary_Capability": "Splinting",
             "Verification_Status": "Pending_Verification",
             "Competency_Level": "P2", "Assessment_Date": "",
             "Assessor": "", "Expiry_Date": ""},
        ],
        "Data_Dictionary": [
            {"Key": "Core Therapist", "Value": "Permanent therapist"},
            {"Key": "Tamheer Therapist", "Value": "Tamheer trainee therapist"},
            {"Key": "Core Secretary", "Value": "Permanent secretary"},
            {"Key": "Tamheer Secretary", "Value": "Tamheer trainee secretary"},
            {"Key": "Contractor", "Value": "Agency/locum therapist on fixed-term contract"},
            {"Key": "Status: Active", "Value": "Currently working, full access"},
            {"Key": "Status: Leave", "Value": "On approved leave"},
            {"Key": "Status: Suspended", "Value": "Access revoked, pending review"},
            {"Key": "Status: Offboarded", "Value": "Left department, no access"},
            {"Key": "Competency P1", "Value": "Supervised practice — requires oversight"},
            {"Key": "Competency P2", "Value": "Independent practice — standard caseload"},
            {"Key": "Competency P3", "Value": "Advanced/supervisory — can mentor & sign off"},
            {"Key": "Doc_Status: Complete", "Value": "All notes signed within 24h"},
            {"Key": "Doc_Status: Incomplete", "Value": "Unsigned notes >24h, triggers escalation"},
            {"Key": "Doc_Status: Overdue", "Value": "Unsigned notes >48h, supervisor action"},
            {"Key": "Readiness: Ready", "Value": "Full staffing, equipment functional"},
            {"Key": "Readiness: Partial", "Value": "1 staff short OR 1 equipment issue"},
            {"Key": "Readiness: Not Ready", "Value": "2+ staff short OR critical equipment down"},
            {"Key": "Severity: Critical", "Value": "Immediate danger — alert head now"},
            {"Key": "Leave: Coverage_Required", "Value": "Approved leave needs named cover"},
        ],
        "Telegram_Users": [
            {"Staff_Name": "Abdulrahman Hawsawi", "Unit": "U08",
             "Telegram_Username": "", "Telegram_Chat_ID": "", "Active": "TRUE"},
            {"Staff_Name": "Abdulmajeed Mohammed AlJuraid", "Unit": "U01",
             "Telegram_Username": "", "Telegram_Chat_ID": "", "Active": "TRUE"},
        ],
        "API_Configuration": [
            {"Service": "Telegram_Bot_Token", "Value": "", "Notes": "Store token manually"},
            {"Service": "Telegram_Bot_Username", "Value": "@Rehab_RCSH_bot",
             "Notes": "Verified bot name"},
            {"Service": "Google_Sheet_ID", "Value": "", "Notes": "After Google Sheet creation"},
            {"Service": "Apps_Script_Webhook", "Value": "",
             "Notes": "Deployment URL"},
            {"Service": "Copilot_Agent_ID", "Value": "", "Notes": "Optional"},
        ],
        "Leave_Tracker": [
            {"Leave_ID": "LV-2026-001", "Staff_Name": "Nouf Mohammed Abduldaim",
             "Leave_Type": "Annual", "Start_Date": day, "End_Date": day,
             "Duration_Days": "1", "Status": "Approved",
             "Approved_By": "Shahad Abdullah Albalawi", "Requested_Date": day,
             "Approved_Date": day, "Coverage_Arranged": "No",
             "Coverage_Staff": "", "Notes": "Cover not yet arranged"},
        ],
        "Incident_Reports": [],
        "Policy_Registry": [
            {"Policy_ID": "POL-001", "Title": "Equipment Request Procedure",
             "Version": "2.1", "Effective_Date": "2026-01-01",
             "Review_Date": "2020-06-01", "Owner": "Section Head",
             "Status": "Active", "Last_Reviewed_By": "",
             "Notes": "Overdue for scheduled review"},
        ],
        "Reminders": [
            {"Reminder_ID": "REM-2026-001",
             "Title": "Confirm weekend coverage roster",
             "Audience": "Supervisors", "Start_Date": day, "End_Date": "",
             "Cadence": "Weekly", "Priority": "Normal", "Status": "Active",
             "Created_By": "Section Head", "Last_Sent": "",
             "Calendar_Event_ID": "",
             "Notes": "Seeded example — edit or set Status=Done"},
        ],
        "Memo_Log": [
            {"Memo_ID": "MEM-2026-001", "Date": day,
             "Title": "Welcome to agent reminders",
             "Body": "Reminders, memos and agendas from the bot are saved "
                     "here and in your calendar when connected.",
             "Audience": "All", "Author": "Section Head", "Status": "Active"},
        ],
        "Meeting_Agenda": [
            {"Meeting_ID": "MTG-2026-001", "Date": day,
             "Title": "Weekly supervisors huddle",
             "Agenda_Items": "1) Coverage gaps 2) Overdue actions "
                             "3) Equipment issues",
             "Attendees": "Supervisors", "Status": "Scheduled",
             "Calendar_Event_ID": "", "Minutes_Ref": ""},
        ],
        "Staff_Evaluations": [],
        "Announcements_Log": [
            {"Date": day, "Title": "Weekly huddle moved to 09:30",
             "Body": "Tuesday huddle starts 09:30 this week only.",
             "Audience": "All units", "Author": "Section Head", "Status": "Sent"},
        ],
        "Operational_Actions": [
            {"Action_ID": f"ACT-{date.today().year}-001", "Date_Raised": day,
             "Title": "Restock 4-inch cast rolls", "Owner": "Shoug Atallah Alanazi",
             "Due_Date": day, "Status": "Open", "Priority": "High",
             "Source": "Daily Report", "Notes": "From U06 staff report"},
            {"Action_ID": f"ACT-{date.today().year}-002", "Date_Raised": day,
             "Title": "Fix ultrasound probe (U03)", "Owner": "Sumaya Abdullah Al Batook",
             "Due_Date": day, "Status": "Open", "Priority": "Medium",
             "Source": "Daily Report", "Notes": ""},
            {"Action_ID": f"ACT-{date.today().year}-003", "Date_Raised": day,
             "Title": "Publish September leave roster", "Owner": "Shahad Abdullah Albalawi",
             "Due_Date": day, "Status": "Done", "Priority": "Medium",
             "Source": "Meeting", "Notes": ""},
        ],
        "Training_Tracker": [
            {"Staff_Name": "Khaled Sultan Al-Otaibi", "Course": "BLS",
             "Provider": "AHA", "Date": day, "Status": "Valid",
             "Expiry_Date": (date.today().replace(day=1)).isoformat(),
             "Hours": "6"},
        ],
        "Equipment_Issues": [
            {"Issue_ID": f"ISS-{date.today().year}-001", "Date": day,
             "Unit": "U03", "Equipment": "Ultrasound probe",
             "Issue": "Intermittent signal", "Severity": "High",
             "Status": "Open", "Reported_By": "Sumaya Abdullah Al Batook",
             "Resolved_Date": ""},
            {"Issue_ID": f"ISS-{date.today().year}-002", "Date": day,
             "Unit": "U01", "Equipment": "Treadmill belt",
             "Issue": "Belt slipping", "Severity": "Medium",
             "Status": "Resolved", "Reported_By": "Khaled Sultan Al-Otaibi",
             "Resolved_Date": day},
        ],
        "Coverage_Tracker": [
            {"Date": day, "Unit": "U03", "Absent_Staff": "1 sick leave",
             "Covering_Staff": "On-call pool", "Coverage_Status": "Partial",
             "Notes": ""},
        ],
        "Supervisor_Briefings": [],
        "Agent_Audit_Log": [],
        "Knowledge_FAQ": [
            {"Question": "What is the process for equipment request?",
             "Answer": "Raise it in your daily report or /equipment; supervisor verifies; "
                       "Section Head approves; Biomedical fulfils.",
             "Source": "SOP", "Updated": day},
            {"Question": "Show rehabilitation escalation path.",
             "Answer": "Team → Shift In-Charge → Unit Supervisor → Section Head → "
                       "Hospital Operations (after hours: on-call administrator).",
             "Source": "Structure", "Updated": day},
            {"Question": "How is annual leave coverage arranged?",
             "Answer": "Request 14 days ahead with named covering therapist; supervisor "
                       "confirms; Section Head approves.",
             "Source": "SOP", "Updated": day},
        ],
    }
    # BLS expiry: 20 days from today (expiring soon by design).
    tabs["Training_Tracker"][0]["Expiry_Date"] = date.fromordinal(
        date.today().toordinal() + 20
    ).isoformat()
    return tabs


# ----------------------------------------------------------------------------
# High-level operations database
# ----------------------------------------------------------------------------
class OpsDB:
    """Department operations queries over any backend."""

    def __init__(self, backend: SheetBackend) -> None:
        self.b = backend

    # -- org structure ---------------------------------------------------
    def units(self) -> list[dict[str, str]]:
        return self.b.read_tab("Units")

    def unit_by_id(self, unit_id: str) -> Optional[dict[str, str]]:
        want = _s(unit_id).upper()
        for u in self.units():
            if _s(u.get("Unit_ID")).upper() == want:
                return u
        return None

    def resolve_unit(self, text: str) -> Optional[dict[str, str]]:
        """Accept U01 / 01 / 1 / name fragment → unit row."""
        t = _s(text).upper()
        if re.fullmatch(r"U?0?(\d{1,2})", t):
            num = re.fullmatch(r"U?0?(\d{1,2})", t).group(1)  # type: ignore[union-attr]
            return self.unit_by_id(f"U{int(num):02d}")
        for u in self.units():
            if t and t in _s(u.get("Unit_Name")).upper():
                return u
        return None

    def supervisors(self) -> list[dict[str, str]]:
        return self.b.read_tab("Supervisors")

    def staff(self) -> list[dict[str, str]]:
        return self.b.read_tab("Staff_Register")

    def staff_role(self, name: str) -> str:
        want = _s(name).lower()
        for s in self.staff():
            if _s(s.get("Name")).lower() == want:
                role = _s(s.get("Role"))
                return role if not _missing(role) else "Staff"
        return "Staff"

    def staff_by_unit(self, unit_name_or_id: str) -> list[dict[str, str]]:
        unit = self.resolve_unit(unit_name_or_id)
        names = {unit_name_or_id.strip().lower()}
        if unit:
            names.add(_s(unit.get("Unit_ID")).lower())
            names.add(_s(unit.get("Unit_Name")).lower())
        return [s for s in self.staff() if _s(s.get("Unit")).lower() in names]

    def find_staff(self, query: str) -> list[dict[str, str]]:
        q = _s(query).lower()
        return [s for s in self.staff() if q and q in _s(s.get("Name")).lower()]

    # -- telegram users (auth source) -------------------------------------
    def telegram_users(self, active_only: bool = True) -> list[dict[str, str]]:
        rows = self.b.read_tab("Telegram_Users")
        if not active_only:
            return rows
        return [r for r in rows if _s(r.get("Active")).lower() in ACTIVE_MARKERS]

    def chat_id_for(self, staff_name: str) -> str:
        """Active Chat ID for a staff name ('' when unknown/inactive)."""
        want = _s(staff_name).lower()
        for r in self.telegram_users(active_only=True):
            if _s(r.get("Staff_Name")).lower() == want:
                chat = _s(r.get("Telegram_Chat_ID"))
                return chat if chat.lstrip("-").isdigit() else ""
        return ""

    def pending_telegram_users(self) -> list[dict[str, str]]:
        """Rows awaiting admin approval (Active flag off but Chat ID present)."""
        return [r for r in self.b.read_tab("Telegram_Users")
                if _s(r.get("Active")).lower() not in ACTIVE_MARKERS
                and _s(r.get("Telegram_Chat_ID"))]

    def upsert_telegram_user(self, staff_name: str, unit: str, username: str,
                             chat_id: str, active: str = "FALSE") -> None:
        """Insert or update a Telegram_Users row by staff name (for /register)."""
        updated = self.b.update_rows("Telegram_Users", "Staff_Name", staff_name, {
            "Unit": unit, "Telegram_Username": username,
            "Telegram_Chat_ID": chat_id, "Active": active,
        })
        if not updated:
            self.b.append_row("Telegram_Users", {
                "Staff_Name": staff_name, "Unit": unit,
                "Telegram_Username": username,
                "Telegram_Chat_ID": chat_id, "Active": active,
            })

    def set_user_active(self, staff_name: str, active: bool = True) -> bool:
        """Approve/suspend a user. Returns True when a row was updated."""
        return self.b.update_rows(
            "Telegram_Users", "Staff_Name", staff_name,
            {"Active": "TRUE" if active else "FALSE"}) > 0

    def supervisor_reports_between(self, unit_id: str,
                                   start: date, end: date) -> list[dict[str, str]]:
        """Supervisor reports for one unit in [start, end] (inclusive)."""
        out = []
        for r in self.b.read_tab("Daily_Supervisor_Reports"):
            day = _parse_date(r.get("Date"))
            if not day or not (start <= day <= end):
                continue
            unit = self.resolve_unit(_s(r.get("Unit")))
            if unit and _s(unit.get("Unit_ID")).upper() == unit_id.upper():
                out.append(r)
        return out

    # -- dashboard ---------------------------------------------------------
    def dashboard(self) -> dict[str, str]:
        return {_s(r.get("KPI")): _s(r.get("Value")) for r in self.b.read_tab("Dashboard")}

    # -- daily reports ------------------------------------------------------
    def staff_reports(self, day: date | str) -> list[dict[str, str]]:
        want = _datestr(day)
        return [r for r in self.b.read_tab("Daily_Staff_Reports")
                if _norm_date(r.get("Report_Date")) == want]

    def supervisor_reports(self, day: date | str) -> list[dict[str, str]]:
        want = _datestr(day)
        return [r for r in self.b.read_tab("Daily_Supervisor_Reports")
                if _norm_date(r.get("Date")) == want]

    def missing_staff_reports(self, day: date | str) -> list[str]:
        """Staff expected to file who have no report for `day`.

        Excludes supervisors/head/secretary roles, non-active staff, and
        anyone on approved leave that day.
        """
        day_d = day if isinstance(day, date) else (_parse_date(day) or date.today())
        reported = {_s(r.get("Staff_Name")).lower() for r in self.staff_reports(day_d)}
        on_leave = {_s(r.get("Staff_Name")).lower() for r in self.on_leave(day_d)}
        missing: list[str] = []
        for s in self.staff():
            name = _s(s.get("Name"))
            if not name or name.lower() in reported or name.lower() in on_leave:
                continue
            if _s(s.get("Status")).lower() not in {"", "active"}:
                continue
            if STAFF_REPORT_EXCLUDED_ROLES.search(_s(s.get("Role"))):
                continue
            missing.append(f"{name} ({_s(s.get('Unit')) or 'no unit'})")
        return missing

    def missing_supervisor_reports(self, day: date | str) -> list[str]:
        reported_ids: set[str] = set()
        for r in self.supervisor_reports(day):
            unit = self.resolve_unit(_s(r.get("Unit")))
            if unit:
                reported_ids.add(_s(unit.get("Unit_ID")).upper())
        missing: list[str] = []
        for uid in EXPECTED_SUP_UNITS:
            if uid not in reported_ids:
                unit = self.unit_by_id(uid)
                label = f"{uid} {_s(unit.get('Unit_Name'))}" if unit else uid
                missing.append(label.strip())
        return missing

    def add_staff_report(self, row: dict[str, str]) -> None:
        self.b.append_row("Daily_Staff_Reports", row)

    def add_supervisor_report(self, row: dict[str, str]) -> None:
        self.b.append_row("Daily_Supervisor_Reports", row)

    # -- actions --------------------------------------------------------------
    def open_actions(self) -> list[dict[str, str]]:
        return [r for r in self.b.read_tab("Operational_Actions")
                if _s(r.get("Status")).lower() not in {"done", "closed", "cancelled"}]

    def overdue_actions(self, today: Optional[date] = None) -> list[dict[str, str]]:
        today = today or date.today()
        out = []
        for r in self.open_actions():
            due = _parse_date(r.get("Due_Date"))
            if due and due < today:
                out.append(r)
        return out

    def actions_due_within(self, days: int,
                           today: Optional[date] = None) -> list[dict[str, str]]:
        """Open actions due today..today+days (inclusive)."""
        today = today or date.today()
        out = []
        for r in self.open_actions():
            due = _parse_date(r.get("Due_Date"))
            if due and today <= due <= today + timedelta(days=days):
                out.append(r)
        return out

    def next_action_id(self) -> str:
        year = date.today().year
        best = 0
        for r in self.b.read_tab("Operational_Actions"):
            m = re.fullmatch(rf"ACT-{year}-(\d+)", _s(r.get("Action_ID")))
            if m:
                best = max(best, int(m.group(1)))
        return f"ACT-{year}-{best + 1:03d}"

    def add_action(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Action_ID", self.next_action_id())
        row.setdefault("Date_Raised", date.today().isoformat())
        row.setdefault("Status", "Open")
        self.b.append_row("Operational_Actions", row)
        return row["Action_ID"]

    # -- equipment --------------------------------------------------------------
    def open_equipment_issues(self) -> list[dict[str, str]]:
        return [r for r in self.b.read_tab("Equipment_Issues")
                if _s(r.get("Status")).lower() not in {"resolved", "closed"}]

    def next_issue_id(self) -> str:
        year = date.today().year
        best = 0
        for r in self.b.read_tab("Equipment_Issues"):
            m = re.fullmatch(rf"ISS-{year}-(\d+)", _s(r.get("Issue_ID")))
            if m:
                best = max(best, int(m.group(1)))
        return f"ISS-{year}-{best + 1:03d}"

    def add_equipment_issue(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Issue_ID", self.next_issue_id())
        row.setdefault("Date", date.today().isoformat())
        row.setdefault("Status", "Open")
        self.b.append_row("Equipment_Issues", row)
        return row["Issue_ID"]

    # -- training / coverage / announcements --------------------------------------
    def training_expiring(self, days: int = 30) -> list[dict[str, str]]:
        today = date.today()
        out = []
        for r in self.b.read_tab("Training_Tracker"):
            exp = _parse_date(r.get("Expiry_Date"))
            if exp and 0 <= (exp - today).days <= days:
                out.append(r)
        return out

    def training_expired(self) -> list[dict[str, str]]:
        today = date.today()
        out = []
        for r in self.b.read_tab("Training_Tracker"):
            exp = _parse_date(r.get("Expiry_Date"))
            if exp and exp < today:
                out.append(r)
        return out

    def coverage_on(self, day: date | str) -> list[dict[str, str]]:
        want = _datestr(day)
        return [r for r in self.b.read_tab("Coverage_Tracker")
                if _norm_date(r.get("Date")) == want]

    def add_coverage(self, row: dict[str, str]) -> None:
        self.b.append_row("Coverage_Tracker", row)

    def add_announcement(self, row: dict[str, str]) -> None:
        row = dict(row)
        row.setdefault("Date", date.today().isoformat())
        row.setdefault("Status", "Sent")
        self.b.append_row("Announcements_Log", row)

    def recent_announcements(self, limit: int = 5) -> list[dict[str, str]]:
        return self.b.read_tab("Announcements_Log")[-limit:]

    # -- briefing / faq / audit ---------------------------------------------------
    def add_briefing(self, row: dict[str, str]) -> None:
        self.b.append_row("Supervisor_Briefings", row)

    def faq_search(self, query: str, top_k: int = 2) -> list[dict[str, str]]:
        tokens = {t for t in re.findall(r"[a-z0-9]{3,}", query.lower())}
        scored = []
        for r in self.b.read_tab("Knowledge_FAQ"):
            qt = set(re.findall(r"[a-z0-9]{3,}", _s(r.get("Question")).lower()))
            overlap = tokens & qt
            if overlap:
                scored.append((len(overlap), r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def audit_append(self, event: str, telegram_id: str = "",
                     name: str = "", details: str = "") -> None:
        self.b.append_row("Agent_Audit_Log", {
            "Timestamp": datetime.now().isoformat(timespec="seconds"),
            "Event": event,
            "Telegram_ID": telegram_id,
            "Name": name,
            "Details": details[:500],
        })

    # -- v4.1: status, licenses, capabilities ------------------------------------
    def staff_status(self, name: str) -> str:
        """Status or 'Active' when the column is empty (backward compatible)."""
        want = _s(name).lower()
        for s in self.staff():
            if _s(s.get("Name")).lower() == want:
                st = _s(s.get("Status"))
                return st if st else "Active"
        return "Unknown"

    def active_staff(self) -> list[dict[str, str]]:
        return [s for s in self.staff()
                if _s(s.get("Status")).lower() in {"", "active"}]

    def licenses_expiring(self, days: int = 30) -> list[dict[str, str]]:
        today = date.today()
        out = []
        for s in self.staff():
            exp = _parse_date(s.get("License_Expiry"))
            if exp and 0 <= (exp - today).days <= days:
                out.append(s)
        return out

    def licenses_expired(self) -> list[dict[str, str]]:
        today = date.today()
        return [s for s in self.staff()
                if (_parse_date(s.get("License_Expiry")) or today) < today
                and _s(s.get("License_Expiry"))]

    def capabilities_for(self, name: str) -> list[dict[str, str]]:
        want = _s(name).lower()
        return [r for r in self.b.read_tab("Capability_Matrix")
                if _s(r.get("Staff_Name")).lower() == want]

    def competency_expiring(self, days: int = 30) -> list[dict[str, str]]:
        today = date.today()
        out = []
        for r in self.b.read_tab("Capability_Matrix"):
            exp = _parse_date(r.get("Expiry_Date"))
            if exp and 0 <= (exp - today).days <= days:
                out.append(r)
        return out

    def unit_min_staff(self, unit_id: str) -> int:
        unit = self.unit_by_id(unit_id)
        return _num(unit.get("Min_Staff_Required")) if unit else 0

    # -- v4.1: leave ------------------------------------------------------------
    def _leave_covers(self, row: dict[str, str], day: date) -> bool:
        if _s(row.get("Status")).lower() != "approved":
            return False
        start = _parse_date(row.get("Start_Date"))
        end = _parse_date(row.get("End_Date")) or start
        return bool(start and end and start <= day <= end)

    def on_leave(self, day: date | str) -> list[dict[str, str]]:
        day = day if isinstance(day, date) else (_parse_date(day) or date.today())
        return [r for r in self.b.read_tab("Leave_Tracker")
                if self._leave_covers(r, day)]

    def leave_for_staff(self, name: str) -> list[dict[str, str]]:
        want = _s(name).lower()
        return [r for r in self.b.read_tab("Leave_Tracker")
                if _s(r.get("Staff_Name")).lower() == want]

    def pending_leaves(self) -> list[dict[str, str]]:
        return [r for r in self.b.read_tab("Leave_Tracker")
                if _s(r.get("Status")).lower() in {"pending", "requested"}]

    def uncovered_leaves(self, day: date | str) -> list[dict[str, str]]:
        day = day if isinstance(day, date) else (_parse_date(day) or date.today())
        out = []
        for r in self.on_leave(day):
            arranged = _s(r.get("Coverage_Arranged")).lower()
            if arranged not in {"yes", "true", "arranged", "covered"}:
                out.append(r)
        return out

    def next_leave_id(self) -> str:
        year = date.today().year
        best = 0
        for r in self.b.read_tab("Leave_Tracker"):
            m = re.fullmatch(rf"LV-{year}-(\d+)", _s(r.get("Leave_ID")))
            if m:
                best = max(best, int(m.group(1)))
        return f"LV-{year}-{best + 1:03d}"

    def add_leave_request(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Leave_ID", self.next_leave_id())
        row.setdefault("Requested_Date", date.today().isoformat())
        row.setdefault("Status", "Pending")
        start = _parse_date(row.get("Start_Date"))
        end = _parse_date(row.get("End_Date")) or start
        if start and end:
            row["Duration_Days"] = str((end - start).days + 1)
        self.b.append_row("Leave_Tracker", row)
        return row["Leave_ID"]

    def approve_leave(self, leave_id: str, approver: str,
                      coverage_staff: str = "") -> bool:
        updates: dict[str, str] = {
            "Status": "Approved", "Approved_By": approver,
            "Approved_Date": date.today().isoformat(),
        }
        if coverage_staff.strip():
            updates["Coverage_Staff"] = coverage_staff.strip()
            updates["Coverage_Arranged"] = "Yes"
        return self.b.update_rows("Leave_Tracker", "Leave_ID", leave_id, updates) > 0

    # -- v4.1: incidents (bot surfaces metadata only) ------------------------------
    def open_incidents(self) -> list[dict[str, str]]:
        return [r for r in self.b.read_tab("Incident_Reports")
                if _s(r.get("Status")).lower() not in {"closed", "resolved"}]

    def serious_incidents(self) -> list[dict[str, str]]:
        return [r for r in self.open_incidents()
                if str(r.get("Severity", "")).strip().lower()
                in {"serious", "3_serious", "critical", "4_critical", "3", "4"}]

    def next_incident_id(self) -> str:
        year = date.today().year
        best = 0
        for r in self.b.read_tab("Incident_Reports"):
            m = re.fullmatch(rf"INC-{year}-(\d+)", _s(r.get("Incident_ID")))
            if m:
                best = max(best, int(m.group(1)))
        return f"INC-{year}-{best + 1:03d}"

    def add_incident(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Incident_ID", self.next_incident_id())
        row.setdefault("Date", date.today().isoformat())
        row.setdefault("Status", "Open")
        self.b.append_row("Incident_Reports", row)
        return row["Incident_ID"]

    @staticmethod
    def incident_public(r: dict[str, str]) -> dict[str, str]:
        """Metadata safe for chat: never Description or patient-linked fields."""
        return {k: _s(r.get(k)) for k in (
            "Incident_ID", "Date", "Unit", "Incident_Type", "Severity",
            "Status", "Reported_By")}

    # -- v4.1: policies ------------------------------------------------------------
    def policies(self) -> list[dict[str, str]]:
        return self.b.read_tab("Policy_Registry")

    def policies_overdue(self, today: Optional[date] = None) -> list[dict[str, str]]:
        today = today or date.today()
        out = []
        for r in self.policies():
            if _s(r.get("Status")).lower() not in {"active", ""}:
                continue
            review = _parse_date(r.get("Review_Date"))
            if review and review < today:
                out.append(r)
        return out

    # -- v4.1: minimal RBAC -----------------------------------------------------------
    def is_head(self, staff_name: str) -> bool:
        want = _s(staff_name).lower()
        unit = self.unit_by_id("U08")
        heads = set()
        if unit and _s(unit.get("Supervisor")):
            heads.add(_s(unit.get("Supervisor")).lower())
        for s in self.supervisors():
            if _s(s.get("Area")).lower() == "section head":
                heads.add(_s(s.get("Supervisor")).lower())
        return want in heads

    def supervises(self, staff_name: str, unit_id: str) -> bool:
        unit = self.unit_by_id(unit_id)
        if not unit:
            return False
        return _s(unit.get("Supervisor")).lower() == _s(staff_name).lower()

    def can_manage(self, staff_name: str, unit_id: str) -> bool:
        """Head or the unit's supervisor (used by /leave_approve)."""
        return self.is_head(staff_name) or self.supervises(staff_name, unit_id)

    # -- v4.2: audiences + email ------------------------------------------------------
    def email_for(self, staff_name: str) -> str:
        want = _s(staff_name).lower()
        for s in self.staff():
            if _s(s.get("Name")).lower() == want:
                return _s(s.get("Email"))
        return ""

    def supervisor_names(self) -> list[str]:
        names: list[str] = []
        for u in self.units():
            sup = _s(u.get("Supervisor"))
            if sup and sup not in names:
                names.append(sup)
        for s in self.supervisors():
            sup = _s(s.get("Supervisor"))
            if sup and sup not in names:
                names.append(sup)
        return names

    def resolve_audience(self, audience: str) -> list[str]:
        """Audience label → staff names. All / Supervisors / unit / name."""
        label = _s(audience).strip()
        low = label.lower()
        if low == "all":
            return [_s(s.get("Name")) for s in self.active_staff()
                    if _s(s.get("Name"))]
        if low in {"supervisors", "supervisor"}:
            return self.supervisor_names()
        unit = self.resolve_unit(label)
        if unit:
            uid = str(unit.get("Unit_ID")).upper()
            out = []
            for s in self.active_staff():
                u = self.resolve_unit(str(s.get("Unit", "")))
                if u and str(u.get("Unit_ID")).upper() == uid:
                    out.append(_s(s.get("Name")))
            if out:
                return out
        if any(_s(s.get("Name")).lower() == low for s in self.staff()):
            return [_s(s.get("Name")) for s in self.staff()
                    if _s(s.get("Name")).lower() == low]
        return []

    def emails_for_audience(self, audience: str) -> list[str]:
        addrs = []
        for name in self.resolve_audience(audience):
            email = self.email_for(name)
            if email and "@" in email and email not in addrs:
                addrs.append(email)
        return addrs

    # -- v4.2: reminders ------------------------------------------------------------
    def reminders(self) -> list[dict[str, str]]:
        return self.b.read_tab("Reminders")

    def active_reminders(self) -> list[dict[str, str]]:
        return [r for r in self.reminders()
                if _s(r.get("Status")).lower() == "active"]

    def _next_seq_id(self, tab: str, col: str, prefix: str) -> str:
        year = date.today().year
        best = 0
        for r in self.b.read_tab(tab):
            m = re.fullmatch(rf"{prefix}-{year}-(\d+)", _s(r.get(col)))
            if m:
                best = max(best, int(m.group(1)))
        return f"{prefix}-{year}-{best + 1:03d}"

    def next_reminder_id(self) -> str:
        return self._next_seq_id("Reminders", "Reminder_ID", "REM")

    def add_reminder(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Reminder_ID", self.next_reminder_id())
        row.setdefault("Status", "Active")
        self.b.append_row("Reminders", row)
        return row["Reminder_ID"]

    def mark_reminder_sent(self, reminder_id: str, day: date | str,
                           done: bool = False) -> bool:
        updates = {"Last_Sent": _datestr(day)}
        if done:
            updates["Status"] = "Done"
        return self.b.update_rows("Reminders", "Reminder_ID",
                                  reminder_id, updates) > 0

    def due_reminders(self, today: date | None = None) -> list[dict[str, str]]:
        """Active reminders due on `today` per their cadence."""
        today = today or date.today()
        out = []
        for r in self.active_reminders():
            start = _parse_date(r.get("Start_Date")) or today
            if start > today:
                continue
            end = _parse_date(r.get("End_Date"))
            if end and end < today:
                continue
            cadence = _s(r.get("Cadence")).lower() or "once"
            last = _parse_date(r.get("Last_Sent"))
            if cadence == "once":
                if last is None and start <= today:
                    out.append(r)
            elif cadence == "daily":
                if last != today:
                    out.append(r)
            elif cadence == "weekly":
                if today.weekday() == start.weekday() and last != today:
                    out.append(r)
            elif cadence == "monthly":
                anchor = min(start.day, monthrange(today.year, today.month)[1])
                anchor_date = date(today.year, today.month, anchor)
                if today >= anchor_date and (last is None or last < anchor_date):
                    out.append(r)
        return out

    # -- v4.2: memos + agendas ---------------------------------------------------------
    def memos(self) -> list[dict[str, str]]:
        return self.b.read_tab("Memo_Log")

    def add_memo(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Memo_ID", self._next_seq_id("Memo_Log", "Memo_ID", "MEM"))
        row.setdefault("Date", date.today().isoformat())
        row.setdefault("Status", "Active")
        self.b.append_row("Memo_Log", row)
        return row["Memo_ID"]

    def agendas(self) -> list[dict[str, str]]:
        return self.b.read_tab("Meeting_Agenda")

    def upcoming_agendas(self, today: date | None = None,
                         days: int = 14) -> list[dict[str, str]]:
        today = today or date.today()
        out = []
        for r in self.agendas():
            if _s(r.get("Status")).lower() in {"done", "cancelled", "canceled"}:
                continue
            d = _parse_date(r.get("Date"))
            if d and today <= d <= today + timedelta(days=days):
                out.append(r)
        return sorted(out, key=lambda r: str(r.get("Date")))

    def add_agenda(self, row: dict[str, str]) -> str:
        row = dict(row)
        row.setdefault("Meeting_ID",
                       self._next_seq_id("Meeting_Agenda", "Meeting_ID", "MTG"))
        row.setdefault("Status", "Scheduled")
        self.b.append_row("Meeting_Agenda", row)
        return row["Meeting_ID"]

    # -- v4.2: evaluation range reads -----------------------------------------------------
    def staff_reports_between(self, start: date, end: date,
                              name: str = "") -> list[dict[str, str]]:
        want = _s(name).lower()
        out = []
        for r in self.b.read_tab("Daily_Staff_Reports"):
            d = _parse_date(r.get("Report_Date"))
            if not d or not (start <= d <= end):
                continue
            if want and _s(r.get("Staff_Name")).lower() != want:
                continue
            out.append(r)
        return out

    def approved_leave_days_between(self, name: str, start: date,
                                    end: date) -> int:
        want = _s(name).lower()
        total = 0
        for r in self.b.read_tab("Leave_Tracker"):
            if _s(r.get("Staff_Name")).lower() != want:
                continue
            if _s(r.get("Status")).lower() != "approved":
                continue
            s = _parse_date(r.get("Start_Date"))
            e = _parse_date(r.get("End_Date")) or s
            if not s or not e:
                continue
            lo, hi = max(s, start), min(e, end)
            if lo <= hi:
                total += (hi - lo).days + 1
        return total

    def evaluations_for(self, month: str) -> list[dict[str, str]]:
        """Latest snapshot per staff for `month` (append-wins on re-runs)."""
        latest: dict[str, dict[str, str]] = {}
        for r in self.b.read_tab("Staff_Evaluations"):
            if _s(r.get("Eval_Month")) == month:
                latest[_s(r.get("Staff_Name")).lower()] = r
        return list(latest.values())

    def save_evaluation(self, row: dict[str, str]) -> None:
        """Append-only snapshot; readers take the latest per staff."""
        self.b.append_row("Staff_Evaluations", row)

    # -- governance ---------------------------------------------------------------
    def ensure_schema(self) -> dict[str, str]:
        return self.b.ensure_tabs(SCHEMAS)

    def datahealth(self) -> dict[str, Any]:
        """Data-quality findings for /datahealth and the demo."""
        staff = self.staff()
        missing_roles = [f"{_s(s.get('Name'))} ({_s(s.get('Unit'))})"
                         for s in staff if _missing(s.get("Role"))]
        units_no_sup = [_s(u.get("Unit_ID")) for u in self.units()
                        if _missing(u.get("Supervisor"))]
        tg = self.telegram_users(active_only=False)
        tg_no_chat = [_s(r.get("Staff_Name")) for r in tg
                      if _s(r.get("Active")).lower() in ACTIVE_MARKERS
                      and not _s(r.get("Telegram_Chat_ID"))]
        unverified_cap = [r for r in self.b.read_tab("Capability_Matrix")
                          if _s(r.get("Verification_Status")).lower() != "verified"]
        return {
            "staff_count": len(staff),
            "units_count": len(self.units()),
            "missing_roles": missing_roles,
            "units_without_supervisor": units_no_sup,
            "telegram_active_without_chat_id": tg_no_chat,
            "capability_rows": len(self.b.read_tab("Capability_Matrix")),
            "capability_unverified": len(unverified_cap),
        }


# ----------------------------------------------------------------------------
# Cached accessor for bot handlers
# ----------------------------------------------------------------------------
_ops_db: Optional[OpsDB] = None
_ops_db_ready = False


def get_ops_db() -> Optional[OpsDB]:
    """Return the live ops DB, or None when the sheet is not connected.

    Cached after first call; use :func:`reset_ops_db` after changing
    credentials (e.g. in /setup).
    """
    global _ops_db, _ops_db_ready
    if _ops_db_ready:
        return _ops_db
    _ops_db_ready = True
    if settings.ops_sheet_id and settings.has_google_credentials:
        try:
            # Fail fast if the sheet is unreachable (bad ID / not shared).
            backend = GSpreadBackend(settings.ops_sheet_id)
            backend.read_tab("Units")
            _ops_db = OpsDB(backend)
            log.info("Ops sheet connected: %s", settings.ops_sheet_id)
        except Exception as exc:
            log.warning("Ops sheet unavailable (%s) — ops commands disabled.", exc)
            _ops_db = None
    else:
        log.info("OPS_SHEET_ID not set — ops commands disabled (core bot still works).")
    return _ops_db


def reset_ops_db() -> None:
    global _ops_db, _ops_db_ready
    _ops_db, _ops_db_ready = None, False


def demo_ops_db(today: Optional[date] = None) -> OpsDB:
    """In-memory ops DB seeded with the real department structure."""
    return OpsDB(MemoryBackend(seed_demo_tabs(today)))
