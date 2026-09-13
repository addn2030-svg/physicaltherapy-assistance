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
from datetime import date, datetime
from typing import Any, Optional

from config import settings

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Schemas — 11 core tabs + 8 Agent v3 tabs (headers must match the Sheet)
# ----------------------------------------------------------------------------
SCHEMAS: dict[str, list[str]] = {
    # -- core workbook ---------------------------------------------------
    "Units": ["Unit_ID", "Unit_Name", "Supervisor"],
    "Supervisors": ["Supervisor", "Area"],
    "Staff_Register": ["Name", "Unit", "Role"],
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
        "Capability_Matrix": [],
        "Data_Dictionary": [
            {"Key": "Core Therapist", "Value": "Permanent therapist"},
            {"Key": "Tamheer Therapist", "Value": "Tamheer trainee therapist"},
            {"Key": "Core Secretary", "Value": "Permanent secretary"},
            {"Key": "Tamheer Secretary", "Value": "Tamheer trainee secretary"},
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
        """Staff expected to file who have no report for `day`."""
        reported = {_s(r.get("Staff_Name")).lower() for r in self.staff_reports(day)}
        missing: list[str] = []
        for s in self.staff():
            name = _s(s.get("Name"))
            if not name or name.lower() in reported:
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
