# Rehab RCH Agent v2 🏥

A true AI assistant for the **Rehabilitation Department — RCH**:
answers department questions, drafts announcements, summarizes meetings,
generates operational reports, searches approved documents, and
**auto-saves everything to Google Drive** — available **24/7 via Telegram**.

> ⚠️ **Operational use only — no patient information allowed.**
> The bot screens every message and rejects patient names, MRNs,
> medical records, diagnoses, and treatment details.

## What it does

- ✅ Answers rehabilitation department questions (SOPs, escalation, processes)
- ✅ Drafts announcements
- ✅ Creates meeting summaries
- ✅ Generates operational reports (weekly / monthly / annual)
- ✅ Searches approved department documents
- ✅ Saves reports automatically to Google Drive
- ✅ Available 24/7 via Telegram
- ✅ No patient information allowed (PHI guardrail + refusal flow)

## Safety rails (Phase 2)

- 🧾 **Audit trail** — every access, block, question, and Drive save logged
  (local JSONL + Google Sheet mirror); admins review with `/audit`
- 📑 **Versioned citations** — answers cite `Document vVersion (approved: By, Date)`;
  only `Active` manifest documents are indexed
- 📶 **Knowledge coverage** — every answer shows High / Medium / Low / None;
  out-of-scope answers are labelled general guidance and flagged for human review
- 🔐 **Access review** — `Status` + `Valid Until` columns suspend/expire staff
  without deleting rows
- 🛡️ **Staff-only lockdown** — private chats enforced (bot auto-leaves
  groups), code-gated `/register` + admin approval, hourly access refresh.
  Policy: [docs/SECURITY.md](docs/SECURITY.md)

## Architecture

```
Staff → Telegram → Rehab RCH Agent → Gemini AI API → Google Drive
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full module map.

## Recommended free stack

| Component | Solution |
|---|---|
| Telegram interface | Telegram Bot |
| AI engine | Google Gemini |
| Source control | GitHub |
| Document storage | Google Drive |
| Database (staff access) | Google Sheets |
| Hosting | Oracle Cloud Free Tier |
| OS | Ubuntu |

**Estimated cost: $0/month** for moderate department usage.

## Repository structure

```
rehab-rch-agent/
├── bot.py               # Telegram entry point (commands + conversations)
├── ops_handlers.py      # Agent v3 ops commands (/briefing, /daily, ...)
├── sheets_ops.py        # Rehab_Operations_Master_v2 workbook layer
├── agents.py            # Agent v4 orchestra (6 support agents + escalator)
├── messenger.py         # Escalation routing + delivery (live/demo)
├── scheduler.py         # 24/7 proactive timetable + heartbeat
├── demo_ops.py          # Zero-credential ops demo (in-memory sheet)
├── demo_orchestra.py    # Full proactive-day simulation (no keys)
├── gemini_client.py     # Gemini AI wrapper (operational prompts, demo fallback)
├── google_drive.py      # Drive folder tree + dated uploads
├── knowledge_base.py    # Approved-docs index + keyword search + manifest governance
├── report_generator.py  # Branded .docx builder
├── auth.py              # Google Sheets staff allowlist (+ env/JSON fallback)
├── safety.py            # PHI screen — blocks patient data
├── audit.py             # Append-only audit trail (JSONL + Sheet mirror)
├── config.py            # Typed settings from .env
├── requirements.txt
├── .env.example         # Copy to .env (never commit .env)
├── staff_allowlist.example.json
├── systemd/rehab-agent.service   # 24/7 auto-restart service
├── scripts/setup_oracle.sh       # Oracle Cloud installer
├── scripts/retention_cleanup.py  # Local retention cleanup (audit exempt)
├── knowledge/           # Approved SOPs / guidelines / contacts (samples incl.)
│   └── manifest.example.json     # Document version control template
├── tests/               # pytest: safety, auth, KB, governance, audit, reports
└── docs/                # ARCHITECTURE, GOOGLE_SETUP, PRELAUNCH_CHECKLIST,
                         # STAFF_TRAINING, INCIDENT_RESPONSE
