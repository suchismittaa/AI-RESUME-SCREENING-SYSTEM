"""FastAPI wrapper:  uvicorn screener.api:app --app-dir src   (then open http://127.0.0.1:8000)

POST /screen   {"input_dir": "./resumes"}  -> runs the pipeline, stores and returns the result
GET  /results                              -> last result. Before any /screen call it serves the saved
                                              output/results.json (written by the CLI), so the console works right after
                                              `python main.py`. 404 only when neither exists.
GET  /status                               -> where /results currently comes from ("live run" or the saved file)
GET  /compare?candidates=a.pdf&candidates=b.pdf   -> comparison data for 2-3 candidates from the same result
                                              (file names or candidate names; comma-separated also accepted)
GET  /                                     -> the recruiter console (frontend/dist, built with `npm run build`)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .compare import build_comparison
from .config import load_settings
from .pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = Path(os.environ.get("RESULTS_PATH", ROOT / "output" / "results.json"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", ROOT / "frontend" / "dist"))

app = FastAPI(title="Resume screener")
# Only needed when the frontend is served from another origin (e.g. a separate static server during development).
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

_last: dict | None = None
_source: str = "none"


class ScreenRequest(BaseModel):
    input_dir: str = "./resumes"


def _current() -> dict | None:
    """The last live run, else the saved results file (read on demand so a re-run of the CLI is picked up)."""
    global _last, _source
    if _last is not None:
        return _last
    try:
        data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    _source = "saved file"
    return data if isinstance(data, dict) and "ranked_candidates" in data else None


@app.post("/screen")
def screen(req: ScreenRequest) -> dict:
    global _last, _source
    try:
        _last = run_pipeline(Path(req.input_dir), load_settings())
        _source = "live run"
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _last


@app.get("/results")
def results() -> dict:
    data = _current()
    if data is None:
        raise HTTPException(status_code=404, detail="No results yet: run `python main.py -i ./resumes -o output/results.json` or POST /screen")
    return data


@app.get("/status")
def status() -> dict:
    data = _current()
    return {"has_results": data is not None, "source": _source if data is not None else "none", "results_path": str(RESULTS_PATH)}


@app.get("/compare")
def compare(candidates: list[str] = Query(..., description="2-3 candidate file names or names")) -> dict:
    data = _current()
    if data is None:
        raise HTTPException(status_code=404, detail="No results yet: run `python main.py` or POST /screen first")
    ids = [i for c in candidates for i in c.split(",")]
    try:
        return build_comparison(data, ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Serve the built console last so the API routes above take precedence.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="console")
