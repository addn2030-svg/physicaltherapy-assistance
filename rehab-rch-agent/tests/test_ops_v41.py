"""Agent v4.1 tests — leave, incidents, capability, policies, RBAC, new alerts."""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import Ctx, GapAgent, WatchdogAgent  # noqa: E402
from messenger import Directory  # noqa: E402
from sheets_ops import OpsDB, demo_ops_db  # noqa: E402

DAY = date(2026, 9, 13)


@pytest.fixture
def db() -> OpsDB:
    return demo_ops_db(DAY)


@pytest.fixture
def ctx(db: OpsDB) -> Ctx:
    return Ctx(db=db, now=datetime(2026, 9, 13, 9, 0), directory=Directory(db))


# -- leave --------------------------------------------------------------------
def test_leave_seed_uncovered(db: OpsDB):
    on_leave = db.on_leave(DAY)
    assert any(r.get("Leave_ID") == "LV-2026-001" for r in on_leave)
    uncovered = db.uncovered_leaves(DAY)
    assert [r["Leave_ID"] for r in uncovered] == ["LV-2026-001"]


def test_add_and_approve_leave(db: OpsDB):
    lid = db.add_leave_request({
        "Staff_Name": "Ahmed Mohammed Bakri", "Leave_Type": "Annual",
        "Start_Date": "2026-09-20", "End_Date": "2026-09-22", "Notes": "x"})
    assert lid == "LV-2026-002"
    assert db.pending_leaves() and \
        db.pending_leaves()[0]["Duration_Days"] == "3"
    assert db.approve_leave(lid, "Abdulmajeed Mohammed AlJuraid", "Khaled Sultan Al-Otaibi")
    row = next(r for r in db.b.read_tab("Leave_Tracker")
               if r.get("Leave_ID") == lid)
    assert row["Status"] == "Approved"
    assert row["Coverage_Staff"] == "Khaled Sultan Al-Otaibi"
    assert row["Coverage_Arranged"] == "Yes"
    assert not db.pending_leaves()


def test_approve_unknown_leave_returns_false(db: OpsDB):
    assert db.approve_leave("LV-2026-999", "Abdulrahman Hawsawi") is False


def test_leave_multi_day_span(db: OpsDB):
    db.add_leave_request({
        "Staff_Name": "Ahmed Mohammed Bakri", "Leave_Type": "Sick",
        "Start_Date": "2026-09-14", "End_Date": "2026-09-15",
        "Status": "Approved"})
    assert any(r["Staff_Name"] == "Ahmed Mohammed Bakri"
               for r in db.on_leave(date(2026, 9, 15)))
    assert not any(r["Staff_Name"] == "Ahmed Mohammed Bakri"
                   for r in db.on_leave(date(2026, 9, 16)))
    # pending requests never count as on-leave
    db.add_leave_request({
        "Staff_Name": "Khaled Sultan Al-Otaibi", "Leave_Type": "Annual",
        "Start_Date": "2026-09-13", "End_Date": "2026-09-13"})
    assert not any(r["Staff_Name"] == "Khaled Sultan Al-Otaibi"
                   for r in db.on_leave(DAY))


def test_on_leave_excluded_from_missing_reports(db: OpsDB):
    missing = db.missing_staff_reports(DAY)
    on_leave = {r["Staff_Name"].lower() for r in db.on_leave(DAY)}
    assert on_leave  # seed guarantees at least one
    for name in on_leave:
        assert not any(name in m.lower() for m in missing)


# -- incidents (metadata only) --------------------------------------------------
def test_incident_add_and_metadata_only(db: OpsDB):
    iid = db.add_incident({
        "Unit": "U01", "Incident_Type": "Fall", "Severity": "Serious",
        "Description": "PATIENT-DESCRIPTION-MUST-NEVER-SURFACE",
        "Reported_By": "Ahmed Mohammed Bakri"})
    assert iid == "INC-2026-001"
    assert len(db.serious_incidents()) == 1
    public = OpsDB.incident_public(db.open_incidents()[0])
    assert "Description" not in public
    assert "PATIENT-DESCRIPTION" not in str(public.values())


def test_watchdog_serious_incident_alert(db: OpsDB, ctx: Ctx):
    db.add_incident({
        "Unit": "U02", "Incident_Type": "Equipment", "Severity": "Critical",
        "Description": "SECRET-DETAIL", "Reported_By": "Shahad Abdullah Albalawi"})
    alerts = [a for a in WatchdogAgent().run(ctx) if a.key.startswith("watch:inc:")]
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"
    assert "SECRET-DETAIL" not in alerts[0].body
    assert "Incident_Reports tab" in alerts[0].body