```

## Google Drive integration

The AI automatically saves generated reports. Example:

Staff writes: `Generate weekly rehabilitation summary`

Agent returns the summary and saves:

```
Google Drive
/Rehab RCH Reports/2026/September/
Weekly Summary - 13 Sep 2026.docx
```

Folder structure:

```
Rehab RCH Agent
├── Reports
│   ├── Weekly
│   ├── Monthly
│   └── Annual
├── Announcements
├── SOP
├── Meeting Minutes
└── Knowledge Base
```

## Knowledge base

Upload **approved files only**: `SOP.pdf`, `Department Guideline.docx`,
`Rehabilitation Structure.pdf`, `Contacts.xlsx`.
The agent reads them and answers staff questions (citing source files).

For production, register every file in `knowledge/manifest.json`
(see `manifest.example.json`): Document | Version | Approved By | Date | Status.
Only `Active` documents are indexed.

Recommended sources: department SOPs, operational procedures, contact lists,
meeting minutes, announcements, department policies.

⛔ Avoid uploading: patient records, MRNs, diagnostic reports, clinical notes, any PHI.

## Allowed vs blocked

Allowed:
- `What is the process for equipment request?`
- `Show rehabilitation escalation path.`
- `Draft announcement about annual leave coverage.`

Blocked (bot rejects + asks for de-identified resubmission):
- Patient names, medical records, diagnosis information, treatment details

## Telegram commands

| Command | Purpose |
|---|---|
| `/start` | Welcome + access check |
| `/help` | Command reference |
| `/report` | Guided report → `.docx` → Drive |
| `/announcement` | Guided announcement draft → optional Drive save |
| `/sop <question>` | Search SOPs / guidelines |
| `/meeting` | Meeting-minutes builder → Drive |
| `/save` | Save last document to Drive |
| `/kb` | Knowledge-base status (`/kb reload` to re-index) |
| `/audit` | Recent audit events (admins only) |
| `/briefing` | Morning ops briefing (ops sheet) |
| `/daily` | File daily staff report |
| `/supervisor` | File daily supervisor report |
| `/actions` | Open actions (`/actions_add` to add) |
| `/equipment` | Open equipment issues (`/equipment_add` to log) |
| `/dashboard` | Sheet KPIs |
| `/staff` | Staff directory |
| `/units` | Units + supervisors |
| `/datahealth` | Sheet data-quality check |
| `/setup` | Create ops tabs (admins only) |
| `/register` | Self-register for alerts (admin `/approve`) |
| `/digest` | Your personal ops slice |
| `/watchdog` | Run gap scan now (admins only) |
| `/schedule` | Proactive timetable |
| `/leave` | My leave requests (+ pending for managers) |
| `/leave_add` | Request leave (guided) |
| `/leave_approve` | Approve leave (own unit, supervisor/head) |
| `/incidents` | Open incidents — metadata only |
| `/incident_add` | Log an incident (guided, PHI-screened) |
| `/capability` | Capability & competency status |
| `/policies` | Policy register + overdue reviews |
| `/status` | My record: unit, license, leave, capabilities |
| `/whoison` | Who is on leave today (+ cover) |
| `/coverage` | Coverage vs minimum staffing |
| `/reminders` | Active reminders (`/remind_add` to add) |
| `/memos` | Recent memos (`/memo` to save) |
| `/agenda` | Upcoming agendas (`/agenda_add` to add) |
| `/evaluate` | Staff evaluation (self; managers: any name) |
| `/cancel` | Cancel current flow |

### Example — announcement

```
/announcement
Staff meeting Tuesday at 09:00
```

Agent:

```
Draft for review
Dear Team,

