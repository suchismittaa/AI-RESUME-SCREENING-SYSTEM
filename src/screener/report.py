"""Output writers: JSON (primary), CSV (flat), and a compact terminal table."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def write_json(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))


def write_csv(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["rank", "candidate_name", "file", "eligible", "total_score", "ai_project_depth", "python_backend", "cloud_fullstack", "github", "engineering_depth", "github_status", "reasons", "ai_depth_level", "ai_depth_label", "why_candidate"]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for c in result["ranked_candidates"] + result["rejected_candidates"]:
            bd = c.get("score_breakdown", {})
            w.writerow({"rank": c.get("rank", ""), "candidate_name": c["candidate_name"], "file": c["file"], "eligible": c["eligible"],
                        "total_score": c.get("total_score", ""), **{k: bd.get(k, "") for k in cols[5:10]},
                        "github_status": c.get("github", {}).get("status", ""), "reasons": "; ".join(c.get("rejection_reasons", [])),
                        "ai_depth_level": c.get("ai_project_quality", {}).get("level", ""), "ai_depth_label": c.get("ai_project_quality", {}).get("label", ""),
                        "why_candidate": c.get("why_candidate", "")})


def format_table(result: dict, top: int = 15) -> str:
    s = result["batch_summary"]
    lines = [
        f"Resumes: {s['total_files']} | parsed: {s['successfully_parsed']} | eligible: {s['eligible']} | rejected: {s['rejected']} | failed: {s['failed_or_unreadable']} | duplicates: {s['duplicates_skipped']}",
        f"Mode: {s['llm_mode']} | GitHub: {s['github_status_counts']}",
        "",
        f"{'#':>2} {'Candidate':<26}{'Total':>6} {'AI/40':>6} {'Py/30':>6} {'Cld/15':>6} {'GH/10':>6} {'Eng/5':>6}  File",
    ]
    for c in result["ranked_candidates"][:top]:
        b = c["score_breakdown"]
        lines.append(f"{c['rank']:>2} {c['candidate_name'][:25]:<26}{c['total_score']:>6} {b['ai_project_depth']:>6} {b['python_backend']:>6} {b['cloud_fullstack']:>6} {b['github']:>6} {b['engineering_depth']:>6}  {c['file']}")
    return "\n".join(lines)
