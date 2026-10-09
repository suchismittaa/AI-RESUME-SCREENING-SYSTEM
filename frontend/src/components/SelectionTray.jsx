import { hrefs } from "../lib/router.js";

export default function SelectionTray({ selected, byFile, onRemove, onClear }) {
  if (!selected.length) return null;
  const ready = selected.length >= 2;
  return (
    <div className="tray glass" role="region" aria-label="Candidates selected for comparison">
      <div className="tray-items">
        {selected.map((f) => (
          <span key={f} className="chip chip-peach tray-chip">
            {byFile.get(f)?.name || f}
            <button aria-label={`Remove ${byFile.get(f)?.name || f} from comparison`} onClick={() => onRemove(f)}>×</button>
          </span>
        ))}
      </div>
      <span className="muted tray-hint">{ready ? `${selected.length} of 3 selected` : "Select at least one more candidate"}</span>
      <button className="btn-quiet" onClick={onClear}>Clear</button>
      {ready ? <a className="btn-primary" href={hrefs.compare(selected)}>Compare candidates</a> : <span className="btn-primary is-disabled" aria-disabled="true">Compare candidates</span>}
    </div>
  );
}
