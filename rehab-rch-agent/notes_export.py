"""Agent v4.3 notes archive — Obsidian-friendly Markdown + Google Drive.

Every memo, agenda, evaluation digest, and weekly summary is saved as a
Markdown note with YAML frontmatter (tags, id, date) so it works as a
native Obsidian vault AND as a Google Drive archive::

    output/notes/            (or NOTES_VAULT_PATH — open this in Obsidian)
    ├── memos/               → Drive: Notes/Memos/YYYY/Month
    ├── agendas/             → Drive: Notes/Agendas/YYYY/Month
    ├── evaluations/         → Drive: Notes/Evaluations/YYYY/Month
    └── weekly/              → Drive: Notes/Weekly/YYYY/Month

All functions are fail-soft: archiving never breaks bot flows (log +
audit, never raise). Without credentials.json, notes stay local-only.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from config import settings

log = logging.getLogger("notes")

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# local subdir → Drive folder key
DRIVE_FOLDERS = {
    "memos": "Notes/Memos",
    "agendas": "Notes/Agendas",
    "evaluations": "Notes/Evaluations",
    "weekly": "Notes/Weekly",
}


def vault_dir() -> Path:
    """Local vault root (open this folder in Obsidian as a vault)."""
    if settings.notes_vault_path.strip():
        return Path(settings.notes_vault_path).expanduser()
    return settings.output_dir / "notes"


def slug(text: str, limit: int = 50) -> str:
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[\s_-]+", "-", clean).strip("-")
    return clean[:limit] or "note"


def tg_to_md(text: str) -> str:
    """Convert Telegram-flavoured markup (*bold*, _italic_) to Markdown."""
    out = re.sub(r"\*(.+?)\*", r"**\1**", text)
    out = re.sub(r"_(.+?)_", r"*\1*", out)
    return out


def frontmatter(note_id: str, kind: str, day: str,
                tags: list[str], extra: dict[str, str] | None = None) -> str:
    lines = ["---", f"id: {note_id}", f"type: {kind}", f"date: {day}",
             f"tags: [{', '.join(tags)}]"]
    for k, v in (extra or {}).items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def render_memo_note(memo_id: str, title: str, body: str, audience: str,
                     author: str, day: str) -> str:
    head = frontmatter(memo_id, "memo", day, ["rehab", "memo"],
                       {"audience": audience, "author": author})
    return (f"{head}\n\n# 📝 {title}\n\n"
            f"**To:** {audience} · **From:** {author} · **Date:** {day}\n\n"
            f"{body.strip()}\n")


def render_agenda_note(meeting_id: str, title: str, items: str,
                       attendees: str, day: str) -> str:
    head = frontmatter(meeting_id, "agenda", day, ["rehab", "agenda"],
                       {"attendees": attendees})
    return (f"{head}\n\n# 📅 {title} ({day})\n\n"
            f"**Attendees:** {attendees}\n\n## Agenda\n\n{items.strip()}\n\n"
            f"## Minutes\n\n_Paste minutes here or see Meeting Minutes in Drive._\n")


def render_eval_note(label: str, scope: str, digest_tg: str) -> str:
    head = frontmatter(f"eval-{label}-{slug(scope, 20)}", "evaluation",
                       label, ["rehab", "evaluation"], {"scope": scope})
    return f"{head}\n\n{tg_to_md(digest_tg).strip()}\n"


def render_weekly_note(week_tag: str, body_tg: str) -> str:
    head = frontmatter(f"weekly-{week_tag}", "weekly", week_tag,
                       ["rehab", "weekly"])
    return f"{head}\n\n{tg_to_md(body_tg).strip()}\n"


def save_note(subdir: str, filename: str, content: str) -> Path | None:
    """Write a note to the local vault. Returns path or None on failure."""
    try:
        folder = vault_dir() / subdir
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        path.write_text(content, encoding="utf-8")
        return path
    except Exception as exc:
        log.warning("Note save failed (%s).", exc)
        return None


def dated_drive_folder(subdir: str, when: date | None = None) -> str:
    when = when or date.today()
    base = DRIVE_FOLDERS.get(subdir, f"Notes/{subdir}")
    return f"{base}/{when.year}/{MONTH_NAMES[when.month - 1]}"


def archive_note(subdir: str, filename: str, content: str,
                 when: date | None = None) -> dict:
    """Save to vault + upload to Drive. Never raises.

    Returns {local: path|None, drive_link: str, demo: bool}.
    """
    from audit import audit  # lazy: avoid import cycles

    result: dict = {"local": None, "drive_link": "", "demo": True}
    path = save_note(subdir, filename, content)
    result["local"] = str(path) if path else None
    if path is None or not settings.notes_drive_upload:
        return result
    try:
        from google_drive import DriveClient  # lazy: heavy google imports

        res = DriveClient().upload_file(
            path, folder_key=dated_drive_folder(subdir, when),
            dated_subfolders=False)
        result["demo"] = bool(res.get("demo", True))
        result["drive_link"] = res.get("drive_link", "")
        audit.log("note_archived", "", "system",
                  f"{subdir}/{filename} drive={not result['demo']}")
    except Exception as exc:
        log.warning("Note Drive upload skipped (%s).", exc)
    return result
