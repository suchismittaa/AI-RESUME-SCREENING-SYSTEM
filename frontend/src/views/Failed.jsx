import Badge from "../components/Badge.jsx";
import { EmptyState } from "../components/States.jsx";

export default function Failed({ model }) {
  const { failed, duplicates } = model;
  return (
    <div className="page">
      <header className="page-head">
        <h1>Failed processing</h1>
        <p>Files that could not be read are listed here with the reason, so no resume disappears silently.</p>
      </header>
      {failed.length === 0 ? (
        <EmptyState title="No files failed in this batch">{model.summary.successfully_parsed ?? "All"} of {model.summary.total_files ?? "the"} files were read successfully.</EmptyState>
      ) : (
        <div className="glass table-scroll">
          <table className="table">
            <thead><tr><th>Resume</th><th>Status</th><th>Reason</th></tr></thead>
            <tbody>
              {failed.map((r) => (
                <tr key={r.id} className="row"><td className="cell-name">{r.file}</td><td><Badge tone="orange">FAILED</Badge></td><td>{r.raw.error}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {duplicates.length > 0 && (
        <section>
          <div className="section-head"><h2>Skipped duplicates</h2><p>Same text as another resume, so only one was scored.</p></div>
          <div className="glass panel"><ul className="plain-list">{duplicates.map((d, i) => <li key={i}>{typeof d === "string" ? d : JSON.stringify(d)}</li>)}</ul></div>
        </section>
      )}
    </div>
  );
}
