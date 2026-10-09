import copy

import pytest

from conftest import AGENTIC, WRAPPER
from screener.compare import build_comparison, compare_candidates, find_candidates
from screener.pipeline import run_pipeline

BACKEND_HEAVY = """Omar Ali
omar@example.com
PROJECTS
Doc Q&A | Python, FastAPI, PostgreSQL, Redis, Docker, GCP
• Built a retrieval-augmented generation service with embeddings and pgvector search behind async FastAPI, with Redis caching, pytest tests and Cloud Run deployment.
SKILLS
Python, FastAPI, PostgreSQL, Redis, Docker, GCP
"""
JS = "Jo Smith\njo@example.com\nSKILLS\nJavaScript, React, Java\nEXPERIENCE\nFrontend Developer\n• Built React dashboards for a retail client.\n"


@pytest.fixture
def result(tmp_path, settings):
    d = tmp_path / "r"
    d.mkdir()
    for n, t in (("a", AGENTIC), ("w", WRAPPER), ("o", BACKEND_HEAVY), ("j", JS)):
        (d / f"{n}.txt").write_text(t)
    return run_pipeline(d, settings)


def test_comparison_has_all_dimensions_and_fields(result):
    cmp = build_comparison(result, ["a.txt", "w.txt"])
    assert [d["key"] for d in cmp["dimensions"]] == ["ai_project_depth", "python_backend", "cloud_fullstack", "github", "engineering_depth"]
    row = cmp["candidates"][0]
    for k in ("candidate_name", "eligible", "final_score", "scores", "ai_depth_level", "ai_project_quality", "strengths", "concerns", "evidence", "github_status"):
        assert k in row
    assert set(row["scores"]) == {"ai_project_depth", "python_backend", "cloud_fullstack", "github", "engineering_depth"}


def test_comparison_explains_why_not_just_who_is_better(result):
    cmp = build_comparison(result, ["Asha Rao", "Ravi Kumar"])
    ai = next(d for d in cmp["dimensions"] if d["key"] == "ai_project_depth")
    assert ai["leader"] == "a.txt" and "Level 4" in ai["finding"] and "Level 1" in ai["finding"] and "demonstrates" in ai["finding"]
    assert any("scores" in r and "above" in r and "mainly from" in r for r in cmp["ranking_explanation"])
    assert not any(f.strip().lower().endswith("is better.") for f in cmp["findings"])


def test_comparable_dimensions_are_called_comparable(result):
    cmp = build_comparison(result, ["a.txt", "o.txt"])
    assert any("comparable" in d["finding"] for d in cmp["dimensions"])


def test_github_missing_is_not_compared(result):
    cmp = build_comparison(result, ["a.txt", "o.txt"])
    gh = next(d for d in cmp["dimensions"] if d["key"] == "github")
    assert gh["leader"] is None and "not comparable" in gh["finding"]


def test_three_candidates_and_bounds(result):
    cmp = build_comparison(result, ["a.txt", "o.txt", "w.txt"])
    assert len(cmp["candidates"]) == 3 and len(cmp["ranking_explanation"]) == 2
    with pytest.raises(ValueError):
        build_comparison(result, ["a.txt"])
    with pytest.raises(ValueError):
        build_comparison(result, ["a.txt", "o.txt", "w.txt", "j.txt"])
    with pytest.raises(ValueError):
        build_comparison(result, ["a.txt", "a.txt"])
    with pytest.raises(ValueError, match="Unknown"):
        build_comparison(result, ["a.txt", "nobody.pdf"])


def test_rejected_candidate_is_listed_but_excluded(result):
    cmp = build_comparison(result, ["a.txt", "j.txt", "o.txt"])
    assert {r["file"]: r["eligible"] for r in cmp["candidates"]}["j.txt"] is False
    assert any("excluded" in w for w in cmp["warnings"]) and len(cmp["ranking_explanation"]) == 1
    only_one = build_comparison(result, ["a.txt", "j.txt"])
    assert only_one["dimensions"] == [] and only_one["warnings"]


def test_malformed_and_legacy_records_do_not_crash():
    legacy = {"file": "x.pdf", "candidate_name": "X", "eligible": True, "total_score": 50, "score_breakdown": {"ai_project_depth": 30, "python_backend": 10},
              "score_notes": {"python_backend": ["FastAPI: +6 (in projects/experience)"]}}
    broken = {"file": "y.pdf", "candidate_name": "Y", "eligible": True, "total_score": "n/a", "score_breakdown": None, "score_notes": "oops", "strengths": None, "evidence_trace": "bad"}
    empty = {"candidate_name": "Z"}
    cmp = compare_candidates([legacy, broken, empty])
    assert len(cmp["candidates"]) == 3 and cmp["warnings"]
    cmp2 = compare_candidates([legacy, copy.deepcopy(legacy) | {"file": "x2.pdf", "candidate_name": "X2", "total_score": 40, "score_breakdown": {"ai_project_depth": 10}}])
    assert cmp2["dimensions"] and any("no evidence trace" in w for w in cmp2["warnings"])
    assert find_candidates({"ranked_candidates": [legacy, copy.deepcopy(legacy) | {"file": "q.pdf"}]}, ["X", "q.pdf"])[0]["file"] == "x.pdf"
    with pytest.raises(ValueError):
        build_comparison({}, ["a", "b"])
