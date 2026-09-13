#!/usr/bin/env python3
"""Rehab RCH Agent v2 — Telegram entry point.

Staff → Telegram → Rehab RCH Agent → Gemini AI → Google Drive

Commands:
    /start        — welcome + auth check
    /help         — command reference
    /report       — guided operational report → .docx → Google Drive
    /announcement — guided announcement draft → optional Drive save
    /sop          — search SOPs / guidelines ("/sop equipment request")
    /meeting      — guided meeting-minutes builder → Drive save
    /save         — save last generated document to Google Drive
    /kb           — knowledge-base status (admin: "/kb reload")
    /cancel       — cancel current guided flow

Free-text questions from authorized staff are answered with Gemini +
knowledge-base context. Every message is screened for PHI first.
"""

from __future__ import annotations

import html
import logging
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from auth import ACCESS_DENIED_MESSAGE, staff_auth
from config import settings
from gemini_client import gemini
from google_drive import drive
from knowledge_base import kb
from report_generator import (
    build_announcement,
    build_meeting_minutes,
    build_monthly_report,
    build_operational_report,
    build_weekly_report,
)
from safety import BLOCK_MESSAGE, contains_phi

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    level=getattr(logging, settings.log_level, logging.INFO),
)
log = logging.getLogger("rehab-rch-agent")

# ----------------------------------------------------------------------------
# Conversation states
# ----------------------------------------------------------------------------
(REPORT_TYPE, REPORT_NOTES,
 ANN_DETAILS, ANN_CONFIRM,
 MEET_NOTES, MEET_TITLE) = range(6)

WELCOME = """🏥 *Rehab RCH Agent v2*
{dept}

Assalamu alaikum{staff}! I help Rehabilitation Department staff with:

✅ Department questions (SOPs, processes, escalation)
✅ Announcement drafts
✅ Meeting summaries
✅ Operational reports → auto-saved to Google Drive
✅ Approved document search

Type /help for commands, or just ask a question.

⚠️ *Operational use only — no patient information.*
"""

HELP_TEXT = """🏥 *Rehab RCH Agent — Commands*

/start — Welcome & access check
/help — This reference
/report — Generate operational report (weekly / monthly / operational)
/announcement — Draft an announcement
/sop <question> — Search SOPs & guidelines
  e.g. `/sop What is the process for equipment request?`
/meeting — Build meeting minutes from raw notes
/save — Save last document to Google Drive
/kb — Knowledge-base status
/cancel — Cancel current flow

*Free text:* just ask, e.g.
• `Show rehabilitation escalation path.`
• `Draft announcement about annual leave coverage.`

⛔ Blocked: patient names, MRNs, medical records, diagnoses,
treatment details. Resubmit a de-identified operational request.
"""

REPORT_MENU = """📊 *Generate operational report*

Which type?
• `weekly` — Weekly Rehabilitation Operations Summary
• `monthly` — Monthly Rehabilitation Operations Report
• `operational` — General operational report

Reply with one of: weekly / monthly / operational
(/cancel to stop)"""


# ----------------------------------------------------------------------------
# Decorators
# ----------------------------------------------------------------------------
def authorized_only(handler: Callable) -> Callable:
    """Block unauthorized Telegram users before running the handler."""

    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None or not staff_auth.is_authorized(user.id):
            log.warning("Denied access for telegram_id=%s", getattr(user, "id", "?"))
            if update.effective_message:
                await update.effective_message.reply_text(
                    "🔒 Access denied.\n\nContact Rehabilitation Section Head.",
                )
            return ConversationHandler.END if "END" in str(handler) else None
        return await handler(update, context, *args, **kwargs)

    return wrapper


def phi_guarded_text(text: str) -> bool:
    """True when text is blocked (caller should abort the flow)."""
    return contains_phi(text).blocked


async def _reply_phi_blocked(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ This request can't be processed.\n\n"
            "The Rehab RCH Agent handles operational, non-patient requests only. "
            "Your message appears to contain patient information.\n\n"
            "Please resubmit a de-identified operational request.",
        )


