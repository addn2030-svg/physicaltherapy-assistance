"""Knowledge-base indexing + search tests (uses sample files)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_base import KnowledgeBase


def test_index_and_search(tmp_path):
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "sop.txt").write_text(
        "Equipment Request Process: staff fills the form, supervisor signs, "
        "Section Head approves, then Biomedical fulfils the request.",
        encoding="utf-8",
    )
    (kb_dir / "leave.txt").write_text(
        "Annual leave coverage requires a covering therapist and supervisor approval.",
        encoding="utf-8",
    )
    kb = KnowledgeBase(knowledge_dir=kb_dir)
    assert len(kb.files_indexed) == 2

    results = kb.search("What is the process for equipment request?")
    assert results, "expected at least one search hit"
    assert results[0].source == "sop.txt"

    ctx = kb.context_for("leave coverage")
    assert "leave" in ctx.lower()


def test_empty_query_returns_nothing(tmp_path):
    kb = KnowledgeBase(knowledge_dir=tmp_path)
    assert kb.search("") == []
    assert kb.search("anything") == []
