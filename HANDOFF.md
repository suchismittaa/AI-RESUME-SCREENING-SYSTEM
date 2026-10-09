# HANDOFF - Phase 1 (intelligence / explainability layer)

## What already existed (preserved, not rebuilt)
Rule-based eligibility (Python + AI/agentic), deterministic 100-point scoring with per-point notes and penalties, optional
LLM project judgment blended into AI depth, GitHub enrichment with cache and circuit breaker, ranking, CLI (`main.py`),
FastAPI (`POST /screen`, `GET /results`), JSON/CSV output, 30 tests, README. Scores, eligibility and ranking are unchanged:
the regenerated `output/results.json` has identical `batch_summary`, `rank`, `total_score`, `score_breakdown` and
`rejected_candidates` to the supplied `results.json` (checked programmatically).

## What Phase 1 changed
1. **Evidence trace** (`evidence_trace`): per category score, max, explanation, signals, verbatim resume evidence with its section,
   and honest GitHub status/reason. Explains the existing scores; does not re-score.
2. **Why this candidate** (`why_candidate`): 2-4 deterministic sentences from the trace; eligible candidates only.
3. **AI project quality** (`ai_project_quality`): level, label, score, best project, signals, evidence, concerns, thin-wrapper / tutorial / skills-only flags.
   Levels 1-4 as requested plus a Level 0 for "AI named only in the skills list". Framework names alone never exceed Level 2.
4. **Comparison support** (`screener/compare.py`, `GET /compare`): rows for the frontend, per-dimension findings that say *why*, ranking explanation, warnings.
5. GitHub failures stay visible (`scored: false`, `enrichment_status`, `reason`); the existing "GitHub not scored" concern now includes the reason (e.g. `HTTP 403 ...`).

## Files
Added: `src/screener/explain.py`, `src/screener/compare.py`, `tests/test_explain.py`, `tests/test_compare.py`, `HANDOFF.md`.
Modified: `src/screener/models.py` (new models + 3 optional fields on `CandidateResult`), `src/screener/pipeline.py` (builds the new fields after scoring/GitHub),
`src/screener/scoring.py` (one line: records the effective LLM-aware thin/tutorial flags), `src/screener/api.py` (`/compare`), `src/screener/report.py`
(3 trailing CSV columns), `README.md`, `output/results.json`, `output/results.csv`.
No new dependencies.

## API / CLI
- CLI unchanged: `python main.py -i ./resumes -o ./output/results.json [--no-llm] [--no-github]`.
- `POST /screen`, `GET /results` unchanged; the new fields appear inside `ranked_candidates[]`. Rejected candidates are byte-for-byte as before.
- New: `GET /compare?candidates=candidate_35.pdf&candidates=candidate_13.pdf` (file or candidate names, 2-3). 404 before any `/screen`, 400 for bad input.

## Run
```bash
pip install -r requirements.txt
python main.py -i ./resumes -o ./output/results.json
pytest                      # 54 tests
uvicorn screener.api:app --app-dir src
```

## Validation done (Phase 1 checklist)
- 53 tests pass (30 existing + 23 new). 50/50 resumes parsed; 31 eligible, 19 rejected, 0 failed (same as before).
- 295 evidence quotes across the 31 eligible candidates were checked against the extracted resume text: 0 are not verbatim.
- All 31 eligible have `evidence_trace`, `ai_project_quality`, `why_candidate`; no rejected candidate has them.
- Comparison exercised on real pairs/triples, including a rejected candidate and legacy/malformed records.
- AI level distribution: L4 = 11, L3 = 14, L2 = 5, L1 = 1.

