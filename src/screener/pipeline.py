"""Orchestration: ingest -> parse -> hard filter -> score -> (LLM, GitHub) -> rank -> report."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import Settings
from .eligibility import check_eligibility
from .explain import build_ai_quality, build_evidence_trace, build_why
from .extract import parse_resume
from .github import GitHubClient
from .ingest import UnreadableResume, content_hash, discover, read_resume
from .llm import LLMClient, LLMError, build_llm_client
from .models import CandidateResult, FailedFile, GitHubInfo, ParsedResume, ScoreBreakdown
from .scoring import Scored, apply_llm, score_resume

log = logging.getLogger(__name__)


def _github_summary(info: GitHubInfo) -> str:
    return info.summary or info.status


def _missing_requirements(e) -> list[str]:
    """Which hard requirements had no supporting evidence (taken from the eligibility result, not parsed from text)."""
    out = []
    if not e.python_evidence:
        out.append("Python")
    if not e.ai_evidence:
        out.append("AI / agentic")
    return out


def run_pipeline(input_dir: Path, settings: Settings, llm: LLMClient | None = None, github: GitHubClient | None = None) -> dict:
    files = discover(input_dir, settings.supported_extensions)
    failed: list[FailedFile] = []
    parsed: list[ParsedResume] = []
    seen: dict[str, str] = {}
    duplicates: list[dict] = []

    # 1) ingest + parse (a bad file never aborts the batch)
    for f in files:
        try:
            raw = read_resume(f, settings.min_text_chars)
            h = content_hash(raw.text)
            if h in seen:
                duplicates.append({"file": f.name, "duplicate_of": seen[h]})
                continue
            seen[h] = f.name
            parsed.append(parse_resume(raw))
        except UnreadableResume as e:
            failed.append(FailedFile(file=f.name, error=str(e)))
        except Exception as e:  # parsing bug on an odd layout: record and move on
            log.exception("failed on %s", f.name)
            failed.append(FailedFile(file=f.name, error=f"{type(e).__name__}: {e}"))

    # 2) hard eligibility (rule-based, no LLM)
    elig = {p.file: check_eligibility(p) for p in parsed}
    eligible = [p for p in parsed if elig[p.file].eligible]

    # 3) deterministic scores, then optional LLM judgments (bounded concurrency)
    scored: dict[str, Scored] = {p.file: score_resume(p, settings) for p in eligible}
    llm = llm if llm is not None else build_llm_client(settings)
    llm_err: dict[str, str] = {}
    llm_ok: set[str] = set()
    if llm and eligible:
        def judge(p: ParsedResume):
            try:
                return p.file, llm.judge(p.candidate_name, p.text), None
            except LLMError as e:
                return p.file, None, str(e)
            except Exception as e:  # never let one resume kill the batch
                return p.file, None, f"{type(e).__name__}: {e}"

        with ThreadPoolExecutor(max_workers=max(1, settings.llm_max_concurrency)) as ex:
            for fname, j, err in ex.map(judge, eligible):
                if j is not None:
                    pr = next(p for p in eligible if p.file == fname)
                    scored[fname] = apply_llm(scored[fname], j, pr.text, settings)
                    llm_ok.add(fname)
                else:
                    llm_err[fname] = err or "unknown error"

    # 4) GitHub enrichment (eligible candidates only; shared cache, bounded concurrency)
    gh = github or GitHubClient(settings)
    infos: dict[str, GitHubInfo] = {}
    with ThreadPoolExecutor(max_workers=max(1, settings.github_max_concurrency)) as ex:
        for p, info in zip(eligible, ex.map(lambda p: gh.enrich(p.github_usernames), eligible)):
            infos[p.file] = info
    gh.flush()

    # 5) assemble results
    results: list[CandidateResult] = []
    for p in parsed:
        e = elig[p.file]
        base = dict(candidate_name=p.candidate_name, file=p.file, email=p.email, matched_skills=p.matched_skills)
        if not e.eligible:
            results.append(CandidateResult(**base, eligible=False, rejection_reasons=e.rejection_reasons,
                                           missing_requirements=_missing_requirements(e),
                                           github=GitHubInfo(status="skipped" if p.github_usernames else "not_provided",
                                                             username=p.github_usernames[0] if p.github_usernames else None,
                                                             summary="Not evaluated (candidate rejected by hard filter)")))
            continue
        sc, info = scored[p.file], infos[p.file]
        bd = dict(sc.breakdown)
        bd["github"] = round(min(float(settings.weights.github), info.activity_score + info.repo_score), 1)
        concerns = list(sc.concerns)
        if info.status == "not_provided":
            concerns.append("No GitHub profile on resume")
        elif info.status != "ok":
            concerns.append(f"GitHub not scored ({info.status})" + (f": {info.error}" if info.error else ""))
        notes = dict(sc.notes)
        notes["github"] = [info.summary] if info.status == "ok" else [f"status={info.status}: {info.error or info.summary}"]
        total = round(sum(bd.values()), 1)
        quality = build_ai_quality(sc, bd["ai_project_depth"], settings)
        trace = build_evidence_trace(p, sc, bd, info, quality, settings)
        why = build_why(quality, trace, concerns, total)
        results.append(CandidateResult(
            **base, eligible=True, total_score=total, score_breakdown=ScoreBreakdown(**bd), score_notes=notes, penalties=sc.penalties,
            project_summary=sc.project_summary, github_summary=_github_summary(info), github=info,
            strengths=sc.strengths, concerns=concerns[:6], evidence=sc.evidence,
            evidence_trace=trace, ai_project_quality=quality, why_candidate=why,
            llm_used=p.file in llm_ok, llm_error=llm_err.get(p.file),
        ))

    ranked = sorted([r for r in results if r.eligible], key=lambda r: (-r.total_score, -r.score_breakdown.ai_project_depth, r.candidate_name))
    for i, r in enumerate(ranked, 1):
        r.rank = i
    rejected = sorted([r for r in results if not r.eligible], key=lambda r: r.file)

    summary = {
        "total_files": len(files),
        "successfully_parsed": len(parsed),
        "eligible": len(ranked),
        "rejected": len(rejected),
        "failed_or_unreadable": len(failed),
        "duplicates_skipped": len(duplicates),
        "llm_mode": "hybrid (LLM + deterministic)" if llm else "deterministic only (no LLM configured)",
        "llm_failures": len(llm_err),
        "github_status_counts": _count(i.status for i in infos.values()),
    }
    return {
        "batch_summary": summary,
        "ranked_candidates": [r.model_dump(exclude_none=True) for r in ranked],
        "rejected_candidates": [r.model_dump(exclude_none=True) for r in rejected],
        "failed_files": [f.model_dump() for f in failed],
        "duplicates": duplicates,
    }


def _count(items) -> dict:
    out: dict[str, int] = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out
