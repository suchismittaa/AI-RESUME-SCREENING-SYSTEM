# AI Resume Screening & Ranking

Ingests a folder of resumes, applies a **rule-based Python + AI/agentic eligibility filter**, scores eligible
candidates on a transparent 100-point model, enriches with public GitHub activity, and writes a ranked,
evidence-backed shortlist (`results.json` + `results.csv`).

## Setup & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add ANTHROPIC_API_KEY and/or GITHUB_TOKEN

python main.py --input ./resumes --output ./output/results.json
python main.py -i ./resumes --no-llm --no-github      # fully offline/deterministic
pytest                                                # 54 tests, no network needed

# recruiter console (see "Run the full system" below)
cd frontend && npm install && npm run build && cd ..
uvicorn screener.api:app --app-dir src                # open http://127.0.0.1:8000
```

Without any keys the pipeline runs deterministically (no LLM, GitHub via the unauthenticated API).
PDF is required and supported (with a second extractor used automatically for letter-spaced / one-word-per-line
PDFs); DOCX, TXT and MD are also accepted.

### Output (`output/results.json`)
```
batch_summary         total files, parsed, eligible, rejected, failed/unreadable, duplicates, LLM mode, GitHub status counts
ranked_candidates[]   rank, total_score, score_breakdown, score_notes (why each point was given), penalties,
                      matched_skills, project_summary, evidence (verbatim quotes), strengths, concerns, github{...},
                      evidence_trace{...}, ai_project_quality{...}, why_candidate   (see the three sections below)
rejected_candidates[] explicit rejection_reasons + matched_skills
failed_files[]        unreadable/corrupt files with the error
duplicates[]          files skipped because their text duplicates another resume
```

## Evidence Trace
Every eligible candidate carries `evidence_trace` with one entry per score category (`ai_project_depth`, `python_backend`,
`cloud_fullstack`, `github`, `engineering_depth`). Each entry has `score`, `max_score`, a plain-language `explanation`,
the detected `signals`, the existing per-point `notes`, and `evidence[]` items `{signal, text, source}`.
- It **explains the existing score; it does not re-score**. `evidence_trace.<cat>.score` always equals `score_breakdown.<cat>`.
- `text` is a verbatim line from the resume (whitespace-normalised) and `source` is the resume section it came from
  (`projects`, `experience`, `skills`, ...). Quotes are located by the same lexicon patterns the scorer uses, and are dropped
  unless they literally occur in the resume text. LLM-supplied quotes were already filtered the same way. Nothing is generated.
- When a category has no support the trace says so (`No evidence found for: Redis, ...`) with an empty `evidence` list.
- **GitHub** evidence comes only from the real GitHub lookup. When it fails the entry has `scored: false`,
  `enrichment_status` (e.g. `unavailable`, `rate_limited`, `not_provided`) and `reason` (e.g. `HTTP 403 ...`), and the
  explanation states that 0 points mean *missing data, not a negative evaluation*. GitHub is never an eligibility requirement.

## AI Project Quality
`ai_project_quality` exposes the existing AI-project judgment (same score, same penalties) as a level, derived from the signals
the deterministic scorer found in the strongest AI project (plus the thin-wrapper flag, which is also set when the optional LLM judge says so):

| Level | Label | Rule (signal groups detected in the best AI project) |
|---|---|---|
| 0 | No implementation evidence | AI frameworks appear only in the skills list (an addition to the four requested levels, so such candidates are not mislabelled "Level 1") |
| 1 | Thin LLM/API Wrapper | existing thin-wrapper flag: an LLM call with no retrieval, agents, state, evaluation or data+backend logic |
| 2 | Applied AI | real AI use that does not reach the rules below (e.g. a framework name only, retrieval alone, a data+backend workflow around an LLM) |
| 3 | RAG / AI System | explicit agent/tool-use language **plus** a supporting signal, or retrieval **plus** another supporting signal, or an orchestration/LLM framework **plus** two supporting signals including state/retrieval/evaluation |
| 4 | Agentic / Advanced AI System | explicit agent/tool-use language, plus at least two supporting signals (retrieval, state/memory, evaluation, backend integration, data pipeline) of which one is retrieval, state or evaluation |

Framework names (LangChain, LangGraph, ...) never raise the level on their own. The object also carries `score` (post-penalty, /40),
`best_project` (empty when the detected title is a company/date line rather than a project name), `summary`, `implementation_signals`,
`evidence`, `quality_concerns`, `thin_wrapper`, `tutorial_style` and `skills_only`. The level is a presentation of the evidence and
does not change the score; the two can differ (e.g. a Level 4 project that is short on detail can still score 16/40).

## Why This Candidate
`why_candidate` (eligible candidates only) is 2-4 sentences assembled by deterministic templates from the evidence trace and AI quality
objects: the strongest AI project and its level/signals and AI score, the backend technologies demonstrated in projects/experience,
deployment and engineering-practice evidence, and finally either the main caveat or the GitHub status. No LLM text is used and
nothing is asserted that is not in the trace. `strengths` and `concerns` are unchanged (plus the GitHub failure reason in `concerns`).

## Candidate Comparison
`GET /compare?candidates=<file or name>&candidates=<file or name>[&candidates=...]` (2-3 candidates, from the last `/screen` result;
`screener.compare.build_comparison(results_dict, ids)` does the same in code). It returns:
- `candidates[]`: name, rank, eligibility, final score, per-dimension scores and signals, AI depth level/label and quality, GitHub status/reason,
  strengths, concerns, evidence, `why_candidate`.
- `dimensions[]`: for AI depth, Python/backend, Cloud/full-stack, GitHub and Engineering depth: scores, leader(s) or `comparable` (within max(1, 10% of the
  category max)), and a `finding` sentence naming what the leader demonstrates that the other does not (and the AI level when it differs).
- `ranking_explanation[]`: for each adjacent pair, the point gap and which dimensions produce it and which offset it.
- `warnings[]`: ineligible candidates (listed but excluded from the numbers), records without an evidence trace, and so on. If a candidate has no GitHub
  score the GitHub dimension is reported as not comparable instead of being treated as a loss.
Unknown identifiers or a wrong candidate count give HTTP 400 (`ValueError` in code). The console's Compare view is driven by this endpoint.

## Run the full system (backend + recruiter console)

```bash
# 1. Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                   # optional keys

