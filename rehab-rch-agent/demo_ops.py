#!/usr/bin/env python3
"""Rehab RCH Agent v3 — operations demo (zero credentials).

Exercises the Rehab_Operations_Master_v2 layer against an in-memory
sheet seeded with the real department structure (8 units, 4 supervisors,
18 staff): data health, morning briefing, daily report filing, action
and equipment logging, announcements, FAQ.

Usage:  python demo_ops.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_handlers import (  # noqa: E402
    build_briefing_text,
    format_actions,
    format_dashboard,
    format_equipment,
    format_units,
)
from sheets_ops import demo_ops_db  # noqa: E402

BANNER = "=" * 64


def header(title: str) -> None:
    print(f"\n{BANNER}\n{title}\n{BANNER}")


def main() -> int:
    today = date.today()
    db = demo_ops_db(today)

    header("1. ORG STRUCTURE  —  /units")
    print(format_units(db))

    header("2. DATA HEALTH  —  /datahealth")
    h = db.datahealth()
    print(f"Staff: {h['staff_count']} | Units: {h['units_count']}")
    print(f"Missing roles ({len(h['missing_roles'])}):")
    for item in h["missing_roles"][:6]:
        print(f"  • {item}")
    print(f"Telegram active without Chat ID: {h['telegram_active_without_chat_id']}")
    print(f"Capability rows: {h['capability_rows']} "
          f"({h['capability_unverified']} unverified)")

    header("3. DASHBOARD  —  /dashboard")
    print(format_dashboard(db))

    header("4. MORNING BRIEFING  —  /briefing")
    print(build_briefing_text(db, today))

    header("5. FILE A DAILY REPORT  —  /daily")
    db.add_staff_report({
        "Report_Date": today.isoformat(), "Staff_Name": "Ahmed Mohammed Bakri",
        "Unit": "U01", "Patients_Seen": "7", "New_Cases": "1",
        "Follow_Up_Cases": "6", "Documentation_Status": "Complete",
        "Issues": "", "Follow_Up_Tomorrow": "5 booked",
        "Submitted_Time": "15:30",
    })
    print("✅ Ahmed Mohammed Bakri (U01): 7 seen, docs Complete")
    print(f"Still missing: {len(db.missing_staff_reports(today))} staff")

    header("6. ACTIONS  —  /actions + add")
    print(format_actions(db))
    aid = db.add_action({"Title": "Calibrate U02 weighing scale",
                         "Owner": "Shahad Abdullah Albalawi",
                         "Due_Date": today.isoformat(), "Priority": "Low",
                         "Source": "Demo"})
    print(f"\n✅ Added {aid}")

    header("7. EQUIPMENT  —  /equipment + log")
    print(format_equipment(db))
    iid = db.add_equipment_issue({"Unit": "U02", "Equipment": "TENS unit",
                                  "Issue": "Battery cover cracked",
                                  "Severity": "Low",
                                  "Reported_By": "Demo"})
    print(f"\n✅ Logged {iid}")

    header("8. ANNOUNCEMENT LOG + FAQ")
    db.add_announcement({"Title": "Fire drill Thursday 10:00",
                         "Body": "All units participate.", "Audience": "All units",
                         "Author": "Demo", "Status": "Sent"})
    print(f"Announcements: {len(db.recent_announcements(10))}")
    for faq in db.faq_search("equipment request process"):
        print(f"FAQ: {faq['Question']}\n→ {faq['Answer'][:80]}...")

    header("9. SCHEMA CHECK  —  /setup would create these")
    print(f"{len(db.ensure_schema())} tabs present, all headers OK")

    header("OPS DEMO COMPLETE")
    print("Connect the live sheet: set OPS_SHEET_ID in .env, share the Google")
    print("Sheet with the service account as Editor, restart, run /setup.")
    print("Guide: docs/SHEETS_OPS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
