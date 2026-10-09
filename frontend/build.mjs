// Bundles src/main.jsx (+ imported CSS) into dist/ with esbuild, and copies index.html. No other tooling needed.
import { build, context } from "esbuild";
import { mkdirSync, copyFileSync, rmSync } from "node:fs";

const watch = process.argv.includes("--watch");
rmSync("dist", { recursive: true, force: true });
mkdirSync("dist/assets", { recursive: true });
copyFileSync("index.html", "dist/index.html");

const options = {
  entryPoints: { app: "src/main.jsx" },
  outdir: "dist/assets",
  bundle: true,
  format: "esm",
  target: ["es2020"],
  jsx: "automatic",
  loader: { ".js": "jsx" },
  minify: !watch,
  sourcemap: watch,
  define: { "process.env.NODE_ENV": watch ? '"development"' : '"production"' },
  logLevel: "info",
};

if (watch) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("Watching src/ ... rebuilds into dist/ (served by the API at http://127.0.0.1:8000)");
} else {
  await build(options);
}
