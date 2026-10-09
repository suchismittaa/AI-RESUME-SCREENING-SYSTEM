import re

import pytest
import requests
from dataclasses import replace

from conftest import AGENTIC, SKILLS_ONLY_AI, WRAPPER, make
from screener.explain import AI_LEVELS, build_why, classify_ai_level, github_trace
from screener.github import GitHubClient
from screener.models import GitHubInfo
from screener.pipeline import run_pipeline

APPLIED = """Dev Patel
dev@example.com
PROJECTS
Invoice Summariser | Python, FastAPI, OpenAI API, PostgreSQL
• Built a service that ingests uploaded PDF invoices, parses the text, calls the OpenAI API to summarise each one and stores results in PostgreSQL behind a REST backend.
SKILLS
Python, FastAPI, PostgreSQL, OpenAI API
"""

FRAMEWORK_ONLY = """Nina Roy
nina@example.com
PROJECTS
Demo app | Python, LangGraph
• Made a small LangGraph demo.
SKILLS
Python, LangGraph, LangChain
"""


def _run(tmp_path, settings, **texts):
    d = tmp_path / "r"
    d.mkdir()
    for name, t in texts.items():
        (d / f"{name}.txt").write_text(t)
    res = run_pipeline(d, settings)
    return {c["file"]: c for c in res["ranked_candidates"]}, res


def _norm(t):
    return re.sub(r"\s+", " ", t).strip().lower()


# ------------------------------------------------------------------ evidence trace
def test_every_category_has_score_max_and_explanation(tmp_path, settings):
    by, _ = _run(tmp_path, settings, a=AGENTIC)
    tr = by["a.txt"]["evidence_trace"]
    assert set(tr) == {"ai_project_depth", "python_backend", "cloud_fullstack", "github", "engineering_depth"}
    bd = by["a.txt"]["score_breakdown"]
    for k, v in tr.items():
        assert v["score"] == bd[k] and v["max_score"] > 0 and v["explanation"]
    assert tr["python_backend"]["signals"] and tr["engineering_depth"]["signals"]


def test_evidence_is_verbatim_resume_text(tmp_path, settings):
    by, _ = _run(tmp_path, settings, a=AGENTIC, b=APPLIED)
    for f, text in (("a.txt", AGENTIC), ("b.txt", APPLIED)):
        for cat, v in by[f]["evidence_trace"].items():
            if cat == "github":
                continue
            assert v["evidence"] or cat in ("cloud_fullstack", "engineering_depth")
            for e in v["evidence"]:
                assert _norm(e["text"]) in _norm(text), (cat, e)


def test_missing_evidence_is_reported_not_invented(tmp_path, settings):
    by, _ = _run(tmp_path, settings, w=WRAPPER)
    tr = by["w.txt"]["evidence_trace"]
    assert tr["cloud_fullstack"]["score"] == 0 and tr["cloud_fullstack"]["evidence"] == []
    assert "No evidence found for" in tr["cloud_fullstack"]["explanation"]
    assert tr["engineering_depth"]["evidence"] == [] and "no testing" in tr["engineering_depth"]["explanation"]


# ------------------------------------------------------------------ AI depth
def test_agentic_system_is_level_4(tmp_path, settings):
    q = _run(tmp_path, settings, a=AGENTIC)[0]["a.txt"]["ai_project_quality"]
    assert q["level"] == 4 and q["label"] == AI_LEVELS[4] and not q["thin_wrapper"]
    assert any(s.startswith("retrieval/RAG") for s in q["implementation_signals"]) and q["evidence"]
    assert q["score"] == 40 or q["score"] > 30


def test_thin_wrapper_is_level_1_and_flagged(tmp_path, settings):
    c = _run(tmp_path, settings, w=WRAPPER)[0]["w.txt"]
    q = c["ai_project_quality"]
    assert q["level"] == 1 and q["thin_wrapper"] and q["quality_concerns"]
    assert "thin LLM/API wrapper" in c["why_candidate"]


def test_applied_ai_is_level_2(tmp_path, settings):
    assert _run(tmp_path, settings, b=APPLIED)[0]["b.txt"]["ai_project_quality"]["level"] == 2


def test_framework_name_alone_never_reaches_level_3_or_4(tmp_path, settings):
    assert classify_ai_level({"orchestration/multi-agent framework": ["langgraph"]}, thin=False) == 2
    assert classify_ai_level({"LLM framework (LangChain/LlamaIndex)": ["langchain"], "backend integration": ["fastapi"]}, thin=False) == 2
    c = _run(tmp_path, settings, n=FRAMEWORK_ONLY)[0]["n.txt"]
    assert c["ai_project_quality"]["level"] <= 2


