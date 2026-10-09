from pathlib import Path

import pytest

from screener.config import Settings
from screener.extract import parse_resume
from screener.ingest import RawResume, normalize_text

AGENTIC = """Asha Rao
asha@example.com | github.com/asharao
PROJECTS
Support Agent | Python, FastAPI, LangGraph, PostgreSQL, Redis, Docker, GCP
• Built a stateful multi-agent workflow in LangGraph with tool calling and conditional routing between specialist agents.
• Implemented RAG with chunking, embeddings and pgvector retrieval; added an eval harness measuring hallucination rate on 200 queries.
• Exposed it via async FastAPI with Redis caching, retry/fallback on LLM failures and pytest integration tests; deployed on Cloud Run.
SKILLS
Python, FastAPI, LangGraph, PostgreSQL, Redis, Docker, GCP, React
"""

WRAPPER = """Ravi Kumar
ravi@example.com
PROJECTS
Chatbot | Python, OpenAI API
• Made a chatbot using the OpenAI API that answers questions.
SKILLS
Python, OpenAI API
"""

JS_ONLY = """Jo Smith
jo@example.com
SKILLS
JavaScript, React, Next.js, Node.js, Java, Spring Boot
EXPERIENCE
Frontend Developer
• Built React dashboards and an LLM-powered chatbot UI with the OpenAI API.
"""

PYTHON_NO_AI = """Pat Lee
pat@example.com
SKILLS
Python, Django, PostgreSQL, Docker
PROJECTS
Inventory API | Django, PostgreSQL
• Built REST endpoints for inventory management with authentication and tests.
"""

COPILOT_ONLY = """Sam Wu
sam@example.com
SKILLS
Python, Flask
EXPERIENCE
Developer
• Used GitHub Copilot and AI-assisted development to speed up Flask feature delivery.
"""

CLASSICAL_ML = """Mia Chen
mia@example.com
SKILLS
Python, scikit-learn, TensorFlow
PROJECTS
Skin cancer detection | Python, TensorFlow, OpenCV
• Trained CNN models for image classification with 92% accuracy.
"""

SKILLS_ONLY_AI = """Lee Park
lee@example.com
SKILLS
Python, FastAPI, LangChain, LangGraph, RAG, PostgreSQL
EXPERIENCE
Backend Intern
• Maintained REST endpoints for an inventory service and wrote unit tests.
"""


@pytest.fixture
def settings(tmp_path):
    return Settings(github_cache_path=str(tmp_path / "gh.json"), github_enabled=False, anthropic_api_key="", min_text_chars=50)


def make(text: str, name: str = "x.txt", links=None):
    return parse_resume(RawResume(Path(name), normalize_text(text), links or []))
