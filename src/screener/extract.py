"""Resume text -> ParsedResume: name, email, GitHub usernames, sections, matched skills.

Parsing is heuristic and layout-agnostic: section headers are detected by name (not position), and when
no headers are found the whole document is treated as 'other' (counted as evidence context).
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from . import lexicon as lx
from .ingest import RawResume
from .models import ParsedResume, Section

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
GH_RE = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9\-]{0,38}))(?![A-Za-z0-9\-])", re.I)
GH_RESERVED = {"features", "orgs", "login", "sponsors", "settings", "topics", "marketplace", "about", "pricing", "enterprise", "explore", "notifications", "pulls", "issues", "apps", "collections"}
_ALIAS = {alias: sec for sec, aliases in lx.SECTION_ALIASES.items() for alias in aliases}


def clean_ai_noise(text: str) -> str:
    """Remove 'used AI coding tools' phrasing so it is not mistaken for AI project evidence."""
    return re.sub(lx.AI_NOISE, " ", text, flags=re.I)


# ---------------------------------------------------------------- sections
def _header_key(line: str) -> str | None:
    s = re.sub(r"[^A-Za-z& ]", " ", line).strip().lower()
    s = re.sub(r"\s+", " ", s)
    if not s or len(s) > 45:
        return None
    return _ALIAS.get(s)


_INLINE_HDR = re.compile(
    r"(?<![A-Za-z])(" + "|".join(sorted((re.escape(a.upper()) for a in _ALIAS if len(a) > 4), key=len, reverse=True)) + r")(?![A-Za-z])"
)


def split_sections(text: str) -> list[Section]:
    # Some PDFs flatten the whole resume into one line; ALL-CAPS headers can still be recovered.
    text = _INLINE_HDR.sub(lambda m: "\n" + m.group(1) + "\n", text)
    sections: list[tuple[str, list[str]]] = [("header", [])]
    for line in text.split("\n"):
        key = _header_key(line)
        if key:
            sections.append((key, []))
        else:
            sections[-1][1].append(line)
    out = [Section(name=n, text="\n".join(ls).strip()) for n, ls in sections if "\n".join(ls).strip()]
    # No recognisable headers at all -> treat everything as evidence context.
    if not any(s.name not in ("header",) for s in out):
        return [Section(name="other", text=text)]
    return out


def context_text(sections: list[Section]) -> str:
    """Text that shows what the candidate *built* (projects/experience/summary), excluding skills lists and education."""
    parts = [s.text for s in sections if s.name in lx.CONTEXT_SECTIONS or s.name == "header" and False]
    return "\n".join(parts)


def section_text(sections: list[Section], *names: str) -> str:
    return "\n".join(s.text for s in sections if s.name in names)


# ---------------------------------------------------------------- name / email / github
def extract_email(text: str, links: list[str]) -> str | None:
    for l in links:  # mailto: hyperlinks are more reliable than glyph-polluted text
        if l.lower().startswith("mailto:"):
            m = EMAIL_RE.search(l[7:])
            if m:
                return m.group(0).lower()
    head = text[:1500]
    m = EMAIL_RE.search(head) or EMAIL_RE.search(text)
    return m.group(0).lower() if m else None


def extract_name(text: str, email: str | None, filename: str) -> str:
    for line in text.split("\n")[:8]:
        l = re.split(r"Email|E-mail|Phone|Mobile|Contact|\||@|\d{4,}|http|www\.|linkedin|github|,", line, maxsplit=1, flags=re.I)[0]
        l = re.sub(r"\s+(?:Bengaluru|Bangalore|Hyderabad|Delhi|Mumbai|Pune|Chennai)\b.*$", "", l.strip().strip("|/•·-– "))
        if not l or _header_key(l) or re.search(r"resume|curriculum|vitae", l, re.I):
            continue
        words = l.split()
        if 1 < len(words) <= 5 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", w) for w in words):
            return " ".join(w.capitalize() if w.isupper() else w for w in words)
    if email:
        return re.sub(r"[._\d]+", " ", email.split("@")[0]).title().strip() or Path(filename).stem
    return Path(filename).stem


def extract_github_usernames(text: str, links: list[str]) -> list[str]:
    """All plausible usernames, most likely first (hyperlinks beat visible text; profile links beat repo links)."""
    score: Counter = Counter()
    order: dict[str, int] = {}
    for src, weight in ((links, 3), ([text], 1)):
        for chunk in src:
            for m in GH_RE.finditer(chunk):
                u = m.group(1)
                if u.lower() in GH_RESERVED:
                    continue
                # a bare profile URL (no further path) is the strongest signal
                rest = chunk[m.end(): m.end() + 1]
                bonus = 2 if rest != "/" or chunk[m.end():].strip("/ ") == "" else 0
                score[u] += weight + bonus
                order.setdefault(u, len(order))
    return sorted(score, key=lambda u: (-score[u], order[u]))


# ---------------------------------------------------------------- skills
def match_skills(text: str) -> list[str]:
    clean = clean_ai_noise(text)
    found = []
    for name, pat in lx.SKILLS.items():
        flags = 0 if name in lx.CASE_SENSITIVE_SKILLS else re.I
        if re.search(pat, clean, flags):
            found.append(name)
    return found


def parse_resume(raw: RawResume) -> ParsedResume:
    sections = split_sections(raw.text)
    email = extract_email(raw.text, raw.links)
    return ParsedResume(
        file=raw.path.name,
        candidate_name=extract_name(raw.text, email, raw.path.name),
        email=email,
        github_usernames=extract_github_usernames(raw.text, raw.links),
        text=raw.text,
        sections=sections,
        matched_skills=match_skills(raw.text),
    )
