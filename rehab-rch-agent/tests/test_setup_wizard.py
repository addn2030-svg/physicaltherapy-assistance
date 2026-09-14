"""Setup wizard tests — env parsing, rendering, token check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import fix_console_encoding  # noqa: E402
from setup_wizard import mask, parse_env_file, render_env, valid_token  # noqa: E402


def test_parse_env_file():
    text = "# comment\n\nTELEGRAM_BOT_TOKEN=abc:123\nEMPTY=\nBADLINE\n"
    assert parse_env_file(text) == {"TELEGRAM_BOT_TOKEN": "abc:123", "EMPTY": ""}


def test_render_env_roundtrip():
    values = {"TELEGRAM_BOT_TOKEN": "1:A", "TELEGRAM_ADMIN_IDS": "99",
              "ENROLL_CODE": "C"}
    rendered = render_env(values)
    parsed = parse_env_file(rendered)
    assert parsed["TELEGRAM_BOT_TOKEN"] == "1:A"
    assert parsed["TELEGRAM_ADMIN_IDS"] == "99"
    assert parsed["SCHED_TZ"] == "Asia/Riyadh"  # sane defaults included


def test_valid_token():
    assert valid_token("123456:ABCdefGHIjklMNOpqrSTUvwxYZ-1234")
    assert not valid_token("not-a-token")
    assert not valid_token("")


def test_mask():
    assert mask("") == "(empty)"
    assert mask("abcdef") == "ab…ef"


def test_fix_console_encoding_never_raises():
    fix_console_encoding()  # Windows cp1252 guard; no-op elsewhere
