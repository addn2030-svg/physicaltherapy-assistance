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
├── gemini_client.py     # Gemini AI wrapper (operational prompts, demo fallback)
├── google_drive.py      # Drive folder tree + dated uploads
├── knowledge_base.py    # Approved-docs index + keyword search
├── report_generator.py  # Branded .docx builder
├── auth.py              # Google Sheets staff allowlist (+ env/JSON fallback)
├── safety.py            # PHI screen — blocks patient data
├── config.py            # Typed settings from .env
├── requirements.txt
├── .env.example         # Copy to .env (never commit .env)
├── staff_allowlist.example.json
├── systemd/rehab-agent.service   # 24/7 auto-restart service
├── scripts/setup_oracle.sh       # Oracle Cloud installer
├── knowledge/           # Approved SOPs / guidelines / contacts (samples incl.)
├── tests/               # pytest: safety, KB, report generator
└── docs/                # ARCHITECTURE.md, GOOGLE_SETUP.md
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

## Authentication

Only approved staff can use the bot. Google Sheet columns:

```
Telegram ID | Name | Role
```

Example: `123456789 | Abdulrahman | Section Head`

If not listed: `Access denied. Contact Rehabilitation Section Head.`

Fallbacks when Sheets is unavailable: `ALLOWED_TELEGRAM_IDS` env var,
then local `staff_allowlist.json` (see `staff_allowlist.example.json`).

## Quickstart (local)

```bash
cd rehab-rch-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add TELEGRAM_BOT_TOKEN + GEMINI_API_KEY
python bot.py
```

1. **Telegram token:** message [@BotFather](https://t.me/BotFather) → `/newbot` → paste token into `.env`.
2. **Gemini key:** https://aistudio.google.com/app/apikey → paste into `.env`.
3. **Google Drive/Sheets:** follow [docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md) (~20 min).
4. **Knowledge files:** drop approved SOPs into `knowledge/` → `/kb reload`.
5. **Tests:** `pytest -q`.

Without keys, the bot runs in **demo mode** (template drafts + local `output/`
saves) so all Telegram flows are testable for free.

## 24/7 hosting

Best free option: **Oracle Cloud Free Tier**. Full guide: [DEPLOY_ORACLE.md](DEPLOY_ORACLE.md).

```bash
sudo apt update
sudo apt install python3 python3-pip git -y
git clone https://github.com/<yourname>/rehab-rch-agent.git
cd rehab-rch-agent && bash scripts/setup_oracle.sh
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
