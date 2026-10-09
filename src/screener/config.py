"""Configuration: weights, thresholds and environment-driven settings. No business logic here."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # optional convenience; env vars work without it
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


@dataclass(frozen=True)
class Weights:
    ai_project_depth: int = 40
    python_backend: int = 30
    cloud_fullstack: int = 15
    github: int = 10
    engineering_depth: int = 5


@dataclass(frozen=True)
class Penalties:
    thin_wrapper: int = 10          # spec: 5-15
    thin_wrapper_severe: int = 15   # thin wrapper AND tiny/no implementation detail
    tutorial_style: int = 5
    skills_only_ai: int = 5         # AI frameworks only named in a skills list, never used in a project


@dataclass(frozen=True)
class Settings:
    weights: Weights = field(default_factory=Weights)
    penalties: Penalties = field(default_factory=Penalties)
    # Weight applied to a signal found only in the Skills section (vs 1.0 when found in a project/experience).
    skills_only_factor: float = 0.25
    # LLM
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "claude-sonnet-5-5"))
    llm_max_concurrency: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_CONCURRENCY", "4")))
    llm_blend_weight: float = field(default_factory=lambda: float(os.getenv("LLM_BLEND_WEIGHT", "0.5")))
    llm_timeout_s: float = 60.0
    # GitHub
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_max_concurrency: int = field(default_factory=lambda: int(os.getenv("GITHUB_MAX_CONCURRENCY", "4")))
    github_cache_path: str = field(default_factory=lambda: os.getenv("GITHUB_CACHE_PATH", ".cache/github.json"))
    github_cache_ttl_hours: float = field(default_factory=lambda: float(os.getenv("GITHUB_CACHE_TTL_HOURS", "24")))
    github_timeout_s: float = 10.0
    github_breaker_threshold: int = 3  # consecutive hard failures before we stop calling GitHub for this run
    github_enabled: bool = True
    # Ingestion
    supported_extensions: tuple = (".pdf", ".docx", ".txt", ".md")
    min_text_chars: int = 200  # below this a resume is treated as unreadable (likely scanned image)


def load_settings(**overrides) -> Settings:
    return Settings(**overrides)
