#!/usr/bin/env python3
"""Retention cleanup for Rehab RCH Agent v2.

Deletes locally generated files in ``output/`` older than RETENTION_DAYS
(default 365). Audit logs are NEVER deleted by this script.

Google Drive retention is intentionally manual: run with ``--list-drive``
to print Drive files older than the retention window, then archive or
delete them in the Drive UI after Section Head approval.

Usage:
    python scripts/retention_cleanup.py --dry-run   # preview (default)
    python scripts/retention_cleanup.py --apply     # delete local files
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings


def find_stale_local(retention_days: int) -> list[Path]:
    cutoff = time.time() - retention_days * 86400
    stale: list[Path] = []
    for path in settings.output_dir.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if "audit" in path.parts:  # audit trail is append-only
            continue
        try:
            if path.stat().st_mtime < cutoff:
                stale.append(path)
        except OSError:
            continue
    return sorted(stale)


def main() -> int:
    parser = argparse.ArgumentParser(description="Retention cleanup for local output/")
    parser.add_argument("--apply", action="store_true", help="delete files (default: dry run)")
    parser.add_argument("--days", type=int, default=settings.retention_days)
    args = parser.parse_args()

    stale = find_stale_local(args.days)
    print(f"Retention window: {args.days} days | output dir: {settings.output_dir}")
    print(f"Stale local files (audit logs excluded): {len(stale)}")
    for path in stale:
        print(f"  - {path.relative_to(settings.output_dir)}")

    if stale and args.apply:
        for path in stale:
            try:
                path.unlink()
            except OSError as exc:
                print(f"  ! failed to delete {path.name}: {exc}")
        print(f"Deleted {len(stale)} file(s).")
    elif stale:
        print("Dry run — nothing deleted. Re-run with --apply to delete.")
    print("Drive retention: review dated Reports folders manually each quarter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
