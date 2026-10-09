"""Lightweight GitHub enrichment using the public REST API.

* 1 request/user by default (repos list); a 2nd (public events) only when a token is configured, so an
  unauthenticated run of ~45 candidates stays under the 60 req/h limit.
* Results (including 404s) are cached on disk with a TTL, so re-runs and duplicate usernames cost nothing.
* Never raises: every failure is converted to a status on GitHubInfo. A circuit breaker stops calling GitHub
  after repeated hard failures / rate limiting so one outage cannot slow the batch down.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import Settings
from .models import GitHubInfo

log = logging.getLogger(__name__)
API = "https://api.github.com"
AI_REPO_HINTS = ("llm", "rag", "agent", "langchain", "langgraph", "gpt", "openai", "gemini", "embedding", "vector", "chatbot", "ai-", "-ai", "ml", "nlp", "transformer")


class _Fail(Exception):
    def __init__(self, status: str, msg: str):
        super().__init__(msg)
        self.status, self.msg = status, msg


class GitHubClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None, now: datetime | None = None):
        self.s = settings
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "resume-screener"})
        if settings.github_token:
            self.session.headers["Authorization"] = f"Bearer {settings.github_token}"
        self._now = now
        self._lock = threading.Lock()
        self._mem: dict[str, dict] = {}
        self._hard_failures = 0
        self._tripped: tuple[str, str] | None = None  # (status, message) once the breaker opens
        self._cache_path = Path(settings.github_cache_path)
        self._disk = self._load_disk()

    # ---------------------------------------------------------------- cache
    def _load_disk(self) -> dict:
        try:
            return json.loads(self._cache_path.read_text())
        except Exception:
            return {}

    def flush(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(self._disk))
        except Exception as e:  # cache is an optimisation only
            log.debug("cache write failed: %s", e)

    def _cached(self, key: str) -> dict | None:
        if key in self._mem:
            return self._mem[key]
        entry = self._disk.get(key)
        if entry and time.time() - entry["t"] < self.s.github_cache_ttl_hours * 3600:
            self._mem[key] = entry["data"]
            return entry["data"]
        return None

    def _store(self, key: str, data: dict) -> None:
        self._mem[key] = data
        self._disk[key] = {"t": time.time(), "data": data}

    # ---------------------------------------------------------------- http
    def _get(self, path: str, params: dict | None = None):
        if self._tripped:
            raise _Fail(*self._tripped)
        try:
            r = self.session.get(API + path, params=params, timeout=self.s.github_timeout_s)
        except requests.RequestException as e:
            self._hard_fail("unavailable", f"network error: {type(e).__name__}")
            raise _Fail("unavailable", f"network error: {type(e).__name__}")
        if r.status_code == 404:
            self._hard_failures = 0
            raise _Fail("not_found", "profile not found")
        remaining = r.headers.get("X-RateLimit-Remaining")
        if r.status_code in (403, 429) and (remaining == "0" or "rate limit" in r.text.lower() or r.status_code == 429):
            with self._lock:
                self._tripped = ("rate_limited", "GitHub API rate limit reached (set GITHUB_TOKEN for 5000 req/h)")
            raise _Fail(*self._tripped)
        if r.status_code >= 400:
            self._hard_fail("unavailable" if r.status_code in (401, 403) or r.status_code >= 500 else "error", f"HTTP {r.status_code}")
            raise _Fail("unavailable" if r.status_code in (401, 403) or r.status_code >= 500 else "error", f"HTTP {r.status_code}")
        self._hard_failures = 0
        return r.json()

    def _hard_fail(self, status: str, msg: str) -> None:
        with self._lock:
            self._hard_failures += 1
            if self._hard_failures >= self.s.github_breaker_threshold and not self._tripped:
                self._tripped = (status, f"{msg} (GitHub disabled for the rest of this run after repeated failures)")
                log.warning("GitHub circuit breaker opened: %s", msg)

    # ---------------------------------------------------------------- fetch + score
    def _fetch(self, username: str) -> dict:
        key = username.lower()
        hit = self._cached(key)
        if hit is not None:
            return hit
        repos = self._get(f"/users/{username}/repos", {"per_page": 100, "sort": "pushed", "type": "owner"})
        events = []
        if self.s.github_token:
            try:
                events = self._get(f"/users/{username}/events/public", {"per_page": 100})
            except _Fail:
                events = []
        data = {"repos": repos, "events": events}
        self._store(key, data)
        return data

    def _days(self, iso: str) -> int:
        now = self._now or datetime.now(timezone.utc)
        return max(0, (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days)

    def enrich(self, usernames: list[str]) -> GitHubInfo:
        if not self.s.github_enabled:
            return GitHubInfo(status="disabled", summary="GitHub enrichment disabled")
        if not usernames:
            return GitHubInfo(status="not_provided", summary="No GitHub profile found in resume")
        last: _Fail | None = None
        for u in usernames[:3]:  # a resume can mention several handles; first one that resolves wins
            try:
                data = self._fetch(u)
            except _Fail as f:
                last = f
                if f.status in ("rate_limited", "unavailable"):
                    break
                continue
            except Exception as e:  # defensive: malformed JSON etc.
                last = _Fail("error", f"{type(e).__name__}: {e}")
                continue
            return self._score(u, data)
        st = last.status if last else "error"
        return GitHubInfo(status=st, username=usernames[0], profile_url=f"https://github.com/{usernames[0]}",
                          error=last.msg if last else None, summary=f"GitHub enrichment {st}: {last.msg if last else ''}".strip())

    def _score(self, username: str, data: dict) -> GitHubInfo:
        repos = [r for r in data["repos"] if isinstance(r, dict)]
        own = [r for r in repos if not r.get("fork")]
        pushed = [(self._days(r["pushed_at"]), r) for r in own if r.get("pushed_at")]
        maintained = [r for d, r in pushed if d <= 365 and not r.get("archived")]
        last_repo_push = min((d for d, _ in pushed), default=None)
        push_events = [e for e in data.get("events", []) if e.get("type") == "PushEvent" and self._days(e["created_at"]) <= 90]
        last_event = min((self._days(e["created_at"]) for e in data.get("events", []) if e.get("type") == "PushEvent"), default=None)
        last = min([d for d in (last_repo_push, last_event) if d is not None], default=None)

        recency = 0 if last is None else 3 if last <= 30 else 2 if last <= 90 else 1 if last <= 180 else 0
        recent_repos = sum(1 for d, r in pushed if d <= 90)
        volume = max(2 if len(push_events) >= 10 else 1 if len(push_events) >= 3 else 0,
                     2 if recent_repos >= 3 else 1 if recent_repos >= 1 else 0)
        activity = min(5, recency + volume)

        def relevant(r: dict) -> bool:
            blob = " ".join(str(x or "") for x in (r.get("name"), r.get("description"), " ".join(r.get("topics") or []))).lower()
            return (r.get("language") or "").lower() == "python" or any(h in blob for h in AI_REPO_HINTS)

        rel = [r["name"] for r in maintained if relevant(r)]
        repo_score = min(5, (1 if len(maintained) >= 1 else 0) + (1 if len(maintained) >= 3 else 0) + (1 if len(maintained) >= 6 else 0)
                         + (1 if len(rel) >= 1 else 0) + (1 if len(rel) >= 3 else 0))
        recency_txt = "no recent public pushes" if last is None else f"last push {last}d ago"
        summary = (f"{recency_txt}; {len(maintained)} maintained original repos (12m), {len(rel)} Python/AI-relevant"
                   + (f"; {len(push_events)} push events in 90d" if data.get("events") else ""))
        return GitHubInfo(status="ok", username=username, profile_url=f"https://github.com/{username}", public_repos=len(repos),
                          recent_push_events_90d=len(push_events) if data.get("events") else None, last_push_days_ago=last,
                          maintained_repos_12m=len(maintained), relevant_repos=rel[:5],
                          activity_score=activity, repo_score=repo_score, summary=summary)
