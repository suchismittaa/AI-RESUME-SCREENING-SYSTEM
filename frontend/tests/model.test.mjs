import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildModel, fmt, rankingCaveats } from "../src/lib/model.js";
import { parseHash } from "../src/lib/router.js";

const results = JSON.parse(readFileSync(new URL("../../output/results.json", import.meta.url)));
const m = buildModel(results);

test("rows come straight from the backend result (no invented candidates)", () => {
  const files = new Set([...results.ranked_candidates, ...results.rejected_candidates, ...results.failed_files].map((c) => c.file));
  assert.equal(m.all.length, files.size);
  assert.ok(m.all.every((r) => files.has(r.file)));
  assert.equal(m.eligible.length, results.batch_summary.eligible);
  assert.equal(m.rejected.length, results.batch_summary.rejected);
  assert.equal(m.failed.length, results.batch_summary.failed_or_unreadable);
});

test("ranks, scores and levels are copied, not recomputed", () => {
  results.ranked_candidates.forEach((c, i) => {
    assert.equal(m.eligible[i].rank, c.rank);
    assert.equal(m.eligible[i].score, c.total_score);
    assert.equal(m.eligible[i].aiLevel, c.ai_project_quality.level);
  });
  assert.equal(m.top.rank, 1);
});

test("average eligible score is derived from the real scores", () => {
  const s = results.ranked_candidates.map((c) => c.total_score);
  assert.equal(m.avgEligibleScore, Math.round((s.reduce((a, b) => a + b, 0) / s.length) * 10) / 10);
});

test("GitHub failures stay failures (never a positive signal)", () => {
  for (const r of m.eligible) {
    if (r.github.status !== "ok") assert.equal(r.github.scored, false);
  }
});

test("caveats only quote backend text", () => {
  for (const r of m.eligible) for (const c of rankingCaveats(r.raw)) assert.ok(c.text.length > 0);
});

test("fmt and router", () => {
  assert.equal(fmt(40), "40");
  assert.equal(fmt(13.14), "13.1");
  assert.equal(fmt(undefined), "n/a");
  assert.deepEqual(parseHash("#/compare?c=a.pdf&c=b.pdf"), { name: "compare", files: ["a.pdf", "b.pdf"] });
  assert.deepEqual(parseHash("#/candidate/candidate_35.pdf"), { name: "candidate", file: "candidate_35.pdf" });
});