# 2. Screen the resumes (writes output/results.json and output/results.csv)
python main.py -i ./resumes -o ./output/results.json

# 3. Frontend (Node 18+). Only react, react-dom and esbuild are needed; there is no dev server to configure.
cd frontend && npm install && npm run build && cd ..   # a prebuilt frontend/dist is also included

# 4. Serve API + console on one port
uvicorn screener.api:app --app-dir src                 # http://127.0.0.1:8000
```

While editing the UI run `npm run dev` in `frontend/` (esbuild watch, rebuilds `dist/` on save) next to uvicorn and reload the page.
`npm test` runs the frontend data tests against `output/results.json`. `pytest` runs the backend tests.
Scores are read from `output/results.json` until you run a new screening, so the console works straight after step 2. `POST /screen` (see below) re-runs the pipeline from the API and replaces what the console shows.

## Architecture

```
resumes/ -> main.py / POST /screen -> screener pipeline -> output/results.json
                                              |
                       FastAPI (screener/api.py): GET /results, /compare, /status, POST /screen, serves frontend/dist
                                              |
                       React console (frontend/): dashboard, candidate detail, compare, rejected, failed
```

The frontend is a pure presentation layer. It does not score, rank, judge eligibility or write explanations; it renders what the backend produced
(`rank`, `total_score`, `score_breakdown`, `ai_project_quality`, `evidence_trace`, `why_candidate`, `strengths`, `concerns`, and the `/compare` findings).
The only things computed in the browser are display aggregates: the average eligible score on the dashboard and sorting/filtering of the table.

### API
| Endpoint | Purpose |
|---|---|
| `POST /screen` `{"input_dir": "./resumes"}` | run the pipeline, store and return the result |
| `GET /results` | last live result, else the saved `output/results.json`; 404 if neither exists |
| `GET /status` | `{has_results, source: "live run" \| "saved file" \| "none", results_path}` |
| `GET /compare?candidates=a.pdf&candidates=b.pdf` | comparison data for 2-3 candidates |
| `GET /` | the console (`frontend/dist`) |

Environment overrides: `RESULTS_PATH` (default `output/results.json`), `FRONTEND_DIST` (default `frontend/dist`).

## Frontend Features
- **Dashboard:** KPI cards (processed, eligible, rejected, failed, average eligible score, top candidate), a pipeline strip with this batch's real counts, and the ranked table with search, sortable columns, eligibility filter, AI-depth filter and minimum-score filter.
- **Candidate detail:** identity and resume file, ELIGIBLE / REJECTED, final score, "Why this candidate?", strengths, concerns, "What could change this ranking?", score breakdown, AI project quality, evidence trace, GitHub panel and matched skills.
- **Compare:** tick 2-3 eligible candidates (a tray appears), then *Compare candidates*. Side-by-side columns with subtle "Leads" highlights, then a comparison summary taken from the backend.
- **Rejected:** every rejected candidate with the rule-based reason and the missing requirement (`missing_requirements`, new in Phase 2).
- **Failed:** unreadable files with the error, plus skipped duplicates. An empty list says so explicitly.
- Keyboard-reachable controls, visible focus, `prefers-reduced-motion` respected, desktop-first layout that stays usable on tablet.

### Evidence trace in the UI
Each category shows the score (`AI / Agentic / RAG: 38 / 40`), then **Evidence** (verbatim resume quotes tagged with the signal they support and the resume section they came from), then **Explanation** (the backend's plain-language reason, the detected signals, and an expandable list of how each point was earned). Categories with no support say so instead of showing anything. "What could change this ranking?" only quotes backend text: GitHub not assessed, categories whose explanation lists missing evidence, applied penalties and AI project concerns.

### AI project quality in the UI
A four-step indicator marks the level (Level 0, "no implementation evidence", leaves all steps empty), followed by the strongest AI project, its summary, implementation signals, evidence quotes, quality concerns and the thin-wrapper / tutorial-style / skills-only checks. When the backend could not identify a project title the UI says so rather than guessing one.

### Candidate comparison in the UI
Leaders per category come from the backend's `dimensions[].leaders`; categories within tolerance are "comparable", not ranked. GitHub is shown as unavailable (with the reason) instead of as a loss. The summary lists the backend's evidence-based findings and why the ranking order is what it is, with a reminder that a higher total is not automatically a better fit.

## Frontend Design Decisions
- **Palette:** only `#3E3232`, `#7E5F66`, `#FFBC9F`, `#F29A65`, `#F8C53C`, `#FFFFFF` and transparencies of them (tokens in `frontend/src/styles/tokens.css`). Yellow is reserved for rank 1, the final score, selection and the primary action; orange means "attention" (unavailable GitHub, concerns, failures). There are no green/red status colours: states are carried by words and shape as well as colour.
- **Glass:** translucent surfaces with a soft peach border and 14px blur on KPI cards, filters, tables, panels, evidence and comparison; solid brown behind everything keeps text contrast.
- **No external assets:** system font stack, inline icon, no CDN calls, so the console works offline.
- **Build:** React 19 bundled by a 30-line esbuild script instead of a larger toolchain. The frontend is plain JavaScript with a hash router, so there is nothing else to install or configure.

