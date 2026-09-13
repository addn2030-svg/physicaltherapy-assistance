# Email + Calendar Setup (Agent v4.2)

Both channels are **optional and off by default**. The bot works fully on
Telegram alone; enable either channel when ready — no code changes needed.

## Email (SMTP — any provider)

Used for: memo copies (`/memo`), reminder copies, monthly evaluation
digests. Recipients come from `Staff_Register.Email`.

1. Fill the `Email` column in `Staff_Register` (one address per staffer).
2. In `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.address@gmail.com
   SMTP_PASSWORD=<app-password>
   SMTP_FROM=your.address@gmail.com
   ```
   Gmail needs an **App Password** (Google Account → Security → 2-Step →
   App passwords), not your login password. Hospital SMTP works the same
   way — ask IT for host/port/credentials (port 465 = implicit SSL).
3. Restart the bot. Test: `/memo` to yourself → "📧 Emailed to 1 staff."

Rules: operational content only, never PHI (same rule as Telegram);
every send/failure is audit-logged (`email_sent` / `email_failed`).
SMTP_PASSWORD lives only in server `.env` (`chmod 600 .env`).

## Google Calendar (service account — same credentials as Drive)

Used for: reminder events (`/remind_add`), meeting events (`/agenda_add`).
Event IDs are stored back (`Calendar_Event_ID` columns).

1. Create/open the department calendar in Google Calendar → Settings →
   "Share with specific people" → add the service-account email (the
   `client_email` in `credentials.json`) with **Make changes to events**.
2. Copy the Calendar ID (Settings → Integrate calendar) into `.env`:
   ```
   GOOGLE_CALENDAR_ID=<calendar-id>@group.calendar.google.com
   ```
3. Restart the bot. Test: `/agenda_add` → "📅 Calendar event created."

Without these, the bot replies "not connected" and continues normally —
nothing breaks, nothing is retried silently.

## Notes archive (v4.3: Obsidian vault + Drive)

Every memo, agenda, evaluation digest, and weekly summary is also saved
as a Markdown note with tags + id + date, in two places:

1. **Local vault** — `output/notes/` on the server (or set
   `NOTES_VAULT_PATH=` to any folder). Open that folder in
   [Obsidian](https://obsidian.md/) via "Open folder as vault" to
   browse/search/link everything. Tip: point it at a cloud-synced
   folder (OneDrive/Drive-Desktop/iCloud) to read notes on your phone.
2. **Google Drive** — `Notes/Memos|Agendas|Evaluations|Weekly/YYYY/Month`
   (same service account as reports; set `NOTES_DRIVE_UPLOAD=false`
   to keep notes local-only).

No setup needed — archiving starts on the next memo/agenda/evaluation.
Sheet stays the live database; notes are the readable archive.
