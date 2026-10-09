import AiDepthIndicator from "./AiDepthIndicator.jsx";
import Badge from "./Badge.jsx";
import EvidenceBlock from "./EvidenceBlock.jsx";
import { fmt } from "../lib/model.js";

function Flag({ on, onText, offText }) {
  return on ? <Badge tone="orange">{onText}</Badge> : <Badge tone="peach">{offText}</Badge>;
}

export default function AiProjectQuality({ q }) {
  if (!q) return null;
  const title = q.best_project || `Project title not identified (evidence is from the ${q.best_project_section || "resume"} section)`;
  return (
    <section className="glass panel aiq" aria-labelledby="aiq-h">
      <div className="section-head">
        <h2 id="aiq-h">AI project quality</h2>
        <span className="muted num">{fmt(q.score)} / {fmt(q.max_score)} points</span>
      </div>
      <p className="aiq-level">Level {q.level} <span>{q.label}</span></p>
      <AiDepthIndicator level={q.level} label={q.label} />
      <div className="aiq-grid">
        <div>
          <h4>Strongest AI project</h4>
          <p className={q.best_project ? "aiq-title" : "aiq-title muted"}>{title}</p>
          {q.summary ? <p className="muted aiq-summary">{q.summary}</p> : null}
          <h4>Status checks</h4>
          <ul className="status-list">
            <li><Flag on={q.thin_wrapper} onText="Thin wrapper" offText="Not a thin wrapper" /><span className="muted">{q.thin_wrapper ? "An LLM call without retrieval, agents, state or evaluation." : "Goes beyond a single LLM API call."}</span></li>
            <li><Flag on={q.tutorial_style} onText="Tutorial-style" offText="Not tutorial-style" /><span className="muted">{q.tutorial_style ? "Reads like a course or tutorial project." : "No tutorial markers found."}</span></li>
            {q.skills_only ? <li><Badge tone="orange">Skills list only</Badge><span className="muted">AI frameworks are named but not shown in project work.</span></li> : null}
          </ul>
        </div>
        <div>
          <h4>Implementation signals</h4>
          {q.implementation_signals?.length ? <div className="chips">{q.implementation_signals.map((s, i) => <span key={i} className="chip">{s}</span>)}</div> : <p className="empty-line">No implementation signals detected.</p>}
          <h4>Quality concerns</h4>
          {q.quality_concerns?.length ? <ul className="plain-list">{q.quality_concerns.map((c, i) => <li key={i}>{c}</li>)}</ul> : <p className="empty-line">None flagged.</p>}
        </div>
      </div>
      <h4>Evidence</h4>
      {q.evidence?.length ? <div className="quotes">{q.evidence.map((t, i) => <EvidenceBlock key={i} item={{ text: t, source: q.best_project_section || "resume" }} />)}</div> : <p className="empty-line">No project evidence quoted.</p>}
    </section>
  );
}