def test_minor_incident_no_watchdog_alert(db: OpsDB, ctx: Ctx):
    db.add_incident({"Unit": "U01", "Incident_Type": "Near-miss",
                     "Severity": "Minor", "Reported_By": "Ahmed Mohammed Bakri"})
    assert not [a for a in WatchdogAgent().run(ctx)
                if a.key.startswith("watch:inc:")]


# -- licenses & competency --------------------------------------------------------
def test_license_alerts(db: OpsDB, ctx: Ctx):
    db.b.update_rows("Staff_Register", "Name", "Ahmed Mohammed Bakri",
                     {"License_Expiry": "2026-09-20"})
    db.b.update_rows("Staff_Register", "Name", "Khaled Sultan Al-Otaibi",
                     {"License_Expiry": "2026-08-01"})
    keys = {a.key.split(":")[1]: a for a in GapAgent().run(ctx)
            if a.key.startswith("gap:lic")}
    assert keys["lic"].severity == "info"
    assert "Ahmed Mohammed Bakri" in keys["lic"].body
    assert keys["licexp"].severity == "warning"
    assert "Khaled Sultan Al-Otaibi" in keys["licexp"].body


def test_competency_expiring_alert(db: OpsDB, ctx: Ctx):
    db.b.update_rows("Capability_Matrix", "Staff_Name", "Reem Abdulrazeq",
                     {"Expiry_Date": "2026-09-25"})
    comp = [a for a in GapAgent().run(ctx) if a.key.startswith("gap:comp:")]
    assert len(comp) == 1
    assert "Reem Abdulrazeq" in comp[0].body


def test_capability_seed(db: OpsDB):
    rows = db.capabilities_for("Abdulmajeed Mohammed AlJuraid")
    assert len(rows) == 1
    assert rows[0]["Verification_Status"] == "Pending_Verification"
    assert rows[0]["Competency_Level"] == "P3"
    assert db.capabilities_for("Nobody Nobody") == []


# -- readiness / understaffing / cover / policy alerts ---------------------------
def test_uncovered_leave_alert(db: OpsDB, ctx: Ctx):
    alerts = [a for a in GapAgent().run(ctx) if a.key.startswith("gap:cover:")]
    assert len(alerts) == 1
    assert alerts[0].severity == "warning"
    assert "Nouf Mohammed Abduldaim" in alerts[0].title


def test_not_ready_and_understaffed_alerts(db: OpsDB, ctx: Ctx):
    db.b.update_rows("Units", "Unit_ID", "U01", {"Min_Staff_Required": "8"})
    db.b.update_rows("Daily_Supervisor_Reports", "Unit", "U01",
                     {"Readiness": "Not Ready"})
    alerts = GapAgent().run(ctx)
    nr = [a for a in alerts if a.key.startswith("gap:notready:")]
    assert len(nr) == 1 and nr[0].severity == "warning"
    under = [a for a in alerts if a.key.startswith("gap:understaff:")]
    assert len(under) == 1  # 6 present < 8 minimum
    assert "6/8" in under[0].title


def test_policies_overdue_alert(db: OpsDB, ctx: Ctx):
    overdue = db.policies_overdue(DAY)
    assert [r["Policy_ID"] for r in overdue] == ["POL-001"]
    alerts = [a for a in GapAgent().run(ctx) if a.key.startswith("gap:policy:")]
    assert len(alerts) == 1
    assert "POL-001" in alerts[0].body


# -- RBAC -----------------------------------------------------------------------
def test_rbac(db: OpsDB):
    assert db.is_head("Abdulrahman Hawsawi")
    assert not db.is_head("Shahad Abdullah Albalawi")
    assert db.supervises("Shahad Abdullah Albalawi", "U02")
    assert not db.supervises("Shahad Abdullah Albalawi", "U01")
    assert db.can_manage("Abdulrahman Hawsawi", "U03")  # head: everywhere
    assert db.can_manage("Shahad Abdullah Albalawi", "U02")
    assert not db.can_manage("Shahad Abdullah Albalawi", "U01")
    assert not db.can_manage("Ahmed Mohammed Bakri", "U01")
    assert not db.can_manage("Ahmed Mohammed Bakri", "NOPE")


# -- status defaults & dictionary --------------------------------------------------
def test_status_defaults_active(db: OpsDB):
    assert db.staff_status("Ahmed Mohammed Bakri") == "Active"
    assert db.staff_status("Ghost Person") == "Unknown"
    assert len(db.active_staff()) == len(db.staff())  # no statuses in seed


def test_dictionary_has_20_entries(db: OpsDB):
    rows = db.b.read_tab("Data_Dictionary")
    assert len(rows) == 20
