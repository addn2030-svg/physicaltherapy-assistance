# Security Policy — Staff Only, No Exceptions

This bot serves **Rehabilitation Department staff only**. Every layer below
is enforced in code, not just documented.

## 1. Private chats only (group-proof)

- The bot **refuses to operate in groups, supergroups, and channels**:
  group messages get no data and no hints (silent deny + audit),
  and the bot **auto-leaves** any group it is added to.
- Harden at the platform level too (do once):
  1. Message [@BotFather](https://t.me/BotFather) → `/setjoingroups` →
     select your bot → **Disable** (bot can no longer be added to groups).
  2. `/setprivacy` → **Enable** (default; bot ignores non-command chatter).
- Never forward bot messages containing unit data to non-staff chats.

## 2. Enrollment is code-gated + admin-approved

1. Section Head sets `ENROLL_CODE` in `.env` (e.g. `RCH-2026-X7`) and shares
   it with supervisors only — rotate it when supervisors change.
2. Staff send `/register <code>` → name + unit → row in `Telegram_Users`
   with `Active=FALSE` (pending, **zero access**).
3. Admins get a nudge → `/approve` lists pending → `/approve <name>` →
   user receives ✅ and can use the bot.
4. No code configured = registration **closed** (fail-closed by design).

## 3. Access sources (checked in order, first hit wins)

1. Staff access Sheet (`Telegram ID | Name | Role | Status | Valid Until`)
2. Ops workbook `Telegram_Users` tab (`Active=TRUE` + matching Chat ID)
3. `ALLOWED_TELEGRAM_IDS` in `.env`
4. `staff_allowlist.json`

`Status ≠ Active` or expired `Valid Until` = denied. The allowlist
**reloads every hour** automatically, so suspensions/offboarding take
effect within 60 minutes without a restart.

## 4. Offboarding checklist (same day the staff leaves)

- [ ] Set `Status=Suspended` in the Staff Sheet **and/or** `Active=FALSE`
      in `Telegram_Users` (whichever source granted them access)
- [ ] Remove their ID from `ALLOWED_TELEGRAM_IDS` if listed there
- [ ] Confirm: `/audit` shows no new `auth_granted` for them
- [ ] If they knew the `ENROLL_CODE`, rotate it

## 5. Secrets handling

- Tokens live **only** in `.env` on the server (`chmod 600 .env` — the bot
  warns at startup if it is world-readable). Never in chat, email, Sheets,
  Drive docs, or GitHub (`.env`, `credentials.json`, `staff_allowlist.json`
  are git-ignored; keep the repo **private**).
- Compromised token? Revoke in minutes (see `INCIDENT_RESPONSE.md` P2):
  BotFather `/revoke`, AI Studio delete key, Cloud Console delete key.

## 6. What is logged (and what is never stored)

- Logged: grants, denials, group blocks, PHI blocks (**reason labels only,
  never message content**), questions (first 120 chars), reports generated,
  alerts routed, approvals, leave requests/approvals (IDs + names only),
  incident logs (**metadata only — ID, unit, type, severity**),
  hourly access refreshes.
- Incident rule: `Incident_Reports.Description` is **never** read by the bot
  and never enters Telegram, logs, or alerts — supervisors complete it in
  the Sheet. `/incidents` and watchdog pages show metadata only.
- Stored in: `output/audit/*.jsonl` + Sheet `AuditLog` tab +
  ops `Agent_Audit_Log` tab. Review monthly (`/audit`).

## 7. Residual risks (accepted, documented)

- A staffer can screenshot bot replies — mitigated by policy + training,
  not technology. Sensitive rollups stay high-level (counts, no names).
- Telegram account takeover = bot access as that staffer — staff must
  enable Telegram 2-Step Verification (Settings → Privacy → 2-Step).
- Conversation memory lives in RAM only; server access = active
  conversations visible — restrict server SSH to the Section Head.
