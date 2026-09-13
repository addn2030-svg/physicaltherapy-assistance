# Operations Sheet Setup — Rehab_Operations_Master_v2 (Agent v3)

Connects the bot to the department's Google Sheet mirror of
`Rehab_Operations_Master_v2.xlsx`. Time: ~30 min (mostly data entry).

## 1. Create the Google Sheet

Option A — import your `.xlsx`:
1. Drive → New → Google Sheets → File → Import → Upload → select
   `Rehab_Operations_Master_v2.xlsx` → "Replace spreadsheet".
2. Rename it `Rehab_Operations_Master_v2`.

Option B — build manually: create 19 tabs with the exact headers below
(row 1, exact spelling). Then run `/setup` in Telegram — the bot creates
any missing tabs + headers automatically.

## 2. Tab schemas (headers must match exactly)

Core workbook (11 tabs):

| Tab | Headers |
|---|---|
| Units | Unit_ID, Unit_Name, Supervisor |
| Supervisors | Supervisor, Area |
| Staff_Register | Name, Unit, Role |
| Daily_Staff_Reports | Report_Date, Staff_Name, Unit, Patients_Seen, New_Cases, Follow_Up_Cases, Documentation_Status, Issues, Follow_Up_Tomorrow, Submitted_Time |
| Daily_Supervisor_Reports | Date, Supervisor, Unit, Readiness, Present, Leave, Sick_Leave, Absent, Scheduled, Attended, No_Show, Attendance_Rate, Doc_Complete, Doc_Incomplete, Equipment, Urgent_Decision |
| Weekly_Summary | Week_Start, Week_End, Supervisor, Unit, Total_Appointments, Total_Attendance, Attendance_Rate, Documentation_Rate, Completed_Actions, Pending_Actions, Risks, Decisions_Required |
| Dashboard | KPI, Value |
| Capability_Matrix | Staff_Name, Primary_Capability, Secondary_Capability, Verification_Status |
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

Conventions:
- Dates: `YYYY-MM-DD` (`DD/MM/YYYY` also accepted when reading).
- `Active` / `Status` fields: TRUE/FALSE, Open/Done, Ready/Partial/Not Ready.
- `Telegram_Users.Active`: only `TRUE`/`Yes`/`Active`/`1` can use the bot.
- IDs: `ACT-2026-001`, `ISS-2026-001` (bot auto-numbers; keep the pattern
  for manual rows).

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
   (bot appends reports/actions/issues).
2. Copy the Spreadsheet ID from the URL into `.env`:
   `OPS_SHEET_ID=1AbC...`
3. Restart the bot, then send `/setup` (admin) to verify all 19 tabs.
4. Send `/datahealth` — fix missing roles and Chat IDs it flags.
5. Send `/briefing` — your first live morning briefing. 🌅

## 5. Column rules (privacy)

- Reporting tabs hold **operational counts only** — never add patient
  names, MRNs, or diagnoses to any tab. The bot PHI-screens every
  free-text field before appending and refuses blocked content.
- `Read` rule: the bot reads all tabs above and nothing else.
- `Write` rule: the bot only **appends** to Daily_Staff_Reports,
  Daily_Supervisor_Reports, Operational_Actions, Equipment_Issues,
  Coverage_Tracker, Announcements_Log, Supervisor_Briefings,
  Agent_Audit_Log. It never edits or deletes Sheet rows.

## 6. Daily rhythm (suggested)

| When | Who | What |
|---|---|---|
| 07:30 | Section Head | `/briefing` — readiness, gaps, overdue, urgent |
| 08:00 | Supervisors | `/supervisor` — file unit readiness |
| End of shift | Therapists | `/daily` — file counts |
| As needed | Anyone | `/equipment_add`, `/actions_add` |
| Weekly | Section Head | `/report` → weekly .docx (Drive) from Weekly_Summary |

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Operations sheet not connected" | `OPS_SHEET_ID` empty/wrong, or Sheet not shared with service email as Editor |
| `/setup` shows tabs created but empty | Normal — core tabs need your data; v3 tabs fill via bot |
| Auth works but `/briefing` empty | No reports filed yet — have a supervisor run `/supervisor` |
| Wrong numbers | Check date formats (`YYYY-MM-DD`) and unit IDs (`U01`–`U07`) |
