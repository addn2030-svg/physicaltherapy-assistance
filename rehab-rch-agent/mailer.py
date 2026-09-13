"""Agent v4.2 email sender — plain SMTP, stdlib only.

Disabled unless SMTP_HOST + SMTP_FROM are configured. All sends are
fail-soft (log + audit, never raise) so a mail outage can't break the bot.
Staff addresses come from Staff_Register.Email; operational content only —
never PHI (same rule as Telegram).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from config import settings

log = logging.getLogger("mail")


def email_configured() -> bool:
    """True when the admin enabled mail AND set host + from address."""
    return bool(settings.email_enabled and settings.smtp_host
                and settings.smtp_from)


def build_message(to_addrs: list[str], subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = f"[Rehab RCH] {subject}"
    msg.set_content(body)
    return msg


def send_email(to: str | list[str], subject: str, body: str) -> bool:
    """Send one email. Returns True on success, False when disabled/failing."""
    from audit import audit  # lazy: avoid import cycles

    if not email_configured():
        log.debug("Email skipped (not configured): %s", subject)
        return False
    addrs = [to] if isinstance(to, str) else list(to)
    addrs = [a.strip() for a in addrs if a and "@" in a]
    if not addrs:
        return False
    try:
        msg = build_message(addrs, subject, body)
        if settings.smtp_port == 465:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(settings.smtp_host,
                                                  settings.smtp_port,
                                                  timeout=20)
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port,
                                timeout=20)
        with smtp:
            try:
                smtp.starttls()
            except smtplib.SMTPException:
                pass  # server may not advertise TLS (e.g. local relay)
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        audit.log("email_sent", "", "system",
                  f"to={len(addrs)} subj={subject[:100]}")
        return True
    except Exception as exc:
        log.warning("Email send failed (%s); continuing without email.", exc)
        audit.log("email_failed", "", "system",
                  f"subj={subject[:100]} err={exc!r}"[:300])
        return False


def send_staff_email(db, audience: str, subject: str, body: str) -> int:
    """Email a sheet audience (All / Supervisors / unit / name).

    Returns the number of addresses mailed (0 when disabled or none)."""
    if not email_configured():
        return 0
    addrs = db.emails_for_audience(audience)
    if not addrs:
        log.info("No staff emails on file for audience %r.", audience)
        return 0
    return len(addrs) if send_email(addrs, subject, body) else 0
