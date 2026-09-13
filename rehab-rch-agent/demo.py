#!/usr/bin/env python3
"""Rehab RCH Agent v2 — zero-credential runnable demo.

Runs the FULL agent pipeline without Telegram/Gemini/Google keys:
auth → PHI screen → KB search + citations + coverage → Gemini (demo
drafts) → .docx reports → Drive (demo save) → audit trail.

Usage:
    python demo.py              # scripted end-to-end scenario
    python demo.py --interactive  # chat with the agent in your terminal

The Telegram wiring itself lives in bot.py (import-tested); this demo
exercises everything the bot calls.
"""

from __future__ import annotations

import os
import sys

# Demo identity must be set BEFORE importing agent modules (they read env).
os.environ.setdefault("ALLOWED_TELEGRAM_IDS", "123456789")
os.environ.setdefault("DEPARTMENT_NAME", "Rehabilitation Department — RCH")

sys.path.insert(0, str(__file__ and __import__("pathlib").Path(__file__).resolve().parent))

from datetime import datetime  # noqa: E402

from audit import AuditLogger  # noqa: E402
from auth import StaffAuth  # noqa: E402
from config import settings  # noqa: E402
from gemini_client import GeminiClient  # noqa: E402
from google_drive import DriveClient  # noqa: E402
from knowledge_base import KnowledgeBase, coverage_label  # noqa: E402
from report_generator import (  # noqa: E402
    build_announcement,
    build_meeting_minutes,
    build_weekly_report,
)
from safety import contains_phi  # noqa: E402

DEMO_USER = "123456789"
BANNER = "=" * 64


def header(title: str) -> None:
    print(f"\n{BANNER}\n{title}\n{BANNER}")


def build_agent():
    """Instantiate the agent stack (demo mode: no external keys)."""
    auth = StaffAuth()
    kb = KnowledgeBase()
    gemini = GeminiClient()
    drive = DriveClient()
    audit = AuditLogger()
    return auth, kb, gemini, drive, audit


def ask(auth, kb, gemini, audit, text: str) -> str:
    """One Q&A turn exactly as bot.py handle_message/cmd_sop does."""
    staff = auth.get_staff(DEMO_USER)
    name = staff.display() if staff else ""
    phi = contains_phi(text)
    if phi.blocked:
        audit.log("phi_blocked", DEMO_USER, name, f"reasons={'; '.join(phi.reasons)}")
        return "⛔ Blocked: patient information is not allowed. Resubmit a de-identified operational request."
    results = kb.search(text, top_k=3)
    ctx = kb.context_for(text)
    answer = gemini.explain_sop(text, ctx) if ctx else gemini.answer_question(text)
    level, note = coverage_label(results)
    reply = f"{answer}\n\n_Knowledge coverage: {level} — {note}_"
    if results:
        cites = "\n".join(f"📄 {r.citation}" for r in results)
        reply += f"\n\n*Sources:*\n{cites}"
    audit.log("question_asked", DEMO_USER, name, f"coverage={level} q={text[:100]}")
    if level == "None":
        audit.log("needs_review", DEMO_USER, name, f"out-of-scope q={text[:120]}")
    return reply


def run_scripted() -> int:
    auth, kb, gemini, drive, audit = build_agent()

    header("1. AUTH  —  staff allowlist")
    print(f"Source: {auth.source} | staff: {auth.count()} | active: {auth.active_count()}")
    print(f"Demo user 123456789 authorized: {auth.is_authorized(DEMO_USER)}")
    print(f"Stranger 999999999 authorized: {auth.is_authorized('999999999')}")
    audit.log("auth_granted", DEMO_USER, "Demo Staff", "demo")

    header("2. SAFETY  —  PHI screen")
    allowed = "What is the process for equipment request?"
    blocked = "Patient Ahmed Mohammed, MRN 123456, needs a summary"
    print(f"ALLOWED  '{allowed}' -> blocked={contains_phi(allowed).blocked}")
    print(f"BLOCKED  '{blocked}' -> blocked={contains_phi(blocked).blocked}")

    header("3. KNOWLEDGE  —  SOP search + citations + coverage")
    print(kb.status())
    print()
    q = "What is the process for equipment request?"
    print(f"Q: {q}\n")
    print(ask(auth, kb, gemini, audit, q))

    header("4. OUT-OF-SCOPE  —  flagged for human review")
    q2 = "What is on the cafeteria menu this Friday?"
    print(f"Q: {q2}\n")
    print(ask(auth, kb, gemini, audit, q2))

    header("5. ANNOUNCEMENT  —  draft + .docx")
    draft = gemini.draft_announcement("Staff meeting Tuesday at 09:00")
    print(draft[:400], "...\n")
    apath = build_announcement(draft, subject="Staff Meeting", prepared_by="Demo Staff")
    print(f"Saved: {apath}")
    audit.log("announcement_saved", DEMO_USER, "Demo Staff", f"file={apath.name}")

    header("6. WEEKLY REPORT  —  draft + .docx + Drive save")
    body = gemini.generate_report("weekly", "• OPD coverage stable\n• 2 devices pending maintenance")
    print(body[:400], "...\n")
    rpath = build_weekly_report(body, prepared_by="Demo Staff", when=datetime(2026, 9, 13))
    print(f"Saved: {rpath}")
    result = drive.upload_file(rpath, folder_key="Reports/Weekly")
    print(result["message"])
    audit.log("report_generated", DEMO_USER, "Demo Staff", f"type=weekly file={rpath.name}")

    header("7. MEETING MINUTES  —  summarize + .docx")
    minutes = gemini.summarize_meeting("• Discussed leave coverage\n• Approved duty roster")
    mpath = build_meeting_minutes(minutes, title="Staff Huddle", prepared_by="Demo Staff")
    print(f"Saved: {mpath}")
    audit.log("meeting_saved", DEMO_USER, "Demo Staff", f"file={mpath.name}")

    header("8. AUDIT TRAIL  —  recent events")
    for e in audit.recent(10):
        print(f"{e['ts_utc']}  {e['event']:<18} {e['details'][:70]}")

    header(f"DEMO COMPLETE  —  {settings.department_name}")
    print("Gemini: demo drafts (add GEMINI_API_KEY for live AI) | "
          "Drive: demo saves (add credentials.json for live Drive)")
    print("Next: cp .env.example .env, add keys, then:  python bot.py")
    return 0


def run_interactive() -> int:
    auth, kb, gemini, drive, audit = build_agent()
    if not auth.is_authorized(DEMO_USER):
        print("🔒 Access denied. Contact Rehabilitation Section Head.")
        return 1
    print("🏥 Rehab RCH Agent demo — type a question, or /quit to exit.")
    print("(Operational questions only — PHI is blocked.)")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if text.lower() in {"/quit", "/exit", "quit", "exit"}:
            print("Goodbye.")
            return 0
        if not text:
            continue
        print(f"\nAgent:\n{ask(auth, kb, gemini, audit, text)}")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        return run_interactive()
    return run_scripted()


if __name__ == "__main__":
    raise SystemExit(main())
