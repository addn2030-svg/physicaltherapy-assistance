# Operations Sheet Setup — Rehab_Operations_Master_v2 (Agent v4.2)

Connects the bot to the department's Google Sheet mirror of
`Rehab_Operations_Master_v2.xlsx`. Time: ~30 min (mostly data entry).

## 1. Create the Google Sheet

Option A — import your `.xlsx`:
1. Drive → New → Google Sheets → File → Import → Upload → select
   `Rehab_Operations_Master_v2.xlsx` → "Replace spreadsheet".
2. Rename it `Rehab_Operations_Master_v2`.

Option B — build manually: create 26 tabs with the exact headers below
(row 1, exact spelling). Then run `/setup` in Telegram — the bot creates
any missing tabs + headers automatically.

Upgrading from an older version: just run `/setup` — it adds missing tabs
(v4.1: Leave_Tracker, Incident_Reports, Policy_Registry; v4.2: Reminders,
Memo_Log, Meeting_Agenda, Staff_Evaluations) and appends new optional
columns (incl. Staff_Register.Email) without touching existing data.

## 2. Tab schemas (headers must match exactly)

Core workbook (11 tabs):

| Tab | Headers |
|---|---|
| Units | Unit_ID, Unit_Name, Supervisor, Min_Staff_Required, Capacity_Daily |
| Supervisors | Supervisor, Area |
| Staff_Register | Name, Unit, Role, Status, Contract_Type, License_Expiry, Email |
| Daily_Staff_Reports | Report_Date, Staff_Name, Unit, Patients_Seen, New_Cases, Follow_Up_Cases, Documentation_Status, Issues, Follow_Up_Tomorrow, Submitted_Time |
| Daily_Supervisor_Reports | Date, Supervisor, Unit, Readiness, Present, Leave, Sick_Leave, Absent, Scheduled, Attended, No_Show, Attendance_Rate, Doc_Complete, Doc_Incomplete, Equipment, Urgent_Decision |
| Weekly_Summary | Week_Start, Week_End, Supervisor, Unit, Total_Appointments, Total_Attendance, Attendance_Rate, Documentation_Rate, Completed_Actions, Pending_Actions, Risks, Decisions_Required |
| Dashboard | KPI, Value |
| Capability_Matrix | Staff_Name, Primary_Capability, Secondary_Capability, Verification_Status, Competency_Level, Assessment_Date, Assessor, Expiry_Date |
| Data_Dictionary | Key, Value |
| Telegram_Users | Staff_Name, Unit, Telegram_Username, Telegram_Chat_ID, Active |
| API_Configuration | Service, Value, Notes |

Agent v3 tabs (8 — `/setup` creates these for you):

| Tab | Headers |
|---|---|
| Announcements_Log | Date, Title, Body, Audience, Author, Status |
| Operational_Actions | Action_ID, Date_Raised, Title, Owner, Due_Date, Status, Priority, Source, Notes |
| Training_Tracker | Staff_Name, Course, Provider, Date, Status, Expiry_Date, Hours |
| Equipment_Issues | Issue_ID, Date, Unit, Equipment, Issue, Severity, Status, Reported_By, Resolved_Date |
| Coverage_Tracker | Date, Unit, Absent_Staff, Covering_Staff, Coverage_Status, Notes |
| Supervisor_Briefings | Date, Supervisor, Unit, Summary, Risks, Decisions_Required |
| Agent_Audit_Log | Timestamp, Event, Telegram_ID, Name, Details |
| Knowledge_FAQ | Question, Answer, Source, Updated |

Agent v4.1 tabs (3 — `/setup` creates these for you):

| Tab | Headers |
|---|---|
| Leave_Tracker | Leave_ID, Staff_Name, Leave_Type, Start_Date, End_Date, Duration_Days, Status, Approved_By, Requested_Date, Approved_Date, Coverage_Arranged, Coverage_Staff, Notes |
| Incident_Reports | Incident_ID, Date, Time, Unit, Reported_By, Incident_Type, Severity, Description, Immediate_Action, Supervisor_Notified, Status, Resolution_Date, Closed_By |
| Policy_Registry | Policy_ID, Title, Version, Effective_Date, Review_Date, Owner, Status, Last_Reviewed_By, Notes |

Agent v4.2 tabs (4 — `/setup` creates these for you):

| Tab | Headers |
|---|---|
| Reminders | Reminder_ID, Title, Audience, Start_Date, End_Date, Cadence, Priority, Status, Created_By, Last_Sent, Calendar_Event_ID, Notes |
| Memo_Log | Memo_ID, Date, Title, Body, Audience, Author, Status |
| Meeting_Agenda | Meeting_ID, Date, Title, Agenda_Items, Attendees, Status, Calendar_Event_ID, Minutes_Ref |
| Staff_Evaluations | Eval_Month, Staff_Name, Unit, Working_Days_Pct, Patients_Seen, Patient_Share_Pct, Load_Index, Doc_Rate_Pct, Leave_Days, Flags |

Conventions:
- Dates: `YYYY-MM-DD` (`DD/MM/YYYY` also accepted when reading).
- `Active` / `Status` fields: TRUE/FALSE, Open/Done, Ready/Partial/Not Ready.
- `Telegram_Users.Active`: only `TRUE`/`Yes`/`Active`/`1` can use the bot.
- `Staff_Register.Status`: Active (default when blank), Leave, Suspended,
  Offboarded. Non-active staff are excluded from missing-report nudges.
