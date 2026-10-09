"""Pydantic models: the data contracts between pipeline stages and the JSON output schema."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Section(BaseModel):
    name: str
    text: str


class ParsedResume(BaseModel):
    file: str
    candidate_name: str
    email: Optional[str] = None
    github_usernames: list[str] = Field(default_factory=list)  # ordered by confidence
    text: str
    sections: list[Section] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)


class EligibilityResult(BaseModel):
    eligible: bool
    python_evidence: list[str] = Field(default_factory=list)
    ai_evidence: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    ai_project_depth: float = 0
    python_backend: float = 0
    cloud_fullstack: float = 0
    github: float = 0
    engineering_depth: float = 0


class ProjectJudgment(BaseModel):
    """Structured output requested from the LLM (provider-agnostic)."""

    best_project: str = ""
    ai_depth_score: int = Field(ge=0, le=40, description="0-40 depth of the strongest AI/agentic work, BEFORE penalties")
    thin_wrapper: bool = Field(description="True if the strongest 'AI project' is only an LLM API call with no real workflow")
    tutorial_style: bool = False
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list, description="Short verbatim quotes from the resume")


class GitHubInfo(BaseModel):
    status: Literal[
        "ok", "not_provided", "not_found", "rate_limited", "unavailable", "error", "disabled", "skipped"
    ] = "not_provided"
    username: Optional[str] = None
    profile_url: Optional[str] = None
    public_repos: Optional[int] = None
    recent_push_events_90d: Optional[int] = None
    last_push_days_ago: Optional[int] = None
    maintained_repos_12m: Optional[int] = None
    relevant_repos: list[str] = Field(default_factory=list)
    activity_score: float = 0
    repo_score: float = 0
    summary: str = ""
    error: Optional[str] = None


class EvidenceItem(BaseModel):
    """One piece of supporting evidence. `text` is a verbatim resume quote (or a GitHub API-derived fact when source='github')."""

    signal: str = ""  # what this evidence supports, e.g. "FastAPI"
    text: str
    source: str = "resume"  # resume section name ("projects", "experience", "skills", ...) or "github"


class CategoryEvidence(BaseModel):
    """Explains one score category. Evidence only ever comes from resume text or real GitHub data."""

    score: float = 0
    max_score: float = 0
    explanation: str = ""
    signals: list[str] = Field(default_factory=list)  # detected signals (rule-based)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # the existing per-point score notes
    # GitHub-only fields
    scored: Optional[bool] = None
    enrichment_status: Optional[str] = None
    reason: Optional[str] = None


class EvidenceTrace(BaseModel):
    ai_project_depth: CategoryEvidence = Field(default_factory=CategoryEvidence)
    python_backend: CategoryEvidence = Field(default_factory=CategoryEvidence)
    cloud_fullstack: CategoryEvidence = Field(default_factory=CategoryEvidence)
    github: CategoryEvidence = Field(default_factory=CategoryEvidence)
    engineering_depth: CategoryEvidence = Field(default_factory=CategoryEvidence)


class AIProjectQuality(BaseModel):
    """Recruiter-facing view of the existing AI project judgment (level is derived from detected signals, not framework names)."""

    level: int = Field(ge=0, le=4, description="0 = no implementation evidence, 1 thin wrapper, 2 applied AI, 3 RAG/AI system, 4 agentic/advanced")
    label: str
    score: float = 0
    max_score: float = 40
    best_project: str = ""  # empty when the unit title is not a usable project name (e.g. a company/date line)
    best_project_section: str = ""
    summary: str = ""
    implementation_signals: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    quality_concerns: list[str] = Field(default_factory=list)
    thin_wrapper: bool = False
    tutorial_style: bool = False
    skills_only: bool = False


class CandidateResult(BaseModel):
    rank: Optional[int] = None
    candidate_name: str
    file: str
    email: Optional[str] = None
    eligible: bool
    total_score: Optional[float] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    score_notes: dict[str, list[str]] = Field(default_factory=dict)  # per-category explanations
    penalties: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)  # rejected candidates: which hard requirement(s) had no evidence
    matched_skills: list[str] = Field(default_factory=list)
    project_summary: str = ""
    github_summary: str = ""
    github: Optional[GitHubInfo] = None
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    evidence_trace: Optional[EvidenceTrace] = None
    ai_project_quality: Optional[AIProjectQuality] = None
    why_candidate: Optional[str] = None  # eligible candidates only
    llm_used: bool = False
    llm_error: Optional[str] = None
    duplicate_of: Optional[str] = None


class FailedFile(BaseModel):
    file: str
    error: str
