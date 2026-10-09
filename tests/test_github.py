from datetime import datetime, timezone

import requests

from screener.config import Settings
from screener.github import GitHubClient

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


class Resp:
    def __init__(self, code=200, body=None, headers=None, text=""):
        self.status_code, self._b, self.headers, self.text = code, body if body is not None else [], headers or {}, text

    def json(self):
        return self._b


class FakeSession:
    def __init__(self, handler):
        self.headers, self.calls, self.handler = {}, [], handler

    def get(self, url, **kw):
        self.calls.append(url)
        return self.handler(url)


def repos(n, days_ago=5, lang="Python"):
    return [{"name": f"r{i}", "fork": False, "archived": False, "language": lang, "description": "agent", "topics": [],
             "pushed_at": (NOW.replace(day=1) if days_ago is None else datetime.fromtimestamp(NOW.timestamp() - days_ago * 86400, timezone.utc)).isoformat()} for i in range(n)]


def client(tmp_path, handler, **kw):
    s = Settings(github_cache_path=str(tmp_path / "c.json"), **{"github_token": "", **kw})
    return GitHubClient(s, FakeSession(handler), now=NOW)


def test_active_profile_scores_and_is_capped(tmp_path):
    c = client(tmp_path, lambda u: Resp(200, repos(7)))
    info = c.enrich(["alice"])
    assert info.status == "ok" and info.activity_score + info.repo_score == 10 and info.relevant_repos


def test_stale_profile_scores_low(tmp_path):
    c = client(tmp_path, lambda u: Resp(200, repos(2, days_ago=900)))
    info = c.enrich(["bob"])
    assert info.status == "ok" and info.activity_score == 0 and info.repo_score == 0


def test_missing_username_and_404_fall_through(tmp_path):
    assert client(tmp_path, lambda u: Resp(200)).enrich([]).status == "not_provided"
    c = client(tmp_path, lambda u: Resp(404) if "ghost" in u else Resp(200, repos(3)))
    info = c.enrich(["ghost", "real"])  # first handle 404s, second resolves
    assert info.status == "ok" and info.username == "real"
    assert client(tmp_path, lambda u: Resp(404)).enrich(["ghost"]).status == "not_found"


def test_rate_limit_trips_breaker_and_stops_calls(tmp_path):
    c = client(tmp_path, lambda u: Resp(403, headers={"X-RateLimit-Remaining": "0"}, text="API rate limit exceeded"))
    assert c.enrich(["a"]).status == "rate_limited"
    assert c.enrich(["b"]).status == "rate_limited"
    assert len(c.session.calls) == 1


def test_network_errors_never_raise_and_breaker_opens(tmp_path):
    def boom(u):
        raise requests.ConnectionError("down")
    c = client(tmp_path, boom)
    statuses = [c.enrich([f"u{i}"]).status for i in range(6)]
    assert set(statuses) == {"unavailable"} and len(c.session.calls) == 3


def test_cache_avoids_repeat_calls_and_persists(tmp_path):
    c = client(tmp_path, lambda u: Resp(200, repos(2)))
    c.enrich(["same"]); c.enrich(["Same"])
    assert len(c.session.calls) == 1
    c.flush()
    c2 = client(tmp_path, lambda u: Resp(500))
    assert c2.enrich(["same"]).status == "ok" and not c2.session.calls
