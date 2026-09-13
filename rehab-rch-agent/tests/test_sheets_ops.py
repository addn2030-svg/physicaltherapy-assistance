"""Ops workbook tests — seed integrity, queries, appends, briefing text."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sheets_ops import MemoryBackend, OpsDB, SCHEMAS, demo_ops_db


def test_seed_structure_matches_user_workbook():
    db = demo_ops_db(date(2026, 9, 13))
    assert len(db.units()) == 8
    assert len(db.supervisors()) == 4
    assert len(db.staff()) == 18
    assert db.unit_by_id("U01")["Unit_Name"] == "Physiotherapy Male"
    assert db.unit_by_id("U08")["Supervisor"] == "Abdulrahman Hawsawi"


def test_resolve_unit_accepts_forms():
    db = demo_ops_db()
    assert db.resolve_unit("U01")["Unit_ID"] == "U01"
    assert db.resolve_unit("u03")["Unit_ID"] == "U03"
    assert db.resolve_unit("1")["Unit_ID"] == "U01"
    assert db.resolve_unit("inpatient")["Unit_ID"] == "U03"
    assert db.resolve_unit("U99") is None


def test_missing_reports_logic():
    day = date(2026, 9, 13)
    db = demo_ops_db(day)
    # Seed has supervisor reports for U01 + U03 only.
    missing_units = db.missing_supervisor_reports(day)
    assert "U01 Physiotherapy Male" not in missing_units
    assert any(m.startswith("U02") for m in missing_units)
    assert not any(m.startswith("U08") for m in missing_units)  # office excluded
    # Supervisors / secretary / head never expected to file staff reports.
    missing_staff = db.missing_staff_reports(day)
    assert not any("Hawsawi" in m for m in missing_staff)
    assert not any("Hanin" in m for m in missing_staff)
    assert not any("Khaled Sultan Al-Otaibi" in m for m in missing_staff)  # filed
    assert any("Ahmed Mohammed Bakri" in m for m in missing_staff)  # not filed


def test_append_and_readback():
    db = demo_ops_db(date(2026, 9, 13))
    db.add_staff_report({
        "Report_Date": "2026-09-13", "Staff_Name": "Ahmed Mohammed Bakri",
        "Unit": "U01", "Patients_Seen": "7", "New_Cases": "1",
        "Follow_Up_Cases": "6", "Documentation_Status": "Complete",
        "Issues": "", "Follow_Up_Tomorrow": "", "Submitted_Time": "15:00",
    })
    assert not any("Ahmed Mohammed Bakri" in m
                   for m in db.missing_staff_reports("2026-09-13"))


def test_action_and_issue_ids_increment():
    db = demo_ops_db()
    year = date.today().year
    assert db.next_action_id() == f"ACT-{year}-004"
    assert db.next_issue_id() == f"ISS-{year}-003"
    aid = db.add_action({"Title": "Test", "Owner": "X", "Due_Date": "2026-12-01"})
    assert aid == f"ACT-{year}-004"
    assert any(r["Action_ID"] == aid for r in db.open_actions())


def test_overdue_and_expiry_detection():
    db = demo_ops_db(date(2026, 9, 13))
    db.add_action({"Title": "Old", "Owner": "X", "Due_Date": "2020-01-01"})
    assert any(r["Title"] == "Old" for r in db.overdue_actions(date(2026, 9, 13)))
    expiring = db.training_expiring(30)
    assert any("BLS" in r["Course"] for r in expiring)


def test_datahealth_flags_gaps():
    db = demo_ops_db()
    h = db.datahealth()
    assert h["staff_count"] == 18
    assert len(h["missing_roles"]) == 12  # per the user's register
    assert len(h["telegram_active_without_chat_id"]) == 2
    assert h["units_without_supervisor"] == []


def test_ensure_schema_creates_all_tabs():
    mem = MemoryBackend({})
    status = mem.ensure_tabs(SCHEMAS)
    assert len(status) == 22  # 11 core + 8 v3 + 3 v4.1
    assert all(v == "created" for v in status.values())
    status2 = mem.ensure_tabs(SCHEMAS)
    assert all(v == "exists" for v in status2.values())


def test_briefing_text_is_deterministic():
    from ops_handlers import build_briefing_text

    text = build_briefing_text(demo_ops_db(date(2026, 9, 13)), date(2026, 9, 13))
    for section in ("Morning Briefing", "Dashboard", "Unit readiness",
                    "Staff reports missing", "Open actions",
                    "Open equipment issues", "Rehab_Operations_Master_v2"):
        assert section in text
    assert "U01" in text and "ACT-" in text and "ISS-" in text
