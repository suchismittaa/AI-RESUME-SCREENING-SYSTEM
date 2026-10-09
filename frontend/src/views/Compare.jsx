import { useEffect, useState } from "react";
import { fetchComparison } from "../lib/api.js";
import { CATEGORIES, fmt } from "../lib/model.js";
import { hrefs } from "../lib/router.js";
import ComparisonCell from "../components/ComparisonCell.jsx";
import AiDepthIndicator from "../components/AiDepthIndicator.jsx";
import ScoreBar from "../components/ScoreBar.jsx";
import EvidenceBlock from "../components/EvidenceBlock.jsx";
import Badge from "../components/Badge.jsx";
import { Loading, ErrorState, EmptyState } from "../components/States.jsx";

export default function Compare({ model, files }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [nonce, setNonce] = useState(0);
  const key = files.join("|");

  useEffect(() => {
    setData(null); setError(null);
    if (files.length < 2) return;
    let live = true;
    fetchComparison(files).then((d) => live && setData(d)).catch((e) => live && setError(e));
    return () => { live = false; };
  }, [key, nonce]);

  const options = model.eligible.filter((r) => !files.includes(r.file));
  const setFiles = (next) => { window.location.hash = hrefs.compare(next).slice(1); };

  const picker = (
    <div className="glass filters cmp-picker">
      <label className="field grow">
        <span>Add a candidate (2 or 3)</span>
        <select value="" disabled={files.length >= 3} onChange={(e) => e.target.value && setFiles([...files, e.target.value])}>
          <option value="">{files.length >= 3 ? "Three candidates selected" : "Choose a candidate"}</option>
          {options.map((r) => <option key={r.file} value={r.file}>{r.rank}. {r.name} ({fmt(r.score)})</option>)}
        </select>
      </label>
      <a className="btn-quiet" href={hrefs.dashboard()}>Back to ranking</a>
    </div>
  );

  if (files.length < 2) {
    return (
      <div className="page">
        <header className="page-head"><h1>Compare candidates</h1><p>Pick two or three eligible candidates to see them side by side.</p></header>
        {picker}
        <EmptyState title="Choose at least two candidates">Tick candidates in the ranking table or add them above.</EmptyState>
      </div>
    );
  }
  if (error) return <div className="page"><header className="page-head"><h1>Compare candidates</h1></header>{picker}<ErrorState error={error} onRetry={() => setNonce(nonce + 1)} /></div>;
  if (!data) return <div className="page"><header className="page-head"><h1>Compare candidates</h1></header><Loading text="Building comparison" /></div>;

  const cands = data.candidates;
  const dim = Object.fromEntries((data.dimensions || []).map((d) => [d.key, d]));
  const isLeader = (k, f) => (dim[k]?.leaders || []).includes(f);
  const bestRank = Math.min(...cands.map((c) => (typeof c.rank === "number" ? c.rank : Infinity)));
  const bestLevel = Math.max(...cands.map((c) => (typeof c.ai_depth_level === "number" ? c.ai_depth_level : -1)));
  const levelsDiffer = new Set(cands.map((c) => c.ai_depth_level)).size > 1;
  const cols = { gridTemplateColumns: `minmax(130px, 170px) repeat(${cands.length}, minmax(220px, 1fr))` };
  const removeFile = (f) => setFiles(files.filter((x) => x !== f));

  return (
    <div className="page compare">
      <header className="page-head"><h1>Compare candidates</h1><p>Highlights mark where a candidate leads a category. Close scores are marked comparable rather than ranked against each other.</p></header>
      {picker}

      <div className="cmp-scroll">
        <div className="cmp-grid glass" style={cols}>
          <div className="cmp-label" />
          {cands.map((c) => (
            <div key={c.file} className="cmp-cell cmp-head">
              <a href={hrefs.candidate(c.file)} className="cmp-name">{c.candidate_name}</a>
              <span className="muted file">{c.file}</span>
              <span className="badges">
                <Badge tone={c.eligible ? "peach" : "mauve"}>{c.eligible ? "ELIGIBLE" : "REJECTED"}</Badge>
                {c.rank ? <Badge tone={c.rank === 1 ? "gold" : "plain"}>Rank {c.rank}</Badge> : null}
              </span>
              <button className="link-btn" onClick={() => removeFile(c.file)} aria-label={`Remove ${c.candidate_name} from comparison`}>Remove</button>
            </div>
          ))}

          <div className="cmp-label">Final score</div>
          {cands.map((c) => (
            <ComparisonCell key={c.file} leader={c.rank === bestRank && c.eligible && cands.length > 1}>
              <span className="cmp-big num">{c.final_score === null ? "n/a" : fmt(c.final_score)}<small> / 100</small></span>
            </ComparisonCell>
          ))}

          <div className="cmp-label">AI depth</div>
          {cands.map((c) => (
            <ComparisonCell key={c.file} leader={isLeader("ai_project_depth", c.file)}>
              <ScoreLine k="ai_project_depth" c={c} />
              {dim.ai_project_depth?.comparable ? <span className="muted tiny">Comparable</span> : null}
            </ComparisonCell>
          ))}

          <div className="cmp-label">AI project quality</div>
          {cands.map((c) => (
            <ComparisonCell key={c.file} leader={levelsDiffer && c.ai_depth_level === bestLevel}>
              {c.ai_project_quality ? (
                <>
                  <strong>Level {c.ai_depth_level}: {c.ai_depth_label}</strong>
                  <AiDepthIndicator level={c.ai_depth_level} label={c.ai_depth_label} compact />
                  <span className="muted tiny">{c.ai_project_quality.best_project || "Project title not identified"}</span>
                  {c.ai_project_quality.thin_wrapper ? <Badge tone="orange">Thin wrapper</Badge> : null}
                </>
              ) : <span className="muted">n/a</span>}
            </ComparisonCell>
          ))}

          {CATEGORIES.filter((x) => x.key !== "ai_project_depth").map((cat) => (
            <Row key={cat.key} label={cat.short} cands={cands}>
              {(c) => (
                <ComparisonCell key={c.file} leader={isLeader(cat.key, c.file)}>
                  {cat.key === "github" && !c.github_scored ? (
                    <>
                      <Badge tone="orange">Unavailable</Badge>
                      <span className="muted tiny">{c.github_reason || c.github_status || "No GitHub data"}</span>
                    </>
                  ) : <ScoreLine k={cat.key} c={c} />}
                </ComparisonCell>
              )}
            </Row>
          ))}

          <div className="cmp-label">Strengths</div>
          {cands.map((c) => <ComparisonCell key={c.file}>{c.strengths.length ? <ul className="plain-list">{c.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul> : <span className="muted">None recorded</span>}</ComparisonCell>)}

          <div className="cmp-label">Concerns</div>
          {cands.map((c) => <ComparisonCell key={c.file}>{c.concerns.length ? <ul className="plain-list concerns">{c.concerns.map((s, i) => <li key={i}>{s}</li>)}</ul> : <span className="muted">None recorded</span>}</ComparisonCell>)}

          <div className="cmp-label">Evidence</div>
          {cands.map((c) => (
            <ComparisonCell key={c.file}>
              {c.evidence.length ? (
                <details className="more"><summary>{c.evidence.length} quotes from the resume</summary>
                  {c.evidence.map((t, i) => <EvidenceBlock key={i} item={{ text: t, source: "resume" }} />)}
                </details>
              ) : <span className="muted">None recorded</span>}
            </ComparisonCell>
          ))}
        </div>
      </div>

      <section className="glass panel summary" aria-labelledby="sum-h">
        <h2 id="sum-h">Comparison summary</h2>
        {(data.warnings || []).length ? <ul className="warnings">{data.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul> : null}
        {(data.findings || []).length ? (
          <>
            <h3>Where they differ</h3>
            <ul className="plain-list">{data.findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </>
        ) : null}
        {(data.ranking_explanation || []).length ? (
          <>
            <h3>Why the ranking order is what it is</h3>
            <ul className="plain-list">{data.ranking_explanation.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </>
        ) : null}
        <p className="muted tiny">A higher total does not by itself make a candidate the better fit. Read the differences above against the role.</p>
      </section>
    </div>
  );
}

function Row({ label, cands, children }) {
  return <><div className="cmp-label">{label}</div>{cands.map((c) => children(c))}</>;
}

function ScoreLine({ k, c }) {
  const s = c.scores?.[k];
  if (!s || s.score === null || s.score === undefined) return <span className="muted">n/a</span>;
  return (
    <>
      <span className="cmp-score num">{fmt(s.score)}<small> / {fmt(s.max)}</small></span>
      <ScoreBar value={s.score} max={s.max} />
    </>
  );
}
