// One cell of the comparison grid. `leader` adds a subtle highlight; it never hides the other candidates' values.
export default function ComparisonCell({ leader, children, className = "" }) {
  return <div className={`cmp-cell ${leader ? "is-leader" : ""} ${className}`}>{children}{leader ? <span className="leader-tag">Leads</span> : null}</div>;
}
