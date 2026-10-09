"""Candidate comparison data (2-3 candidates) built purely from an existing results dict.

Returns machine-readable rows for a future frontend plus evidence-based sentences that explain *why* one
candidate leads on a dimension (what the leader demonstrates that the other does not), rather than just
saying "A is better". Works on partial/older records (no evidence_trace) and never raises on malformed data;
only a wrong number of candidates or unknown identifiers raise ValueError.
"""
from __future__ import annotations

from typing import Any

DIMENSIONS = [
    ("ai_project_depth", "AI project depth", 40.0),
    ("python_backend", "Python/backend", 30.0),
    ("cloud_fullstack", "Cloud/full-stack", 15.0),
    ("github", "GitHub", 10.0),
    ("engineering_depth", "Engineering depth", 5.0),
]


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _d(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _l(v: Any) -> list:
    return v if isinstance(v, list) else []


def find_candidates(result: dict, identifiers: list[str]) -> list[dict]:
    """Resolve identifiers (file name or candidate name, case-insensitive) against ranked + rejected candidates."""
    pool = [c for c in _l(result.get("ranked_candidates")) + _l(result.get("rejected_candidates")) if isinstance(c, dict)]
    ids = list(dict.fromkeys(i.strip() for i in identifiers if isinstance(i, str) and i.strip()))
    if not 2 <= len(ids) <= 3:
        raise ValueError("Comparison needs 2 or 3 distinct candidates")
    out, missing = [], []
    for i in ids:
        hit = next((c for c in pool if str(c.get("file", "")).lower() == i.lower()), None) or \
              next((c for c in pool if str(c.get("candidate_name", "")).lower() == i.lower()), None)
        (out if hit else missing).append(hit or i)
    if missing:
        raise ValueError("Unknown candidate(s): " + ", ".join(missing))
    if len({c.get("file") for c in out}) != len(out):
        raise ValueError("Comparison needs 2 or 3 distinct candidates")
    return out


def _signals(c: dict, key: str) -> list[str]:
    """Detected signals for a dimension: from evidence_trace when present, else derived from score_notes."""
    sig = _d(_d(c.get("evidence_trace")).get(key)).get("signals")
    if isinstance(sig, list):
        return [str(s) for s in sig]
    return [str(n).split(":")[0] for n in _l(_d(c.get("score_notes")).get(key)) if isinstance(n, str)]


def _sig_names(key: str, sigs: list[str]) -> set[str]:
    # AI signals look like "retrieval/RAG: chroma, embedding" -> compare on the group name only
    return {s.split(":")[0].split(" (")[0].strip().lower() for s in sigs} if key == "ai_project_depth" else {s.split(" (")[0].strip().lower() for s in sigs}


def _row(c: dict) -> dict:
    bd = _d(c.get("score_breakdown"))
    q = _d(c.get("ai_project_quality"))
    gh = _d(c.get("github"))
    trace = _d(c.get("evidence_trace"))
    gh_t = _d(trace.get("github"))
    scores = {k: {"score": _num(bd.get(k)), "max": mx} for k, _, mx in DIMENSIONS}
    return {
        "file": c.get("file") or c.get("candidate_name") or "(unknown)",
        "candidate_name": c.get("candidate_name") or c.get("file") or "(unknown)",
        "rank": c.get("rank"),
        "eligible": bool(c.get("eligible")),
        "rejection_reasons": _l(c.get("rejection_reasons")),
        "final_score": _num(c.get("total_score")),
        "scores": scores,
        "signals": {k: _signals(c, k) for k, _, _ in DIMENSIONS},
        "ai_depth_level": q.get("level"),
        "ai_depth_label": q.get("label"),
        "ai_project_quality": q or None,
        "github_status": gh.get("status") or gh_t.get("enrichment_status"),
        "github_scored": gh_t.get("scored") if "scored" in gh_t else (gh.get("status") == "ok" if gh else None),
        "github_reason": gh_t.get("reason") or gh.get("error"),
        "why_candidate": c.get("why_candidate"),
        "strengths": _l(c.get("strengths")),
        "concerns": _l(c.get("concerns")),
        "evidence": _l(c.get("evidence")),
        "has_evidence_trace": bool(trace),
    }


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:g}"


def _short(reason: str | None) -> str:
    return (reason or "unknown reason").split(" (")[0]