## Why the system prioritises evidence and explainability
A ranked list is only useful to a recruiter if they can check it. Every point therefore has a note, every claim in the trace is a verbatim resume quote, missing data (GitHub) is shown as missing rather than as a low score, rejections name the rule that failed, and comparisons say what one candidate demonstrates that another does not. The aim is: measure, explain, rank, compare.

## Limitations
- GitHub enrichment was blocked (HTTP 403) in the environment that produced the bundled `results.json`, so all 30 candidates with a profile show "unavailable" and totals are effectively out of 90. Re-run on a normal network (ideally with `GITHUB_TOKEN`).
- The LLM path has not been run against the live API (no key); the bundled results are deterministic-only.
- `POST /screen` runs synchronously and keeps its result in memory only; the CLI-written `results.json` is what survives a restart.
- The console shows one results set at a time and has no accounts, saved shortlists or export; use `results.csv` for export.
- The frontend and the API were verified in a sandbox without access to npm/PyPI: the bundle was built with a locally available React/esbuild, and the API was run with a minimal stand-in for FastAPI. Please do one normal `npm install && npm run build` and `uvicorn` run on your machine.

## Pipeline
`ingest.py` → `extract.py` (name/email/GitHub/sections/skills) → `eligibility.py` (hard filter) → `scoring.py`
(deterministic) → `llm.py` (optional judgment, blended) → `github.py` (enrichment, cached) → `explain.py` (evidence trace, AI level, why-candidate) → `pipeline.py` (rank/assemble) → `report.py`; `compare.py` builds comparisons on demand.
Weights, penalties, model name, concurrency and thresholds live in `config.py`/env; keyword lists in `lexicon.py` (pure data).

## Design Decisions

**Filtering (rules only, never the LLM).** A candidate is eligible only with *both*:
1. *Python evidence* — "Python" (or a Python-only ecosystem such as FastAPI/Django/LangChain/pandas) in skills, projects, experience or summary. Education, coursework and certification sections don't count, so a Java/React-only profile or a "Python (coursework)" mention is rejected.
2. *AI/agentic evidence* — strong signals (LangGraph, LangChain, LlamaIndex, ADK, CrewAI, RAG, embeddings/vector search, tool calling, multi-agent, fine-tuning, evals, Transformers) count anywhere; weaker generic signals (OpenAI/Gemini/LLM/chatbot) count only when they appear in a project/experience, not just a skills list.
   Deliberately **not** evidence: "AI-assisted development", Copilot/Claude Code usage, and classical ML/CV only (scikit-learn, CNNs, TensorFlow image classifiers). Those candidates are rejected with a specific reason ("only classical ML/CV"). This is a judgment call — flip it in `lexicon.py` if you want ML-only profiles to pass.
   JS/Java/React alongside Python + AI is fine.

