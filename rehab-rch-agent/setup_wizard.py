"""Interactive setup wizard — creates your `.env` config without editing files.

Run it after installing dependencies:

    python setup_wizard.py

It asks a few questions (paste your bot token, IDs, keys), keeps your
previous answers as defaults when re-run, and writes `.env` for you.
Nothing is sent anywhere — everything stays on this machine.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# (env key, question, required?, secret?)
QUESTIONS: list[tuple[str, str, bool, bool]] = [
    ("TELEGRAM_BOT_TOKEN", "Bot token from @BotFather", True, True),
    ("TELEGRAM_ADMIN_IDS", "Your Telegram ID (from @userinfobot)", True, False),
    ("ENROLL_CODE", "Enrollment code for staff (invent one, e.g. RCH-2026-STAFF)",
     True, False),
    ("GEMINI_API_KEY", "Gemini API key [optional, Enter to skip]", False, True),
    ("OPS_SHEET_ID", "Operations Google Sheet ID [optional, Enter to skip]",
     False, False),
    ("SMTP_HOST", "Email SMTP host, e.g. smtp.gmail.com [optional]", False, False),
    ("SMTP_USER", "SMTP username [optional]", False, False),
    ("SMTP_PASSWORD", "SMTP password / app-password [optional]", False, True),
    ("SMTP_FROM", "SMTP from-address [optional]", False, False),
    ("GOOGLE_CALENDAR_ID", "Google Calendar ID [optional, Enter to skip]",
     False, False),
]

TEMPLATE = """# Rehab RCH Agent — created by setup_wizard.py. Keep this file private!
# Re-run `python setup_wizard.py` any time to update it.

TELEGRAM_BOT_TOKEN={TELEGRAM_BOT_TOKEN}
TELEGRAM_ADMIN_IDS={TELEGRAM_ADMIN_IDS}
ENROLL_CODE={ENROLL_CODE}

GEMINI_API_KEY={GEMINI_API_KEY}
GOOGLE_CREDENTIALS_FILE=credentials.json
OPS_SHEET_ID={OPS_SHEET_ID}

SCHED_ENABLED=true
SCHED_TZ=Asia/Riyadh
BRIEFING_TIME=07:30
GAP_SCAN_TIMES=09:00,12:00,15:00
REPORT_CUTOFF=15:00
ROLLUP_TIME=17:00
WEEKLY_DAY=SUN
WEEKLY_TIME=08:00
WATCHDOG_MINUTES=30
QUIET_HOURS=22:00-06:30
REMINDER_TIMES=08:15
EVAL_DAY=1
EVAL_TIME=08:00

EMAIL_ENABLED=true
SMTP_HOST={SMTP_HOST}
SMTP_PORT=587
SMTP_USER={SMTP_USER}
SMTP_PASSWORD={SMTP_PASSWORD}
SMTP_FROM={SMTP_FROM}

CALENDAR_ENABLED=true
GOOGLE_CALENDAR_ID={GOOGLE_CALENDAR_ID}
"""


def parse_env_file(text: str) -> dict[str, str]:
    """Read KEY=VALUE lines (ignores comments/blanks)."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip("'\"")
    return values


def render_env(values: dict[str, str]) -> str:
    merged = {key: values.get(key, "") for key, _, _, _ in QUESTIONS}
    return TEMPLATE.format(**merged)


def mask(value: str) -> str:
    if len(value) <= 4:
        return "****" if value else "(empty)"
    return value[:2] + "…" + value[-2:]


def ask(question: str, default: str, secret: bool) -> str:
    hint = f" [{mask(default) if secret and default else default}]" \
        if default else ""
    try:
        answer = input(f"  {question}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled — nothing was changed.")
        sys.exit(1)
    return answer or default


def valid_token(token: str) -> bool:
    return bool(re.fullmatch(r"\d{6,}:[\w-]{20,}", token.strip()))


def main() -> int:
    try:  # Windows consoles default to cp1252 — don't crash on emoji
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 60)
    print("Rehab RCH Agent — setup wizard")
    print("=" * 60)
    existing = parse_env_file(ENV_FILE.read_text(encoding="utf-8")) \
        if ENV_FILE.exists() else {}
    if existing:
        print(f"Found an existing .env — press Enter to keep shown values.\n")

    values: dict[str, str] = {}
    for key, question, required, secret in QUESTIONS:
        while True:
            val = ask(question, existing.get(key, ""), secret)
            if val or not required:
                break
            print("    ⚠️  This one is required — please paste a value.")
        if key == "TELEGRAM_BOT_TOKEN" and not valid_token(val):
            print("    ⚠️  That doesn't look like a bot token (digits:letters). "
                  "Continuing anyway — double-check it.")
        values[key] = val

    ENV_FILE.write_text(render_env(values), encoding="utf-8")
    try:
        os.chmod(ENV_FILE, 0o600)  # private file on Linux/Mac
    except OSError:
        pass  # Windows: nothing to do

    print("\n✅ Saved! Your settings file (.env) is ready.")
    print(f"   Token: {mask(values['TELEGRAM_BOT_TOKEN'])} | "
          f"Admin: {values['TELEGRAM_ADMIN_IDS'] or '?'} | "
          f"Code: {values['ENROLL_CODE'] or '?'}")
    if not (BASE_DIR / "credentials.json").exists():
        print("\n⚠️  Still missing: credentials.json (Google service account).")
        print("   The bot runs without it, but sheet features stay in demo mode.")
    print("\nNext: run the bot with  `python bot.py`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
