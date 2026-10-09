// Presentation-layer shaping of the backend result. NO scoring, ranking or eligibility logic lives here:
// every score, rank, level, reason and sentence is read straight from results.json / the API.

export const CATEGORIES = [
  { key: "ai_project_depth", label: "AI / Agentic / RAG", short: "AI depth", max: 40 },
  { key: "python_backend", label: "Python / Backend", short: "Python / Backend", max: 30 },
  { key: "cloud_fullstack", label: "Cloud / Deployment / Full Stack", short: "Cloud / Full stack", max: 15 },
  { key: "github", label: "GitHub", short: "GitHub", max: 10 },
  { key: "engineering_depth", label: "Engineering Depth", short: "Engineering depth", max: 5 },
];

const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const arr = (v) => (Array.isArray(v) ? v : []);

export function fmt(n) {
  const v = num(n);
  if (v === null) return "n/a";
  return Number.isInteger(v) ? String(v) : String(Math.round(v * 10) / 10);
}

export function githubView(c) {
  const t = c?.evidence_trace?.github || {};
  const g = c?.github || {};
  const status = g.status || t.enrichment_status || "not_provided";
  const scored = typeof t.scored === "boolean" ? t.scored : status === "ok";
  return { status, scored, reason: t.reason || g.error || "", score: num(c?.score_breakdown?.github), info: g };
}

function eligibleRow(c) {
  const q = c.ai_project_quality || {};
  const b = c.score_breakdown || {};
  return {
    id: c.file, file: c.file, name: c.candidate_name || c.file, email: c.email || "", kind: "eligible",
    rank: num(c.rank), score: num(c.total_score),
    aiLevel: num(q.level), aiLabel: q.label || "", aiScore: num(b.ai_project_depth),
    pyScore: num(b.python_backend), github: githubView(c), status: "Scored", raw: c,
  };
}

function rejectedRow(c) {
  return {
    id: c.file, file: c.file, name: c.candidate_name || c.file, email: c.email || "", kind: "rejected",
    rank: null, score: null, aiLevel: null, aiLabel: "", aiScore: null, pyScore: null,
    github: githubView(c), status: "Rejected", raw: c,
  };
}

function failedRow(f) {
  return {
    id: f.file, file: f.file, name: f.file, email: "", kind: "failed", rank: null, score: null,
    aiLevel: null, aiLabel: "", aiScore: null, pyScore: null,
    github: { status: "skipped", scored: false, reason: "", score: null, info: {} }, status: "Failed", raw: f,
  };
}

export function buildModel(results) {
  const ranked = arr(results?.ranked_candidates);
  const eligible = ranked.map(eligibleRow);
  const rejected = arr(results?.rejected_candidates).map(rejectedRow);
  const failed = arr(results?.failed_files).map(failedRow);
  const scores = eligible.map((r) => r.score).filter((s) => s !== null);
  const avg = scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10 : null;
  const top = eligible.find((r) => r.rank === 1) || null;
  return {
    summary: results?.batch_summary || {},
    eligible, rejected, failed,
    duplicates: arr(results?.duplicates),
    all: [...eligible, ...rejected, ...failed],
    byFile: new Map([...eligible, ...rejected, ...failed].map((r) => [r.file, r])),
    avgEligibleScore: avg,
    top,
  };
}

// Items shown under "What could change this ranking?". Every item quotes backend text; nothing is invented.
export function rankingCaveats(c) {
  const out = [];
  const trace = c.evidence_trace || {};
  const gh = trace.github || {};
  if (gh.scored === false) {
    out.push({ title: "GitHub not assessed", text: gh.explanation || c.github_summary || "", source: "GitHub" });
  }
  for (const cat of CATEGORIES) {
    if (cat.key === "github") continue;
    const e = trace[cat.key];
    if (!e) continue;
    const missing = /No evidence found for: ([^.]+)\./.exec(e.explanation || "");
    if (missing && e.score < e.max_score) {
      out.push({ title: `${cat.label}: no evidence for ${missing[1]}`, text: `${fmt(e.score)} / ${fmt(e.max_score)} points. ${e.explanation}`, source: cat.label });
    }
  }
  for (const p of c.penalties || []) out.push({ title: "Penalty applied", text: p, source: "Scoring" });
  for (const t of c.ai_project_quality?.quality_concerns || []) {
    if (!(c.penalties || []).some((p) => p.includes(t))) out.push({ title: "AI project concern", text: t, source: "AI project quality" });
  }
  return out;
}