**Scoring (deterministic baseline, 100 pts; every point has a note).** Evidence in projects/experience earns full credit, evidence only in a skills list earns 40%.
- *AI project depth (40):* resumes are split into project/experience "units"; the best AI unit is scored on orchestration frameworks, retrieval/RAG, agentic/tool use, state/memory, evaluation, fine-tuning, data pipeline, backend integration and quantified outcomes (+ up to 5 for a second solid AI project). **Penalties:** −10/−15 if the best AI project is a thin LLM-API wrapper (no retrieval/agents/state/eval/data+backend logic), −5 for tutorial-style markers, −5 when AI frameworks are only named in a skills list. So a strong Python engineer with no real AI project scores low on the biggest category and can't reach the top.
- *Python & backend (30):* Python, FastAPI (Flask/Django at 60%), async, PostgreSQL, Redis, other backend signals.
- *Cloud/deploy/full-stack (15):* GCP (other clouds at 60%), Docker, deployment/CI-CD, React/Next.js only as a supporting signal when a backend is present.
- *Engineering depth (5):* one point per distinct category found in project/experience text: testing, architecture, caching, queues, observability, concurrency, failure handling.
- *GitHub (10):* see below.

**LLM usage.** Optional (`ANTHROPIC_API_KEY`). One call per *eligible* resume returns a validated Pydantic `ProjectJudgment` (forced tool call with the schema): depth 0-40, thin-wrapper/tutorial flags, summary, strengths, concerns, verbatim evidence quotes. Final AI depth = `(1-w)·deterministic + w·LLM` (w = `LLM_BLEND_WEIGHT`, default 0.5); penalties apply once if either judge flags the project. Evidence quotes are kept only if they literally occur in the resume. Resume text is treated as untrusted (prompt says to ignore instructions inside it). Provider code is isolated behind `LLMClient`/`AnthropicJudge`. Any failure (API error, invalid output) is recorded per resume (`llm_error`) and that candidate keeps the deterministic score. **The LLM-enabled path was exercised only with a fake client in tests, not against the live API** — no key was available when this was built.

**GitHub scoring (max 10 = 5 activity + 5 repos).** Usernames come from PDF hyperlinks first, then visible text (profile or repo URLs; several handles are tried in order). Activity (0-5): recency of last push (≤30d 3, ≤90d 2, ≤180d 1) + volume (repos pushed in 90d, or push events if a token is set). Repos (0-5): maintained original (non-fork, non-archived) repos pushed in 12 months (1/3/6 → 1/2/3) + Python/AI-relevant ones (1/3 → 1/2). Missing profile → 0 and a "No GitHub profile" note, never a failure. 404 / rate limit / outage → status recorded, batch continues; a circuit breaker stops calling GitHub after 3 consecutive hard failures or the first rate-limit. One request per user unauthenticated (fits the 60/h limit for ~50 resumes); results are cached in memory and in `.cache/github.json` (24 h TTL), so re-running fills in anyone skipped. Only eligible candidates are enriched.
Trade-off: candidates without a GitHub link lose up to 10 points relative to active ones; that matches the rubric's "additional positive signal" but is worth knowing when comparing close scores.

**Robustness.** One bad file never stops the batch (corrupt/encrypted/empty/scanned → `failed_files`); duplicate content is detected by hash; PDF hyperlink annotations are read (they hold the real GitHub/email when the visible text is just "GitHub"); mixed-case, glued-word PDF text is handled by permissive patterns.

## Notes on the provided dataset run
`output/results.json` was generated in a sandbox where `api.github.com` is blocked, so **every GitHub status is `unavailable` and GitHub points are 0 in that file** — scores are therefore out of 90 effective. Re-run `python main.py -i resumes -o output/results.json` on a normal network (ideally with `GITHUB_TOKEN`) to include them. It was also produced without an LLM key (deterministic mode). The Phase 1 regeneration of `output/` had the same constraints (GitHub answered HTTP 403, no LLM key), and the GitHub failure is kept visible in `github`, `evidence_trace.github` and `concerns`. `results.csv` gained three trailing columns: `ai_depth_level`, `ai_depth_label`, `why_candidate`.

## If I Had More Time
1. Calibrate weights/lexicons against a labelled set of recruiter decisions and add a golden-file regression test on the 50 resumes.
2. Better project segmentation (layout-aware parsing; some single-line PDFs fall back to whole-section scoring) and OCR for scanned resumes.
3. Run the LLM judge with async batching + response caching keyed by resume hash, and add an LLM-based cross-check of the eligibility rules to *flag* (not decide) borderline rejections for human review.
4. Richer GitHub signal (commit counts per repo, README/AI relevance, stars of owned repos) via GraphQL with a token, and a small HTML report.
