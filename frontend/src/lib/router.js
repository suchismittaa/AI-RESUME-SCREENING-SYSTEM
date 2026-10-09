// Tiny hash router: #/ , #/candidate/<file> , #/compare?c=a&c=b , #/rejected , #/failed
export function parseHash(hash) {
  const raw = (hash || "").replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  const parts = path.split("/").filter(Boolean);
  const params = new URLSearchParams(query);
  if (parts[0] === "candidate" && parts[1]) return { name: "candidate", file: decodeURIComponent(parts[1]) };
  if (parts[0] === "compare") return { name: "compare", files: params.getAll("c") };
  if (parts[0] === "rejected") return { name: "rejected" };
  if (parts[0] === "failed") return { name: "failed" };
  return { name: "dashboard" };
}

export const hrefs = {
  dashboard: () => "#/",
  candidate: (f) => `#/candidate/${encodeURIComponent(f)}`,
  compare: (files) => `#/compare?${files.map((f) => `c=${encodeURIComponent(f)}`).join("&")}`,
  rejected: () => "#/rejected",
  failed: () => "#/failed",
};