# ----------------------------------------------------------------------------
# Basic commands
# ----------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    assert user is not None
    staff = staff_auth.get_staff(user.id)
    if staff is None:
        await update.message.reply_text(  # type: ignore[union-attr]
            "🔒 Access denied.\n\nContact Rehabilitation Section Head."
        )
        return
    await update.message.reply_text(  # type: ignore[union-attr]
        WELCOME.format(dept=settings.department_name, staff=f", {staff.name}"),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not staff_auth.is_authorized(update.effective_user.id):  # type: ignore[union-attr]
        await update.message.reply_text("🔒 Access denied.\n\nContact Rehabilitation Section Head.")  # type: ignore[union-attr]
        return
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Type /help for commands.")  # type: ignore[union-attr]
    return ConversationHandler.END


@authorized_only
async def cmd_kb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if args and args[0].lower() == "reload":
        kb.index()
        await update.message.reply_text(f"🔄 Knowledge base reloaded.\n\n{kb.status()}")  # type: ignore[union-attr]
    else:
        await update.message.reply_text(kb.status())  # type: ignore[union-attr]


@authorized_only
async def cmd_sop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args or []).strip()
    if not query:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Usage: /sop <question>\nExample: /sop What is the process for equipment request?"
        )
        return
    if phi_guarded_text(query):
        await _reply_phi_blocked(update)
        return
    await update.message.reply_text("🔍 Searching approved department documents…")  # type: ignore[union-attr]
    ctx = kb.context_for(query)
    answer = gemini.explain_sop(query, ctx) if ctx else gemini.answer_question(query)
    sources = "\n".join(f"📄 {r.source}" for r in kb.search(query, top_k=3))
    reply = f"{answer}\n\n"
    if sources:
        reply += f"*Sources:*\n{sources}\n\n"
    elif not kb.files_indexed:
        reply += "_No knowledge-base files indexed yet — _\n\n"
    reply += "_Draft for review — Rehabilitation Department, RCH._"
    await _send_long(update, reply)


@authorized_only
async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    last = context.user_data.get("last_file")
    folder = context.user_data.get("last_folder", "Reports/Weekly")
    if not last or not Path(str(last)).exists():
        await update.message.reply_text("Nothing to save yet. Generate a /report, /announcement, or /meeting first.")  # type: ignore[union-attr]
        return
    await update.message.reply_text("💾 Saving to Google Drive…")  # type: ignore[union-attr]
    result = drive.upload_file(Path(str(last)), folder_key=folder)
    msg = result["message"]
    if result.get("drive_link"):
        msg += f"\n🔗 {result['drive_link']}"
    await update.message.reply_text(msg)  # type: ignore[union-attr]


# ----------------------------------------------------------------------------
# /report flow
# ----------------------------------------------------------------------------
@authorized_only
async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(REPORT_MENU, parse_mode=ParseMode.MARKDOWN)  # type: ignore[union-attr]
    return REPORT_TYPE


async def report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = (update.message.text or "").strip().lower()  # type: ignore[union-attr]
    if phi_guarded_text(choice):
        await _reply_phi_blocked(update)
        return ConversationHandler.END
    if choice not in {"weekly", "monthly", "operational"}:
        await update.message.reply_text("Please reply with: weekly / monthly / operational (/cancel to stop).")  # type: ignore[union-attr]
        return REPORT_TYPE
    context.user_data["report_type"] = choice
    await update.message.reply_text(  # type: ignore[union-attr]
        f"📝 Send bullet notes for the *{choice}* report (or type `skip`).\n"
        "Example:\n`• OPD coverage stable\n• 2 devices pending maintenance\n• Leave requests for next week`",
        parse_mode=ParseMode.MARKDOWN,
    )
    return REPORT_NOTES


