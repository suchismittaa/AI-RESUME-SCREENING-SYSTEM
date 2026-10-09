"""Ingestion: find resume files and turn each into plain text plus embedded hyperlinks."""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

for _n in ("pypdf", "pdfminer", "pdfplumber"):  # third-party PDF libs are noisy on slightly malformed files
    logging.getLogger(_n).setLevel(logging.ERROR)


class UnreadableResume(Exception):
    """Raised when a file cannot yield usable text (corrupt, encrypted, scanned image, empty)."""


@dataclass
class RawResume:
    path: Path
    text: str
    links: list[str] = field(default_factory=list)  # hyperlink targets (URIs / mailto:) found in the document


def discover(input_dir: Path, extensions: tuple[str, ...]) -> list[Path]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    files = [p for p in sorted(input_dir.rglob("*")) if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith(".")]
    return files


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", " ").replace("•", "•")
    text = re.sub(r"[​‌‍﻿]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def content_hash(text: str) -> str:
    canon = re.sub(r"\W+", "", text.lower())
    return hashlib.sha1(canon.encode()).hexdigest()


def _looks_degraded(text: str) -> bool:
    """Detect extraction artefacts: letter-spaced text ("P y t h o n") or one-word-per-line output."""
    lines = text.split("\n")
    if not lines:
        return True
    blank_ratio = sum(1 for l in lines if not l.strip() or l == " ") / len(lines)
    spaced_runs = len(re.findall(r"(?:\b\w ){6,}\w\b", text))
    return blank_ratio > 0.25 or spaced_runs > 10


def _plumber_text(path: Path) -> str:
    import pdfplumber  # fallback extractor: uses glyph geometry, so it recovers word spacing

    with pdfplumber.open(str(path)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def _read_pdf(path: Path) -> RawResume:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                raise UnreadableResume("PDF is password-protected")
        except UnreadableResume:
            raise
        except Exception as e:
            raise UnreadableResume(f"PDF encrypted and could not be decrypted: {e}")
    pages, links = [], []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # one bad page must not lose the whole resume
            pages.append("")
        try:
            for annot in page.get("/Annots") or []:
                action = annot.get_object().get("/A") or {}
                uri = action.get("/URI")
                if uri:
                    links.append(str(uri).strip())
        except Exception:
            continue
    text = "\n".join(pages)
    if _looks_degraded(text):
        try:
            alt = _plumber_text(path)
            if len(alt.strip()) >= 0.5 * len(re.sub(r"\s+", "", text)) and not _looks_degraded(alt):
                text = alt
        except Exception:  # fallback is best-effort; keep the pypdf text
            pass
    return RawResume(path, text, links)


def _read_docx(path: Path) -> RawResume:
    import docx  # python-docx, optional dependency

    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    links = [r.target_ref for r in d.part.rels.values() if r.reltype.endswith("/hyperlink")]
    return RawResume(path, "\n".join(parts), links)


def read_resume(path: Path, min_chars: int = 200) -> RawResume:
    """Read one resume. Raises UnreadableResume (never anything else) so the batch can continue."""
    try:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            raw = _read_pdf(path)
        elif suffix == ".docx":
            raw = _read_docx(path)
        else:
            raw = RawResume(path, path.read_text(errors="ignore"), [])
    except UnreadableResume:
        raise
    except Exception as e:
        raise UnreadableResume(f"{type(e).__name__}: {e}") from e
    raw.text = normalize_text(raw.text)
    if len(raw.text) < min_chars:
        raise UnreadableResume(f"Only {len(raw.text)} characters of text extracted (empty or scanned image; OCR not supported)")
    return raw
