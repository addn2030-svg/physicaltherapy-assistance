"""Build a blank Rehab_Operations_Master_v2.xlsx template (all tabs + headers).

Usage:  python scripts/build_template.py
Output: Rehab_Operations_Master_v2_template.xlsx (import into Google Sheets).

Headers always match SCHEMAS in sheets_ops.py. Units and Data_Dictionary
come pre-filled from the department seed; everything else is headers-only
for staff to fill (or for /setup + the bot to fill).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook  # noqa: E402
from sheets_ops import SCHEMAS, demo_ops_db  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / \
    "Rehab_Operations_Master_v2_template.xlsx"

README_ROWS = [
    ["READ ME — Rehab_Operations_Master_v2"],
    [""],
    ["1. In Google Sheets: File → Import → Upload this file → Replace spreadsheet."],
    ["2. Share the sheet with your service-account email as Editor."],
    ["3. Copy the Sheet ID from the URL into the bot's setup wizard."],
    ["4. In Telegram: /setup (creates anything missing), then /datahealth."],
    [""],
    ["Check the Units tab supervisors, then fill Telegram_Users",
     "(one row per staffer; Chat ID from @userinfobot; Active=TRUE)."],
]


def main() -> None:
    seed = demo_ops_db(date(2026, 9, 13))
    units = seed.units()
    dictionary = seed.b.read_tab("Data_Dictionary")

    wb = Workbook()
    guide = wb.active
    assert guide is not None
    guide.title = "_READ_ME"
    for row in README_ROWS:
        guide.append(row)

    for tab, headers in SCHEMAS.items():
        ws = wb.create_sheet(tab)
        ws.append(list(headers))
        if tab == "Units":
            for u in units:
                ws.append([u.get(h, "") for h in headers])
        elif tab == "Data_Dictionary":
            for r in dictionary:
                ws.append([r.get(h, "") for h in headers])

    wb.save(OUT)
    print(f"Saved {OUT} ({len(SCHEMAS)} tabs)")


if __name__ == "__main__":
    main()
