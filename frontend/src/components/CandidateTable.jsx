import { useMemo, useState } from "react";
import CandidateRow from "./CandidateRow.jsx";
import { EmptyState } from "./States.jsx";

const COLUMNS = [
  { key: "rank", label: "Rank" },
  { key: "name", label: "Candidate" },
  { key: "score", label: "Final score" },
  { key: "aiLevel", label: "AI depth" },
  { key: "pyScore", label: "Python / Backend" },
  { key: "github", label: "GitHub" },
  { key: "kind", label: "Eligibility" },
  { key: "status", label: "Status" },
];

const sortValue = (r, key) => {
  if (key === "name") return r.name.toLowerCase();
  if (key === "github") return r.github?.scored ? r.github.score : null;
  if (key === "kind") return r.kind;
  if (key === "status") return r.status;
  return r[key];
};

export default function CandidateTable({ rows, selected, onToggle }) {
  const [view, setView] = useState({ key: "rank", dir: "asc" });
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("eligible");
  const [level, setLevel] = useState("any");
  const [minScore, setMinScore] = useState(0);

  const counts = useMemo(() => ({
    eligible: rows.filter((r) => r.kind === "eligible").length,
    rejected: rows.filter((r) => r.kind === "rejected").length,
    failed: rows.filter((r) => r.kind === "failed").length,
    all: rows.length,
  }), [rows]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = rows.filter((r) => {
      if (scope !== "all" && r.kind !== scope) return false;
      if (q && !`${r.name} ${r.file} ${r.email}`.toLowerCase().includes(q)) return false;
      if (level !== "any" && r.aiLevel !== Number(level)) return false;
      if (minScore > 0 && !(r.score !== null && r.score >= minScore)) return false;
      return true;
    });
    const { key, dir } = view;
    const sign = dir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => {
      const x = sortValue(a, key), y = sortValue(b, key);
      if (x === null || x === undefined) return y === null || y === undefined ? 0 : 1; // blanks always last
      if (y === null || y === undefined) return -1;
      return (x < y ? -1 : x > y ? 1 : 0) * sign;
    });
  }, [rows, scope, query, level, minScore, view]);

  const sortBy = (key) => setView((v) => (v.key === key ? { key, dir: v.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" || key === "rank" || key === "kind" ? "asc" : "desc" }));
  const reset = () => { setQuery(""); setScope("eligible"); setLevel("any"); setMinScore(0); };
  const filtered = query || level !== "any" || minScore > 0 || scope !== "eligible";
  const full = selected.length >= 3;

  return (
    <div className="table-wrap">
      <div className="glass filters">
        <label className="field grow">
          <span>Search</span>
          <input type="search" placeholder="Name, file or email" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <div className="field">
          <span id="scope-label">Eligibility</span>
          <div className="seg" role="group" aria-labelledby="scope-label">
            {[["eligible", "Eligible"], ["rejected", "Rejected"], ["failed", "Failed"], ["all", "All"]].map(([k, l]) => (
              <button key={k} aria-pressed={scope === k} onClick={() => setScope(k)}>{l} <small className="num">{counts[k]}</small></button>
            ))}
          </div>
        </div>
        <label className="field">
          <span>AI depth</span>
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="any">Any level</option>
            {[4, 3, 2, 1, 0].map((n) => <option key={n} value={n}>Level {n}</option>)}
          </select>
        </label>
        <label className="field range">
          <span>Minimum score <strong className="num">{minScore}</strong></span>
          <input type="range" min="0" max="100" step="5" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} />
        </label>
        {filtered && <button className="btn-quiet" onClick={reset}>Reset</button>}
      </div>

      {shown.length === 0 ? (
        <EmptyState title="No candidates match these filters">Adjust the search, depth or score filter, or reset them.</EmptyState>
      ) : (
        <div className="glass table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th className="cell-check"><span className="sr-only">Select for comparison</span></th>
                {COLUMNS.map((c) => (
                  <th key={c.key} aria-sort={view.key === c.key ? (view.dir === "asc" ? "ascending" : "descending") : "none"}>
                    <button onClick={() => sortBy(c.key)}>{c.label}<span className={`sort ${view.key === c.key ? view.dir : ""}`} aria-hidden="true" /></button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <CandidateRow key={r.id} row={r} selectable={r.kind === "eligible"} selected={selected.includes(r.file)} disableSelect={full} onToggle={onToggle} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted table-foot">Showing {shown.length} of {counts.all} files. Tick 2 or 3 eligible candidates to compare them.</p>
    </div>
  );
}
