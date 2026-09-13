# Knowledge Base — approved department documents only

Drop approved operational files here (or upload them to the Drive
`Knowledge Base` folder). Supported: `.pdf`, `.docx`, `.xlsx`, `.csv`, `.md`, `.txt`

Recommended:
- `SOP.pdf` — department standard operating procedures
- `Department Guideline.docx` — operational guidelines
- `Rehabilitation Structure.pdf` — org chart, roles, escalation path
- `Contacts.xlsx` — internal contact list

⛔ NEVER upload: patient records, MRNs, diagnostic reports,
clinical notes, or any PHI. The agent refuses PHI-flagged content.

After adding files, run `/kb reload` in Telegram (or restart the bot).
Sample operational files are included below — replace them with your
approved department versions.

## Version control (required for production)

Copy `manifest.example.json` to `manifest.json` and register every file:

Document | Version | Approved By | Date | Status
---------|---------|-------------|------|--------
SOP.pdf | 2.1 | Section Head | 2026-09-01 | Active

Only `Active` documents are indexed; archived/draft files are skipped and
shown in `/kb`. Every answer cites `Document vVersion (approved: By, Date)`.
Without a manifest, files load as "unversioned — pilot only".
