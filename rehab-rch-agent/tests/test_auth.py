"""Staff access tests — Status / Valid Until enforcement."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import StaffAuth, StaffMember
from config import settings


def _auth_with(tmp_path: Path, staff: list[dict]) -> StaffAuth:
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(staff), encoding="utf-8")
    settings.staff_allowlist_file = str(path)
    settings.staff_sheet_id = ""
    settings.allowed_telegram_ids = []
    return StaffAuth()


def test_active_staff_authorized(tmp_path):
    auth = _auth_with(tmp_path, [
        {"telegram_id": "111", "name": "Abdulrahman", "role": "Section Head"},
    ])
    assert auth.source == "json"
    assert auth.is_authorized("111")
    assert auth.get_staff(111).display() == "Abdulrahman (Section Head)"


def test_suspended_staff_denied(tmp_path):
    auth = _auth_with(tmp_path, [
        {"telegram_id": "222", "name": "Ex Staff", "status": "Suspended"},
    ])
    assert not auth.is_authorized("222")
    assert auth.get_staff("222") is not None  # row kept for review, access denied


def test_expired_staff_denied(tmp_path):
    auth = _auth_with(tmp_path, [
        {"telegram_id": "333", "name": "Temp", "valid_until": "2020-01-01"},
        {"telegram_id": "444", "name": "Current", "valid_until": "2099-01-01"},
    ])
    assert not auth.is_authorized("333")
    assert auth.is_authorized("444")


def test_access_ok_defaults():
    assert StaffMember("1", "A").access_ok
    assert not StaffMember("1", "A", status="Inactive").access_ok
