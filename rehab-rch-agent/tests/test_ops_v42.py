"""Agent v4.2 tests — email, calendar, reminders, memos, agendas, evaluation."""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import calendar_ops  # noqa: E402
import mailer  # noqa: E402
import staff_eval  # noqa: E402
from agents import Ctx, EvaluationAgent, ReminderAgent  # noqa: E402
from config import settings  # noqa: E402
from messenger import Directory  # noqa: E402
from scheduler import due_jobs, mark_ran  # noqa: E402
from sheets_ops import OpsDB, demo_ops_db  # noqa: E402

DAY = date(2026, 9, 13)  # a Sunday


@pytest.fixture
def db() -> OpsDB:
    return demo_ops_db(DAY)


@pytest.fixture
def ctx(db: OpsDB) -> Ctx:
    return Ctx(db=db, now=datetime(2026, 9, 13, 8, 30),
               directory=Directory(db))


@pytest.fixture
def mail_defaults(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_from", "rehab@test.local")


# -- mailer ---------------------------------------------------------------------
class FakeSMTP:
    sent: list = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, u, p):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_email_disabled_without_host(mail_defaults):
    assert mailer.email_configured() is False
    assert mailer.send_email("a@x.y", "sub", "body") is False


def test_build_message(mail_defaults):
    msg = mailer.build_message(["a@x.y"], "Hi", "hello")
    assert msg["To"] == "a@x.y"
    assert msg["Subject"] == "[Rehab RCH] Hi"
    assert "hello" in msg.get_content()


