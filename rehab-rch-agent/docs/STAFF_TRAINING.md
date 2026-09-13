# Staff Training — Rehab RCH Agent v2 (15-minute onboarding)

## 1. What the bot is (2 min)
Official AI assistant of the Rehabilitation Department — RCH. It helps with
**operational, non-patient** work: SOP questions, announcements, meeting
minutes, and reports auto-saved to Google Drive. Available 24/7 in Telegram.

## 2. The one rule: NO patient information (3 min)
⛔ NEVER send: patient names, MRNs/file numbers, diagnoses, medical records,
treatment details, phone numbers, national IDs, bed numbers.

The bot screens every message and will refuse. Refusals are logged (without
your message content) for compliance.

✅ Instead, always de-identify. Say:
- `What is the process for equipment request?`
- `Show rehabilitation escalation path.`
- `Draft announcement about annual leave coverage.`

## 3. Commands hands-on (7 min)
| Try this | Expected |
|---|---|
| `/start` | Welcome with your name (or Access denied → contact Section Head) |
| `/sop What is the process for equipment request?` | Step-by-step answer + source files + coverage level |
| `/announcement` → `Staff meeting Tuesday at 09:00` | Draft memo; reply `yes` to save to Drive |
| `/meeting` → title → paste notes | Formal minutes + Drive save |
| `/report` → `weekly` → paste bullets | Weekly summary + Drive save + .docx in chat |
| `/save` | Re-saves your last document to Drive |
| `/kb` | Which approved documents the bot knows |
| `/cancel` | Stop any flow |

## 4. Trusting answers (3 min)
- Every answer shows **Knowledge coverage: High / Medium / Low / None**.
- **High**: backed by approved documents (sources listed) — still review before acting.
- **Medium/Low**: partially covered — verify with your supervisor.
- **None / "General guidance (not from approved documents)"**: NOT department policy — requires Section Head review.
- Every output is a **draft for review**, never a final decision.

## 5. Access & housekeeping
- Access is per-staff (Telegram ID allowlist). Never share your Telegram account.
- Leaving the department? Tell the Section Head so access is suspended the same day.
- Bot not responding? Wait 2 minutes, try `/start`; if still down, contact the Section Head (see Incident Response plan).
- Found a wrong answer? Screenshot it and send to the Section Head — it improves the knowledge base.
