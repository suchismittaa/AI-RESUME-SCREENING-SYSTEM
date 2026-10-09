# 🤖 AI Resume Screening & Ranking System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/AI%20%2F%20LLM-Optional-8B5CF6?style=for-the-badge" alt="AI">
  <img src="https://img.shields.io/badge/Tests-54%20Passing-22C55E?style=for-the-badge" alt="Tests">
</p>

<p align="center">
  <strong>An evidence-first AI resume screening and ranking platform built for transparent, explainable recruiter decisions.</strong>
</p>

<p align="center">
  Ingest resumes → filter candidates → score evidence → enrich GitHub → explain decisions → compare candidates → rank
</p>

---

## ✨ Overview

The **AI Resume Screening & Ranking System** is an end-to-end recruiter-focused screening platform designed to make resume evaluation more **transparent, explainable, evidence-backed, and reproducible**.

The system:

- 📄 Ingests a folder of resumes
- 🔎 Applies a **rule-based Python + AI/agentic eligibility filter**
- 🧠 Scores eligible candidates using a transparent **100-point model**
- 🐙 Enriches candidates with public GitHub activity
- 📊 Produces a ranked shortlist
- 🔍 Provides evidence for every major scoring decision
- ⚖️ Supports candidate-to-candidate comparison
- 📝 Generates structured JSON and CSV outputs
- 🖥️ Provides a React-based recruiter console

The final output includes:

```text
output/results.json
output/results.csv
```

The core philosophy is simple:

> **Measure → Explain → Rank → Compare**

---

# 🧭 Table of Contents

