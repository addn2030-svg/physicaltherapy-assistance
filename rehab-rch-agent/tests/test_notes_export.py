"""Agent v4.3 tests — notes archive (Markdown + Drive)."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import notes_export  # noqa: E402
from config import settings  # noqa: E402


def test_slug():
    assert notes_export.slug("Weekly Supervisors Huddle!") == "weekly-supervisors-huddle"
    assert notes_export.slug("!!!") == "note"


def test_tg_to_md():
    assert notes_export.tg_to_md("*bold* and _italic_") == "**bold** and *italic*"


def test_render_memo_note():
    md = notes_export.render_memo_note("MEM-2026-002", "Cover Plan", "Body here",
                                       "U01", "Shahad", "2026-09-13")
    assert md.startswith("---\nid: MEM-2026-002\ntype: memo")
    assert "tags: [rehab, memo]" in md
    assert "# 📝 Cover Plan" in md
    assert "Body here" in md


def test_render_agenda_note():
    md = notes_export.render_agenda_note("MTG-1", "Huddle", "1) Coverage",
                                         "Supervisors", "2026-09-14")
    assert "type: agenda" in md and "## Agenda" in md and "## Minutes" in md


def test_render_eval_and_weekly_notes():
    md = notes_export.render_eval_note("2026-08", "U01", "*Digest* _x_")
    assert "type: evaluation" in md and "**Digest**" in md
    md = notes_export.render_weekly_note("2026-09-06..2026-09-12", "*Week*")
    assert "type: weekly" in md and "**Week**" in md


def test_save_note_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path)
    monkeypatch.setattr(settings, "notes_vault_path", "")
    path = notes_export.save_note("memos", "2026-09-13 MEM-1 test.md", "# hi")
    assert path is not None and path.read_text() == "# hi"
    assert path.parent == tmp_path / "notes" / "memos"


def test_vault_dir_override(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "notes_vault_path", str(tmp_path / "vault"))
    assert notes_export.vault_dir() == tmp_path / "vault"


def test_dated_drive_folder():
    assert notes_export.dated_drive_folder("memos", date(2026, 9, 13)) == \
        "Notes/Memos/2026/September"


def test_archive_note_demo_stays_local(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path)
    monkeypatch.setattr(settings, "notes_vault_path", "")
    monkeypatch.setattr(settings, "notes_drive_upload", True)

    class DemoDrive:  # hermetic: pass with or without real credentials.json
        def upload_file(self, *a, **k):
            return {"demo": True, "drive_link": ""}

    monkeypatch.setattr("google_drive.DriveClient", DemoDrive)
    res = notes_export.archive_note("memos", "n.md", "# n")
    assert res["local"] and Path(res["local"]).exists()
    assert res["demo"] is True and res["drive_link"] == ""


def test_archive_note_upload_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "output_dir", tmp_path)
    monkeypatch.setattr(settings, "notes_vault_path", "")
    monkeypatch.setattr(settings, "notes_drive_upload", False)
    res = notes_export.archive_note("memos", "n.md", "# n")
    assert res["local"] and res["demo"] is True
