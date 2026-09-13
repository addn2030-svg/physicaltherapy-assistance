"""Messenger — who gets what in the Agent v4 orchestra.

Resolves escalation recipients from the ops workbook and delivers
messages over Telegram (live) or into a list (demo/tests).

Escalation ladder:
  therapist → unit supervisor → section head → higher admin.
When a direct Chat ID is unknown, the message escalates one level up
with a "(for X — no Chat ID on file)" note, and the gap is flagged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from config import settings
from sheets_ops import OpsDB

log = logging.getLogger(__name__)

LEVELS = ("therapist", "supervisor", "head", "admin")


@dataclass
class Recipient:
    level: str
    chat_id: str
    label: str  # human description, e.g. "U03 supervisor (Sumaya Abdullah Al Batook)"
    escalated: bool = False  # True when redirected upward (chat unknown)
    note: str = ""


@dataclass
class OutboxMessage:
    chat_id: str
    text: str
    level: str
    key: str  # dedup key
    meta: dict = field(default_factory=dict)


class Directory:
    """Chat-ID directory backed by Telegram_Users + Units + env admins."""

    def __init__(self, db: OpsDB) -> None:
        self.db = db

    def chat_for_staff(self, name: str) -> str:
        return self.db.chat_id_for(name)

    def supervisor_of(self, unit_id: str) -> tuple[str, str]:
        """(supervisor name, chat_id) for a unit."""
        unit = self.db.unit_by_id(unit_id)
        name = (unit or {}).get("Supervisor", "") if unit else ""
        name = str(name or "").strip()
        return name, self.db.chat_id_for(name) if name else ""

    def section_head(self) -> tuple[str, str]:
        unit = self.db.unit_by_id("U08")
        name = str((unit or {}).get("Supervisor", "") or "").strip()
        if not name:
            for s in self.db.supervisors():
                if str(s.get("Area", "")).strip().lower() == "section head":
                    name = str(s.get("Supervisor", "")).strip()
                    break
        return name, self.db.chat_id_for(name) if name else ""

    def all_supervisor_chats(self) -> dict[str, str]:
        """{supervisor name: chat_id} for every unit supervisor with a chat."""
        out: dict[str, str] = {}
        for u in self.db.units():
            name = str(u.get("Supervisor", "") or "").strip()
            if name and name not in out:
                chat = self.db.chat_id_for(name)
                if chat:
                    out[name] = chat
        return out

    def higher_admins(self) -> list[str]:
        return [c for c in settings.higher_admin_chat_ids if c.strip()]

    # -- escalation ------------------------------------------------------
    def resolve(self, level: str, staff_name: str = "",
                unit_id: str = "") -> Recipient:
        """Resolve one recipient, escalating upward when chat is unknown."""
        order = list(LEVELS[LEVELS.index(level):])
        first_target = staff_name or unit_id or level
        for step, lvl in enumerate(order):
            chat, label = "", ""
            if lvl == "therapist":
                chat, label = self.chat_for_staff(staff_name), staff_name
            elif lvl == "supervisor" and unit_id:
                name, chat = self.supervisor_of(unit_id)
                label = f"{unit_id} supervisor ({name})" if name else f"{unit_id} supervisor"
            elif lvl == "head":
                name, chat = self.section_head()
                label = f"Section Head ({name})" if name else "Section Head"
            elif lvl == "admin":
                admins = self.higher_admins()
                if admins:
                    return Recipient("admin", admins[0], "Higher admin",
                                     escalated=step > 0,
                                     note=f"also for {first_target}" if step else "")
                continue
            if chat:
                return Recipient(lvl, chat, label, escalated=step > 0,
                                 note=f"(for {first_target} — no Chat ID on file)"
                                 if step else "")
        # Nowhere to deliver — return undeliverable marker for the head/admin.
        head_name, head_chat = self.section_head()
        if head_chat:
            return Recipient("head", head_chat, f"Section Head ({head_name})",
                             escalated=True, note=f"(UNROUTABLE alert for {first_target})")
        return Recipient("head", "", "nowhere", escalated=True,
                         note=f"UNROUTABLE: no chat on file for {first_target}")


class TelegramMessenger:
    """Live delivery via the python-telegram-bot Bot object."""

    def __init__(self, bot) -> None:
        self.bot = bot

    async def send(self, msg: OutboxMessage) -> bool:
        if not msg.chat_id:
            log.warning("Skipped undeliverable message: %s", msg.key)
            return False
        try:
            text = msg.text
            for i in range(0, max(len(text), 1), 3500):
                await self.bot.send_message(chat_id=int(msg.chat_id),
                                            text=text[i:i + 3500])
            return True
        except Exception as exc:
            log.warning("Send failed to %s (%s): %s", msg.chat_id, msg.key, exc)
            return False


class CollectingMessenger:
    """Demo/test messenger — collects instead of sending."""

    def __init__(self) -> None:
        self.sent: list[OutboxMessage] = []

    async def send(self, msg: OutboxMessage) -> bool:
        if not msg.chat_id:
            return False
        self.sent.append(msg)
        return True

    def by_level(self) -> dict[str, list[OutboxMessage]]:
        out: dict[str, list[OutboxMessage]] = {}
        for m in self.sent:
            out.setdefault(m.level, []).append(m)
        return out
