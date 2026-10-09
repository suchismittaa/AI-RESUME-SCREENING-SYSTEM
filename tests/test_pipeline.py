import json

from conftest import AGENTIC, JS_ONLY, WRAPPER
from screener.github import GitHubClient
from screener.llm import LLMError
from screener.models import ProjectJudgment
from screener.pipeline import run_pipeline
from main import main


def folder(tmp_path):
    d = tmp_path / "resumes"
    d.mkdir()
    (d / "a.txt").write_text(AGENTIC)
    (d / "b.txt").write_text(WRAPPER)
    (d / "c.txt").write_text(JS_ONLY)
    (d / "dup_of_a.txt").write_text(AGENTIC)
    (d / "empty.txt").write_text("")
    (d / "corrupt.pdf").write_bytes(b"%PDF-1.4 this is not really a pdf")
    (d / "notes.xyz").write_text("ignored extension")
    return d


class FlakyLLM:
    def judge(self, name, text):
        if name == "Ravi Kumar":
            raise LLMError("boom")
        return ProjectJudgment(ai_depth_score=35, thin_wrapper=False, summary="Strong agentic system", strengths=["x"], evidence=[])


def test_batch_survives_bad_files_duplicates_and_reports_everything(tmp_path, settings):
    res = run_pipeline(folder(tmp_path), settings)
    s = res["batch_summary"]
    assert s["total_files"] == 6 and s["failed_or_unreadable"] == 2 and s["duplicates_skipped"] == 1
    assert s["eligible"] == 2 and s["rejected"] == 1
    assert {f["file"] for f in res["failed_files"]} == {"empty.txt", "corrupt.pdf"}
    ranked = res["ranked_candidates"]
    assert [r["rank"] for r in ranked] == [1, 2] and ranked[0]["candidate_name"] == "Asha Rao"
    assert res["rejected_candidates"][0]["rejection_reasons"]
    assert ranked[0]["github"]["status"] == "disabled" or ranked[0]["github"]["status"] in ("not_provided",)


def test_llm_failure_falls_back_per_resume(tmp_path, settings):
    res = run_pipeline(folder(tmp_path), settings, llm=FlakyLLM())
    by = {r["candidate_name"]: r for r in res["ranked_candidates"]}
    assert by["Asha Rao"]["llm_used"] and not by["Ravi Kumar"]["llm_used"]
    assert "boom" in by["Ravi Kumar"]["llm_error"] and by["Ravi Kumar"]["total_score"] is not None
    assert res["batch_summary"]["llm_failures"] == 1


def test_github_outage_does_not_break_batch(tmp_path, settings):
    from dataclasses import replace
    import requests

    class Down:
        headers = {}
        def get(self, *a, **k):
            raise requests.ConnectionError("down")

    s = replace(settings, github_enabled=True)
    res = run_pipeline(folder(tmp_path), s, github=GitHubClient(s, Down()))
    assert res["batch_summary"]["eligible"] == 2
    assert any("GitHub not scored" in c for r in res["ranked_candidates"] for c in r["concerns"] if r["github"]["username"])


def test_cli_writes_json_and_csv(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = tmp_path / "o" / "results.json"
    assert main(["-i", str(folder(tmp_path)), "-o", str(out), "--no-github", "--no-llm"]) == 0
    data = json.loads(out.read_text())
    assert set(data) >= {"batch_summary", "ranked_candidates", "rejected_candidates", "failed_files"}
    assert out.with_suffix(".csv").exists()
    assert main(["-i", str(tmp_path / "missing"), "-o", str(out)]) == 2


def test_rejected_candidates_name_the_missing_requirement(tmp_path, settings):
    from conftest import JS_ONLY
    from screener.pipeline import run_pipeline
    d = tmp_path / "r"
    d.mkdir()
    (d / "js.txt").write_text(JS_ONLY)
    rej = run_pipeline(d, settings)["rejected_candidates"][0]
    assert rej["missing_requirements"], "a rejected candidate must say which requirement had no evidence"
    assert set(rej["missing_requirements"]) <= {"Python", "AI / agentic"}
