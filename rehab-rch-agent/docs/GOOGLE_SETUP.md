# Google Cloud Setup — Drive + Sheets (Service Account)

Estimated time: ~20 minutes. Cost: $0.

## 1. Create a Google Cloud project
1. Go to https://console.cloud.google.com → New Project → e.g. `rehab-rch-agent`.
2. Select the project.

## 2. Enable APIs
APIs & Services → Library → enable:
- **Google Drive API**
- **Google Sheets API**

## 3. Create a Service Account
1. IAM & Admin → Service Accounts → Create Service Account.
2. Name: `rehab-rch-agent` → Create → Done (no role needed).
3. Open the account → Keys → Add Key → JSON → Download.
4. Save as `credentials.json` in the project root (next to `bot.py`).
   ⛔ Never commit this file — it is git-ignored.

Note the service-account email, like:
`rehab-rch-agent@rehab-rch-agent-123456.iam.gserviceaccount.com`

## 4. Drive folder
Option A (recommended): let the bot create it.
1. The bot creates `Rehab RCH Agent/` + subfolders on first run.
2. To SEE the folder from your own Google account, share it the other way:
   after first run, the service account owns the folder — open it via a link
   from the bot log, or pre-create the folder yourself (Option B).

Option B: pre-create and share.
1. In YOUR Google Drive, create folder `Rehab RCH Agent`.
2. Right-click → Share → add the service-account email as **Editor**.
3. (Optional) copy the folder ID from its URL into `.env` as `DRIVE_ROOT_FOLDER_ID`.

Now the bot can: ✅ create folders ✅ upload reports ✅ update sheets ✅ archive docs.

## 5. Staff access Sheet
1. Create a Google Sheet, e.g. `Rehab RCH Staff Access`.
2. First tab named `Staff` with header row:
   `Telegram ID | Name | Role`
3. Add rows, e.g. `123456789 | Abdulrahman | Section Head`.
   (Staff find their Telegram ID via @userinfobot.)
4. Share the Sheet with the service-account email as **Viewer**.
5. Copy the Spreadsheet ID from the URL (`.../d/<ID>/edit`) into `.env` as `STAFF_SHEET_ID`.

## 6. Verify
```bash
cp .env.example .env   # fill in values
pip install -r requirements.txt
python bot.py
```
In Telegram: `/start` → welcome; unauthorized users get `Access denied.`
Run `/kb` to confirm knowledge files, `/report` for an end-to-end Drive test.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `credentials.json not found` | File must sit next to `bot.py`; check `GOOGLE_CREDENTIALS_FILE`. |
| Drive 404 / access denied | Folder not shared with service-account email as Editor. |
| Sheets: `Unable to parse range` | Tab must be named exactly as `STAFF_SHEET_TAB` (default `Staff`). |
| Empty staff list | Header must be `Telegram ID / Name / Role`; IDs must be numeric. |
