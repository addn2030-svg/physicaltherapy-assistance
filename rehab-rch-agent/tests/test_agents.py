"""Orchestra tests — gaps, escalation, dedup, quiet hours, auto-reports."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import InsightAgent, Orchestrator, in_quiet_hours  # noqa: E402
from audit import audit  # noqa: E402
from config import settings  # noqa: E402
from scheduler import due_jobs, mark_ran  # noqa: E402
from sheets_ops import demo_ops_db  # noqa: E402

DAY = datetime(2026, 9, 13)  # a Sunday


@pytest.fixture
def hermetic(tmp_path, monkeypatch):
    """Redirect all file output (reports, state, audit) to tmp."""
    monkeypatch.setattr(settings, "output_dir", tmp_path)
    monkeypatch.setattr(audit, "dir", tmp_path / "audit")
    (tmp_path / "audit").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def sched_defaults(monkeypatch):
    """Pin timetable settings regardless of local .env."""
    monkeypatch.setattr(settings, "briefing_time", "07:30")
    monkeypatch.setattr(settings, "rollup_time", "17:00")
    monkeypatch.setattr(settings, "gap_scan_times", ["09:00", "12:00", "15:00"])
    monkeypatch.setattr(settings, "report_cutoff", "15:00")
    monkeypatch.setattr(settings, "watchdog_minutes", 30)
    monkeypatch.setattr(settings, "weekly_day", "SUN")
    monkeypatch.setattr(settings, "weekly_time", "08:00")
    monkeypatch.setattr(settings, "quiet_hours", "22:00-06:30")


def _db_with_chats():
    db = demo_ops_db(DAY.date())
    db.upsert_telegram_user("Abdulrahman Hawsawi", "U08", "@head", "111", "TRUE")
    db.upsert_telegram_user("Abdulmajeed Mohammed AlJuraid", "U01", "@ptm", "112", "TRUE")
    db.upsert_telegram_user("Shahad Abdullah Albalawi", "U02", "@ptf", "113", "TRUE")
    db.upsert_telegram_user("Sumaya Abdullah Al Batook", "U03", "@inp", "114", "TRUE")
    db.upsert_telegram_user("Ahmed Mohammed Bakri", "U01", "@ahmed", "121", "TRUE")
    return db


def _orch(db, tmp_path):
    return Orchestrator(db, state_path=tmp_path / "state.json")


def test_gap_scan_routes_missing_reports(hermetic, sched_defaults):
    outbox = _orch(_db_with_chats(), hermetic).tick(
        DAY.replace(hour=9), ["gaps"])
    keys = [m.key for m in outbox]
    assert any(k.startswith("gap:sup:2026-09-13:U02") for k in keys)
    assert any(k.startswith("gap:staff:2026-09-13:U01") for k in keys)
    # U01 supervisor alert must reach supervisor chat 112.
    u01 = [m for m in outbox if m.key == "gap:staff:2026-09-13:U01"]
    assert u01 and u01[0].chat_id == "112"


def test_dedup_second_tick_is_silent(hermetic, sched_defaults):
    orch = _orch(_db_with_chats(), hermetic)
    first = orch.tick(DAY.replace(hour=9), ["gaps"])
    assert first
    second = Orchestrator(orch.db, state_path=hermetic / "state.json").tick(
        DAY.replace(hour=9, minute=5), ["gaps"])
    assert second == []


def test_cutoff_nudges_therapists_directly(hermetic, sched_defaults):
    outbox = _orch(_db_with_chats(), hermetic).tick(
        DAY.replace(hour=16), ["gaps"])
    nudges = [m for m in outbox if m.key.startswith("esc:nudge:")]
    assert nudges
    ahmed = [m for m in nudges if m.key.endswith("Ahmed Mohammed Bakri")]
    assert ahmed and ahmed[0].chat_id == "121"  # direct to therapist


def test_unknown_chat_escalates_upward(hermetic, sched_defaults):
    outbox = _orch(_db_with_chats(), hermetic).tick(
        DAY.replace(hour=16), ["gaps"])
    # Sayfaleslam has no chat → his nudge escalates with a note.
    sayfa = [m for m in outbox if m.key.endswith("Sayfaleslam Salem Alenzi")]
    assert sayfa
    assert sayfa[0].chat_id in {"112", "111"}  # U01 sup or head
    assert "no Chat ID on file" in sayfa[0].text


def test_quiet_hours_hold_non_critical(hermetic, sched_defaults):
    assert in_quiet_hours(DAY.replace(hour=23))
    assert not in_quiet_hours(DAY.replace(hour=10))
    outbox = _orch(_db_with_chats(), hermetic).tick(
        DAY.replace(hour=23), ["gaps"])
    assert outbox == []


def test_critical_pierces_quiet_hours(hermetic, sched_defaults):
    db = _db_with_chats()
    db.add_equipment_issue({"Unit": "U03", "Equipment": "Ventilator port",
                            "Issue": "Total failure", "Severity": "Critical",
                            "Reported_By": "Test"})
    outbox = _orch(db, hermetic).tick(DAY.replace(hour=23), ["watchdog"])
    assert len(outbox) == 2  # supervisor + head
    assert all(m.meta["severity"] == "critical" for m in outbox)


def test_briefing_reaches_head_and_supervisors(hermetic, sched_defaults):
    outbox = _orch(_db_with_chats(), hermetic).tick(
        DAY.replace(hour=7, minute=30), ["briefing"])
    chats = {m.chat_id for m in outbox}
    assert {"111", "112", "113", "114"} <= chats


def test_rollup_appends_briefing_rows(hermetic, sched_defaults):
    db = _db_with_chats()
    before = len(db.b.read_tab("Supervisor_Briefings"))
    outbox = _orch(db, hermetic).tick(DAY.replace(hour=17), ["rollup"])
    assert len(db.b.read_tab("Supervisor_Briefings")) == before + 2  # U01 + U03
    assert any(m.level == "head" for m in outbox)


def test_weekly_autofill_seven_units(hermetic, sched_defaults, monkeypatch):
    monkeypatch.setattr(settings, "higher_admin_chat_ids", ["999"])
    db = _db_with_chats()
    outbox = _orch(db, hermetic).tick(DAY.replace(hour=8), ["weekly"])
    rows = db.b.read_tab("Weekly_Summary")
    assert len(rows) == 1 + 7  # seed row + U01..U07
    assert any(m.level == "admin" for m in outbox)


def test_due_jobs_timetable(sched_defaults):
    assert "briefing" in due_jobs(DAY.replace(hour=7, minute=31), {})
    assert "briefing" not in due_jobs(DAY.replace(hour=7, minute=29), {})
    assert "gaps" in due_jobs(DAY.replace(hour=9, minute=1), {})
    last: dict = {}
    mark_ran(last, due_jobs(DAY.replace(hour=7, minute=31), last),
             DAY.replace(hour=7, minute=31))
    assert "briefing" not in due_jobs(DAY.replace(hour=7, minute=32), last)
    assert "weekly" in due_jobs(DAY.replace(hour=8, minute=1), {})  # Sunday


def test_insight_demo_returns_empty(monkeypatch):
    import gemini_client

    monkeypatch.setattr(gemini_client.gemini, "_model", None)  # force demo
    assert InsightAgent().run(None, "stats") == ""  # type: ignore[arg-type]


def test_update_rows_backend():
    db = _db_with_chats()
    assert db.set_user_active("Ahmed Mohammed Bakri", False)
    assert db.chat_id_for("Ahmed Mohammed Bakri") == ""  # inactive → no chat
    assert db.set_user_active("Ahmed Mohammed Bakri", True)
    assert db.chat_id_for("Ahmed Mohammed Bakri") == "121"
