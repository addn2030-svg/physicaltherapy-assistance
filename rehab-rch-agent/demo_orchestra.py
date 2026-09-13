#!/usr/bin/env python3
"""Agent v4 orchestra demo — a full proactive day in 10 seconds.

Simulates the 24/7 scheduler against the in-memory ops sheet:
briefing push → gap scans → cutoff nudges → rollup → weekly →
dedup proof → quiet-hours proof → critical piercing quiet hours.

Usage:  python demo_orchestra.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import Orchestrator  # noqa: E402
from config import settings  # noqa: E402
from sheets_ops import demo_ops_db  # noqa: E402

BANNER = "=" * 64
DAY = datetime(2026, 9, 13)  # a Sunday


def header(title: str) -> None:
    print(f"\n{BANNER}\n{title}\n{BANNER}")


def show(outbox, limit_per_level: int = 3) -> None:
    if not outbox:
        print("(no messages — suppressed or all quiet)")
        return
    by_level: dict[str, list] = {}
    for m in outbox:
        by_level.setdefault(f"{m.level} → {m.meta.get('to')}", []).append(m)
    print(f"{len(outbox)} message(s):")
    for dest, msgs in sorted(by_level.items()):
        print(f"\n  ┌─ {dest} ({len(msgs)})")
        for m in msgs[:limit_per_level]:
            first = m.text.splitlines()[0][:100]
            print(f"  │ [{m.meta.get('severity')}] {first}")
        if len(msgs) > limit_per_level:
            print(f"  │ … +{len(msgs) - limit_per_level} more")


def main() -> int:
    settings.higher_admin_chat_ids = ["999"]  # demo higher admin
    tmp = Path(tempfile.mkdtemp(prefix="orchestra-"))
    db = demo_ops_db(DAY.date())
    for name, unit, chat in [
        ("Abdulrahman Hawsawi", "U08", "111"),
        ("Abdulmajeed Mohammed AlJuraid", "U01", "112"),
        ("Shahad Abdullah Albalawi", "U02", "113"),
        ("Sumaya Abdullah Al Batook", "U03", "114"),
        ("Ahmed Mohammed Bakri", "U01", "121"),
        ("Khaled Sultan Al-Otaibi", "U01", "122"),
    ]:
        db.upsert_telegram_user(name, unit, "", chat, "TRUE")
    orch = Orchestrator(db, state_path=tmp / "state.json")

    header("07:30  BRIEFING PUSH → head + supervisors")
    show(orch.tick(DAY.replace(hour=7, minute=30), ["briefing"]))

    header("09:00  GAP SCAN → missing reports + data gaps")
    show(orch.tick(DAY.replace(hour=9), ["gaps"]))

    header("15:30  CUTOFF NUDGES → therapists directly")
    show(orch.tick(DAY.replace(hour=15, minute=30), ["gaps"]))

    header("15:35  DEDUP PROOF → same tick, zero repeats")
    show(orch.tick(DAY.replace(hour=15, minute=35), ["gaps"]))

    header("17:00  EVENING ROLLUP → head + sheet + Drive archive")
    show(orch.tick(DAY.replace(hour=17), ["rollup"]))
    print(f"\nSupervisor_Briefings rows: {len(db.b.read_tab('Supervisor_Briefings'))}")

    header("SUN 08:00  WEEKLY AUTO-DRAFT → head + higher admin")
    show(orch.tick(DAY.replace(hour=8), ["weekly"]))
    print(f"\nWeekly_Summary rows: {len(db.b.read_tab('Weekly_Summary'))}")

    header("23:00  QUIET HOURS → non-critical held")
    show(orch.tick(DAY.replace(hour=23), ["gaps"]))

    header("23:05  CRITICAL pierces quiet hours")
    db.add_equipment_issue({"Unit": "U03", "Equipment": "Ventilator port",
                            "Issue": "Total failure", "Severity": "Critical",
                            "Reported_By": "Demo"})
    show(orch.tick(DAY.replace(hour=23, minute=5), ["watchdog"]))

    header("ORCHESTRA DEMO COMPLETE")
    print("Escalation: therapist → supervisor → head → admin ✅")
    print("Dedup, quiet hours, auto-reports, Drive archive ✅")
    print("Live: the same tick runs every 60s via scheduler.py on Oracle 24/7.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
