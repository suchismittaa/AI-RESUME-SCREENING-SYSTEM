const LEVELS = [1, 2, 3, 4];
const NAMES = { 1: "Thin wrapper", 2: "Applied AI", 3: "RAG / AI system", 4: "Agentic / advanced" };

// Four-step track. The active step is filled; Level 0 (no implementation evidence) leaves every step empty.
export default function AiDepthIndicator({ level, label, compact = false }) {
  if (level === null || level === undefined) return <span className="muted">n/a</span>;
  return (
    <div className={`depth ${compact ? "depth-compact" : ""}`} role="img" aria-label={`AI depth level ${level}${label ? `: ${label}` : ""}`}>
      <div className="depth-track">
        {LEVELS.map((n, i) => (
          <div key={n} className="depth-step">
            {i > 0 && <span className={`depth-line ${level >= n ? "on" : ""}`} />}
            <span className={`depth-dot ${level === n ? "active" : level > n ? "past" : ""}`} />
          </div>
        ))}
      </div>
      {!compact && (
        <div className="depth-labels">
          {LEVELS.map((n) => (
            <span key={n} className={level === n ? "active" : ""}>
              Level {n}
              <small>{NAMES[n]}</small>
            </span>
          ))}
        </div>
      )}
      {compact && <span className="depth-compact-text num">L{level}</span>}
    </div>
  );
}
