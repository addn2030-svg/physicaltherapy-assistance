# Incident Response Plan — Rehab RCH Agent v2

Owner: Rehabilitation Section Head. Review yearly. Keep a printed copy.

## Severity levels
- **P1 — suspected patient-data exposure**: PHI may have reached Gemini/Drive/chat.
- **P2 — credential compromise**: bot token, Gemini key, or `credentials.json` leaked.
- **P3 — outage**: bot down > 1 hour during working hours.

## P1: Suspected patient-data exposure
1. **Contain (minutes)**: ask the sender to delete the message in Telegram if possible;
   revoke the document in Drive (Move to Trash) if one was generated.
2. **Assess**: check `/audit` (admin) for the `phi_blocked` event — note the bot
   blocks most PHI before it reaches Gemini or Drive. Confirm whether a Drive
   file or Gemini call occurred (audit: `report_generated`, `drive_upload`).
3. **Report**: notify hospital IT Security & Compliance per local policy within
   the required window. Provide timestamps (UTC) from the audit log.
4. **Remediate**: retrain the staff member; if a prompt pattern bypassed the
   screen, add keywords/patterns to `safety.py` + regression tests, redeploy.
5. **Follow-up**: record the incident, root cause, and fix in the compliance file.

## P2: Credential compromise
1. **Telegram token**: @BotFather → `/revoke` → update `.env` → `sudo systemctl restart rehab-agent`.
2. **Gemini key**: Google AI Studio → delete key → create new → update `.env` → restart.
3. **Service account**: Google Cloud Console → delete compromised key → download new
   `credentials.json` → copy to server → restart. Re-share Drive folder/Sheet if the
   account itself was replaced.
4. Verify: `/start` works, `/kb` loads, `/audit` shows fresh events.

## P3: Outage
1. `sudo systemctl status rehab-agent` → if failed, `sudo journalctl -u rehab-agent -n 100`.
2. Common causes: expired Gemini quota, revoked token, server reboot without
   `enable`, full disk (`df -h`).
3. `sudo systemctl restart rehab-agent`; if still failing, roll back:
   `git log --oneline -3` → `git checkout <last-good> -- .` → restart.
4. Notify staff of expected recovery time via existing channels.

## Contacts
| Role | Contact |
|---|---|
| Rehabilitation Section Head | Abdulrahman Bakor Howsawy |
| Deputy / on-call supervisor | _fill in_ |
| Hospital IT Security | _fill in_ |
| Compliance officer | _fill in_ |

## Backups
- Knowledge files: master copies live in Drive `Knowledge Base` + this GitHub repo.
- Generated reports: Drive dated folders (primary) + server `output/` (secondary).
- Audit trail: server `output/audit/*.jsonl` (primary) + Sheet `AuditLog` tab (mirror).
- Quarterly: Section Head exports the `AuditLog` tab and stores it per records policy.