async def report_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    notes = (update.message.text or "").strip()  # type: ignore[union-attr]
    if phi_guarded_text(notes):
        await _reply_phi_blocked(update)
        return ConversationHandler.END
    rtype = context.user_data.get("report_type", "weekly")
    staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
    prepared_by = staff.display() if staff else "Rehab RCH Agent"

    await update.message.reply_text("🤖 Drafting report with Gemini…")  # type: ignore[union-attr]
    ctx = kb.context_for(f"{rtype} rehabilitation operations report")
    body = gemini.generate_report(rtype, notes if notes.lower() != "skip" else "", context=ctx)

    builders = {
        "weekly": (build_weekly_report, "Reports/Weekly"),
        "monthly": (build_monthly_report, "Reports/Monthly"),
        "operational": (build_operational_report, "Reports"),
    }
    builder, folder = builders[rtype]
    if rtype == "operational":
        path = builder(body, title="Rehabilitation Operational Report", prepared_by=prepared_by)  # type: ignore[operator]
    else:
        path = builder(body, prepared_by=prepared_by)  # type: ignore[operator]
    context.user_data["last_file"] = str(path)
    context.user_data["last_folder"] = folder

    await _send_long(update, f"Draft for review\n\n{body}\n\n_Saving to Google Drive…_")

    result = drive.upload_file(path, folder_key=folder)
    msg = result["message"]
    if result.get("drive_link"):
        msg += f"\n🔗 {result['drive_link']}"
    await update.message.reply_text(msg)  # type: ignore[union-attr]
    # Also send the .docx file to chat
    try:
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, filename=Path(path).name)  # type: ignore[union-attr]
    except Exception as exc:
        log.warning("Could not send docx to chat: %s", exc)
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# /announcement flow
# ----------------------------------------------------------------------------
@authorized_only
async def ann_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(  # type: ignore[union-attr]
        "📢 *New announcement*\n\nSend the announcement details.\n"
        "Example: `Staff meeting Tuesday at 09:00 in the Rehab conference room`"
        "\n(/cancel to stop)",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ANN_DETAILS


async def ann_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = (update.message.text or "").strip()  # type: ignore[union-attr]
    if phi_guarded_text(details):
        await _reply_phi_blocked(update)
        return ConversationHandler.END
    await update.message.reply_text("🤖 Drafting announcement…")  # type: ignore[union-attr]
    draft = gemini.draft_announcement(details)
    context.user_data["ann_draft"] = draft
    context.user_data["ann_subject"] = details[:60]
    await _send_long(update, f"Draft for review\n\n{draft}\n\nSave to Drive? Reply `yes` or `no`.")
    return ANN_CONFIRM


async def ann_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = (update.message.text or "").strip().lower()  # type: ignore[union-attr]
    if choice not in {"yes", "y", "no", "n"}:
        await update.message.reply_text("Reply `yes` to save to Drive, or `no` to discard.")  # type: ignore[union-attr]
        return ANN_CONFIRM
    if choice.startswith("y"):
        staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
        prepared_by = staff.display() if staff else "Rehab RCH Agent"
        path = build_announcement(
            context.user_data.get("ann_draft", ""),
            subject=context.user_data.get("ann_subject", "Department Announcement"),
            prepared_by=prepared_by,
        )
        context.user_data["last_file"] = str(path)
        context.user_data["last_folder"] = "Announcements"
        result = drive.upload_file(path, folder_key="Announcements", dated_subfolders=False)
        msg = result["message"]
        if result.get("drive_link"):
            msg += f"\n🔗 {result['drive_link']}"
        await update.message.reply_text(msg)  # type: ignore[union-attr]
        try:
            with open(path, "rb") as f:
                await update.message.reply_document(document=f, filename=Path(path).name)  # type: ignore[union-attr]
        except Exception as exc:
            log.warning("Could not send docx to chat: %s", exc)
    else:
        await update.message.reply_text("Discarded. Type /announcement to start over.")  # type: ignore[union-attr]
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# /meeting flow
# ----------------------------------------------------------------------------
@authorized_only
async def meet_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(  # type: ignore[union-attr]
        "🗒️ *Meeting minutes builder*\n\nSend the meeting title (or type `skip`).\n(/cancel to stop)",
        parse_mode=ParseMode.MARKDOWN,
    )
    return MEET_TITLE


async def meet_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = (update.message.text or "").strip()  # type: ignore[union-attr]
    if phi_guarded_text(title):
        await _reply_phi_blocked(update)
        return ConversationHandler.END
    context.user_data["meet_title"] = "" if title.lower() == "skip" else title
    await update.message.reply_text("Now paste the raw meeting notes / bullet points.")  # type: ignore[union-attr]
    return MEET_NOTES


async def meet_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    notes = (update.message.text or "").strip()  # type: ignore[union-attr]
    if phi_guarded_text(notes):
        await _reply_phi_blocked(update)
        return ConversationHandler.END
    staff = staff_auth.get_staff(update.effective_user.id)  # type: ignore[union-attr]
    prepared_by = staff.display() if staff else "Rehab RCH Agent"
    title = context.user_data.get("meet_title") or f"Staff Meeting {datetime.now():%d %b %Y}"

    await update.message.reply_text("🤖 Summarizing meeting…")  # type: ignore[union-attr]
    minutes = gemini.summarize_meeting(notes)
    path = build_meeting_minutes(minutes, title=title, prepared_by=prepared_by)
    context.user_data["last_file"] = str(path)
    context.user_data["last_folder"] = "Meeting Minutes"

    await _send_long(update, f"Draft for review\n\n{minutes}\n\n_Saving to Google Drive…_")
    result = drive.upload_file(path, folder_key="Meeting Minutes", dated_subfolders=False)
    msg = result["message"]
    if result.get("drive_link"):
        msg += f"\n🔗 {result['drive_link']}"
    await update.message.reply_text(msg)  # type: ignore[union-attr]
    try:
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, filename=Path(path).name)  # type: ignore[union-attr]
    except Exception as exc:
        log.warning("Could not send docx to chat: %s", exc)
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# Free-text Q&A
# ----------------------------------------------------------------------------
@authorized_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()  # type: ignore[union-attr]
    if not text:
        return
    if phi_guarded_text(text):
        await _reply_phi_blocked(update)
        return
    ctx = kb.context_for(text)
    answer = gemini.answer_question(text, context=ctx)
    await _send_long(update, answer)