def test_send_email_via_smtp_mock(mail_defaults, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("smtplib.SMTP_SSL", FakeSMTP)
    FakeSMTP.sent.clear()
    assert mailer.send_email(["a@x.y", "b@x.y"], "Sub", "Body") is True
    assert len(FakeSMTP.sent) == 1
    assert FakeSMTP.sent[0]["To"] == "a@x.y, b@x.y"


def test_send_email_failure_is_soft(mail_defaults, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")

    class Boom:
        def __init__(self, *a, **k):
            raise ConnectionError("no route")

    monkeypatch.setattr("smtplib.SMTP", Boom)
    assert mailer.send_email("a@x.y", "Sub", "Body") is False


def test_staff_email_audience(db: OpsDB, mail_defaults, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    FakeSMTP.sent.clear()
    assert mailer.send_staff_email(db, "U01", "S", "B") == 0  # no emails yet
    db.b.update_rows("Staff_Register", "Name", "Ahmed Mohammed Bakri",
                     {"Email": "ahmed@test.local"})
    db.b.update_rows("Staff_Register", "Name", "Khaled Sultan Al-Otaibi",
                     {"Email": "khaled@test.local"})
    assert mailer.send_staff_email(db, "U01", "S", "B") == 2
    assert len(FakeSMTP.sent) == 1


# -- calendar ----------------------------------------------------------------------
def test_calendar_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "calendar_enabled", True)
    monkeypatch.setattr(settings, "calendar_id", "")
    assert calendar_ops.calendar_configured() is False
    assert calendar_ops.CalendarClient().demo_mode is True
    assert calendar_ops.create_calendar_event("T", DAY) == ""


def test_build_event_body():
    body = calendar_ops.build_event_body("Huddle", DAY, "desc")
    assert body["summary"] == "[Rehab] Huddle"
    assert body["start"]["date"] == "2026-09-13"
    assert body["description"] == "desc"


def test_create_event_api_mock(monkeypatch):
    client = calendar_ops.CalendarClient()
    calls = {}

    class FakeEvents:
        def insert(self, calendarId, body):
            calls["cal"] = calendarId
            calls["body"] = body
            return self

        def execute(self):
            return {"id": "EVT-1"}

    class FakeSvc:
        def events(self):
            return FakeEvents()

    monkeypatch.setattr(settings, "calendar_id", "cal@test")
    client._service = FakeSvc()
    client.demo_mode = False
    assert client.create_event("T", DAY) == "EVT-1"
    assert calls["cal"] == "cal@test"


# -- audiences ----------------------------------------------------------------------
def test_resolve_audience(db: OpsDB):
    everyone = db.resolve_audience("All")
    assert "Ahmed Mohammed Bakri" in everyone
    assert "Shahad Abdullah Albalawi" in db.resolve_audience("Supervisors")
    assert "Nouf Mohammed Abduldaim" in db.resolve_audience("U02")
    assert db.resolve_audience("Ahmed Mohammed Bakri") == ["Ahmed Mohammed Bakri"]
    assert db.resolve_audience("No Such Thing") == []


def test_emails_for_audience(db: OpsDB):
    assert db.emails_for_audience("All") == []
    db.b.update_rows("Staff_Register", "Name", "Ahmed Mohammed Bakri",
                     {"Email": "ahmed@test.local"})
    assert db.emails_for_audience("Ahmed Mohammed Bakri") == ["ahmed@test.local"]
    assert db.emails_for_audience("U02") == []


# -- reminder cadence ------------------------------------------------------------------
def _add(db: OpsDB, rid: str, **kw):
    row = {"Reminder_ID": rid, "Title": rid, "Audience": "U01",
           "Start_Date": "2026-09-13", "End_Date": "", "Cadence": "Once",
           "Priority": "Normal", "Status": "Active", "Created_By": "t",
           "Last_Sent": ""}
    row.update(kw)
    db.b.append_row("Reminders", row)


def test_due_reminders_cadences(db: OpsDB):
    _add(db, "R-ONCE-DUE")
    _add(db, "R-ONCE-SENT", Last_Sent="2026-09-13")
    _add(db, "R-FUTURE", Start_Date="2026-09-14")
    _add(db, "R-DAILY-DUE", Cadence="Daily", Last_Sent="2026-09-12")
    _add(db, "R-DAILY-DONE", Cadence="Daily", Last_Sent="2026-09-13")
    _add(db, "R-WEEKLY-DUE", Cadence="Weekly", Start_Date="2026-09-06")
    _add(db, "R-WEEKLY-OFF", Cadence="Weekly", Start_Date="2026-09-07")
    _add(db, "R-MONTHLY-DUE", Cadence="Monthly", Start_Date="2026-08-13")
    _add(db, "R-MONTHLY-LATER", Cadence="Monthly", Start_Date="2026-08-20")
    _add(db, "R-ENDED", Cadence="Daily", End_Date="2026-09-12")
    _add(db, "R-OFF", Status="Done")
    due = {r["Reminder_ID"] for r in db.due_reminders(DAY)}
    for rid in ("R-ONCE-DUE", "R-DAILY-DUE", "R-WEEKLY-DUE", "R-MONTHLY-DUE",
                "REM-2026-001"):  # seeded weekly, Sunday anchor
        assert rid in due
    for rid in ("R-ONCE-SENT", "R-FUTURE", "R-DAILY-DONE", "R-WEEKLY-OFF",
                "R-MONTHLY-LATER", "R-ENDED", "R-OFF"):
        assert rid not in due


def test_mark_reminder_sent_done(db: OpsDB):
    assert db.next_reminder_id() == "REM-2026-002"
    rid = db.add_reminder({"Title": "t", "Audience": "All",
                           "Start_Date": "2026-09-13", "Cadence": "Once"})
    assert db.mark_reminder_sent(rid, DAY, done=True) is True
    row = next(r for r in db.reminders() if r["Reminder_ID"] == rid)
    assert row["Status"] == "Done" and row["Last_Sent"] == "2026-09-13"


# -- ReminderAgent -------------------------------------------------------------------
def test_reminder_fanout_marks_sent(db: OpsDB, ctx: Ctx):
    alerts = [a for a in ReminderAgent().run(ctx) if a.key.startswith("rem:REM-")]
    assert len(alerts) == len(db.supervisor_names()) == 4
    row = next(r for r in db.reminders() if r["Reminder_ID"] == "REM-2026-001")
    assert row["Last_Sent"] == "2026-09-13"  # weekly stays Active


def test_high_task_nudges(db: OpsDB, ctx: Ctx):
    alerts = [a for a in ReminderAgent().run(ctx)
              if a.key.startswith("rem:task:")]
    assert len(alerts) == 1  # only the High action, not Medium
    assert alerts[0].staff_name == "Shoug Atallah Alanazi"
    db.b.append_row("Operational_Actions",
                    {"Action_ID": "ACT-X", "Title": "x", "Owner": "Ahmed Mohammed Bakri",
                     "Due_Date": "2026-09-12", "Status": "Open",
                     "Priority": "High"})
    alerts = [a for a in ReminderAgent().run(ctx)
              if a.key.startswith("rem:task:")]
    over = [a for a in alerts if "OVERDUE" in a.title]
    assert len(over) == 1 and over[0].severity == "warning"


def test_weekly_task_digest_only_on_weekly_day(db: OpsDB, ctx: Ctx,
                                               monkeypatch):
    monkeypatch.setattr(settings, "weekly_day", "SUN")
    assert any(a.key.startswith("taskdigest:") for a in ReminderAgent().run(ctx))
    ctx_mon = Ctx(db=db, now=datetime(2026, 9, 14, 8, 30),
                  directory=Directory(db))
    assert not any(a.key.startswith("taskdigest:")
                   for a in ReminderAgent().run(ctx_mon))


def test_agenda_tomorrow_nudge(db: OpsDB, ctx: Ctx):
    assert not [a for a in ReminderAgent().run(ctx)
                if a.key.startswith("agenda:")]  # seed agenda is today
    db.add_agenda({"Title": "g", "Date": "2026-09-14", "Attendees": "U02",
                   "Agenda_Items": "x"})
    alerts = [a for a in ReminderAgent().run(ctx)
              if a.key.startswith("agenda:")]
    assert alerts and all("tomorrow" in a.title.lower() for a in alerts)
    assert "Nouf Mohammed Abduldaim" in {a.staff_name for a in alerts}


# -- memos + agendas --------------------------------------------------------------------
def test_add_memo_and_agenda_ids(db: OpsDB):
    assert db.add_memo({"Title": "m", "Body": "b", "Audience": "All",
                        "Author": "t"}) == "MEM-2026-002"
    assert db.add_agenda({"Title": "g", "Date": "2026-09-20",
                          "Attendees": "All"}) == "MTG-2026-002"
    upcoming = db.upcoming_agendas(DAY, days=14)
    assert [a["Meeting_ID"] for a in upcoming] == ["MTG-2026-001",
                                                   "MTG-2026-002"]
    assert db.upcoming_agendas(DAY, days=0)[0]["Meeting_ID"] == "MTG-2026-001"


# -- evaluation ----------------------------------------------------------------------------
def _august_reports(db: OpsDB):
    """Ahmed: 20 days x10 pts, all Complete, 2 leave days.
    Khaled: 10 days x5 pts, half Complete, no leave."""
    wdays = staff_eval.working_days(2026, 8)
    assert len(wdays) == 22
    for i, d in enumerate(wdays[:20]):
        db.b.append_row("Daily_Staff_Reports",
                        {"Report_Date": d.isoformat(),
                         "Staff_Name": "Ahmed Mohammed Bakri", "Unit": "U01",
                         "Patients_Seen": "10", "New_Cases": "2",
                         "Follow_Up_Cases": "8",
                         "Documentation_Status": "Complete"})
    for i, d in enumerate(wdays[:10]):
        db.b.append_row("Daily_Staff_Reports",
                        {"Report_Date": d.isoformat(),
                         "Staff_Name": "Khaled Sultan Al-Otaibi", "Unit": "U01",
                         "Patients_Seen": "5", "New_Cases": "1",
                         "Follow_Up_Cases": "4",
                         "Documentation_Status": "Complete" if i % 2 == 0
                         else "Incomplete"})
    lid = db.add_leave_request(
        {"Staff_Name": "Ahmed Mohammed Bakri", "Leave_Type": "Annual",
         "Start_Date": wdays[20].isoformat(), "End_Date": wdays[21].isoformat()})
    assert db.approve_leave(lid, "Abdulmajeed Mohammed AlJuraid")


def test_evaluation_math(db: OpsDB):
    _august_reports(db)
    a = staff_eval.evaluate_staff(db, "Ahmed Mohammed Bakri", 2026, 8)
    assert a["Eval_Month"] == "2026-08"
    assert a["Working_Days_Pct"] == "100.0"   # 20 reported / (22-2 leave)
    assert a["Patients_Seen"] == "200"
    assert a["Patient_Share_Pct"] == "80.0"   # 200 / 250
    assert a["Load_Index"] == "160.0"         # 200 / 125 avg
    assert a["Doc_Rate_Pct"] == "100.0"
    assert a["Leave_Days"] == "2"
    assert a["Flags"] == staff_eval.FLAG_LOAD_HIGH

    k = staff_eval.evaluate_staff(db, "Khaled Sultan Al-Otaibi", 2026, 8)
    assert k["Working_Days_Pct"] == "45.5"    # 10 / 22
    assert k["Patient_Share_Pct"] == "20.0"
    assert k["Load_Index"] == "40.0"
    assert k["Doc_Rate_Pct"] == "50.0"
    assert staff_eval.FLAG_WORKING in k["Flags"]
    assert staff_eval.FLAG_DOC in k["Flags"]
    assert staff_eval.FLAG_LOAD_LOW in k["Flags"]


def test_evaluation_excludes_supervisors(db: OpsDB):
    _august_reports(db)
    names = {r["Staff_Name"] for r in staff_eval.evaluate_all(db, 2026, 8)}
    assert "Ahmed Mohammed Bakri" in names
    assert "Shahad Abdullah Albalawi" not in names
    assert "Abdulrahman Hawsawi" not in names


def test_monthly_run_idempotent(db: OpsDB):
    _august_reports(db)
    label, rows = staff_eval.run_monthly_evaluation(db, DAY)
    assert label == "2026-08" and rows
    n = len(db.b.read_tab("Staff_Evaluations"))
    label2, rows2 = staff_eval.run_monthly_evaluation(db, DAY)
    assert label2 == label and len(rows2) == len(rows)
    assert len(db.b.read_tab("Staff_Evaluations")) == n  # no duplicates


def test_evaluation_agent_flow(db: OpsDB, ctx: Ctx):
    assert EvaluationAgent().run(ctx) == []  # no August data → silent
    _august_reports(db)
    alerts = EvaluationAgent().run(ctx)
    keys = {a.key for a in alerts}
    assert "eval:2026-08:head" in keys
    assert any(k.startswith("eval:2026-08:U") for k in keys)
    head = next(a for a in alerts if a.key == "eval:2026-08:head")
    assert "Khaled Sultan Al-Otaibi" in head.body  # flagged staffer listed
    assert EvaluationAgent().run(ctx) == []  # restart-safe: announce once


def test_format_eval_card(db: OpsDB):
    _august_reports(db)
    card = staff_eval.format_eval_card(
        staff_eval.evaluate_staff(db, "Ahmed Mohammed Bakri", 2026, 8))
    assert "Ahmed Mohammed Bakri (2026-08)" in card
    assert "160.0%" in card and "Formulas:" in card


# -- scheduler --------------------------------------------------------------------------------
def test_due_jobs_reminders_and_evaluation(monkeypatch):
    monkeypatch.setattr(settings, "reminder_times", ["08:15"])
    monkeypatch.setattr(settings, "eval_day", 1)
    monkeypatch.setattr(settings, "eval_time", "08:00")
    assert "reminders" in due_jobs(datetime(2026, 9, 13, 8, 16), {})
    assert "reminders" not in due_jobs(datetime(2026, 9, 13, 8, 14), {})
    assert "evaluation" in due_jobs(datetime(2026, 9, 13, 8, 16), {})
    assert "evaluation" not in due_jobs(datetime(2026, 9, 1, 7, 59), {})
    assert "evaluation" in due_jobs(datetime(2026, 9, 1, 8, 1), {})
    last: dict = {}
    mark_ran(last, ["reminders", "evaluation"],
             datetime(2026, 9, 13, 8, 16))
    assert last["reminders:08:15"] == datetime(2026, 9, 13, 8, 16)
    assert "evaluation" not in due_jobs(datetime(2026, 9, 13, 9, 0), last)
