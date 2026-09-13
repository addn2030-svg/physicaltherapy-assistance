"""Knowledge base for Rehab RCH Agent v2.

Reads APPROVED department documents only (SOPs, guidelines, structure,
contacts, policies, meeting minutes, announcements). Never upload patient
records, MRNs, diagnostic reports, clinical notes, or any PHI.

Supported local formats: .pdf, .docx, .xlsx, .csv, .md, .txt
Search: lightweight keyword scoring (no embeddings → $0 cost).
Optional: sync from the Google Drive "Knowledge Base" folder.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import settings

log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".csv", ".md", ".txt"}

TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


@dataclass
class KBChunk:
    source: str
    text: str
    tokens: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.tokens = set(TOKEN_RE.findall(self.text.lower()))


@dataclass
class KBResult:
    source: str
    snippet: str
    score: float


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        log.warning("PDF read failed for %s: %s", path.name, exc)
        return ""


def _read_docx(path: Path) -> str:
    try:
        import docx

        doc = docx.Document(str(path))
        paras = [p.text for p in doc.paragraphs]
        tables = [" | ".join(c.text for c in row.cells) for t in doc.tables for row in t.rows]
        return "\n".join(paras + tables)
    except Exception as exc:
        log.warning("DOCX read failed for %s: %s", path.name, exc)
        return ""


def _read_xlsx(path: Path) -> str:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        lines: list[str] = []
        for ws in wb.worksheets:
            lines.append(f"[{ws.title}]")
            for row in ws.iter_rows(values_only=True):
                vals = [str(v).strip() for v in row if v not in (None, "")]
                if vals:
                    lines.append(" | ".join(vals))
        wb.close()
        return "\n".join(lines)
    except Exception as exc:
        log.warning("XLSX read failed for %s: %s", path.name, exc)
        return ""


def _read_csv(path: Path) -> str:
    try:
        lines: list[str] = []
        with path.open(encoding="utf-8", errors="ignore", newline="") as f:
            for row in csv.reader(f):
                vals = [v.strip() for v in row if v.strip()]
                if vals:
                    lines.append(" | ".join(vals))
        return "\n".join(lines)
    except Exception as exc:
        log.warning("CSV read failed for %s: %s", path.name, exc)
        return ""


READERS = {
    ".pdf": _read_pdf,
    ".docx": _read_docx,
    ".xlsx": _read_xlsx,
    ".csv": _read_csv,
    ".md": _read_txt,
    ".txt": _read_txt,
}


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks on paragraph boundaries."""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= chunk_size:
        return [text] if text else []
    paras = text.split("\n\n")
    chunks, current = [], ""
    for para in paras:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # overlap: carry tail of previous chunk
            current = (current[-overlap:] + "\n\n" + para) if current else para
            if len(current) > chunk_size + overlap:
                # hard split very long paragraph
                for i in range(0, len(current), chunk_size):
                    chunks.append(current[i : i + chunk_size])
                current = ""
    if current:
        chunks.append(current)
    return [c.strip() for c in chunks if c.strip()]


class KnowledgeBase:
    """Local-file knowledge base with keyword search."""

    def __init__(self, knowledge_dir: Optional[Path] = None) -> None:
        self.dir = knowledge_dir or settings.knowledge_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.chunks: list[KBChunk] = []
        self.files_indexed: list[str] = []
        self.index()

    # -- indexing ---------------------------------------------------------
    def index(self) -> int:
        self.chunks = []
        self.files_indexed = []
        for path in sorted(self.dir.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            text = READERS[path.suffix.lower()](path)
            text = text.strip()
            if not text:
                continue
            for chunk in chunk_text(text):
                self.chunks.append(KBChunk(source=path.name, text=chunk))
            self.files_indexed.append(path.name)
        log.info("KB indexed %d files, %d chunks.", len(self.files_indexed), len(self.chunks))
        return len(self.chunks)

    # -- search -----------------------------------------------------------
    def search(self, query: str, top_k: int = 4) -> list[KBResult]:
        qtokens = set(TOKEN_RE.findall(query.lower()))
        if not qtokens or not self.chunks:
            return []
        scored: list[tuple[float, KBChunk]] = []
        for chunk in self.chunks:
            overlap = qtokens & chunk.tokens
            if not overlap:
                continue
            # score: coverage of query + density bonus for rare overlap
            score = len(overlap) / max(len(qtokens), 1)
            score += 0.1 * min(len(overlap), 5) / max(len(chunk.tokens), 1) * 100 * 0.01
            # phrase bonus
            if query.lower().strip() in chunk.text.lower():
                score += 0.5
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[KBResult] = []
        for score, chunk in scored[:top_k]:
            snippet = chunk.text[:600].strip()
            results.append(KBResult(source=chunk.source, snippet=snippet, score=round(score, 3)))
        return results

    def context_for(self, query: str, top_k: int = 4, max_chars: int = 4000) -> str:
        results = self.search(query, top_k=top_k)
        if not results:
            return ""
        parts = [f"[Source: {r.source}]\n{r.snippet}" for r in results]
        context = "\n\n---\n\n".join(parts)
        return context[:max_chars]

    # -- helpers -----------------------------------------------------------
    def add_text_file(self, filename: str, content: str) -> Path:
        path = self.dir / filename
        path.write_text(content, encoding="utf-8")
        self.index()
        return path

    def status(self) -> str:
        if not self.files_indexed:
            return (
                "📚 Knowledge base is empty.\nUpload approved files "
                "(SOP.pdf, Department Guideline.docx, Rehabilitation Structure.pdf, "
                "Contacts.xlsx) to the `knowledge/` folder or the Drive Knowledge Base folder."
            )
        lines = [f"📚 Knowledge base: {len(self.files_indexed)} file(s), {len(self.chunks)} chunks."]
        for name in self.files_indexed[:20]:
            lines.append(f"• {name}")
        return "\n".join(lines)


# Singleton (lazy-indexed)
kb = KnowledgeBase()
