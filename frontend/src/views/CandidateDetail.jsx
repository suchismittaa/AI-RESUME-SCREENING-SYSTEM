import { useState } from "react";
import { CATEGORIES, fmt, rankingCaveats } from "../lib/model.js";
import { hrefs } from "../lib/router.js";
import { EligibilityBadge } from "../components/Badge.jsx";
import Badge from "../components/Badge.jsx";
import ScoreCard from "../components/ScoreCard.jsx";
import EvidenceCategory from "../components/EvidenceCategory.jsx";
import AiProjectQuality from "../components/AiProjectQuality.jsx";
import GithubPanel from "../components/GithubPanel.jsx";
import { EmptyState } from "../components/States.jsx";

function Header({ row, c, selected, onToggle, canSelect, full }) {
  const gh = row.github;
  return (
    <header className="glass panel detail-head">
      <div className="detail-id">
        <a className="back" href={hrefs.dashboard()}>Back to ranking</a>
        <h1>{row.name}</h1>
        <p className="muted">{c.email ? <a href={`mailto:${c.email}`}>{c.email}</a> : "No email on resume"}  ·  Resume file: {row.file}</p>
        <div className="badges">
          <EligibilityBadge eligible={row.kind === "eligible"} kind={row.kind} />
          {row.rank ? <Badge tone={row.rank === 1 ? "gold" : "plain"}>Rank {row.rank}</Badge> : null}
          {c.llm_used ? <Badge tone="plain">LLM-assisted</Badge> : <Badge tone="plain">Rule-based scoring</Badge>}
        </div>
        {canSelect && (
          <label className="check-line">
            <input type="checkbox" checked={selected} disabled={full && !selected} onChange={() => onToggle(row.file)} />
            Add to comparison
          </label>
        )}
      </div>
      {row.kind === "eligible" && (
        <div className="final-score" aria-label={`Final score ${fmt(row.score)} out of 100`}>
          <span className="final-label">Final score</span>
          <span className="final-value num">{fmt(row.score)}<small> / 100</small></span>
          {!gh.scored ? <span className="final-note">GitHub was not scored, so it adds 0 points. That is missing data, not a weak profile.</span> : null}
        </div>
      )}
    </header>
  );
}

function Why({ c }) {
  const caveats = rankingCaveats(c);
  return (
    <section className="glass panel why" aria-labelledby="why-h">
      <h2 id="why-h">Why this candidate?</h2>
      <p className="why-text">{c.why_candidate}</p>
      <div className="grid cols-2 sc">
        <div>
          <h3>Strengths</h3>
          {c.strengths?.length ? <ul className="plain-list">{c.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul> : <p className="empty-line">No strengths recorded.</p>}
        </div>
        <div>
          <h3>Concerns</h3>
          {c.concerns?.length ? <ul className="plain-list concerns">{c.concerns.map((s, i) => <li key={i}>{s}</li>)}</ul> : <p className="empty-line">No concerns recorded.</p>}
        </div>
      </div>
      <div className="change">
        <h3>What could change this ranking?</h3>
        {caveats.length ? (
          <ul className="caveats">
            {caveats.map((k, i) => <li key={i}><strong>{k.title}</strong><span className="muted">{k.text}</span></li>)}
          </ul>
        ) : <p className="empty-line">No missing or weak evidence was flagged for this candidate.</p>}
      </div>
    </section>
  );
}

function Rejected({ c }) {
  return (
    <>
      <section className="glass panel" aria-labelledby="rej-h">
        <h2 id="rej-h">Why this candidate was rejected</h2>
        <p className="muted">Eligibility is decided by fixed rules: Python evidence and AI / agentic project evidence are both required.</p>
        {c.missing_requirements?.length ? <div className="chips">{c.missing_requirements.map((m) => <Badge key={m} tone="orange">Missing: {m}</Badge>)}</div> : null}
        <ul className="plain-list">{(c.rejection_reasons || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
      </section>
    </>
  );
}

export default function CandidateDetail({ model, file, selected, onToggle }) {
  const row = model.byFile.get(file);
  const [all, setAll] = useState(undefined);
  if (!row) return <div className="page"><EmptyState title="Candidate not found">No resume named {file} is in these results. <a className="inline-link" href={hrefs.dashboard()}>Back to the ranking</a>.</EmptyState></div>;
  if (row.kind === "failed") return <div className="page"><EmptyState title={`${row.file} could not be processed`}>{row.raw.error}</EmptyState></div>;
  const c = row.raw;
  const trace = c.evidence_trace;
  const eligible = row.kind === "eligible";
  return (
    <div className="page detail">
      <Header row={row} c={c} selected={selected.includes(file)} onToggle={onToggle} canSelect={eligible} full={selected.length >= 3} />
      {!eligible ? <Rejected c={c} /> : (
        <>
          <Why c={c} />
          <section aria-labelledby="bd-h">
            <div className="section-head"><h2 id="bd-h">Score breakdown</h2><p>Points per category, as scored by the backend.</p></div>
            <div className="grid cols-5">
              {CATEGORIES.map((cat) => {
                const g = cat.key === "github" && row.github.scored === false;
                return <ScoreCard key={cat.key} label={cat.label} score={c.score_breakdown?.[cat.key]} max={cat.max} unassessed={g} unassessedText={row.github.reason ? row.github.reason.split(" (")[0] : row.github.status} />;
              })}
            </div>
          </section>
          <AiProjectQuality q={c.ai_project_quality} />
          <section aria-labelledby="trace-h">
            <div className="section-head">
              <h2 id="trace-h">Evidence trace: why this score?</h2>
              <button className="btn-quiet" onClick={() => setAll(all === true ? false : true)}>{all === true ? "Collapse all" : "Expand all"}</button>
            </div>
            {trace ? (
              <div className="stack">
                {CATEGORIES.map((cat) => <EvidenceCategory key={cat.key} label={`${cat.label}`} entry={trace[cat.key]} defaultOpen={cat.key === "ai_project_depth"} open={all} />)}
              </div>
            ) : <EmptyState title="No evidence trace in this results file">Re-run the screening to generate it.</EmptyState>}
          </section>
          <GithubPanel candidate={c} />
        </>
      )}
      {c.matched_skills?.length ? (
        <section className="glass panel" aria-labelledby="skills-h">
          <h2 id="skills-h">Skills found on the resume</h2>
          <div className="chips">{c.matched_skills.map((s) => <span key={s} className="chip">{s}</span>)}</div>
        </section>
      ) : null}
    </div>
  );
}