Please note that a Rehabilitation Department staff meeting is scheduled
for Tuesday at 09:00...
```

### Example — weekly report

```
/report
```

Agent:

```
Draft for review
Weekly Rehabilitation Operations Summary
Status Overview
...
Decisions Required
...
Next Actions
...
```

…and automatically saves the report to Google Drive.

Every answer also shows `Knowledge coverage: High/Medium/Low/None` plus
source citations, e.g. `📄 SOP.pdf v2.1 (approved: Section Head, 2026-09-01)`.

## Authentication

Only approved staff can use the bot. Google Sheet columns:

```
Telegram ID | Name | Role | Status | Valid Until
```

Example: `123456789 | Abdulrahman | Section Head | Active | 2027-09-01`

`Status` ≠ Active or past `Valid Until` denies access — use for monthly
access reviews and offboarding without deleting rows.

If not listed: `Access denied. Contact Rehabilitation Section Head.`

Second source: the `Telegram_Users` tab of the operations workbook —
rows with `Active = TRUE` and a matching `Telegram_Chat_ID` grant access
(roles resolve from `Staff_Register`).

Further fallbacks when Sheets is unavailable: `ALLOWED_TELEGRAM_IDS` env
var, then local `staff_allowlist.json` (see `staff_allowlist.example.json`).

## Quickstart (local)

```bash
cd rehab-rch-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python setup_wizard.py   # answers a few questions, creates .env for you
python bot.py
```

Windows shortcut: double-click `restart_bot.bat` — it pulls the latest
code, stops any running bot, and starts a fresh one (no typing needed).

No keys yet? Run the zero-credential demo — it exercises the full
pipeline (auth → PHI screen → KB search → drafts → .docx → Drive save
→ audit) with template AI responses:

```bash
python demo.py                 # scripted end-to-end scenario
python demo.py --interactive   # chat with the agent in your terminal
```

Or build the container: `docker build -t rehab-rch-agent .`

1. **Telegram token:** message [@BotFather](https://t.me/BotFather) → `/newbot` → paste token into `.env`.
2. **Gemini key:** https://aistudio.google.com/app/apikey → paste into `.env`.
3. **Google Drive/Sheets:** follow [docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md) (~20 min).
4. **Knowledge files:** drop approved SOPs into `knowledge/` → `/kb reload`.
5. **Tests:** `pytest -q`.

Without keys, the bot runs in **demo mode** (template drafts + local `output/`
saves) so all Telegram flows are testable for free.

## Operations workbook (Agent v3)

Mirror `Rehab_Operations_Master_v2.xlsx` to Google Sheets (11 core tabs +
8 agent tabs + 3 v4.1 tabs) and the bot becomes your daily operations desk:
`/briefing` morning rollup, `/daily` + `/supervisor` guided reporting,
`/actions` and `/equipment` tracking, `/dashboard` KPIs, `/datahealth`
quality checks — plus v4.1 leave management (`/leave`, `/leave_add`,
`/leave_approve`), incident logging (`/incidents`, `/incident_add`,
metadata only), capabilities (`/capability`), policies (`/policies`),
`/status`, `/whoison`, and `/coverage` — with every event mirrored to the
`Agent_Audit_Log` tab.

Setup: [docs/SHEETS_OPS.md](docs/SHEETS_OPS.md) · Zero-key preview:
`python demo_ops.py`

## Proactive orchestra (Agent v4)

Six support agents run 24/7 inside the bot: gap finder, watchdog, cutoff
escalator (therapist → supervisor → head → higher admin), briefing pusher,
report automator (evening rollup + weekly auto-fill into the sheet and
Drive), and a Gemini insight narrator. Dedup windows, quiet hours, full
audit. Manual: [docs/ORCHESTRA.md](docs/ORCHESTRA.md) · Simulation:
`python demo_orchestra.py`

## Reminders, comms & evaluation (Agent v4.2)

Eight agents now: + reminder cadence (Once/Daily/Weekly/Monthly audiences,
HIGH-task daily nudges, weekly task digests, meeting-day-before nudges)
and monthly staff evaluation (working-days %, patient share, load vs unit
average, documentation rate, flags — transparent formulas, no black-box
score). Reminders, memos (`/memo`), and agendas (`/agenda_add`) are saved
to the sheet and optionally fanned out by **email** (any SMTP provider)
and **Google Calendar** (same service account as Drive) — both off by
default until configured. Setup: [docs/COMMS.md](docs/COMMS.md)

## Notes archive (Agent v4.3)

Memos, agendas, evaluation digests, and weekly summaries are auto-saved
as tagged Markdown notes — browseable in Obsidian (open `output/notes/`
as a vault, or set `NOTES_VAULT_PATH`) and mirrored to Drive under
`Notes/...`. Sheet stays the live database; notes are the readable
archive. No setup needed.

## Before launch

Work through [docs/PRELAUNCH_CHECKLIST.md](docs/PRELAUNCH_CHECKLIST.md):
adversarial PHI tests, `manifest.json`, private repo, IT/Compliance written
approval, pilot testers, [staff training](docs/STAFF_TRAINING.md), and the
[incident response plan](docs/INCIDENT_RESPONSE.md).

## 24/7 hosting

Best free option: **Oracle Cloud Free Tier**. Full guide: [DEPLOY_ORACLE.md](DEPLOY_ORACLE.md).

```bash
sudo apt update
sudo apt install python3 python3-pip git -y
git clone https://github.com/addn2030-svg/physicaltherapy-assistance.git
cd physicaltherapy-assistance/rehab-rch-agent && bash scripts/setup_oracle.sh
sudo systemctl enable rehab-agent   # auto-restart on reboot
```

## Google Drive service account

1. Create Google Cloud Project.
2. Enable: Google Drive API + Google Sheets API.
3. Create Service Account → download `credentials.json`.
4. Share the Drive folder with the service-account email.

Full steps: [docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md).

Now the bot can: ✅ create folders ✅ upload reports ✅ update spreadsheets ✅ archive documents.

## Recommendation

As **Abdulrahman Bakor Howsawy**, Rehabilitation Section Head, build:

**Telegram + Gemini + Google Drive + GitHub + Oracle Cloud Free Tier**

The simplest way to get a 24/7 AI-powered Rehab RCH Agent running at
essentially no hosting cost — auto-generating and saving department reports
to Google Drive while staying focused on operational, non-patient information.
