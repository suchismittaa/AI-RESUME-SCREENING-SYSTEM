import Badge from "./Badge.jsx";
import { fmt } from "../lib/model.js";

const STATUS_TEXT = {
  ok: "GitHub activity found",
  not_provided: "No GitHub profile on the resume",
  not_found: "GitHub profile not found",
  rate_limited: "GitHub rate limit reached",
  unavailable: "GitHub enrichment unavailable",
  error: "GitHub enrichment failed",
  disabled: "GitHub enrichment was turned off for this run",
  skipped: "GitHub not checked",
};

export default function GithubPanel({ candidate }) {
  const g = candidate.github || {};
  const t = candidate.evidence_trace?.github || {};
  const status = g.status || "not_provided";
  const ok = status === "ok";
  return (
    <section className="glass panel github">
      <div className="section-head">
        <h2>GitHub</h2>
        {ok ? <Badge tone="peach">Scored</Badge> : status === "not_provided" ? <Badge tone="mauve">No profile</Badge> : <Badge tone="orange">Not scored</Badge>}
      </div>
      <p className="github-status">{STATUS_TEXT[status] || status}</p>
      {!ok && (g.error || t.reason) ? <p className="callout">{g.error || t.reason}</p> : null}
      {ok ? (
        <dl className="facts">
          {g.username && <><dt>Profile</dt><dd><a href={g.profile_url} target="_blank" rel="noreferrer">{g.username}</a></dd></>}
          {g.public_repos != null && <><dt>Public repositories</dt><dd className="num">{g.public_repos}</dd></>}
          {g.last_push_days_ago != null && <><dt>Last push</dt><dd className="num">{g.last_push_days_ago} days ago</dd></>}
          {g.maintained_repos_12m != null && <><dt>Maintained repos (12 months)</dt><dd className="num">{g.maintained_repos_12m}</dd></>}
          {g.recent_push_events_90d != null && <><dt>Push events (90 days)</dt><dd className="num">{g.recent_push_events_90d}</dd></>}
          <dt>Activity score</dt><dd className="num">{fmt(g.activity_score)} / 5</dd>
          <dt>Repository score</dt><dd className="num">{fmt(g.repo_score)} / 5</dd>
          {g.relevant_repos?.length ? <><dt>Relevant repositories</dt><dd><div className="chips">{g.relevant_repos.map((r) => <span key={r} className="chip">{r}</span>)}</div></dd></> : null}
        </dl>
      ) : (
        <>
          {g.username ? <p className="muted">Username from resume: {g.profile_url ? <a href={g.profile_url} target="_blank" rel="noreferrer">{g.username}</a> : g.username}</p> : null}
          <p className="github-note">{t.explanation || "Missing GitHub data is not a negative signal."}</p>
        </>
      )}
      {ok && g.summary ? <p className="github-note">{g.summary}</p> : null}
    </section>
  );
}