- [✨ Overview](#-overview)
- [🚀 Key Features](#-key-features)
- [🏗️ Architecture](#️-architecture)
- [🔄 Pipeline](#-pipeline)
- [⚙️ Setup & Installation](#️-setup--installation)
- [▶️ Run the System](#️-run-the-system)
- [📊 Output](#-output)
- [🔍 Evidence Trace](#-evidence-trace)
- [🤖 AI Project Quality](#-ai-project-quality)
- [👤 Why This Candidate](#-why-this-candidate)
- [⚖️ Candidate Comparison](#️-candidate-comparison)
- [🖥️ Recruiter Console](#️-recruiter-console)
- [🔌 API](#-api)
- [🎨 Frontend Design](#-frontend-design)
- [🧠 Design Decisions](#-design-decisions)
- [🛡️ Robustness](#️-robustness)
- [⚠️ Limitations](#️-limitations)
- [🔮 Future Improvements](#-future-improvements)
- [📁 Project Structure](#-project-structure)
- [👩‍💻 Author](#-author)

---

# 🚀 Key Features

| Feature | Description |
|---|---|
| 📄 Resume ingestion | Processes PDF, DOCX, TXT and MD files |
| 🧹 Duplicate detection | Detects duplicate resume content using hashes |
| 🔎 Eligibility filtering | Rule-based Python + AI/agentic screening |
| 🧠 Explainable scoring | Transparent 100-point scoring model |
| 🤖 Optional LLM judgment | Optional Anthropic-powered project evaluation |
| 🐙 GitHub enrichment | Public GitHub activity and repository signals |
| 🔬 Evidence trace | Verbatim resume evidence behind scoring |
| 🏆 AI project quality | Levels AI implementations from 0 to 4 |
| 💡 Candidate explanation | Automatically explains why a candidate ranked where they did |
| ⚖️ Candidate comparison | Evidence-backed comparison of 2–3 candidates |
| 🖥️ Recruiter console | React dashboard for screening results |
| 📊 CSV + JSON output | Structured results for downstream use |
| 🧪 Automated testing | 54 backend tests plus frontend data tests |
| ♿ Accessible UI | Keyboard navigation, visible focus and reduced-motion support |

---

# 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │       resumes/       │
                         │  PDF / DOCX / TXT    │
                         │         / MD         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      Ingestion       │
                         │     ingest.py        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Text Extraction    │
                         │     extract.py       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Eligibility Filter   │
                         │    eligibility.py    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Deterministic Scoring│
                         │      scoring.py      │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                ┌─────────────────┐   ┌─────────────────┐
                │ Optional LLM    │   │ GitHub          │
                │ Judgment        │   │ Enrichment      │
                │ llm.py          │   │ github.py       │
                └────────┬────────┘   └────────┬────────┘
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Explainability Layer │
                         │     explain.py       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Ranking & Assembly   │
                         │     pipeline.py      │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    ▼                                ▼
           ┌─────────────────┐              ┌─────────────────┐
           │ results.json    │              │ results.csv     │
           └─────────────────┘              └─────────────────┘
                    │
                    ▼
           ┌─────────────────────┐
           │      FastAPI        │
           │      screener/api   │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   React Recruiter   │
           │      Console        │
           └─────────────────────┘
```

---

# 🔄 Pipeline

```text
ingest.py
   ↓
extract.py
   ↓
eligibility.py
   ↓
scoring.py
   ↓
llm.py              ← optional
   ↓
github.py            ← enrichment
   ↓
explain.py
   ↓
pipeline.py
   ↓
report.py

compare.py → builds candidate comparisons on demand
```

Weights, penalties, model name, concurrency and thresholds are controlled through `config.py` / environment variables.

Keyword lists are maintained as pure data in:

```text
lexicon.py
```

---

# ⚙️ Setup & Installation

## 1. Create a virtual environment

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure environment variables

```bash
cp .env.example .env
```

Optional:

```text
ANTHROPIC_API_KEY
GITHUB_TOKEN
```

Without these keys, the core pipeline can still run deterministically.

---

# ▶️ Run the System

## Screen resumes

```bash
python main.py --input ./resumes --output ./output/results.json
```

Short form:

```bash
python main.py -i ./resumes -o ./output/results.json
```

---

## Fully offline / deterministic mode

```bash
python main.py -i ./resumes --no-llm --no-github
```

---

## Run tests

```bash
pytest
```

The project contains **54 backend tests**, with no network required.

---

# 🖥️ Run the Recruiter Console

Build the frontend:

```bash
cd frontend
npm install
npm run build
cd ..
```

A prebuilt `frontend/dist` is also included.

Start the API and recruiter console:

```bash
uvicorn screener.api:app --app-dir src
```

Open:

```text
http://127.0.0.1:8000
```

---

# 📊 Output

The system generates:

```text
output/
├── results.json
└── results.csv
```

## `results.json`

The output contains:

### Batch summary

Includes:

- total files
- parsed files
- eligible candidates
- rejected candidates
- failed/unreadable files
- duplicates
- LLM mode
- GitHub status counts

### Ranked candidates

Each eligible candidate can contain:

- rank
- total score
- score breakdown
- score notes
- penalties
- matched skills
- project summary
- evidence
- strengths
- concerns
- GitHub information
- evidence trace
- AI project quality
- `why_candidate`

### Rejected candidates

Contains:

```text
rejection_reasons
matched_skills
```

### Failed files

Contains unreadable or corrupt files and their errors.

### Duplicates

Contains files skipped because their text duplicates another resume.

---

# 🔍 Evidence Trace

Every eligible candidate contains an `evidence_trace`.

The trace covers:

```text
ai_project_depth
python_backend
cloud_fullstack
github
engineering_depth
```

Each category contains:

- score
- maximum score
- plain-language explanation
- detected signals
- scoring notes
- evidence items

Evidence items follow:

```text
{
  signal,
  text,
  source
}
```

### Evidence-first design

The system does **not generate fake supporting quotes**.

Resume evidence is:

- verbatim
- whitespace-normalised
- linked to its source section
- validated against the actual resume text

If no evidence exists, the system explicitly reports that.

For example:

```text
No evidence found for: Redis
```

GitHub evidence comes only from the actual GitHub lookup.

If GitHub enrichment fails, the candidate is **not negatively evaluated** simply because the data was unavailable.

---

# 🤖 AI Project Quality

The system exposes an `ai_project_quality` object that represents the existing AI-project judgment.

## AI quality levels

| Level | Label | Meaning |
|---:|---|---|
| 0 | No implementation evidence | AI frameworks appear only in the skills list |
| 1 | Thin LLM/API Wrapper | LLM call without retrieval, agents, state, evaluation or meaningful data/backend logic |
| 2 | Applied AI | Real AI use that does not satisfy the higher-level rules |
| 3 | RAG / AI System | Agent/tool use or retrieval plus supporting implementation signals |
| 4 | Agentic / Advanced AI System | Agent/tool use plus at least two supporting signals, including retrieval, state or evaluation |

Framework names such as:

```text
LangChain
LangGraph
```

do **not** raise the AI quality level on their own.

The object also contains:

```text
score
best_project
summary
implementation_signals
evidence
quality_concerns
thin_wrapper
tutorial_style
skills_only
```

The AI quality level is a presentation of the evidence and **does not change the underlying score**.

---

# 👤 Why This Candidate

Eligible candidates receive a deterministic `why_candidate` explanation.

It is assembled from:

1. strongest AI project
2. AI quality level and signals
3. AI score
4. backend technologies
5. deployment evidence
6. engineering-practice evidence
7. main caveat or GitHub status

No LLM-generated text is used.

The explanation does not assert anything that is absent from the evidence trace.

---

# ⚖️ Candidate Comparison

The backend supports:

```text
GET /compare?candidates=<candidate>&candidates=<candidate>
```

Comparison supports **2–3 candidates**.

The response includes:

- candidate identity
- rank
- eligibility
- final score
- per-dimension scores
- detected signals
- AI depth level
- AI quality
- GitHub status
- strengths
- concerns
- evidence
- `why_candidate`

### Comparison dimensions

```text
AI depth
Python / backend
Cloud / full-stack
GitHub
Engineering depth
```

The system identifies:

- leaders
- comparable categories
- ranking differences
- point gaps
- evidence behind those differences
- warnings

Candidates within the defined tolerance are treated as **comparable**, rather than artificially forcing a winner.

If GitHub data is unavailable, that dimension is reported as unavailable instead of treating the candidate as losing.

---

# 🖥️ Recruiter Console

The React recruiter console contains several views.

## 📊 Dashboard

Includes:

- processed candidates
- eligible candidates
- rejected candidates
- failed files
- average eligible score
- top candidate
- pipeline counts
- ranked candidate table
- search
- sortable columns
- eligibility filter
- AI-depth filter
- minimum-score filter

---

## 👤 Candidate Detail

Shows:

- candidate identity
- resume file
- eligibility status
- final score
- Why this candidate?
- strengths
- concerns
- ranking-change explanation
- score breakdown
- AI project quality
- evidence trace
- GitHub panel
- matched skills

---

## ⚖️ Compare

Select 2–3 candidates and compare them side-by-side.

The interface highlights category leaders while preserving cases where candidates are considered comparable.

---

## ❌ Rejected

Displays every rejected candidate with:

- rule-based rejection reason
- missing requirement
- matched skills

---

## ⚠️ Failed

Displays:

- unreadable files
- extraction errors
- skipped duplicates

An empty result is explicitly shown rather than hidden.

---

# 🔌 API

| Endpoint | Purpose |
|---|---|
| `POST /screen` | Run the pipeline and return/store results |
| `GET /results` | Return the latest results |
| `GET /status` | Return current result status |
| `GET /compare` | Compare 2–3 candidates |
| `GET /` | Serve the recruiter console |

### Example

```http
POST /screen
```

```json
{
  "input_dir": "./resumes"
}
```

Environment overrides:

```text
RESULTS_PATH
FRONTEND_DIST
```

---

# 🎨 Frontend Design

The recruiter console follows a deliberate visual system.

## 🎨 Palette

```text
#3E3232
#7E5F66
#FFBC9F
#F29A65
#F8C53C
#FFFFFF
```

Yellow is reserved for:

- rank 1
- final score
- selection
- primary actions

Orange represents:

- attention
- unavailable GitHub
- concerns
- failures

The interface intentionally avoids traditional green/red status colours.

---

## 🪟 Glass UI

The interface uses:

- translucent surfaces
- soft peach borders
- 14px blur
- glass-style KPI cards
- filtered tables
- evidence panels
- comparison surfaces

A solid brown background maintains text contrast.

---

## 🧩 Frontend Architecture

The frontend uses:

```text
React 19
esbuild
JavaScript
Hash Router
```

React is bundled using a lightweight esbuild script rather than a larger toolchain.

There are no external CDN assets, allowing the console to work offline.

---

# 🧠 Design Decisions

## Filtering

Eligibility is determined by rules, **never by the LLM**.

A candidate must satisfy both:

### 1. Python evidence

Python or a Python-only ecosystem such as:

```text
FastAPI
Django
LangChain
pandas
```

must appear in:

- skills
- projects
- experience
- summary

Education, coursework and certification sections do not count.

---

### 2. AI / Agentic evidence

Strong signals include:

```text
LangGraph
LangChain
LlamaIndex
ADK
CrewAI
RAG
embeddings
vector search
tool calling
multi-agent
fine-tuning
evaluation
Transformers
```

Generic signals such as:

```text
OpenAI
Gemini
LLM
chatbot
```

only count when they appear in a project or experience section.

The system deliberately does not treat:

```text
AI-assisted development
Copilot / Claude Code usage
classical ML/CV only
```

as sufficient AI evidence.

---

# 📈 Scoring Model

The deterministic baseline is **100 points**.

Evidence in projects and experience receives full credit.

Evidence appearing only in a skills list receives **40% credit**.

| Category | Max Score |
|---|---:|
| 🤖 AI Project Depth | 40 |
| 🐍 Python & Backend | 30 |
| ☁️ Cloud / Deploy / Full-stack | 15 |
| 🧪 Engineering Depth | 5 |
| 🐙 GitHub | 10 |
| **Total** | **100** |

---

## 🤖 AI Project Depth — 40

Evaluates:

- orchestration frameworks
- retrieval / RAG
- agentic/tool use
- state / memory
- evaluation
- fine-tuning
- data pipelines
- backend integration
- quantified outcomes

A second solid AI project can also contribute.

Penalties include:

```text
-10 / -15 → thin LLM API wrapper
-5        → tutorial-style project
-5        → AI framework only in skills
```

---

## 🐍 Python & Backend — 30

Signals include:

```text
Python
FastAPI
Flask
Django
async
PostgreSQL
Redis
backend technologies
```

---

## ☁️ Cloud / Deploy / Full-stack — 15

Signals include:

```text
GCP
Docker
deployment
CI/CD
React
Next.js
```

React/Next.js acts as a supporting signal when backend evidence exists.

---

## 🧪 Engineering Depth — 5

One point is available for each distinct engineering category found in project/experience text:

```text
testing
architecture
caching
queues
observability
concurrency
failure handling
```

---

## 🐙 GitHub — 10

GitHub scoring combines:

### Activity

Up to 5 points based on:

- recent pushes
- repository activity
- push volume

### Repositories

Up to 5 points based on:

- maintained original repositories
- recent repository activity
- Python/AI relevance

Missing GitHub information is recorded rather than treated as a failure.

---

# 🧠 Optional LLM Judgment

The LLM layer is optional.

Environment variable:

```text
ANTHROPIC_API_KEY
```

One call is made per eligible resume.

The validated output includes:

- project depth
- thin-wrapper flag
- tutorial flag
- summary
- strengths
- concerns
- evidence quotes

The final AI depth can combine:

```text
deterministic score
+
LLM score
```

using:

```text
LLM_BLEND_WEIGHT
```

The default blend weight is `0.5`.

Evidence quotes are retained only if they literally occur in the resume.

Resume content is treated as untrusted input, and instructions inside resumes are ignored.

---

# 🐙 GitHub Enrichment

GitHub usernames are detected from:

1. PDF hyperlinks
2. visible profile URLs
3. repository URLs
4. multiple possible handles

GitHub scoring considers:

- recent activity
- repository maintenance
- original repositories
- Python/AI relevance

Results are cached in:

```text
.cache/github.json
```

with a 24-hour TTL.

Only eligible candidates are enriched.

If GitHub is unavailable, the system records the failure and continues processing the batch.

---

# 🛡️ Robustness

The pipeline is designed so one problematic resume does not stop the entire batch.

It handles:

- corrupt files
- encrypted files
- empty files
- unreadable files
- scanned PDFs
- duplicate resumes
- mixed-case PDF text
- glued-word PDF text
- PDF hyperlink annotations

PDF is required and supported, with a secondary extractor automatically used for difficult letter-spaced or one-word-per-line PDFs.

Supported formats:

```text
PDF
DOCX
TXT
MD
```

---

# 🧪 Testing

Run backend tests:

```bash
pytest
```

Run frontend tests:

```bash
npm test
```

The backend currently contains **54 tests** and does not require network access.

---

# ⚠️ Limitations

### GitHub

The bundled `results.json` was generated in an environment where GitHub API access returned HTTP 403.

Therefore:

```text
GitHub status = unavailable
GitHub score = 0
```

for affected candidates in the bundled dataset.

Re-run the pipeline on a normal network, ideally with:

```text
GITHUB_TOKEN
```

---

### LLM

The bundled results were generated without an LLM API key.

The LLM-enabled path was tested using a fake client rather than a live API.

---

### API persistence

`POST /screen` runs synchronously and keeps its result in memory.

The CLI-generated:

```text
output/results.json
```

is what survives an application restart.

---

### Recruiter console

The console currently displays one results set at a time.

It does not currently provide:

- accounts
- saved shortlists
- built-in export

`results.csv` can be used for export.

---

# 🔮 Future Improvements

### 1. Better score calibration

Calibrate weights and lexicons against labelled recruiter decisions and add golden-file regression testing across the 50 resumes.

### 2. Better project segmentation

Improve layout-aware parsing and introduce OCR for scanned resumes.

### 3. Advanced LLM evaluation

Run the LLM judge with:

- async batching
- response caching
- resume-hash based caching
- human-review flags for borderline eligibility decisions

### 4. Richer GitHub intelligence

Add:

- commit counts
- repository README analysis
- AI relevance
- repository stars
- GraphQL-based enrichment
- HTML reporting

---

# 📁 Project Structure

```text
resume-screener/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── styles/
│   │   └── views/
│   ├── tests/
│   ├── build.mjs
│   ├── package.json
│   └── package-lock.json
│
├── resumes/
│   ├── candidate_01.pdf
│   ├── candidate_02.pdf
│   └── ...
│
├── src/
│   └── screener/
│       ├── api.py
│       ├── compare.py
│       ├── config.py
│       ├── eligibility.py
│       ├── explain.py
│       ├── extract.py
│       ├── github.py
│       ├── ingest.py
│       ├── lexicon.py
│       ├── llm.py
│       ├── models.py
│       ├── pipeline.py
│       ├── report.py
│       └── scoring.py
│
├── tests/
│   ├── test_compare.py
│   ├── test_eligibility.py
│   ├── test_explain.py
│   ├── test_extract.py
│   ├── test_github.py
│   ├── test_pipeline.py
│   └── test_scoring.py
│
├── output/
│   ├── results.json
│   └── results.csv
│
├── main.py
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

---

# 🎯 Why This System Exists

Recruiting systems often produce rankings without making the reasoning behind those rankings easy to inspect.

This project takes a different approach.

Every important decision is designed to be:

```text
                    ┌──────────────┐
                    │    EVIDENCE  │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │    EXPLAIN   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │     RANK     │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   COMPARE    │
                    └──────────────┘
```

The goal is not simply to say:

> **"This candidate scored higher."**

It is to show:

> **"This candidate scored higher because the resume contains this evidence, these signals contributed these points, these factors differentiated the candidates, and these limitations remain."**

---

# 📌 Notes on the Provided Dataset

The bundled `output/results.json` was generated without a live GitHub connection and without an LLM key.

Therefore, the dataset represents the **deterministic baseline**.

For a fresh run:

```bash
python main.py -i resumes -o output/results.json
```

Use a normal network connection and optionally configure:

```text
GITHUB_TOKEN
ANTHROPIC_API_KEY
```

to activate the corresponding enrichment and LLM functionality.

---

# 🚀 Run It Yourself

```bash
# clone
git clone https://github.com/suchismittaa/AI-RESUME-SCREENING-SYSTEM.git

# enter project
cd AI-RESUME-SCREENING-SYSTEM

# create environment
python -m venv .venv

# activate
# Windows
.venv\Scripts\Activate.ps1

# install
pip install -r requirements.txt

# run screening
python main.py -i ./resumes -o ./output/results.json

# build frontend
cd frontend
npm install
npm run build
cd ..

# launch recruiter console
uvicorn screener.api:app --app-dir src
```

Then open:

```text
http://127.0.0.1:8000
```

---

# 👩‍💻 Author

<p align="center">
  <strong>Suchismita Sarkar</strong><br>
  Information Technology | KIIT
</p>

<p align="center">
  <a href="https://suchismitasportfolio.netlify.app/" target="_blank">
    <img src="https://img.shields.io/badge/🌐%20Portfolio-Visit-FFBC9F?style=for-the-badge" alt="Portfolio">
  </a>
  &nbsp;
  <a href="https://www.linkedin.com/in/suchismitasarkar222/" target="_blank">
    <img src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
  </a>
</p>

<p align="center">
  <a href="https://github.com/suchismittaa/AI-RESUME-SCREENING-SYSTEM">
    <img src="https://img.shields.io/badge/GitHub-Project-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub">
  </a>
</p>

---

<p align="center">
  <strong>Built with Python • FastAPI • React • AI • Explainable Scoring</strong>
</p>

<p align="center">
  ⭐ If you found the project interesting, consider giving it a star!
</p>