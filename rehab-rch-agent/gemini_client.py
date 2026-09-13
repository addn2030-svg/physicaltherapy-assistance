"""Gemini AI client for Rehab RCH Agent v2.

Wraps Google's Generative AI SDK with department-specific system prompts.
All generation helpers refuse PHI-flagged input before calling the API.

If ``GEMINI_API_KEY`` is missing, the client runs in demo mode and returns
clearly-labelled template drafts so the Telegram flows can be tested
without spending quota.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from config import settings
from safety import contains_phi

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Rehab RCH Agent, the official AI assistant of the \
Rehabilitation Department at RCH.

Rules:
1. Answer ONLY operational / administrative rehabilitation department questions \
(SOPs, escalation paths, equipment requests, leave coverage, meetings, reports, announcements).
2. NEVER request, repeat, or process patient information: no patient names, MRNs, \
medical records, diagnoses, or treatment details. If the user provides any, refuse \
and ask for a de-identified operational request.
3. Base answers on the provided department knowledge base context when available. \
Cite EVERY factual claim with its source as [Source: filename]. Never invent \
SOP section numbers, names, dates, or procedures not present in the context.
4. If the context does not cover the question, start with the exact line \
"General guidance (not from approved documents):" then give best-practice \
operational guidance for Section Head review. Never present general \
guidance as department policy.
5. Be concise, professional, and structured with headings and bullets.
6. Use British English spelling for clinical-administrative terms where natural \
(e.g. organised) but keep names and titles as given.
7. Every draft ends with: "Draft for review — Rehabilitation Department, RCH."
"""

DEMO_BANNER = "_Demo mode — set GEMINI_API_KEY for full AI generation._\n\n"


class GeminiClient:
    """Thin wrapper around google-generativeai with safe defaults."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model_name = model or settings.gemini_model
        self._model = None
        if self.api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={
                        "temperature": settings.gemini_temperature,
                        "max_output_tokens": settings.gemini_max_tokens,
                    },
                )
                log.info("Gemini model initialised: %s", self.model_name)
            except Exception as exc:
                log.warning("Gemini init failed (%s); falling back to demo mode.", exc)
                self._model = None
        else:
            log.warning("GEMINI_API_KEY not set — running in demo mode.")

    @property
    def demo_mode(self) -> bool:
        return self._model is None

    # -- core -------------------------------------------------------------
    def generate(self, prompt: str, context: str = "") -> str:
        """Generate text. Returns a refusal when PHI is detected."""
        phi = contains_phi(prompt + "\n" + context)
        if phi.blocked:
            log.warning("Blocked PHI in generation request: %s", phi.reasons)
            return (
                "⛔ I can't process this request because it appears to contain "
                "patient information. Please resubmit a de-identified operational "
                "request (no patient names, MRNs, diagnoses, or treatment details)."
            )
        if self._model is None:
            return self._demo_response(prompt)
        try:
            full = f"Knowledge base context:\n{context}\n\nRequest:\n{prompt}" if context else prompt
            resp = self._model.generate_content(full)
            text = (getattr(resp, "text", "") or "").strip()
            return text or "I couldn't generate a response. Please try again."
        except Exception as exc:
            log.exception("Gemini generation failed: %s", exc)
            return (
                "⚠️ The AI service is temporarily unavailable. "
                "Please try again in a moment."
            )

    # -- task helpers ------------------------------------------------------
    def answer_question(self, question: str, context: str = "") -> str:
        prompt = (
            "Answer this Rehabilitation Department operational question. "
            "When knowledge base context is provided, cite the source document "
            "name(s) for every factual claim as [Source: filename]. When no "
            "context is provided, begin with 'General guidance (not from "
            "approved documents):'.\n\n"
            f"Question: {question}"
        )
        return self.generate(prompt, context=context)

    def draft_announcement(self, details: str) -> str:
        prompt = (
            "Draft a professional department announcement from these details. "
            "Use memo style: Title, Date, To (Rehabilitation Department Team), "
            "From (Rehabilitation Section Head), Body, Action required, Contact.\n\n"
            f"Details: {details}\nDate: {datetime.now().strftime('%d %b %Y')}"
        )
        return self.generate(prompt)

    def summarize_meeting(self, notes: str) -> str:
        prompt = (
            "Turn these raw meeting notes into formal Rehabilitation Department "
            "meeting minutes with: Attendees (if given), Agenda, Discussion Summary, "
            "Decisions, Action Items (owner + due date), Next Meeting.\n\n"
            f"Notes:\n{notes}"
        )
        return self.generate(prompt)

    def generate_report(self, report_type: str, notes: str = "", context: str = "") -> str:
        prompt = (
            f"Generate a {report_type} Rehabilitation Operations report with: "
            "Status Overview, Key Activities, Staffing & Coverage, Equipment & Resources, "
            "Issues & Risks, Decisions Required, Next Actions. Professional tone, "
            "bullet points, no patient information.\n\n"
            f"Input notes:\n{notes or '(no notes provided — use general operational structure)'}"
        )
        return self.generate(prompt, context=context)

    def explain_sop(self, query: str, context: str) -> str:
        prompt = (
            "Answer strictly from the SOP / guideline context below. "
            "Give step-by-step process, responsible roles, and escalation path, "
            "citing each fact as [Source: filename]. "
            "If the context is insufficient, say exactly what is missing and "
            "do not invent procedures.\n\n"
            f"Question: {query}"
        )
        return self.generate(prompt, context=context)

    # -- demo fallback ------------------------------------------------------
    def _demo_response(self, prompt: str) -> str:
        preview = prompt[:600].replace("\n", " ")
        return (
            DEMO_BANNER
            + "Draft for review\n\n"
            + "This is a template response generated without the Gemini API key. "
            + "Connect `GEMINI_API_KEY` to enable full AI drafting.\n\n"
            + f"Request preview: {preview}\n\n"
            + "Status Overview\n• Department operations continue as scheduled.\n\n"
            + "Decisions Required\n• Section Head review and approval.\n\n"
            + "Next Actions\n• Confirm details and re-run with live AI.\n\n"
            + "Draft for review — Rehabilitation Department, RCH."
        )


# Singleton
gemini = GeminiClient()
