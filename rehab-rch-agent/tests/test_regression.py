"""Regression tests for bugs caught by the first demo.py run.

1. KB context containing PHI-words (e.g. "never upload MRNs") must NOT
   block grounded answers — only the user-supplied prompt is screened.
2. Stopwords ("what", "the", ...) must not inflate coverage scores.
3. knowledge/README.md must not be indexed or cited as a source.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gemini_client import GeminiClient
from knowledge_base import KnowledgeBase, coverage_label, tokenize


def test_kb_context_with_phi_words_does_not_block():
    gemini = GeminiClient(api_key="")  # force demo mode
    assert gemini.demo_mode
    out = gemini.generate(
        "What is the process for equipment request?",
        context="[Source: SOP]\nNever upload patient MRNs or clinical notes.",
    )
    assert "Draft for review" in out
    assert "can't process" not in out


def test_user_prompt_with_phi_still_blocked():
    gemini = GeminiClient(api_key="")
    out = gemini.generate("Patient Ahmed Mohammed, MRN 123456 needs a summary")
    assert "can't process" in out


def test_stopwords_not_counted():
    assert tokenize("What is the process for equipment request?") == {
        "process", "equipment", "request",
    }


def test_stopwords_dont_inflate_coverage(tmp_path):
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "sop.txt").write_text(
        "The equipment process for the department.", encoding="utf-8"
    )
    kb = KnowledgeBase(knowledge_dir=kb_dir)
    # Query shares only stopwords + "equipment"/"process" with the doc;
    # "cafeteria menu friday" shares nothing -> no results -> None.
    assert kb.search("What is on the cafeteria menu this Friday?") == []
    assert coverage_label([])[0] == "None"


def test_readme_not_indexed(tmp_path):
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "README.md").write_text("Unique readme marker zzzreadme.", encoding="utf-8")
    (kb_dir / "sop.txt").write_text("Equipment request process.", encoding="utf-8")
    kb = KnowledgeBase(knowledge_dir=kb_dir)
    assert kb.files_indexed == ["sop.txt"]
    assert kb.search("zzzreadme") == []
