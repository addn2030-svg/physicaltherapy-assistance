"""Staff-only access tests — private-chat gate + enrollment code."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import check_enroll_code, is_private_chat  # noqa: E402
from config import settings  # noqa: E402


class _Chat:
    def __init__(self, chat_type):
        self.type = chat_type


class _Update:
    def __init__(self, chat_type):
        self.effective_chat = _Chat(chat_type) if chat_type else None


def test_private_chat_allowed():
    assert is_private_chat(_Update("private"))


def test_groups_channels_denied():
    for chat_type in ("group", "supergroup", "channel"):
        assert not is_private_chat(_Update(chat_type))


def test_missing_chat_denied():
    assert not is_private_chat(_Update(None))
    assert not is_private_chat(object())


def test_enroll_code_checked(monkeypatch):
    monkeypatch.setattr(settings, "enroll_code", "RCH-2026-X7")
    assert check_enroll_code("RCH-2026-X7")
    assert not check_enroll_code("wrong")
    assert not check_enroll_code("")


def test_enroll_code_fail_closed_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "enroll_code", "")
    assert not check_enroll_code("anything")
    assert not check_enroll_code("")
