import { hrefs } from "../lib/router.js";
import Badge from "../components/Badge.jsx";
import { EmptyState } from "../components/States.jsx";

export default function Rejected({ model }) {
  const rows = model.rejected;
  return (
    <div className="page">
      <header className="page-head">
        <h1>Rejected candidates</h1>
        <p>Rejection is rule-based and always explained. A candidate needs Python evidence and AI / agentic project evidence; the reason and the missing requirement are listed for each.</p>
      </header>
      {rows.length === 0 ? <EmptyState title="Nobody was rejected in this batch" /> : (
        <div className="glass table-scroll">
          <table className="table rejected">
            <thead><tr><th>Candidate</th><th>Status</th><th>Rejection reason</th><th>Missing requirement</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="row">
                  <td className="cell-name"><a href={hrefs.candidate(r.file)} className="name-link">{r.name}</a><span className="muted file">{r.file}</span></td>
                  <td><Badge tone="mauve">REJECTED</Badge></td>
                  <td><ul className="plain-list">{(r.raw.rejection_reasons || []).map((x, i) => <li key={i}>{x}</li>)}</ul></td>
                  <td>{(r.raw.missing_requirements || []).length ? <div className="chips">{r.raw.missing_requirements.map((m) => <Badge key={m} tone="orange">{m}</Badge>)}</div> : <span className="muted">Not recorded</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
