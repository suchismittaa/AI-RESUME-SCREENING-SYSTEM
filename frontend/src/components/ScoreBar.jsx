import { fmt } from "../lib/model.js";

export default function ScoreBar({ value, max, tone = "peach", muted = false, label }) {
  const pct = value === null || value === undefined || !max ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`bar ${muted ? "bar-muted" : ""}`} role="img" aria-label={label || `${fmt(value)} of ${fmt(max)}`}>
      <div className={`bar-fill bar-${tone}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
