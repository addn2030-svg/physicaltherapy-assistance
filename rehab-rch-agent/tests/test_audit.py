"""Audit trail tests — logging must never break flows or leak content."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit import AuditLogger


def test_log_writes_jsonl(tmp_path):
    audit = AuditLogger(audit_dir=tmp_path)
    entry = audit.log("auth_denied", "999", "Intruder", "handler=cmd_start")
    assert entry["event"] == "auth_denied"
    assert entry["telegram_id"] == "999"

    files = list(tmp_path.glob("audit-*.jsonl"))
    assert len(files) == 1
    stored = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert stored["event"] == "auth_denied"
    assert "ts_utc" in stored


def test_recent_returns_newest_last(tmp_path):
    audit = AuditLogger(audit_dir=tmp_path)
    audit.log("e1")
    audit.log("e2")
    audit.log("e3")
    events = [e["event"] for e in audit.recent(2)]
    assert events == ["e2", "e3"]


def test_details_truncated(tmp_path):
    audit = AuditLogger(audit_dir=tmp_path)
    entry = audit.log("question_asked", "1", "Sara", "x" * 1000)
    assert len(entry["details"]) <= 500