def test_skills_list_only_is_level_0(tmp_path, settings):
    c = _run(tmp_path, settings, s=SKILLS_ONLY_AI)[0]["s.txt"]
    q = c["ai_project_quality"]
    assert q["level"] == 0 and q["skills_only"] and q["best_project"] == ""
    assert "skills list" in c["why_candidate"]


def test_level_rules():
    full = {"agentic/tool-use": ["agent"], "retrieval/RAG": ["rag"], "evaluation": ["eval"]}
    assert classify_ai_level(full, False) == 4
    assert classify_ai_level({"agentic/tool-use": ["agent"], "backend integration": ["fastapi"]}, False) == 3
    assert classify_ai_level({"retrieval/RAG": ["rag"]}, False) == 2
    assert classify_ai_level(full, True) == 1  # thin flag (deterministic or LLM) caps the level
    assert classify_ai_level(None, False) == 0


def test_llm_thin_flag_lowers_level(tmp_path, settings):
    from screener.models import ProjectJudgment

    class ThinLLM:
        def judge(self, name, text):
            return ProjectJudgment(ai_depth_score=5, thin_wrapper=True, summary="just an API call", evidence=["Made-up quote that is not in the resume"])

    d = tmp_path / "r"; d.mkdir(); (d / "a.txt").write_text(AGENTIC)
    c = run_pipeline(d, settings, llm=ThinLLM())["ranked_candidates"][0]
    assert c["ai_project_quality"]["thin_wrapper"] and c["ai_project_quality"]["level"] == 1
    assert all("Made-up quote" not in e["text"] for e in c["evidence_trace"]["ai_project_depth"]["evidence"])  # invented quotes never reach the trace


# ------------------------------------------------------------------ why this candidate
def test_why_candidate_is_specific_and_short(tmp_path, settings):
    by, res = _run(tmp_path, settings, a=AGENTIC, w=WRAPPER)
    why = by["a.txt"]["why_candidate"]
    assert 2 <= len(re.findall(r"[.!?](?:\s|$)", why)) <= 5
    assert "Support Agent" in why and "Level 4" in why and "FastAPI" in why
    assert by["w.txt"]["why_candidate"] != why
    assert "Excellent candidate" not in why


def test_why_candidate_only_for_eligible(tmp_path, settings):
    _, res = _run(tmp_path, settings, a=AGENTIC)
    d = tmp_path / "r2"; d.mkdir()
    (d / "j.txt").write_text("Jo Smith\njo@example.com\nSKILLS\nJavaScript, React, Next.js, Node.js, Java\nEXPERIENCE\nFrontend Developer\n• Built React dashboards for a retail client.\n")
    r = run_pipeline(d, settings)
    assert r["rejected_candidates"] and "why_candidate" not in r["rejected_candidates"][0] and "evidence_trace" not in r["rejected_candidates"][0]


# ------------------------------------------------------------------ GitHub honesty
def test_github_unavailable_is_visible_and_not_scored():
    t = github_trace(GitHubInfo(status="unavailable", username="x", error="HTTP 403 (GitHub disabled for the rest of this run)", summary="GitHub enrichment unavailable: HTTP 403"), 0, 10)
    assert t.scored is False and t.enrichment_status == "unavailable" and "HTTP 403" in t.reason
    assert "Reason: HTTP 403" in t.explanation and "not a negative evaluation" in t.explanation and t.evidence == []


def test_github_ok_has_evidence_and_missing_profile_is_not_an_error():
    ok = github_trace(GitHubInfo(status="ok", username="x", profile_url="https://github.com/x", summary="last push 3d ago", relevant_repos=["rag-bot"], activity_score=4, repo_score=3), 7, 10)
    assert ok.scored and ok.score == 7 and [e.source for e in ok.evidence] == ["github", "github"]
    none = github_trace(GitHubInfo(status="not_provided"), 0, 10)
    assert none.scored is False and "No GitHub profile" in none.reason
    assert github_trace(None, 0, 10).scored is False  # missing data never crashes


def test_pipeline_github_outage_appears_in_trace_and_why(tmp_path, settings):
    class Down:
        headers = {}
        def get(self, *a, **k):
            raise requests.ConnectionError("down")

    s = replace(settings, github_enabled=True)
    d = tmp_path / "r"; d.mkdir(); (d / "a.txt").write_text(AGENTIC)
    c = run_pipeline(d, s, github=GitHubClient(s, Down()))["ranked_candidates"][0]
    gh = c["evidence_trace"]["github"]
    assert gh["scored"] is False and gh["enrichment_status"] == "unavailable" and gh["reason"]
    assert "GitHub could not be assessed" in c["why_candidate"]
    assert any("GitHub not scored" in x for x in c["concerns"])


def test_ranking_and_scores_unchanged_by_explainability(tmp_path, settings):
    by, _ = _run(tmp_path, settings, a=AGENTIC, w=WRAPPER)
    for c in by.values():
        assert round(sum(c["score_breakdown"].values()), 1) == c["total_score"]
