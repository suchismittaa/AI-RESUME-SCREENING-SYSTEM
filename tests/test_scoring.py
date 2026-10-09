from conftest import AGENTIC, SKILLS_ONLY_AI, WRAPPER, make
from screener.scoring import apply_llm, score_resume
from screener.models import ProjectJudgment


def test_agentic_project_beats_thin_wrapper(settings):
    a, w = score_resume(make(AGENTIC), settings), score_resume(make(WRAPPER), settings)
    assert a.breakdown["ai_project_depth"] >= 25
    assert w.breakdown["ai_project_depth"] <= 5
    assert w.flags["thin"] and any("thin" in p for p in w.penalties)


def test_skills_only_ai_gets_little_credit_and_penalty(settings):
    s = score_resume(make(SKILLS_ONLY_AI), settings)
    assert s.breakdown["ai_project_depth"] <= 5
    assert any("skills list" in p for p in s.penalties)


def test_python_evidence_in_project_beats_skills_list(settings):
    in_proj = score_resume(make(AGENTIC), settings).breakdown["python_backend"]
    skills = score_resume(make(SKILLS_ONLY_AI), settings).breakdown["python_backend"]
    assert in_proj > skills


def test_category_caps_respected(settings):
    b = score_resume(make(AGENTIC), settings).breakdown
    w = settings.weights
    assert b["ai_project_depth"] <= w.ai_project_depth and b["python_backend"] <= w.python_backend
    assert b["cloud_fullstack"] <= w.cloud_fullstack and b["engineering_depth"] <= w.engineering_depth


def test_every_point_is_explained(settings):
    s = score_resume(make(AGENTIC), settings)
    assert s.notes["python_backend"] and s.notes["ai_project_depth"] and s.evidence


def test_llm_blend_and_evidence_verification(settings):
    r = make(AGENTIC)
    sc = score_resume(r, settings)
    pre = sc.breakdown["ai_project_depth"]
    j = ProjectJudgment(best_project="Support Agent", ai_depth_score=10, thin_wrapper=False, summary="ok",
                        evidence=["Built a stateful multi-agent workflow in LangGraph", "this quote was invented by the model"])
    out = apply_llm(sc, j, r.text, settings)
    assert out.breakdown["ai_project_depth"] < pre  # blended toward the lower LLM score
    assert out.evidence == ["Built a stateful multi-agent workflow in LangGraph"]  # hallucinated quote dropped


def test_llm_thin_flag_applies_penalty_once(settings):
    r = make(AGENTIC)
    sc = score_resume(r, settings)
    j = ProjectJudgment(ai_depth_score=30, thin_wrapper=True)
    out = apply_llm(sc, j, r.text, settings)
    assert len(out.penalties) == 1
