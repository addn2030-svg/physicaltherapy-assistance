"""KB governance tests — manifest filtering, citations, coverage levels."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_base import KBResult, KnowledgeBase, coverage_label


def _write_kb(tmp_path: Path, with_manifest: bool = True) -> Path:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    (kb_dir / "sop.txt").write_text(
        "Equipment Request Process: staff fills the form, supervisor signs, "
        "Section Head approves, then Biomedical fulfils the request.",
        encoding="utf-8",
    )
    (kb_dir / "old-policy.txt").write_text(
        "Old equipment policy from 2020, superseded.",
        encoding="utf-8",
    )
    if with_manifest:
        manifest = [
            {"file": "sop.txt", "version": "2.1", "approved_by": "Section Head",
             "date": "2026-09-01", "status": "Active"},
            {"file": "old-policy.txt", "version": "1.0", "approved_by": "Former Head",
             "date": "2020-01-01", "status": "Archived"},
        ]
        (kb_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return kb_dir


def test_manifest_filters_inactive(tmp_path):
    kb = KnowledgeBase(knowledge_dir=_write_kb(tmp_path))
    assert kb.files_indexed == ["sop.txt"]
    assert kb.skipped_inactive == ["old-policy.txt [Archived]"]
    assert "Archived" in kb.status()
    assert "unversioned" not in kb.status()


def test_citation_carries_version(tmp_path):
    kb = KnowledgeBase(knowledge_dir=_write_kb(tmp_path))
    results = kb.search("equipment request process")
    assert results
    assert results[0].citation == "sop.txt v2.1 (approved: Section Head, 2026-09-01)"
    ctx = kb.context_for("equipment request process")
    assert "sop.txt v2.1" in ctx


def test_no_manifest_marks_unversioned(tmp_path):
    kb = KnowledgeBase(knowledge_dir=_write_kb(tmp_path, with_manifest=False))
    assert sorted(kb.files_indexed) == ["old-policy.txt", "sop.txt"]
    assert "unversioned" in kb.status()


def test_coverage_levels():
    assert coverage_label([])[0] == "None"
    assert coverage_label([KBResult("a", "s", 0.9)])[0] == "High"
    assert coverage_label([KBResult("a", "s", 0.45)])[0] == "Medium"
    assert coverage_label([KBResult("a", "s", 0.1)])[0] == "Low"
    assert "Section Head" in coverage_label([])[1]
