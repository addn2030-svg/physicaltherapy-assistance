"""Safety guardrails for Rehab RCH Agent v2.

The agent is strictly OPERATIONAL. It must never process patient
information (PHI). Every inbound user message is screened here before
it reaches Gemini, the knowledge base, or Google Drive.

Blocked categories:
  - Patient names / identifiers (MRN, national ID, phone, DOB, bed no.)
  - Medical records, diagnoses, ICD codes
  - Treatment details, medications, dosages
  - Clinical notes / symptoms tied to an identifiable person

When blocked, the bot refuses and asks the user to resubmit a
de-identified operational request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BLOCK_MESSAGE = (
    "⛔ *This request can't be processed.*\n\n"
    "The Rehab RCH Agent handles *operational, non-patient* requests only. "
    "Your message appears to contain patient information, which is not allowed.\n\n"
    "*Please resubmit a de-identified operational request.* Examples:\n"
    "• `What is the process for equipment request?`\n"
    "• `Show rehabilitation escalation path.`\n"
    "• `Draft announcement about annual leave coverage.`\n\n"
    "Blocked: patient names, MRNs, medical records, diagnoses, treatment details."
)

# --- Keyword signals (case-insensitive) ------------------------------------
_KEYWORDS = [
    # Identifiers
    "patient name", "patient is", "pt name", "mrn", "medical record number",
    "medical record no", "file number", "hospital number",
    # Clinical content
    "diagnosis", "diagnosed", "diagnostic report", "icd", "icd-10", "icd10",
    "treatment details", "treatment plan for patient", "clinical note",
    "clinical notes", "progress note", "discharge summary", "operative report",
    "history of present illness", "past medical history", "chief complaint",
    "medication list", "dosage", "mg/d", "mg / day",
    # Explicit PHI markers
    "date of birth is", "dob is", "saudi id", "national id is", "iqama",
]

# --- Regex signals ----------------------------------------------------------
_PATTERNS: list[tuple[str, str]] = [
    (r"\bmrn\s*[:#-]?\s*\d{3,}", "MRN-like number"),
    (r"\bmedical\s+record\s*(no|number|#)?\s*[:#-]?\s*\d{3,}", "medical record number"),
    (r"\bfile\s*(no|number)\s*[:#-]?\s*\d{4,}", "file number"),
    (r"\b[12]\d{9}\b", "10-digit national-ID-like number"),
    (r"\b(?:\+?966|0)?\s?5\d{8}\b", "Saudi phone-like number"),
    (r"\bdiagnos(?:is|ed|es)\b.{0,40}\b(?:with|as|of)\b", "diagnosis statement"),
    (r"\bicd[-\s]?10?\s*[:#-]?\s*[A-Z]\d{2}", "ICD code"),
    (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b.{0,30}\b(?:dob|birth|diagnos|patient)\b", "date tied to patient context"),
    (r"\b(?:dob|date of birth)\b\s*[:#-]?\s*\d", "date of birth value"),
    (r"\b\d+\s?mg\b.{0,30}\b(?:daily|bid|tid|qid|od|bd|tds|patient)\b", "medication dosage instruction"),
    (r"\bbed\s*(no|number)\s*[:#-]?\s*\w*\d+", "bed number reference"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in _PATTERNS]


@dataclass
class SafetyResult:
    blocked: bool
    reasons: list[str]


def contains_phi(text: str) -> SafetyResult:
    """Return whether `text` looks like it contains PHI.

    This is a conservative keyword + pattern screen, not a clinical NLP
    model. False positives are acceptable: the user is asked to rephrase.
    """
    if not text or not text.strip():
        return SafetyResult(blocked=False, reasons=[])

    lowered = text.lower()
    reasons: list[str] = []

    for kw in _KEYWORDS:
        if kw in lowered:
            reasons.append(f"keyword: '{kw}'")

    for rx, label in _COMPILED:
        if rx.search(text):
            reasons.append(f"pattern: {label}")

    # Heuristic: "patient <Name>" with a capitalized two-word name.
    if re.search(r"\bpatient\s+[A-Z][a-z]+\s+[A-Z][a-z]+", text):
        reasons.append("pattern: 'patient <Name>'")

    return SafetyResult(blocked=bool(reasons), reasons=reasons)


def is_safe(text: str) -> bool:
    return not contains_phi(text).blocked
