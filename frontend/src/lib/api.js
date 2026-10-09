// Thin client for the existing FastAPI backend. The backend is the source of truth.

async function getJson(path) {
  let res;
  try {
    res = await fetch(path, { headers: { Accept: "application/json" } });
  } catch (e) {
    const err = new Error("Cannot reach the screening API.");
    err.kind = "network";
    throw err;
  }
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch { /* not JSON */ }
    const err = new Error(detail || `Request failed (HTTP ${res.status})`);
    err.kind = res.status === 404 ? "empty" : "http";
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const API_BASE = (typeof window !== "undefined" && window.__API_BASE__) || "";

export const fetchResults = () => getJson(`${API_BASE}/results`);
export const fetchStatus = () => getJson(`${API_BASE}/status`).catch(() => null);
export const fetchComparison = (files) =>
  getJson(`${API_BASE}/compare?` + files.map((f) => `candidates=${encodeURIComponent(f)}`).join("&"));
