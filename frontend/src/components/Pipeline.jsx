import { useMemo } from "react";

// Real counts from batch_summary. The descriptions say what each stage does; the numbers are the batch's own.
export default function Pipeline({ summary }) {
  const s = summary || {};
  const gh = s.github_status_counts || {};
  const ghOk = gh.ok || 0;
  const ghUnavail = Object.entries(gh).filter(([k]) => !["ok", "not_provided", "skipped", "disabled"].includes(k)).reduce((a, [, v]) => a + v, 0);
  const stages = useMemo(() => [
    { name: "Resumes", value: s.total_files, note: "files received" },
    { name: "Extract", value: s.successfully_parsed, note: s.failed_or_unreadable ? `${s.failed_or_unreadable} failed to read` : "all files readable" },
    { name: "Eligibility", value: s.eligible, note: `eligible, ${s.rejected ?? 0} rejected by rules` },
    { name: "AI analysis", value: s.eligible, note: s.llm_mode },
    { name: "Scoring", value: s.eligible, note: "scored out of 100" },
    { name: "GitHub", value: ghOk, note: ghUnavail ? `${ghUnavail} unavailable` : gh.not_provided ? `${gh.not_provided} without a profile` : "enriched", attn: ghUnavail > 0 },
    { name: "Ranking", value: s.eligible, note: "candidates ranked" },
  ], [s, ghOk, ghUnavail, gh.not_provided]);
  return (
    <ol className="pipeline" aria-label="Screening pipeline">
      {stages.map((st) => (
        <li key={st.name} className={`glass stage ${st.attn ? "attn" : ""}`}>
          <span className="stage-name">{st.name}</span>
          <span className="stage-value num">{st.value ?? "–"}</span>
          <span className="stage-note">{st.note}</span>
        </li>
      ))}
    </ol>
  );
}
