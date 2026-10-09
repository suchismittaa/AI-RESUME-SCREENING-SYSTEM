"""Deterministic, explainable scoring (100 pts). Every point can be traced to a matched keyword group.

Design: evidence found in *what the candidate built* (projects / experience / summary) earns full credit;
evidence found only in a skills list earns `skills_only_factor` of it. AI depth is judged per project/
experience "unit" so one thin wrapper project can be told apart from a real agentic system.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import lexicon as lx
from .config import Settings
from .extract import clean_ai_noise, context_text
from .models import ParsedResume, Section

BULLET = re.compile(r"^\s*[•●◦▪▫■\-–—*·]\s*")


def _has(pat: str, text: str, cs: bool = False) -> bool:
    return bool(re.search(pat, text, 0 if cs else re.I))


def _find(pat: str, text: str, cs: bool = False) -> list[str]:
    return sorted({m.group(0).lower() for m in re.finditer(pat, text, 0 if cs else re.I)})


# ------------------------------------------------------------------ units
@dataclass
class Unit:
    title: str
    text: str
    section: str


def split_units(sections: list[Section]) -> list[Unit]:
    """Split projects/experience into per-item blocks using layout-agnostic title heuristics."""
    units: list[Unit] = []
    for sec in sections:
        if sec.name not in ("projects", "experience", "other"):
            continue
        cur_title, cur_lines, prev = "", [], ""
        for raw in sec.text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            is_bullet = bool(BULLET.match(line))
            # A title is a short, capitalised, non-bullet line that follows a finished sentence (or carries a "|" tech list).
            # Wrapped bullet continuations usually start lowercase or follow an unfinished line, so they are excluded.
            looks_title = (
                not is_bullet
                and len(line) <= 140
                and not line.endswith(".")
                and (line[0].isupper() or line[0].isdigit())
                and (not prev or prev.endswith((".", "!", "?", "%", ")")) or "|" in line)
            )
            if looks_title:
                if cur_lines:
                    units.append(Unit(cur_title, "\n".join(cur_lines), sec.name))
                cur_title, cur_lines = line, [line]
            else:
                if not cur_lines:
                    cur_title = "" if is_bullet else line
                cur_lines.append(line)
            prev = line
        if cur_lines:
            units.append(Unit(cur_title, "\n".join(cur_lines), sec.name))
    return [u for u in units if len(u.text) > 60]


# ------------------------------------------------------------------ AI signals
def ai_signals(text: str) -> dict[str, list[str]]:
    t = clean_ai_noise(text)
    strong = [n for n, p in lx.AI_STRONG.items() if _has(p, t, cs=(n == "RAG"))]
    generic = [n for n, p in lx.AI_GENERIC.items() if _has(p, t)]
    if strong == ["Multi-Agent"] and not generic and not _has(r"agentic|multi[- ]?agent|ai agent|llm agent", t):
        strong = []  # bare "agent" without AI context
    return {"strong": strong, "generic": generic}


@dataclass
class UnitScore:
    unit: Unit
    score: float
    is_ai: bool
    thin: bool
    tutorial: bool
    groups: dict[str, list[str]] = field(default_factory=dict)


def score_ai_unit(unit: Unit) -> UnitScore:
    t = clean_ai_noise(unit.text)
    sig = ai_signals(t)
    is_ai = bool(sig["strong"] or sig["generic"])
    g: dict[str, list[str]] = {}
    pts = 0.0
    if not is_ai:
        return UnitScore(unit, 0, False, False, False, g)

    def add(name: str, pat: str, points: float, cs: bool = False):
        nonlocal pts
        found = _find(pat, t, cs)
        if found:
            g[name] = found[:4]
            pts += points
        return bool(found)

    orch = add("orchestration/multi-agent framework", lx.FRAMEWORK_ORCH, 8)
    add("LLM framework (LangChain/LlamaIndex)", lx.FRAMEWORK_CHAIN, 4)
    retr = _find(lx.DEPTH_RETRIEVAL, t, cs=False)
    retr = [r for r in retr if r != "rag" or _has(r"(?<![A-Z])RAG(?![A-Z])", t, cs=True)]
    if retr:
        g["retrieval/RAG"] = retr[:4]
        pts += 8 + (2 if len(retr) >= 3 else 0)
    agentic_strict = _find(r"agentic|multi[- ]?agent|(?<![a-z])agents?(?![a-z])|tool[- ]?call|function[- ]?call|(?<![a-z])mcp(?![a-z])|planner|human[- ]in[- ]the[- ]loop|supervisor", t)
    if agentic_strict:
        g["agentic/tool-use"] = agentic_strict[:4]
        pts += 6
    elif add("workflow orchestration", r"orchestrat|workflow|state ?machine|routing|router", 2):
        pass
    add("state/memory", lx.DEPTH_STATE, 3)
    strict_eval = _find(r"(?<![a-z])evals?(?![a-z])|ragas|llm[- ]as[- ]a?[- ]?judge|hallucination|guardrail|benchmark|evaluat", t)
    if strict_eval:
        g["evaluation"] = strict_eval[:4]
        pts += 4
    elif add("accuracy metrics", r"accuracy|precision|recall|f1", 1):
        pass
    add("fine-tuning", lx.DEPTH_FINETUNE, 3)
    data = add("data pipeline", lx.DEPTH_DATA, 3)
    back = add("backend integration", lx.DEPTH_BACKEND, 3)
    add("quantified outcome", lx.DEPTH_METRIC, 2)
    pts = min(pts, float(40))

    # Thin wrapper = an LLM/API call with no AI-specific depth, and not even a real data-processing + backend workflow around it.
    ai_specific = {"orchestration/multi-agent framework", "LLM framework (LangChain/LlamaIndex)", "retrieval/RAG", "agentic/tool-use", "workflow orchestration", "state/memory", "evaluation", "fine-tuning"}
    thin = not (ai_specific & set(g)) and not {"data pipeline", "backend integration"} <= set(g)
    tutorial = _has(lx.TUTORIAL_MARKERS, unit.text)
    return UnitScore(unit, pts, True, thin, tutorial, g)


# ------------------------------------------------------------------ category scorers
@dataclass
class Scored:
    breakdown: dict[str, float]
    notes: dict[str, list[str]]
    penalties: list[str]
    strengths: list[str]
    concerns: list[str]
    evidence: list[str]
    project_summary: str
    best_unit: UnitScore | None
    flags: dict = field(default_factory=dict)


def _tier(pat: str, ctx: str, full: str, weight: float, factor: float, cs: bool = False):
    """Return (points, where) — full credit in project/experience context, reduced for skills-list-only."""
    if _has(pat, ctx, cs):
        return weight, "in projects/experience"
    if _has(pat, full, cs):
        return round(weight * factor, 1), "skills list only"
    return 0.0, ""


def score_python_backend(ctx: str, full: str, s: Settings) -> tuple[float, list[str], list[str]]:
    w = s.weights.python_backend
    f = s.skills_only_factor
    notes, concerns, total = [], [], 0.0
    plan = [
        ("Python", lx.PYTHON_DIRECT + "|" + lx.PYTHON_IMPLICIT, 0.27),
        ("FastAPI", lx.BACKEND["fastapi"], 0.20),
        ("async programming", lx.BACKEND["async"], 0.13),
        ("PostgreSQL", lx.BACKEND["postgres"], 0.17),
        ("Redis", lx.BACKEND["redis"], 0.13),
        ("other backend (REST/WebSocket/Celery/SQLAlchemy/microservices)", lx.BACKEND["other_backend"], 0.10),
    ]
    for name, pat, share in plan:
        pts, where = _tier(pat, ctx, full, w * share, f)
        if name == "FastAPI" and not pts:  # Flask/Django are a weaker but real signal
            pts, where = _tier(lx.BACKEND["flask_django"], ctx, full, w * share * 0.6, f)
            name = "Flask/Django"
        if pts:
            notes.append(f"{name}: +{round(pts, 1)} ({where})")
            total += pts
        else:
            concerns.append(f"No {name} evidence")
    return min(total, w), notes, concerns


def score_cloud(ctx: str, full: str, s: Settings) -> tuple[float, list[str], list[str]]:
    w = s.weights.cloud_fullstack
    f = s.skills_only_factor
    notes, concerns, total = [], [], 0.0
    pts, where = _tier(lx.CLOUD["gcp"], ctx, full, w * 0.33, f)
    label = "GCP"
    if not pts:
        pts, where = _tier(lx.CLOUD["other_cloud"], ctx, full, w * 0.20, f)
        label = "Other cloud (AWS/Azure)"
    if pts:
        notes.append(f"{label}: +{round(pts, 1)} ({where})"); total += pts
    else:
        concerns.append("No cloud (GCP/AWS/Azure) evidence")
    for name, key, share in (("Docker", "docker", 0.27), ("Deployment/CI-CD", "deploy", 0.20)):
        pts, where = _tier(lx.CLOUD[key], ctx, full, w * share, f)
        if pts:
            notes.append(f"{name}: +{round(pts, 1)} ({where})"); total += pts
        else:
            concerns.append(f"No {name} evidence")
    fe_ctx = _has(lx.CLOUD["frontend"], ctx)
    be_ctx = _has("|".join(lx.BACKEND.values()), ctx)
    if fe_ctx and be_ctx:
        notes.append(f"React/Next.js as part of an end-to-end system: +{round(w * 0.20, 1)}"); total += w * 0.20
    elif fe_ctx or _has(lx.CLOUD["frontend"], full):
        notes.append(f"Frontend frameworks without backend context: +{round(w * 0.07, 1)}"); total += w * 0.07
    return min(total, w), notes, concerns


def score_engineering(ctx: str, s: Settings) -> tuple[float, list[str]]:
    hit = [name for name, pat in lx.ENG_DEPTH.items() if _has(pat, ctx)]
    pts = min(float(len(hit)), float(s.weights.engineering_depth))
    return pts, [f"{h.replace('_', ' ')}" for h in hit]


def ai_penalties(thin: bool, tutorial: bool, unit_len: int, s: Settings) -> list[tuple[int, str]]:
    out = []
    if thin:
        pen = s.penalties.thin_wrapper_severe if unit_len < 250 else s.penalties.thin_wrapper
        out.append((pen, "strongest AI project looks like a thin LLM/API wrapper (no retrieval, agents, state, evaluation, data pipeline or backend logic)"))
    if tutorial:
        out.append((s.penalties.tutorial_style, "tutorial/course-style project markers without ownership evidence"))
    return out


def score_ai(resume: ParsedResume, ctx: str, full: str, s: Settings):
    units = split_units(resume.sections)
    scored = [score_ai_unit(u) for u in units]
    ai_units = sorted([u for u in scored if u.is_ai], key=lambda u: u.score, reverse=True)
    if not ai_units:  # segmentation failed or AI only in summary/skills: judge the whole context as one unit
        whole = score_ai_unit(Unit("(whole resume)", ctx or full, "other"))
        if whole.is_ai:
            ai_units = [whole]
    notes, penalties = [], []
    if not ai_units:
        # AI keywords exist only in a skills list: minimal credit + explicit penalty
        n = len(ai_signals(full)["strong"])
        pts = min(6.0, 1.5 * n)
        pen = s.penalties.skills_only_ai if n else 0
        if pen:
            penalties.append(f"-{pen}: AI frameworks only named in a skills list, no implementation evidence")
        notes.append(f"AI keywords only in skills list ({n}): +{pts}")
        return max(0.0, pts - pen), notes, penalties, None, pts
    best = ai_units[0]
    pts = best.score
    if len(ai_units) > 1 and not ai_units[1].thin:
        bonus = min(5.0, 0.25 * ai_units[1].score)
        pts += bonus
        notes.append(f"Second AI project '{ai_units[1].unit.title[:50]}': +{bonus:.1f}")
    notes.insert(0, f"Best AI project '{best.unit.title[:60] or 'n/a'}': {best.score:.0f}/40 from " + "; ".join(f"{k} ({', '.join(v[:3])})" for k, v in best.groups.items()))
    pts = min(pts, float(s.weights.ai_project_depth))
    for pen, msg in ai_penalties(best.thin, best.tutorial, len(best.unit.text), s):
        penalties.append(f"-{pen}: {msg}")
        pts -= pen
    pre = min(best.score + (min(5.0, 0.25 * ai_units[1].score) if len(ai_units) > 1 and not ai_units[1].thin else 0), float(s.weights.ai_project_depth))
    return max(0.0, pts), notes, penalties, best, pre


def _snippets(text: str, pats: list[str], n: int = 3) -> list[str]:
    out = []
    for sent in re.split(r"(?<=[.!?])\s+|\n", text):
        sent = BULLET.sub("", sent).strip()
        if 25 <= len(sent) <= 260 and any(_has(p, sent) for p in pats):
            out.append(sent)
        if len(out) >= n:
            break
    return out


def score_resume(resume: ParsedResume, s: Settings) -> Scored:
    """Everything except GitHub (added by the pipeline once enrichment is available)."""
    full = clean_ai_noise(resume.text)
    ctx = clean_ai_noise(context_text(resume.sections)) or full
    ai_pts, ai_notes, penalties, best, ai_pre = score_ai(resume, ctx, full, s)
    py_pts, py_notes, py_concerns = score_python_backend(ctx, full, s)
    cl_pts, cl_notes, cl_concerns = score_cloud(ctx, full, s)
    en_pts, en_notes = score_engineering(ctx, s)

    strengths, concerns = [], []
    if best and best.groups:
        keys = list(best.groups)
        if any(k in keys for k in ("orchestration/multi-agent framework", "agentic/tool-use")):
            strengths.append("Agentic/orchestrated AI work: " + ", ".join(list(dict.fromkeys(sum((best.groups.get(k, []) for k in ("orchestration/multi-agent framework", "agentic/tool-use")), [])))[:4]))
        if "retrieval/RAG" in keys:
            strengths.append("Retrieval/RAG implementation: " + ", ".join(best.groups["retrieval/RAG"][:3]))
        if "evaluation" in keys:
            strengths.append("Evaluation/guardrails present: " + ", ".join(best.groups["evaluation"][:3]))
    if any(n.startswith("FastAPI") and "projects" in n for n in py_notes):
        strengths.append("FastAPI backend used in real work" + (" with async" if any(n.startswith("async") for n in py_notes) else ""))
    if any(n.startswith("GCP") and "projects" in n for n in cl_notes):
        strengths.append("GCP used in projects/experience")
    if en_pts >= 3:
        strengths.append("Engineering depth signals: " + ", ".join(en_notes[:4]))
    concerns += [c for c in py_concerns if any(k in c for k in ("FastAPI", "Flask", "PostgreSQL", "Redis", "async"))][:3]
    concerns += [c for c in cl_concerns if "cloud" in c.lower() or "Docker" in c][:2]
    if penalties:
        concerns.append(penalties[0].split(": ", 1)[1])

    evidence = _snippets(best.unit.text, [lx.FRAMEWORK_ORCH, lx.FRAMEWORK_CHAIN, lx.DEPTH_RETRIEVAL, lx.DEPTH_AGENTIC]) if best else []
    if best:
        sig = [x for k in ("orchestration/multi-agent framework", "LLM framework (LangChain/LlamaIndex)", "retrieval/RAG", "agentic/tool-use", "evaluation") for x in best.groups.get(k, [])]
        title = best.unit.title.split("|")[0].strip()[:80]
        summary = f"{title}: " + (", ".join(dict.fromkeys(sig[:6])) if sig else "LLM/API usage") + (" (thin: LLM call with little surrounding logic)" if best.thin else "")
    else:
        summary = "No concrete AI project found beyond skill keywords."

    return Scored(
        breakdown={
            "ai_project_depth": round(ai_pts, 1),
            "python_backend": round(py_pts, 1),
            "cloud_fullstack": round(cl_pts, 1),
            "engineering_depth": round(en_pts, 1),
        },
        notes={"ai_project_depth": ai_notes, "python_backend": py_notes, "cloud_fullstack": cl_notes, "engineering_depth": en_notes},
        penalties=penalties,
        strengths=strengths,
        concerns=concerns,
        evidence=evidence,
        project_summary=summary,
        best_unit=best,
        flags={"thin": bool(best and best.thin), "tutorial": bool(best and best.tutorial), "ai_pre": ai_pre, "unit_len": len(best.unit.text) if best else 0},
    )


def apply_llm(sc: Scored, j, resume_text: str, s: Settings) -> Scored:
    """Blend an LLM project judgment into the deterministic AI-depth score. Hard eligibility is never touched.

    final = (1-w)*deterministic + w*llm, then penalties apply once if EITHER judge flags the project.
    Evidence quotes returned by the model are kept only if they literally occur in the resume (anti-hallucination).
    """
    w = s.llm_blend_weight
    pre = (1 - w) * sc.flags["ai_pre"] + w * j.ai_depth_score
    thin = sc.flags["thin"] or j.thin_wrapper
    tutorial = sc.flags["tutorial"] or j.tutorial_style
    pens = ai_penalties(thin, tutorial, sc.flags["unit_len"] or 999, s)
    sc.flags["thin_effective"], sc.flags["tutorial_effective"] = thin, tutorial  # exposed via ai_project_quality
    sc.penalties = [f"-{p}: {m}" for p, m in pens]
    sc.breakdown["ai_project_depth"] = round(max(0.0, min(pre, s.weights.ai_project_depth) - sum(p for p, _ in pens)), 1)
    sc.notes["ai_project_depth"].append(f"LLM judgment: {j.ai_depth_score}/40 blended at weight {w} with deterministic {sc.flags['ai_pre']:.1f}")
    norm = lambda t: re.sub(r"\s+", " ", t).lower()
    hay = norm(resume_text)
    verified = [q for q in j.evidence if len(q) > 15 and norm(q) in hay]
    if verified:
        sc.evidence = verified[:4]
    if j.summary:
        sc.project_summary = (j.best_project + ": " if j.best_project else "") + j.summary
    sc.strengths = (j.strengths + [x for x in sc.strengths if x not in j.strengths])[:5]
    sc.concerns = (j.concerns + [x for x in sc.concerns if x not in j.concerns])[:5]
    return sc
