import { fmt } from "../lib/model.js";
import { hrefs } from "../lib/router.js";
import Badge, { EligibilityBadge } from "./Badge.jsx";
import AiDepthIndicator from "./AiDepthIndicator.jsx";

function GithubCell({ g, kind }) {
  if (kind !== "eligible") return <span className="muted">–</span>;
  if (g.scored) return <span className="num">{fmt(g.score)} / 10</span>;
  if (g.status === "not_provided") return <Badge tone="mauve" title="No GitHub profile on the resume">No profile</Badge>;
  return <Badge tone="orange" title={g.reason || g.status}>Unavailable</Badge>;
}

export default function CandidateRow({ row, selected, selectable, disableSelect, onToggle }) {
  const top = row.rank === 1;
  return (
    <tr className={`row ${selected ? "is-selected" : ""}`}>
      <td className="cell-check">
        {selectable ? (
          <input type="checkbox" checked={selected} disabled={disableSelect && !selected} onChange={() => onToggle(row.file)} aria-label={`Select ${row.name} for comparison`} />
        ) : null}
      </td>
      <td className="cell-rank num">{row.rank ? <span className={`rank ${top ? "rank-top" : ""}`}>{row.rank}</span> : <span className="muted">–</span>}</td>
      <td className="cell-name">
        <a href={hrefs.candidate(row.file)} className="name-link">{row.name}</a>
        <span className="muted file">{row.file}</span>
      </td>
      <td className="num cell-score">{row.score !== null ? <strong>{fmt(row.score)}</strong> : <span className="muted">–</span>}</td>
      <td>{row.aiLevel !== null ? (
        <span className="ai-cell"><AiDepthIndicator level={row.aiLevel} label={row.aiLabel} compact /><span className="muted num">{fmt(row.aiScore)} / 40</span></span>
      ) : <span className="muted">–</span>}</td>
      <td className="num">{row.pyScore !== null ? `${fmt(row.pyScore)} / 30` : <span className="muted">–</span>}</td>
      <td><GithubCell g={row.github} kind={row.kind} /></td>
      <td><EligibilityBadge eligible={row.kind === "eligible"} kind={row.kind} /></td>
      <td className="muted">{row.status}</td>
    </tr>
  );
}
