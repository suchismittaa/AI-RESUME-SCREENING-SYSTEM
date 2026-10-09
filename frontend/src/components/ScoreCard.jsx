import { fmt } from "../lib/model.js";
import ScoreBar from "./ScoreBar.jsx";
import Badge from "./Badge.jsx";

// One category of the backend score breakdown. A GitHub score that was never assessed is shown as such, not as 0.
export default function ScoreCard({ label, score, max, unassessed, unassessedText }) {
  return (
    <div className="glass score-card">
      <div className="score-card-label">{label}</div>
      {unassessed ? (
        <>
          <div className="score-card-value muted">not scored</div>
          <ScoreBar value={0} max={max} muted />
          <div className="score-card-note"><Badge tone="orange">Unavailable</Badge> {unassessedText}</div>
        </>
      ) : (
        <>
          <div className="score-card-value num">{fmt(score)}<span> / {fmt(max)}</span></div>
          <ScoreBar value={score} max={max} tone="peach" />
        </>
      )}
    </div>
  );
}