async def _send_long(update: Update, text: str, chunk: int = 3500) -> None:
    """Send long replies split into Telegram-safe chunks."""
    assert update.message is not None
    for i in range(0, max(len(text), 1), chunk):
        await update.message.reply_text(text[i : i + chunk])


# ----------------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------------
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Update %s caused error: %s", update, context.error)
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again or type /help."
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# App factory
# ----------------------------------------------------------------------------
def build_app() -> Application:
    if not settings.has_telegram:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and add your token."
        )
    app = Application.builder().token(settings.telegram_bot_token).build()

    report_conv = ConversationHandler(
        entry_points=[CommandHandler("report", report_start)],
        states={
            REPORT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_type)],
            REPORT_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_notes)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )
    ann_conv = ConversationHandler(
        entry_points=[CommandHandler("announcement", ann_start)],
        states={
            ANN_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_details)],
            ANN_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )
    meet_conv = ConversationHandler(
        entry_points=[CommandHandler("meeting", meet_start)],
        states={
            MEET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, meet_title)],
            MEET_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, meet_notes)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("sop", cmd_sop))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("kb", cmd_kb))
    app.add_handler(report_conv)
    app.add_handler(ann_conv)
    app.add_handler(meet_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(on_error)
    return app


def main() -> None:
    log.info("Starting Rehab RCH Agent v2 | dept=%s | kb_files=%d | gemini_demo=%s | drive_demo=%s",
             settings.department_name, len(kb.files_indexed), gemini.demo_mode, drive.demo_mode)
    log.info("Staff source=%s count=%d", staff_auth.source, staff_auth.count())
    drive.ensure_folder_structure()
    build_app().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