## Known limitations
- **GitHub:** the sandbox used for this run blocks `api.github.com` (HTTP 403), so all 30 candidates with a profile show `unavailable` and 0 GitHub points; one candidate has no profile. Re-run on a normal network (ideally with `GITHUB_TOKEN`) to populate it.
- **LLM path** was not run against the live API (no key); it is covered by fake-client tests only. With an LLM, `thin_wrapper` from the judge lowers the level, and only verbatim-verified quotes reach the trace.
- **`/compare` could not be run through FastAPI here** (PyPI is blocked in this environment, so `fastapi` was not installable). The endpoint is a thin wrapper over the unit-tested `build_comparison`; I exercised its function body with a stub `fastapi`. Please do one real `uvicorn` smoke test.
- Test runs used a pre-installed `pytest` with the system site-packages because `pip install pytest` was blocked.
- Project titles come from the existing layout heuristic. Ones that look like company/date lines are not quoted (`best_project` is empty, and `why_candidate` says "the strongest AI work (in experience)"). Evidence quotes are verbatim, so PDF glue artefacts such as `clientSiemcomby` appear as extracted.
- AI level and AI score can disagree (a Level 4 project with 16/40). The level describes which signals exist, the score reflects the original scoring philosophy; both are shown on purpose.
- Level rules and the comparison tolerance (max(1, 10% of category max)) are judgment calls; they are plain constants in `explain.py` / `compare.py`.

## Phase 2 (done): recruiter console

**Preserved:** all Phase 1 scoring, eligibility, ranking, CLI and API behaviour. Regenerated `output/results.json` has identical `batch_summary`, `rank`, `total_score` and `score_breakdown` to Phase 1 (checked programmatically).

**Backend changes (small, additive):**
- `models.py` / `pipeline.py`: rejected candidates now carry `missing_requirements` (`"Python"`, `"AI / agentic"`), taken from the eligibility result. New test in `tests/test_pipeline.py` (54 tests total).
- `api.py`: `/results` and `/compare` fall back to `output/results.json` when no `/screen` has run; new `GET /status`; serves `frontend/dist` at `/`; CORS for `localhost:5173`. `POST /screen` unchanged.

**Frontend (`frontend/`):** React 19 + esbuild (`build.mjs`), no router/UI library. `src/lib` (api, model shaping, hash router), `src/components` (KpiCard, Badge, ScoreCard/ScoreBar, AiDepthIndicator, AiProjectQuality, EvidenceBlock/EvidenceCategory, GithubPanel, Pipeline, CandidateTable/CandidateRow, ComparisonCell, SelectionTray, States), `src/views` (Dashboard, CandidateDetail, Compare, Rejected, Failed), `src/styles` (tokens, base, layout, components). `tests/model.test.mjs` (`npm test`) checks rows against `results.json`, that ranks/scores/levels are copied not recomputed, and that GitHub failures are never scored.
`frontend/dist` is committed prebuilt so the console runs with Python alone; `npm run build` regenerates it.

**Validation done:** 54 pytest tests pass; 6 frontend tests pass; real `screener/api.py` run under uvicorn (with a stand-in for FastAPI, see below) and every view loaded in headless Chromium against the real 50-resume results with no console errors (dashboard, candidate detail, compare with 3 candidates, rejected, failed, tablet width). Numbers on screen: 50 processed, 31 eligible, 19 rejected, 0 failed, average eligible score 54.6, top candidate Prathameshpatil 88.1.

**Not verified here (please check):**
- npm and PyPI were blocked, so FastAPI itself and Vite-style tooling could not be installed. The API was smoke-tested on starlette+uvicorn with a small shim implementing only the FastAPI features `api.py` uses. Run a real `uvicorn screener.api:app --app-dir src` once.
- `npm install` was not run; the bundle was built with the React 19 / esbuild copies already on the machine. `package.json` pins `react ^19.2.0`, `esbuild ^0.25.0`.
- GitHub is still `unavailable` (HTTP 403) in the bundled results; the "GitHub ok" UI branch (repos, last push, relevant repos) is implemented against the `GitHubInfo` model but has not been seen with live data.
- The compare view for a rejected candidate is not offered in the UI (picker lists eligible candidates only), though the API still accepts one.
- Filtering by AI depth "Level 0" is available but no candidate in this dataset has Level 0.

**Possible next steps:** persist `/screen` results to disk, add CSV/PDF export of a shortlist, a golden-file regression test on the 50 resumes, a live LLM run, a live GitHub run with a token.
