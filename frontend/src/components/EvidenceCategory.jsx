import { useEffect, useState } from "react";
import { fmt } from "../lib/model.js";
import ScoreBar from "./ScoreBar.jsx";
import EvidenceBlock from "./EvidenceBlock.jsx";
import Badge from "./Badge.jsx";

// Score → Evidence → Explanation for one category: the "why this score?" view.
export default function EvidenceCategory({ label, entry, defaultOpen = false, open: controlled }) {
  const [own, setOwn] = useState(defaultOpen);
  const open = own;
  const [showNotes, setShowNotes] = useState(false);
  useEffect(() => { if (controlled !== undefined) setOwn(controlled); }, [controlled]);
  if (!entry) return null;
  const unscored = entry.scored === false;
  const items = entry.evidence || [];
  return (
    <section className={`glass trace ${open ? "is-open" : ""}`}>
      <button className="trace-head" aria-expanded={open} onClick={() => setOwn(!open)}>
        <span className="trace-title">{label}</span>
        <span className="trace-score num">
          {unscored ? <Badge tone="orange">GitHub unavailable</Badge> : <>{fmt(entry.score)} <span className="muted">/ {fmt(entry.max_score)}</span></>}
        </span>
        <span className="trace-bar"><ScoreBar value={unscored ? 0 : entry.score} max={entry.max_score} muted={unscored} /></span>
        <span className="trace-caret" aria-hidden="true" />
      </button>
      {open && (
        <div className="trace-body">
          <div className="trace-col">
            <h4>Evidence</h4>
            {items.length ? items.map((it, i) => <EvidenceBlock key={i} item={it} />) : (
              <p className="empty-line">{unscored ? "No GitHub evidence was collected." : "No supporting evidence found in the resume."}</p>
            )}
          </div>
          <div className="trace-col">
            <h4>Explanation</h4>
            <p className="trace-explain">{entry.explanation}</p>
            {unscored && entry.reason ? <p className="callout"><strong>{entry.enrichment_status || "unavailable"}</strong> {entry.reason}</p> : null}
            {entry.signals?.length ? (
              <div className="chips">{entry.signals.map((s, i) => <span key={i} className="chip">{s}</span>)}</div>
            ) : null}
            {entry.notes?.length ? (
              <div className="notes">
                <button className="link-btn" aria-expanded={showNotes} onClick={() => setShowNotes(!showNotes)}>
                  {showNotes ? "Hide" : "Show"} how the points were earned
                </button>
                {showNotes && <ul>{entry.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </section>
  );
}
