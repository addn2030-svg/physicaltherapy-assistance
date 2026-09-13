# Rehab RCH Agent v2 — Architecture

## Flow

```
Staff
 ↓
Telegram (Bot API, long polling)
 ↓
Rehab RCH Agent (bot.py)
 ├── auth.py          — Google Sheets allowlist (Telegram ID | Name | Role)
 ├── safety.py        — PHI screen on EVERY message (blocks patient data)
 ├── knowledge_base.py— approved SOPs/guidelines/contacts search
 ├── gemini_client.py — Gemini AI drafts & answers (operational only)
 ├── report_generator.py — branded .docx (weekly/monthly/minutes/announcements)
 └── google_drive.py  — auto-save to Drive folder tree
 ↓
Gemini AI API (google-generativeai)
 ↓
Google Drive (service account)
```

## Module responsibilities

| File | Responsibility | Key API |
|---|---|---|
| `bot.py` | Telegram commands + guided conversations | python-telegram-bot v21 |
| `auth.py` | Staff allowlist via Google Sheets, env/JSON fallback | gspread |
| `safety.py` | PHI keyword + pattern screen, refusal message | — |
| `gemini_client.py` | System-prompted generation, demo fallback | google-generativeai |
| `knowledge_base.py` | Local .pdf/.docx/.xlsx/.csv/.md index + keyword search | pypdf, python-docx, openpyxl |
| `report_generator.py` | Branded .docx builder | python-docx |
| `google_drive.py` | Folder tree + dated upload, demo fallback | google-api-python-client |
| `config.py` | Typed env settings | python-dotenv |
| `audit.py` | Append-only audit trail (JSONL + Sheet mirror) | gspread |
| `scripts/retention_cleanup.py` | Local retention cleanup (audit logs exempt) | — |

## Phase 2 safety rails

- **Audit**: `auth_granted/denied`, `phi_blocked` (no content stored),
  `sop_asked`/`question_asked` with coverage, `needs_review` for
  out-of-scope questions, `report_generated`/`announcement_saved`/
  `meeting_saved`/`drive_upload`, `kb_reload`. Admins review via `/audit`.
- **Anti-hallucination**: answers cite `[Source: file]`; out-of-scope
  answers are prefixed `General guidance (not from approved documents):`
  and flagged for human review; every reply shows a knowledge-coverage
  level (High/Medium/Low/None).
- **KB governance**: `manifest.json` gates indexing to `Active` versions;
  citations carry `Document vVersion (approved: By, Date)`.
- **Access review**: Sheet/JSON `Status` + `Valid Until` columns deny
  suspended/expired staff without deleting rows.

## Data safety

1. `safety.contains_phi()` runs before Gemini, KB context injection, and Drive save.
2. Blocked requests return a refusal + resubmit guidance; nothing is stored.
3. Knowledge base accepts operational docs only; README + samples warn against PHI.
4. `.env`, `credentials.json`, `staff_allowlist.json` are git-ignored.

## Drive layout

```
Rehab RCH Agent/
├── Reports/
│   ├── Weekly/2026/September/Weekly Summary - 13 Sep 2026.docx
│   ├── Monthly/...
│   └── Annual/...
├── Announcements/
├── SOP/
├── Meeting Minutes/
└── Knowledge Base/
```

## Scaling notes

- Polling is fine for department scale (tens of staff). For heavier use, switch
  `run_polling()` to webhooks behind HTTPS.
- Keyword search keeps cost at $0. If the KB grows past ~200 docs, add
  embeddings (Gemini text-embedding) + a vector store.
- All Gemini calls are stateless; conversation memory lives in Telegram
  `context.user_data` per flow.
