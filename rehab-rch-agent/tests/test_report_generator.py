"""Report generator tests — verify branded .docx files are created."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

import report_generator as rg


def test_dated_filename():
    name = rg.dated_filename("Weekly Summary", datetime(2026, 9, 13))
    assert name == "Weekly Summary - 13 Sep 2026.docx"


def test_build_weekly_report(tmp_path, monkeypatch):
    monkeypatch.setattr(rg.settings, "output_dir", tmp_path)
    path = rg.build_weekly_report(
        "## Status Overview\n- OPD coverage stable\n\n## Next Actions\n- Confirm leave roster",
        prepared_by="Test",
        when=datetime(2026, 9, 13),
    )
    assert Path(path).exists()
    assert Path(path).suffix == ".docx"
    assert "Weekly Summary - 13 Sep 2026" in str(path)


def test_build_announcement_and_minutes(tmp_path, monkeypatch):
    monkeypatch.setattr(rg.settings, "output_dir", tmp_path)
    a = rg.build_announcement("Dear Team, meeting Tuesday 09:00.", subject="Staff Meeting")
    m = rg.build_meeting_minutes("- Discussed coverage\n- Approved roster", title="Huddle")
    assert Path(a).exists() and Path(m).exists()
