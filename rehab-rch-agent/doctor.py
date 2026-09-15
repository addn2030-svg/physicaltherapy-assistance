"""Rehab RCH Agent — setup doctor.

Checks every prerequisite the bot needs and prints a pass/fail report.
Run:  .\venv\Scripts\python.exe doctor.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
OK = "[ OK ]"
BAD = "[FAIL]"
WARN = "[WARN]"

problems: list[str] = []


def say(mark: str, label: str, detail: str = "") -> None:
    line = f"{mark}  {label}"
    if detail:
        line += f"\n        {detail}"
    print(line)


def fail(label: str, detail: str, fix: str) -> None:
    say(BAD, label, detail)
    problems.append(fix)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 66)
    print(" Rehab RCH Agent — setup doctor")
    print("=" * 66)
    print()

    # ---- 1. .env -----------------------------------------------------
    env_path = BASE / ".env"
    if not env_path.exists():
        fail("1. .env file", "not found", "Create .env from .env.example")
        return report()

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except ImportError:
        fail("1. .env file", "python-dotenv not installed",
             "Run: .\\venv\\Scripts\\pip.exe install -r requirements.txt")
        return report()

    say(OK, "1. .env file", str(env_path))

    def env(key: str) -> str:
        return (os.getenv(key) or "").strip()

    # ---- 2. required keys --------------------------------------------
    print()
    token = env("TELEGRAM_BOT_TOKEN")
    ops_id = env("OPS_SHEET_ID")
    admins = env("TELEGRAM_ADMIN_IDS")
    allowed = env("ALLOWED_TELEGRAM_IDS")

    if token:
        say(OK, "2a. TELEGRAM_BOT_TOKEN", f"set ({len(token)} chars)")
    else:
        fail("2a. TELEGRAM_BOT_TOKEN", "empty", "Set TELEGRAM_BOT_TOKEN in .env")

    if ops_id:
        say(OK, "2b. OPS_SHEET_ID", ops_id)
    else:
        legacy = env("GOOGLE_SHEETS_ID")
        detail = "empty — ops commands will reply 'not connected'"
        if legacy:
            detail += f"\n        (found GOOGLE_SHEETS_ID={legacy}, which the code does NOT read)"
        fail("2b. OPS_SHEET_ID", detail,
             "Add OPS_SHEET_ID=<sheet id> to .env  (run fix_setup.bat)")

    if admins:
        say(OK, "2c. TELEGRAM_ADMIN_IDS", admins)
    else:
        say(WARN, "2c. TELEGRAM_ADMIN_IDS",
            "empty — admin-only commands will be refused")
        problems.append("Add TELEGRAM_ADMIN_IDS=<your id> to .env  (run fix_setup.bat)")

    if allowed:
        say(OK, "2d. ALLOWED_TELEGRAM_IDS", f"{allowed}  (fallback allowlist)")
    else:
        say(WARN, "2d. ALLOWED_TELEGRAM_IDS", "empty — no fallback if Sheets is down")

    # ---- 3. credentials.json -----------------------------------------
    print()
    cred_name = env("GOOGLE_CREDENTIALS_FILE") or "credentials.json"
    cred_path = Path(cred_name)
    if not cred_path.is_absolute():
        cred_path = BASE / cred_path

    sa_email = ""
    if not cred_path.exists():
        fail("3. credentials.json", f"not found at {cred_path}",
             "Download the service-account key from Google Cloud Console")
    else:
        try:
            data = json.loads(cred_path.read_text(encoding="utf-8"))
            sa_email = data.get("client_email", "")
            if data.get("type") != "service_account":
                fail("3. credentials.json",
                     f"type is '{data.get('type')}', expected 'service_account'",
                     "Download a SERVICE ACCOUNT key, not an OAuth client")
            elif not sa_email:
                fail("3. credentials.json", "no client_email field",
                     "Re-download the service-account key")
            else:
                say(OK, "3. credentials.json", sa_email)
        except Exception as exc:
            fail("3. credentials.json", f"unreadable: {exc}",
                 "Re-download the service-account key")

    # ---- 4. Telegram token is live ------------------------------------
    print()
    if token:
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            with urllib.request.urlopen(url, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                bot = body["result"]
                say(OK, "4. Telegram API", f"@{bot.get('username')} (id {bot.get('id')})")
            else:
                fail("4. Telegram API", str(body),
                     "Check TELEGRAM_BOT_TOKEN with @BotFather")
        except Exception as exc:
            fail("4. Telegram API", f"{type(exc).__name__}: {exc}",
                 "Check internet / proxy, or regenerate the token in @BotFather")
    else:
        say(WARN, "4. Telegram API", "skipped — no token")

    # ---- 5. Google Sheets access --------------------------------------
    print()
    sheet = None
    if not ops_id:
        say(WARN, "5. Ops workbook", "skipped — OPS_SHEET_ID not set")
    elif not sa_email:
        say(WARN, "5. Ops workbook", "skipped — no service-account credentials")
    else:
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_file(
                str(cred_path),
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            client = gspread.authorize(creds)
            sheet = client.open_by_key(ops_id)
            say(OK, "5. Ops workbook", f"opened '{sheet.title}'")
        except ImportError:
            fail("5. Ops workbook", "gspread not installed",
                 "Run: .\\venv\\Scripts\\pip.exe install -r requirements.txt")
        except Exception as exc:
            name = type(exc).__name__
            detail = f"{name}: {str(exc)[:300]}"
            hint = (f"Share the sheet with {sa_email} as EDITOR"
                    if sa_email else "Share the sheet with the service account")
            if "PERMISSION_DENIED" in str(exc) or "403" in str(exc) or "404" in name.upper():
                detail += "\n        -> the service account cannot see this sheet"
            fail("5. Ops workbook", detail, hint)

    # ---- 6. Telegram_Users tab ----------------------------------------
    print()
    active_markers = {"true", "yes", "active", "1", "y"}
    if sheet is None:
        say(WARN, "6. Telegram_Users tab", "skipped — workbook not reachable")
    else:
        try:
            tab = sheet.worksheet("Telegram_Users")
            rows = tab.get_all_records()
            active = [r for r in rows
                      if str(r.get("Active", "")).strip().lower() in active_markers]
            if not rows:
                fail("6. Telegram_Users tab", "no rows",
                     "Add a row: Staff_Name | Unit | Telegram_Username | Telegram_Chat_ID | Active=TRUE")
            elif not active:
                names = ", ".join(str(r.get("Staff_Name", "?")) for r in rows[:5])
                fail("6. Telegram_Users tab",
                     f"{len(rows)} row(s) but NONE marked Active: {names}",
                     "Set the Active column to TRUE for your row")
            else:
                say(OK, "6. Telegram_Users tab",
                    f"{len(active)} active of {len(rows)}: "
                    + ", ".join(f"{r.get('Staff_Name')} ({r.get('Telegram_Chat_ID')})"
                                for r in active[:5]))
        except Exception as exc:
            fail("6. Telegram_Users tab", f"{type(exc).__name__}: {str(exc)[:200]}",
                 "Check that a tab named exactly 'Telegram_Users' exists")

    # ---- 7. what the bot will actually load ----------------------------
    print()
    try:
        sys.path.insert(0, str(BASE))
        from auth import staff_auth  # noqa: E402

        src = staff_auth.source
        detail = (f"source={src}  count={staff_auth.count()}  "
                  f"active={staff_auth.active_count()}")
        if src == "ops-telegram-users":
            say(OK, "7. Staff allowlist", detail + "   <- correct source")
        elif src == "none":
            fail("7. Staff allowlist", detail + "  -> every user will be denied",
                 "Fix steps 5 and 6 above")
        else:
            say(WARN, "7. Staff allowlist",
                detail + f"\n        using fallback '{src}' — the sheet is not being read")
            problems.append("Allowlist is falling back to '%s'; fix the sheet access "
                            "so source=ops-telegram-users" % src)
    except Exception as exc:
        fail("7. Staff allowlist", f"{type(exc).__name__}: {str(exc)[:200]}",
             "Import error — run from the rehab-rch-agent folder with the venv python")

    return report()


def report() -> int:
    print()
    print("=" * 66)
    if not problems:
        print(" ALL CHECKS PASSED — start the bot:")
        print("   .\\venv\\Scripts\\python.exe bot.py")
        print("=" * 66)
        return 0
    print(f" {len(problems)} THING(S) TO FIX:")
    print("=" * 66)
    for i, p in enumerate(problems, 1):
        print(f"  {i}. {p}")
    print()
    print(" Fix them, then run this doctor again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
