"""Explainability layer: evidence trace, AI project quality level and the recruiter-facing "why this candidate".

Nothing here re-scores a candidate. It *explains* the numbers produced by `scoring.py` / `github.py`:

* every evidence quote is a verbatim line from the resume (verified against the resume text before it is emitted);
* GitHub evidence comes only from the real GitHub enrichment result; failures are reported as failures;
* the AI depth level is derived from the signal groups the deterministic scorer detected in the strongest AI
  project (plus the thin-wrapper / tutorial flags, including the LLM's when one was used). Framework names alone
  never raise the level.
"""
from __future__ import annotations

import re

from . import lexicon as lx
from .config import Settings
from .extract import clean_ai_noise
from .models import (
    AIProjectQuality,
    CategoryEvidence,
    EvidenceItem,
    EvidenceTrace,
    GitHubInfo,
    ParsedResume,
)
from .scoring import BULLET, Scored, _has

AI_LEVELS = {
    0: "No implementation evidence (AI named in skills list only)",
    1: "Thin LLM/API Wrapper",
    2: "Applied AI",
    3: "RAG / AI System",
    4: "Agentic / Advanced AI System",
}
_AGENTIC = {"agentic/tool-use"}  # framework names alone are deliberately not agentic evidence
_SUPPORT = {"retrieval/RAG", "state/memory", "evaluation", "backend integration", "data pipeline"}
_DEEP = {"retrieval/RAG", "state/memory", "evaluation"}  # at least one of these separates an agent system from a scripted demo

_CONTEXT_FIRST = ("projects", "experience", "summary", "other")


