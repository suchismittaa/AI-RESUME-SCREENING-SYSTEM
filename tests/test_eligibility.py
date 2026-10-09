import pytest

from conftest import AGENTIC, CLASSICAL_ML, COPILOT_ONLY, JS_ONLY, PYTHON_NO_AI, WRAPPER, make
from screener.eligibility import check_eligibility


def test_python_plus_agentic_is_eligible():
    r = check_eligibility(make(AGENTIC))
    assert r.eligible and not r.rejection_reasons
    assert "Python" in r.python_evidence and "LangGraph" in r.ai_evidence


def test_js_only_profile_rejected_even_with_llm_ui():
    r = check_eligibility(make(JS_ONLY))
    assert not r.eligible
    assert any("Python" in x for x in r.rejection_reasons)


def test_python_without_ai_rejected():
    r = check_eligibility(make(PYTHON_NO_AI))
    assert not r.eligible and any("AI" in x for x in r.rejection_reasons)


def test_ai_coding_assistant_is_not_ai_project_evidence():
    assert not check_eligibility(make(COPILOT_ONLY)).eligible


def test_classical_ml_only_rejected_with_specific_reason():
    r = check_eligibility(make(CLASSICAL_ML))
    assert not r.eligible and "classical ML" in r.rejection_reasons[0]


def test_react_alongside_python_and_ai_is_fine():
    assert check_eligibility(make(AGENTIC + "\nReact, Next.js, Java")).eligible


def test_generic_llm_api_project_counts():
    assert check_eligibility(make(WRAPPER)).eligible  # eligible, but must score low (see scoring tests)


def test_substring_false_positive_capgemini_is_not_gemini():
    t = "Bo\nSKILLS\nPython, Java\nEXPERIENCE\n• Completed a Capgemini-sponsored Java program and built Flask services for clients over six months."
    assert not check_eligibility(make(t)).eligible


def test_glued_pdf_text_still_matches():
    t = "Zed\nEXPERIENCE\n• Engineered buildingRAGpipelines with LangGraph and FastAPI on Python for production use cases."
    assert check_eligibility(make(t)).eligible