def _dimension(key: str, label: str, mx: float, rows: list[dict], names: dict[str, str]) -> dict:
    vals = {r["file"]: r["scores"][key]["score"] for r in rows}
    known = {f: v for f, v in vals.items() if v is not None}
    tol = max(1.0, 0.1 * mx)
    out: dict = {"key": key, "label": label, "max": mx, "scores": vals, "leader": None, "leaders": [], "comparable": False, "margin": None, "finding": ""}
    gh_missing = [r for r in rows if key == "github" and not r["github_scored"]]
    if gh_missing:
        who = "; ".join(f"{r['candidate_name']} ({_short(r['github_reason'] or r['github_status'])})" for r in gh_missing)
        out["finding"] = f"GitHub is not comparable: no GitHub score for {who}. Missing GitHub data is not a negative signal."
        return out
    if len(known) < 2:
        out["finding"] = f"{label}: not enough score data to compare."
        return out
    ordered = sorted(known, key=lambda f: -known[f])
    top = ordered[0]
    scores_txt = " vs ".join(_fmt(known[f]) for f in ordered)
    if known[top] - known[ordered[-1]] <= tol:
        out["comparable"] = True
        out["finding"] = f"{label} is comparable across the group ({scores_txt} of {mx:g})."
        if key == "ai_project_depth":
            lv = {names[r["file"]]: r["ai_depth_level"] for r in rows if r["ai_depth_level"] is not None}
            if len(set(lv.values())) > 1:
                out["finding"] += " Depth levels differ: " + ", ".join(f"{n} Level {l}" for n, l in lv.items()) + "."
        return out
    leaders = [f for f in ordered if known[top] - known[f] <= tol]
    trailing = [f for f in ordered if f not in leaders]
    ref = trailing[0]  # closest trailing candidate: the fairest thing to contrast the leader against
    out["leaders"] = leaders
    out["leader"] = top if len(leaders) == 1 else None
    out["margin"] = round(known[top] - known[ref], 1)
    by = {r["file"]: r for r in rows}
    lead, other = by[top], by[ref]
    extra = [e.split(":")[0].split(" (")[0] for e in lead["signals"][key] if _sig_names(key, [e]) - _sig_names(key, other["signals"][key])][:4]
    lead_txt = " and ".join(names[f] for f in leaders)
    f = f"{lead_txt} {'is' if len(leaders) == 1 else 'are'} stronger on {label} ({_fmt(known[top])} vs " + ", ".join(f"{names[t]} {_fmt(known[t])}" for t in trailing) + f" of {mx:g})"
    if key == "ai_project_depth" and lead["ai_depth_level"] is not None and other["ai_depth_level"] is not None:
        if lead["ai_depth_level"] == other["ai_depth_level"]:
            f += f": both are Level {lead['ai_depth_level']} ({lead['ai_depth_label']}), but {names[top]}'s project covers more implementation signals"
        else:
            f += f": {names[top]} is Level {lead['ai_depth_level']} ({lead['ai_depth_label']}) vs Level {other['ai_depth_level']} ({other['ai_depth_label']}) for {names[ref]}"
    if extra:
        f += f"; {names[top]} demonstrates {', '.join(extra)}, which {names[ref]} does not show"
    elif not lead["has_evidence_trace"] or not other["has_evidence_trace"]:
        f += " (no evidence trace available to explain the difference)"
    out["finding"] = f + "."
    return out


def _ranking(rows: list[dict], names: dict[str, str]) -> list[str]:
    ordered = sorted(rows, key=lambda r: (-(r["final_score"] or 0), r["rank"] if isinstance(r["rank"], int) else 10**6))
    notes = []
    for a, b in zip(ordered, ordered[1:]):
        gap = round((a["final_score"] or 0) - (b["final_score"] or 0), 1)
        diffs = []
        for k, label, _ in DIMENSIONS:
            sa, sb = a["scores"][k]["score"], b["scores"][k]["score"]
            if sa is not None and sb is not None and round(sa - sb, 1) != 0:
                diffs.append((round(sa - sb, 1), label))
        pos = sorted([d for d in diffs if d[0] > 0], reverse=True)[:2]
        neg = sorted([d for d in diffs if d[0] < 0])[:1]
        if gap == 0:
            text = f"{names[a['file']]} and {names[b['file']]} have the same total ({_fmt(a['final_score'])}); rank order follows the AI-depth tie-break"
        else:
            text = f"{names[a['file']]} scores {gap:g} point{'' if gap == 1 else 's'} above {names[b['file']]}"
            if pos:
                text += ", mainly from " + " and ".join(f"{l} (+{d:g})" for d, l in pos)
            if neg:
                text += f", partly offset by {neg[0][1]} ({neg[0][0]:g})"
        notes.append(text + ".")
    return notes


def compare_candidates(cands: list[dict]) -> dict:
    rows = [_row(c) for c in cands]
    warnings: list[str] = []
    name_count: dict[str, int] = {}
    for r in rows:
        name_count[r["candidate_name"]] = name_count.get(r["candidate_name"], 0) + 1
    names = {r["file"]: (f"{r['candidate_name']} ({r['file']})" if name_count[r["candidate_name"]] > 1 else r["candidate_name"]) for r in rows}
    elig = [r for r in rows if r["eligible"] and r["final_score"] is not None]
    for r in rows:
        if r not in elig:
            why = "; ".join(map(str, r["rejection_reasons"])) or "no score recorded"
            warnings.append(f"{names[r['file']]} is not scored/eligible ({why}) and is excluded from the numeric comparison.")
        elif not r["has_evidence_trace"]:
            warnings.append(f"{names[r['file']]} has no evidence trace (older results file); differences cannot be explained from evidence.")
    dims, findings, ranking = [], [], []
    if len(elig) >= 2:
        dims = [_dimension(k, lab, mx, elig, names) for k, lab, mx in DIMENSIONS]
        findings = [d["finding"] for d in dims if d["finding"]]
        ranking = _ranking(elig, names)
    else:
        warnings.append("Fewer than two eligible candidates with scores: no dimension comparison produced.")
    return {"candidates": rows, "dimensions": dims, "findings": findings, "ranking_explanation": ranking, "warnings": warnings}


def build_comparison(result: dict, identifiers: list[str]) -> dict:
    return compare_candidates(find_candidates(result, identifiers))