# ------------------------------------------------------------------ verbatim quote finding
def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _logical_lines(text: str) -> list[str]:
    """Join wrapped lines into logical bullets/sentences (bullets start a new line; so does a finished sentence)."""
    out: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if not out or BULLET.match(line) or out[-1].endswith((".", "!", "?")):
            out.append(line)
        else:
            out[-1] += " " + line
    pieces: list[str] = []
    for l in out:
        l = BULLET.sub("", l).strip()
        pieces.extend(p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", l) if p.strip()) if len(l) > 260 else pieces.append(l)
    return pieces


class QuoteFinder:
    """Finds verbatim resume sentences matching a pattern, preferring what the candidate built over skills lists."""

    def __init__(self, resume: ParsedResume):
        self.resume = resume
        self._hay = _norm(resume.text)
        by_priority = sorted(resume.sections, key=lambda s: (_CONTEXT_FIRST.index(s.name) if s.name in _CONTEXT_FIRST else 9))
        self.lines: list[tuple[str, str]] = []  # (section, line)
        for sec in by_priority:
            if sec.name in ("education", "coursework", "certifications", "achievements", "header"):
                continue
            for l in _logical_lines(sec.text):
                if 12 <= len(l) <= 300:
                    self.lines.append((sec.name, l))

    def find(self, pattern: str, n: int = 1, cs: bool = False) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for sec, line in self.lines:
            if _has(pattern, clean_ai_noise(line), cs) and _norm(line) in self._hay and line not in (f for _, f in found):
                found.append((sec, line))
                if len(found) >= n:
                    break
        return found

    def locate(self, quote: str) -> str:
        q = _norm(quote)
        for sec in self.resume.sections:
            if q in _norm(sec.text):
                return sec.name
        return "resume"


def _add(items: list[EvidenceItem], signal: str, found: list[tuple[str, str]], cap: int = 6) -> None:
    for sec, text in found:
        for it in items:
            if it.text == text:
                if signal not in it.signal.split(", "):
                    it.signal += f", {signal}"
                break
        else:
            if len(items) < cap:
                items.append(EvidenceItem(signal=signal, text=text, source=sec))


# ------------------------------------------------------------------ category traces
_NOTE = re.compile(r"^(?P<name>.+?): \+(?P<pts>[\d.]+)(?: \((?P<where>[^)]*)\))?")

_PATTERNS = {  # note-name prefix -> lexicon pattern
    "Python": lx.PYTHON_DIRECT + "|" + lx.PYTHON_IMPLICIT,
    "FastAPI": lx.BACKEND["fastapi"],
    "Flask/Django": lx.BACKEND["flask_django"],
    "async": lx.BACKEND["async"],
    "PostgreSQL": lx.BACKEND["postgres"],
    "Redis": lx.BACKEND["redis"],
    "other backend": lx.BACKEND["other_backend"],
    "GCP": lx.CLOUD["gcp"],
    "Other cloud": lx.CLOUD["other_cloud"],
    "Docker": lx.CLOUD["docker"],
    "Deployment": lx.CLOUD["deploy"],
    "React/Next.js": lx.CLOUD["frontend"],
    "Frontend": lx.CLOUD["frontend"],
}
_EXPECTED = {
    "python_backend": [("Python", ("Python",)), ("FastAPI/Flask/Django", ("FastAPI", "Flask")), ("async programming", ("async",)),
                       ("PostgreSQL", ("PostgreSQL",)), ("Redis", ("Redis",)), ("other backend tooling", ("other backend",))],
    "cloud_fullstack": [("cloud provider (GCP/AWS/Azure)", ("GCP", "Other cloud")), ("Docker", ("Docker",)), ("deployment/CI-CD", ("Deployment",))],
}


def _scored_notes(notes: list[str]) -> list[tuple[str, float, str]]:
    out = []
    for n in notes:
        m = _NOTE.match(n)
        if m:
            out.append((m["name"].strip(), float(m["pts"]), (m["where"] or "").strip()))
    return out


def _skill_trace(key: str, score: float, maxv: float, notes: list[str], qf: QuoteFinder) -> CategoryEvidence:
    parsed = _scored_notes(notes)
    items: list[EvidenceItem] = []
    for name, _pts, _where in parsed:
        pat = next((p for k, p in _PATTERNS.items() if name.startswith(k)), None)
        if pat:
            _add(items, name.split(" (")[0], qf.find(pat, 1))
    in_ctx = [n for n, _, w in parsed if "projects/experience" in w or "end-to-end" in n]
    skills_only = [n for n, _, w in parsed if "skills list only" in w]
    found_names = [n for n, _, _ in parsed]
    missing = [label for label, prefixes in _EXPECTED[key] if not any(f.startswith(p) for f in found_names for p in prefixes)]
    parts = [f"{score:g}/{maxv:g}."]
    if in_ctx:
        parts.append("Demonstrated in projects/experience: " + ", ".join(in_ctx) + ".")
    if skills_only:
        parts.append("Named only in the skills list (reduced credit): " + ", ".join(skills_only) + ".")
    if not parsed:
        parts.append("No supporting signals found in the resume.")
    if missing:
        parts.append("No evidence found for: " + ", ".join(missing) + ".")
    return CategoryEvidence(score=score, max_score=maxv, explanation=" ".join(parts), signals=found_names, evidence=items, notes=list(notes))


def _ai_trace(resume: ParsedResume, sc: Scored, score: float, maxv: float, quality: AIProjectQuality, qf: QuoteFinder) -> CategoryEvidence:
    items = [EvidenceItem(signal="AI project", text=q, source=qf.locate(q)) for q in sc.evidence if _norm(q) in qf._hay]
    if not items and sc.best_unit is not None:  # scorer found signals but no headline snippet (e.g. applied AI): quote lines that contain them
        kws = sorted({k for v in sc.best_unit.groups.values() for k in v if len(k) > 2}, key=len, reverse=True)
        if kws:
            _add(items, "AI project", qf.find("|".join(re.escape(k) for k in kws), 3), cap=3)
    parts = [f"{score:g}/{maxv:g} - level {quality.level}: {quality.label}."]
    if quality.best_project:
        parts.append(f"Strongest AI work: {quality.best_project}.")
    if quality.skills_only:
        parts.append("AI frameworks are named only in the skills list, with no project implementing them.")
    elif quality.implementation_signals:
        parts.append("Implementation signals: " + "; ".join(quality.implementation_signals[:5]) + ".")
    if sc.penalties:
        parts.append("Penalties applied: " + " ".join(sc.penalties))
    return CategoryEvidence(score=score, max_score=maxv, explanation=" ".join(parts), signals=list(quality.implementation_signals),
                            evidence=items, notes=list(sc.notes.get("ai_project_depth", [])))


def _eng_trace(resume: ParsedResume, sc: Scored, score: float, maxv: float, qf: QuoteFinder) -> CategoryEvidence:
    names = [n for n in sc.notes.get("engineering_depth", [])]
    items: list[EvidenceItem] = []
    for label in names:
        pat = lx.ENG_DEPTH.get(label.replace(" ", "_"))
        if pat:
            _add(items, label, qf.find(pat, 1))
    expl = (f"{score:g}/{maxv:g} - one point per distinct engineering practice found in projects/experience: " + ", ".join(names) + "."
            if names else f"{score:g}/{maxv:g} - no testing, architecture, caching, queue, observability, concurrency or failure-handling signals found in projects/experience.")
    return CategoryEvidence(score=score, max_score=maxv, explanation=expl, signals=names, evidence=items, notes=list(names))


def _short_reason(reason: str | None) -> str:
    """'HTTP 403 (GitHub disabled for the rest of this run ...)' -> 'HTTP 403' (full text stays in `reason`)."""
    return re.split(r" \(", reason or "", maxsplit=1)[0] or "unknown"


def github_trace(info: GitHubInfo | None, score: float, maxv: float) -> CategoryEvidence:
    """Honest GitHub representation: 0 points from a failed lookup is 'not scored', never a negative evaluation."""
    if info is None:
        return CategoryEvidence(score=0, max_score=maxv, scored=False, enrichment_status="unknown",
                                reason="No GitHub information recorded", explanation="GitHub was not assessed (no enrichment data).")
    st = info.status
    if st == "ok":
        items = [EvidenceItem(signal="GitHub activity", text=info.summary, source="github")]
        if info.relevant_repos:
            items.append(EvidenceItem(signal="Python/AI-relevant repos", text=", ".join(info.relevant_repos), source="github"))
        sig = []
        if info.last_push_days_ago is not None:
            sig.append(f"last push {info.last_push_days_ago}d ago")
        if info.maintained_repos_12m is not None:
            sig.append(f"{info.maintained_repos_12m} maintained original repos (12m)")
        return CategoryEvidence(score=score, max_score=maxv, scored=True, enrichment_status=st, signals=sig, evidence=items,
                                explanation=f"{score:g}/{maxv:g} - activity {info.activity_score:g}/5 + repositories {info.repo_score:g}/5 from the live GitHub profile {info.profile_url or info.username}.",
                                notes=[info.summary])
    if st == "not_provided":
        reason, expl = "No GitHub profile found on the resume", "No GitHub profile on the resume, so no GitHub points were awarded (GitHub is an extra signal, not a requirement)."
    elif st == "not_found":
        reason, expl = info.error or "profile not found", f"GitHub profile '{info.username}' from the resume could not be found; 0 points."
    elif st in ("disabled", "skipped"):
        reason, expl = info.summary or st, f"GitHub enrichment {st}; GitHub was not scored."
    else:
        reason = info.error or info.summary or st
        expl = f"GitHub enrichment unavailable. Reason: {_short_reason(reason)}. 0/{maxv:g} reflects missing data, not a negative evaluation; GitHub is an additional signal, not an eligibility requirement."
    return CategoryEvidence(score=0, max_score=maxv, scored=False, enrichment_status=st, reason=reason, explanation=expl,
                            notes=[info.summary] if info.summary else [])


# ------------------------------------------------------------------ AI project quality
def classify_ai_level(groups: dict[str, list[str]] | None, thin: bool) -> int:
    """Level from detected implementation signals only. Framework names (LangChain/LangGraph) never lift the level by themselves."""
    if groups is None:
        return 0
    if thin:
        return 1
    keys = set(groups)
    behaviour = "agentic/tool-use" in keys  # explicit agent / tool-calling / planner language, not just a framework name
    framework = bool({"orchestration/multi-agent framework", "LLM framework (LangChain/LlamaIndex)"} & keys)
    support = _SUPPORT & keys
    if behaviour and len(support) >= 2 and (_DEEP & keys):
        return 4
    if (behaviour and support) or ("retrieval/RAG" in keys and support - {"retrieval/RAG"}) or (framework and len(support) >= 2 and (_DEEP & keys)):
        return 3
    return 2


def _usable_title(title: str) -> str:
    """Unit titles come from layout heuristics; only keep ones that read like a project name (not a company/date/sentence line)."""
    bad = (not title or title == "(whole resume)" or len(title) > 75 or len(title.split()) > 9 or title.isupper() or title.endswith((",", ".", ":"))
           or re.search(r"(?<!\d)(19|20)\d\d(?!\d)|present", title, re.I))
    return "" if bad else title


def build_ai_quality(sc: Scored, ai_score: float, settings: Settings) -> AIProjectQuality:
    best = sc.best_unit
    thin = bool(sc.flags.get("thin_effective", sc.flags.get("thin")))
    tutorial = bool(sc.flags.get("tutorial_effective", sc.flags.get("tutorial")))
    skills_only = best is None
    level = classify_ai_level(None if skills_only else best.groups, thin)
    signals = [f"{k}: {', '.join(v)}" for k, v in (best.groups.items() if best else [])]
    title = _usable_title(best.unit.title.split("|")[0].strip()) if best else ""
    concerns: list[str] = [p.split(": ", 1)[-1] for p in sc.penalties]
    if best:
        keys = set(best.groups)
        gaps = []
        if level < 4:
            if not _AGENTIC & keys:
                gaps.append("agentic/tool-use or orchestration")
            if "evaluation" not in keys:
                gaps.append("evaluation")
            if "state/memory" not in keys:
                gaps.append("state/memory")
            if "retrieval/RAG" not in keys and not _AGENTIC & keys:
                gaps.append("retrieval")
        if gaps and level >= 2:
            concerns.append("No evidence of " + ", ".join(gaps[:3]) + " in the strongest AI project")
    else:
        concerns.append("AI frameworks appear only in the skills list; no project shows them being implemented")
    return AIProjectQuality(
        level=level, label=AI_LEVELS[level], score=ai_score, max_score=float(settings.weights.ai_project_depth), best_project=title, best_project_section=(best.unit.section if best else ""),
        summary=sc.project_summary, implementation_signals=signals, evidence=list(sc.evidence), quality_concerns=list(dict.fromkeys(concerns)),
        thin_wrapper=thin, tutorial_style=tutorial, skills_only=skills_only,
    )


# ------------------------------------------------------------------ public builders
def build_evidence_trace(resume: ParsedResume, sc: Scored, breakdown: dict[str, float], info: GitHubInfo | None,
                         quality: AIProjectQuality, settings: Settings) -> EvidenceTrace:
    qf = QuoteFinder(resume)
    w = settings.weights
    ai = _ai_trace(resume, sc, breakdown["ai_project_depth"], w.ai_project_depth, quality, qf)
    if not quality.evidence:  # keep ai_project_quality.evidence consistent with the trace
        quality.evidence = [e.text for e in ai.evidence]
    return EvidenceTrace(
        ai_project_depth=ai,
        python_backend=_skill_trace("python_backend", breakdown["python_backend"], w.python_backend, sc.notes.get("python_backend", []), qf),
        cloud_fullstack=_skill_trace("cloud_fullstack", breakdown["cloud_fullstack"], w.cloud_fullstack, sc.notes.get("cloud_fullstack", []), qf),
        github=github_trace(info, breakdown.get("github", 0), w.github),
        engineering_depth=_eng_trace(resume, sc, breakdown["engineering_depth"], w.engineering_depth, qf),
    )


def _join(items: list[str], limit: int = 4) -> str:
    items = list(dict.fromkeys(items))[:limit]
    return ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1] if items else ""