- `Competency_Level`: P1 supervised, P2 independent, P3 advanced/supervisory.
- `Incident_Reports.Severity`: Minor / Moderate / Serious / Critical.
  Serious + Critical page the supervisor and head automatically.
- IDs: `ACT-2026-001`, `ISS-2026-001`, `LV-2026-001`, `INC-2026-001`,
  `REM-2026-001`, `MEM-2026-001`, `MTG-2026-001`
  (bot auto-numbers; keep the pattern for manual rows).
- `Reminders.Cadence`: Once / Daily / Weekly / Monthly. Weekly fires on the
  Start_Date's weekday; Monthly on the Start_Date's day-of-month.
  `Audience`: All / Supervisors / unit ID / unit name / staff name.
  Set `Status=Done` to stop a reminder.
- `Reminders.Priority` / `Operational_Actions.Priority`: High tasks get a
  **daily** bot nudge when due within 3 days or overdue.
- `Meeting_Agenda.Attendees` uses the same audience labels; attendees get
  a bot nudge the day before the meeting.
- Evaluation columns (`Staff_Evaluations`) are written by the monthly
  auto-run — do not hand-edit. Formulas: working-days % excludes weekends
  (Fri/Sat, see EVAL_WEEKEND) and approved leave; patient share = staff ÷
  unit total; load 100% = unit average; doc rate = Complete ÷ filed.
  Supervisors/head/secretaries are excluded (they file supervisor
  reports, not `/daily`).

## 3. Fill the access tab

In `Telegram_Users`, one row per staff member (staff get Chat ID from
[@userinfobot](https://t.me/userinfobot)):

```
Staff_Name | Unit | Telegram_Username | Telegram_Chat_ID | Active
Abdulrahman Hawsawi | U08 | @... | 123456789 | TRUE
```

This tab becomes bot login #2 (after the Staff access sheet): Chat ID must
match the sender's Telegram ID and `Active` must be TRUE. Roles resolve
from `Staff_Register` by name.

## 4. Share + connect

1. Share the Sheet with the service-account email as **Editor**
   (bot appends reports/actions/issues; approvals update Leave_Tracker rows).
2. Copy the Spreadsheet ID from the URL into `.env`:
   `OPS_SHEET_ID=1AbC...`
3. Restart the bot, then send `/setup` (admin) to verify all 26 tabs.
4. Send `/datahealth` — fix missing roles and Chat IDs it flags.
5. Send `/briefing` — your first live morning briefing. 🌅

## 5. Column rules (privacy)

- Reporting tabs hold **operational counts only** — never add patient
  names, MRNs, or diagnoses to any tab. The bot PHI-screens every
  free-text field before appending and refuses blocked content.
- Incident rule: the bot only ever surfaces incident **metadata**
  (ID, date, unit, type, severity, status, reporter). The `Description`
  column is written and read by humans in the Sheet only — it never
  enters Telegram, logs, or alerts. See `docs/SECURITY.md`.
- `Read` rule: the bot reads all tabs above and nothing else.
- `Write` rule: the bot mostly **appends** (reports, actions, issues,
  coverage, announcements, briefings, audit, leave, incidents, reminders,
  memos, agendas, evaluation snapshots) — plus three narrow in-place
  updates: `/leave_approve` flips a Leave_Tracker row Pending→Approved;
  the reminder agent stamps Reminders.Last_Sent (+ Status=Done for Once);
  new reminders/agendas store their Calendar_Event_ID. It never edits or
  deletes anything else.

## 6. Daily rhythm (suggested)

| When | Who | What |
|---|---|---|
| 07:30 | Section Head | `/briefing` — readiness, gaps, overdue, urgent |
| 08:00 | Supervisors | `/supervisor` — file unit readiness |
| End of shift | Therapists | `/daily` — file counts |
| As needed | Anyone | `/equipment_add`, `/actions_add`, `/leave_add`, `/incident_add` |
| As needed | Supervisors | `/coverage`, `/whoison`, `/leave_approve`, `/capability` |
| As needed | Supervisors | `/remind_add`, `/memo`, `/agenda_add` (saved + calendar + email) |
| Anytime | Anyone | `/evaluate` (self; supervisors: any name + month) |
| Weekly | Section Head | `/report` → weekly .docx (Drive) from Weekly_Summary |
| Monthly (auto) | Agent | Staff evaluation snapshots + digests (1st, 08:00) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Operations sheet not connected" | `OPS_SHEET_ID` empty/wrong, or Sheet not shared with service email as Editor |
| `/setup` shows tabs created but empty | Normal — core tabs need your data; v3/v4.1 tabs fill via bot |
| Auth works but `/briefing` empty | No reports filed yet — have a supervisor run `/supervisor` |
| Wrong numbers | Check date formats (`YYYY-MM-DD`) and unit IDs (`U01`–`U07`) |
| `/leave_approve` says "own unit only" | Approver must supervise the requester's unit (or be head) |
| Reminder never fires | Check Status=Active, Start_Date ≤ today, End_Date empty/future, cadence anchor (weekly = start weekday) |
| `/evaluate` shows 0% everywhere | Nobody filed `/daily` that month, or the staffer is a supervisor/head (excluded by design) |
| Memo "not emailed" | Fill Staff_Register.Email + set SMTP_* in `.env` (see docs/COMMS.md) |
