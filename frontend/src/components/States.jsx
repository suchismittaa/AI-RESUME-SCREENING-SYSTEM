export function Loading({ text = "Loading screening results" }) {
  return <div className="state glass"><span className="spinner" aria-hidden="true" /><p>{text}</p></div>;
}

export function ErrorState({ error, onRetry }) {
  const empty = error?.kind === "empty";
  const net = error?.kind === "network";
  return (
    <div className="state glass" role="alert">
      <h2>{empty ? "No screening results yet" : net ? "The screening API is not reachable" : "Could not load results"}</h2>
      <p>{error?.message}</p>
      {empty && <p className="muted">Run <code>python main.py -i ./resumes -o output/results.json</code> in the project folder, then reload.</p>}
      {net && <p className="muted">Start the backend with <code>uvicorn screener.api:app --app-dir src</code> and open http://127.0.0.1:8000.</p>}
      <button className="btn-primary" onClick={onRetry}>Try again</button>
    </div>
  );
}

export function EmptyState({ title, children }) {
  return <div className="state glass"><h2>{title}</h2>{children ? <p className="muted">{children}</p> : null}</div>;
}
