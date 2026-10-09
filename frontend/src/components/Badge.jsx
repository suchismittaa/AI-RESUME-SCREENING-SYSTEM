// tone: "gold" (top / selected), "peach" (eligible), "mauve" (rejected / neutral), "orange" (attention), "plain"
export default function Badge({ tone = "plain", children, title }) {
  return <span className={`badge badge-${tone}`} title={title}>{children}</span>;
}

export function EligibilityBadge({ eligible, kind }) {
  if (kind === "failed") return <Badge tone="orange">FAILED</Badge>;
  return eligible ? <Badge tone="peach">ELIGIBLE</Badge> : <Badge tone="mauve">REJECTED</Badge>;
}
