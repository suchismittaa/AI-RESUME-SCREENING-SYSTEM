"""Hard eligibility filter. Purely rule-based (no LLM): Python evidence AND AI/agentic evidence."""
from __future__ import annotations

import re

from . import lexicon as lx
from .extract import clean_ai_noise, context_text, section_text
from .models import EligibilityResult, ParsedResume

_STRONG_CS = {"RAG"}  # patterns that must be matched case-sensitively


def _hits(patterns: dict[str, str], text: str) -> list[str]:
    out = []
    for name, pat in patterns.items():
        flags = 0 if name in _STRONG_CS else re.I
        if re.search(pat, text, flags):
            out.append(name)
    return out


def python_evidence(resume: ParsedResume) -> list[str]:
    """Python must appear as a real skill / project / work technology, not in coursework or education only."""
    ev = []
    usable = "\n".join(s.text for s in resume.sections if s.name not in ("education", "coursework", "certifications", "achievements"))
    usable = clean_ai_noise(usable)
    if re.search(lx.PYTHON_DIRECT, usable, re.I):
        ev.append("Python")
    implicit = sorted({m.group(0).lower() for m in re.finditer(lx.PYTHON_IMPLICIT, usable, re.I)})
    if not ev and implicit:
        ev.append("Python ecosystem: " + ", ".join(implicit[:4]))
    return ev


def ai_evidence(resume: ParsedResume) -> list[str]:
    """Strong AI/agent frameworks count anywhere; generic LLM-API mentions must appear in projects/experience."""
    full = clean_ai_noise(resume.text)
    ctx = clean_ai_noise(context_text(resume.sections))
    strong = _hits(lx.AI_STRONG, full)
    generic = _hits(lx.AI_GENERIC, ctx)
    # bare "agent" in non-AI contexts (e.g. "user agent", "sales agent") is not evidence on its own
    if strong == ["Multi-Agent"] and not generic and not re.search(r"agentic|multi[- ]?agent|ai agent|llm agent", full, re.I):
        strong = []
    return strong + [g for g in generic if g not in strong]


def check_eligibility(resume: ParsedResume) -> EligibilityResult:
    py = python_evidence(resume)
    ai = ai_evidence(resume)
    reasons = []
    if not py:
        reasons.append("No evidence of Python stack (no Python skill, project, or Python-only framework found outside education/coursework)")
    if not ai:
        classical = re.findall(lx.ML_CLASSICAL, clean_ai_noise(resume.text), re.I)
        if classical:
            reasons.append(
                "No AI/LLM/agentic project evidence (only classical ML/CV: " + ", ".join(sorted({c.lower() for c in classical})[:4]) + ")"
            )
        else:
            reasons.append("No AI/agentic project evidence (no LLM, RAG, agent, embedding, or AI-framework usage found)")
    return EligibilityResult(eligible=not reasons, python_evidence=py, ai_evidence=ai, rejection_reasons=reasons)
