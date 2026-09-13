"""PHI guardrail tests — must never regress: patient data stays blocked."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from safety import contains_phi


def test_allowed_operational_questions():
    for q in [
        "What is the process for equipment request?",
        "Show rehabilitation escalation path.",
        "Draft announcement about annual leave coverage.",
        "Staff meeting Tuesday at 09:00",
        "Generate weekly rehabilitation summary",
    ]:
        assert not contains_phi(q).blocked, q


def test_blocked_mrn():
    assert contains_phi("Patient MRN: 123456 needs review").blocked
    assert contains_phi("mrn 789012").blocked


def test_blocked_diagnosis_and_records():
    assert contains_phi("The patient was diagnosed with stroke, plan?").blocked
    assert contains_phi("Please summarize this medical record number 445566").blocked
    assert contains_phi("Here are the clinical notes for the patient").blocked


def test_blocked_identifiers():
    assert contains_phi("National ID is 1234567890 for this case").blocked
    assert contains_phi("Call patient on 0512345678 about treatment").blocked
    assert contains_phi("Patient Ahmed Mohammed needs treatment details").blocked


def test_empty_is_safe():
    assert not contains_phi("").blocked
    assert not contains_phi("   ").blocked