def build_why(quality: AIProjectQuality, trace: EvidenceTrace, concerns: list[str], total: float) -> str:
    """2-4 deterministic, evidence-backed sentences. Every fact comes from the trace/quality objects built above."""
    s: list[str] = []
    ai = trace.ai_project_depth
    sig_names = [x.split(":")[0] for x in quality.implementation_signals]
    proj = f"'{quality.best_project}'" if quality.best_project else f"the strongest AI work (in {quality.best_project_section or 'the resume'})"
    if quality.level >= 3:
        lead = "Strong AI fit" if quality.level == 4 else "Solid AI-system fit"
        s.append(f"{lead}: {proj} is a Level {quality.level} {quality.label} showing {_join(sig_names, 4)}; AI depth {ai.score:g}/{ai.max_score:g}.")
    elif quality.level == 2:
        s.append(f"Moderate AI fit: {proj} is Applied AI with {_join(sig_names, 3) or 'LLM usage'} but without retrieval-plus-supporting or agentic depth; AI depth {ai.score:g}/{ai.max_score:g}.")
    elif quality.level == 1:
        s.append(f"Limited AI fit: {proj} reads as a thin LLM/API wrapper, so AI depth is only {ai.score:g}/{ai.max_score:g} after the penalty.")
    else:
        s.append(f"Eligible on keyword evidence only: AI frameworks are named in the skills list but no project implements them (AI depth {ai.score:g}/{ai.max_score:g}).")
    py = trace.python_backend
    py_ctx = [n.split(" (")[0] for n, _, w in _scored_notes(py.notes) if "projects/experience" in w and n != "Python"]
    if py_ctx:
        s.append(f"Backend evidence in real work: {_join(py_ctx, 4)} (Python/backend {py.score:g}/{py.max_score:g}).")
    else:
        s.append(f"Python/backend signals are mostly skills-list mentions (Python/backend {py.score:g}/{py.max_score:g}).")
    cl = trace.cloud_fullstack
    cl_ctx = [n.split(" (")[0] for n, _, w in _scored_notes(cl.notes) if "projects/experience" in w]
    eng = trace.engineering_depth
    tail = []
    if cl_ctx:
        tail.append(f"deployment evidence ({_join(cl_ctx, 3)})")
    if eng.signals:
        tail.append(f"engineering practices ({_join(eng.signals, 3)})")
    if tail:
        s.append("Also shows " + " and ".join(tail) + ".")
    gh = trace.github
    if gh.scored is False and gh.enrichment_status == "not_provided":
        s.append(f"No GitHub profile is listed on the resume, so GitHub adds nothing to the {total:g} total.")
    elif gh.scored is False:
        s.append(f"GitHub could not be assessed ({_short_reason(gh.reason)}), so the {total:g} total excludes it.")
    elif quality.quality_concerns:
        s.append("Caveat: " + quality.quality_concerns[0].rstrip(".") + ".")
    elif concerns:
        s.append("Caveat: " + concerns[0].rstrip(".") + ".")
    return " ".join(s[:4])
