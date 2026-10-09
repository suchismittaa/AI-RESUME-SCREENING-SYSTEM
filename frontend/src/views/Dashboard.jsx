import KpiCard from "../components/KpiCard.jsx";
import Pipeline from "../components/Pipeline.jsx";
import CandidateTable from "../components/CandidateTable.jsx";
import { fmt } from "../lib/model.js";
import { hrefs } from "../lib/router.js";

export default function Dashboard({ model, selected, onToggle }) {
  const s = model.summary;
  const top = model.top;
  return (
    <div className="page">
      <header className="page-head">
        <h1>Measure. Explain. Rank. Compare.</h1>
        <p>Every score below is backed by quotes from the resume. Open a candidate to see why they scored what they did, or tick two or three to compare them side by side.</p>
      </header>

      <section aria-label="Batch summary" className="kpis">
        <KpiCard label="Resumes processed" value={s.total_files ?? model.all.length} note={`${s.successfully_parsed ?? "–"} read successfully`} />
        <KpiCard label="Eligible" value={model.eligible.length} note="Python and AI / agentic evidence" />
        <KpiCard label="Rejected" value={model.rejected.length} note={<a className="inline-link" href={hrefs.rejected()}>See reasons</a>} />
        <KpiCard label="Failed / unreadable" value={model.failed.length} variant={model.failed.length ? "attn" : ""} note={<a className="inline-link" href={hrefs.failed()}>{model.failed.length ? "See failures" : "No failures"}</a>} />
        <KpiCard label="Average eligible score" value={model.avgEligibleScore === null ? "n/a" : fmt(model.avgEligibleScore)} note="out of 100" />
        <KpiCard label="Top candidate" asName variant="top" value={top ? <a href={hrefs.candidate(top.file)}>{top.name}</a> : "n/a"} note={top ? `${fmt(top.score)} points, Level ${top.aiLevel} AI` : ""} />
      </section>

      <section aria-labelledby="pipeline-h">
        <div className="section-head"><h2 id="pipeline-h">How this batch was screened</h2><p>Counts come from this run.</p></div>
        <Pipeline summary={s} />
        {s.github_status_counts && (s.github_status_counts.unavailable || s.github_status_counts.rate_limited || s.github_status_counts.error) ? (
          <p className="callout batch-note">GitHub enrichment did not complete for part of this batch, so those candidates have 0 GitHub points because the data is missing. It does not mean their GitHub is weak.</p>
        ) : null}
      </section>

      <section aria-labelledby="rank-h">
        <div className="section-head"><h2 id="rank-h">Ranked candidates</h2><p>Click a column to sort. Rank, score and depth come from the screening results.</p></div>
        <CandidateTable rows={model.all} selected={selected} onToggle={onToggle} />
      </section>
    </div>
  );
}
