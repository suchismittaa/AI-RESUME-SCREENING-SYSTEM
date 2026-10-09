"""Keyword lexicons (pure data). Kept separate from logic so they are easy to review/extend.

All patterns are regexes applied case-insensitively unless noted. PDF text extraction often glues
words together ("inReact.js", "buildingRAGpipelines"), so most patterns deliberately avoid a
leading word boundary; only short/ambiguous tokens use strict boundaries.
"""
from __future__ import annotations

# Phrases that look like AI evidence but are just "I used an AI coding assistant". Stripped before matching.
AI_NOISE = r"claude code|ai[- ]assisted(?: development| coding)?|ai (?:development |coding )?tools?|github copilot|copilot|cursor ide|chatgpt for (?:coding|debugging)|vibe[- ]cod\w*"

# ---- Python evidence -------------------------------------------------------------------------
PYTHON_DIRECT = r"(?<![a-z])python(?![a-z])"
# Python-only ecosystems: if these appear, the implementation language is Python even when not spelled out.
PYTHON_IMPLICIT = (
    r"fastapi|django|flask|pydantic|sqlalchemy|langchain|langgraph|llamaindex|google[- ]adk|crewai|"
    r"pytorch|pandas|numpy|scikit|sklearn|celery|streamlit|uvicorn|pytest|asyncio"
)

# ---- AI / LLM evidence -----------------------------------------------------------------------
# Strong: unambiguous AI/agentic frameworks and techniques. Count anywhere (even skills list) for eligibility.
AI_STRONG = {
    "LangGraph": r"langgraph",
    "LangChain": r"langchain",
    "LlamaIndex": r"llama[- ]?index",
    "Google ADK": r"google[- ]adk|agent development kit|(?<![a-z])adk(?![a-z])",
    "CrewAI": r"crewai",
    "AutoGen": r"autogen",
    "RAG": r"retrieval[- ]augmented|(?<![A-Z])RAG(?![A-Z])",  # RAG is case-sensitive, see ai_signals()
    "Embeddings": r"embedding",
    "Vector Search": r"vector (?:search|store|database|db|index|databases|embeddings?)|pgvector|(?<![a-z])faiss|chroma(?:db)?|pinecone|weaviate|qdrant|milvus|semantic search",
    "Tool Calling": r"tool[- ]?call|function[- ]?call|(?<![a-z])mcp(?![a-z])|model context protocol",
    "Multi-Agent": r"multi[- ]?agent|agentic|(?<![a-z])ai agents?(?![a-z])|llm agents?|(?<![a-z])agents?(?![a-z])",
    "Fine-tuning": r"fine[- ]?tun(?:e|ing|ed)|(?<![a-z])q?lora(?![a-z])|(?<![a-z])peft(?![a-z])",
    "HuggingFace": r"hugging ?face transformers|sentence[- ]transformers|(?<![a-z])transformers(?![a-z])|(?<![a-z])bert(?![a-z])",
    "Prompt Engineering": r"prompt (?:engineering|template|chain)|system prompt",
    "LLM Evaluation": r"(?<![a-z])evals?(?![a-z])|ragas|llm[- ]as[- ]a?[- ]?judge|langsmith|hallucination|guardrail",
}
# Weak: generic LLM-API mentions. Count for eligibility only when found in projects/experience (not just skills).
AI_GENERIC = {
    "LLM": r"(?<![a-z])llms?(?![a-z])|large language model",
    "OpenAI API": r"openai|(?<![a-z])gpt-?\d|(?<![a-z])chatgpt",
    "Gemini": r"(?<![a-z])gemini",
    "Claude/Anthropic": r"anthropic|(?<![a-z])claude(?![a-z])",
    "Generative AI": r"generative ai|gen-?ai(?![a-z])",
    "Chatbot": r"chat-?bot|conversational ai",
    "Ollama/Groq/Mistral": r"ollama|(?<![a-z])groq|(?<![a-z])mistral|vllm|nvidia nim",
}
# Classical ML / CV: displayed as skills but NOT sufficient for the AI/agentic eligibility rule.
ML_CLASSICAL = r"scikit|sklearn|tensorflow|pytorch|keras|opencv|yolo|(?<![a-z])cnn(?![a-z])|xgboost|machine learning|deep learning"

# ---- Scoring signal groups (AI depth) --------------------------------------------------------
DEPTH_RETRIEVAL = r"retrieval|(?<![A-Z])RAG(?![A-Z])|embedding|vector|semantic search|chunk|rerank|faiss|chroma|pinecone|pgvector|knowledge base|index(?:ing)? (?:pipeline|documents)"
DEPTH_AGENTIC = r"agentic|multi[- ]?agent|(?<![a-z])agents?(?![a-z])|tool[- ]?call|function[- ]?call|orchestrat|workflow|langgraph|state ?machine|(?<![a-z])mcp(?![a-z])|planner|human[- ]in[- ]the[- ]loop|supervisor|router|routing"
DEPTH_STATE = r"state(?:ful| management)|memory|checkpoint|session|conversation history|persist"
DEPTH_EVAL = r"(?<![a-z])evals?(?![a-z])|evaluat|benchmark|ragas|llm[- ]as[- ]a?[- ]?judge|hallucination|guardrail|test set|precision|recall|f1|accuracy"
DEPTH_FINETUNE = r"fine[- ]?tun(?:e|ing|ed)|(?<![a-z])q?lora(?![a-z])|(?<![a-z])peft(?![a-z])|rlhf"
DEPTH_DATA = r"pipeline|ingest|pars(?:e|ing|er)|(?<![a-z])etl(?![a-z])|(?<![a-z])pdf|(?<![a-z])ocr(?![a-z])|preprocess|scrap(?:e|ing)|crawl|nl-?to-?sql|chunk"
DEPTH_BACKEND = r"fastapi|flask|django|backend|endpoint|postgres|redis|mongo|database|websocket|microservice|celery|kafka|queue|authentication|crud|(?<![a-z])rest(?:ful)?(?![a-z])"
DEPTH_METRIC = r"\d+\s?(?:%|x|ms|k\+?|\+|users|requests|documents|docs|queries)"
FRAMEWORK_ORCH = r"langgraph|google[- ]adk|crewai|autogen|multi[- ]?agent"
FRAMEWORK_CHAIN = r"langchain|llama[- ]?index|haystack|semantic kernel"
TUTORIAL_MARKERS = r"tutorial|udemy|coursera project|course project|following (?:a|the) (?:course|tutorial)|clone of|bootcamp project|guided project|youtube"

# ---- Python & backend ------------------------------------------------------------------------
BACKEND = {
    "fastapi": r"fastapi",
    "flask_django": r"flask|django",
    "async": r"asyncio|aiohttp|httpx|async(?:/| )?await|(?<![a-z])async(?![a-z])|asynchronous|uvicorn",
    "postgres": r"postgres|pgvector|psycopg|asyncpg",
    "redis": r"redis",
    "other_backend": r"rest(?:ful)? ?api|websocket|microservice|celery|sqlalchemy|grpc|graphql|kafka|rabbitmq|backend",
}

# ---- Cloud / deployment / full-stack ---------------------------------------------------------
CLOUD = {
    "gcp": r"(?<![a-z])gcp(?![a-z])|google cloud|vertex ai|cloud run|bigquery|(?<![a-z])gke(?![a-z])|firebase|app engine|cloud functions",
    "other_cloud": r"(?<![a-z])aws(?![a-z])|azure|lambda|ec2|(?<![a-z])s3(?![a-z])|sagemaker|bedrock|digitalocean",
    "docker": r"docker|container",
    "deploy": r"deploy|ci/?cd|kubernetes|(?<![a-z])k8s(?![a-z])|github actions|terraform|render\.com|vercel|railway|heroku|nginx|netlify|hosted on",
    "frontend": r"react|next\.?js|vue|angular|streamlit|tailwind",
}

# ---- Engineering depth (1 point per distinct category, capped) --------------------------------
ENG_DEPTH = {
    "testing": r"pytest|unit tests?|integration tests?|test coverage|(?<![a-z])tests?(?![a-z]) suite|unittest|tdd|end-to-end tests?",
    "architecture": r"microservice|clean architecture|modular|design pattern|event[- ]driven|layered|domain[- ]driven|scalable architecture|architected|system design",
    "caching": r"cach(?:e|ing)|memoiz",
    "queues": r"celery|kafka|rabbitmq|(?<![a-z])queues?(?![a-z])|pub/?sub|background (?:jobs?|tasks?|workers?)|sqs|bullmq",
    "observability": r"observab|monitoring|prometheus|grafana|logging|tracing|opentelemetry|sentry|langsmith|langfuse|cloudwatch",
    "concurrency": r"concurren|multi-?thread|parallel|asyncio|async(?:/| )?await|(?<![a-z])async(?![a-z])|workers?",
    "failure_handling": r"retry|retries|fallback|rate[- ]limit|idempoten|graceful|circuit breaker|error handling|failover|backoff|timeout",
}

# ---- Display skill lexicon (ordered). name -> regex -------------------------------------------
SKILLS = {
    # languages
    "Python": PYTHON_DIRECT, "Java": r"(?<![a-z])java(?![a-z])", "JavaScript": r"javascript|(?<![a-z])js(?![a-z])|node\.?js",
    "TypeScript": r"typescript", "C++": r"c\+\+", "Go": r"(?<![a-z])golang(?![a-z])|(?<![A-Za-z])Go(?= ?[,|•/)])", "SQL": r"(?<![a-z])sql(?![a-z])|mysql|postgres",
    # backend
    "FastAPI": r"fastapi", "Flask": r"flask", "Django": r"django", "Spring Boot": r"spring ?boot", "Node.js": r"node\.?js", "Express.js": r"express\.?js",
    "AsyncIO": r"asyncio|aiohttp", "Celery": r"celery", "REST APIs": r"rest(?:ful)? ?apis?", "GraphQL": r"graphql", "WebSockets": r"websocket",
    # data
    "PostgreSQL": r"postgres", "Redis": r"redis", "MongoDB": r"mongo", "MySQL": r"mysql", "pgvector": r"pgvector", "Kafka": r"kafka",
    # frontend
    "React": r"react(?!\s?native)", "Next.js": r"next\.?js", "React Native": r"react ?native", "Tailwind CSS": r"tailwind",
    # cloud
    "GCP": r"(?<![a-z])gcp(?![a-z])|google cloud|vertex ai|cloud run|bigquery", "AWS": r"(?<![a-z])aws(?![a-z])|lambda|ec2|sagemaker|bedrock", "Azure": r"azure",
    "Docker": r"docker", "Kubernetes": r"kubernetes|(?<![a-z])k8s(?![a-z])", "Terraform": r"terraform", "CI/CD": r"ci/?cd|github actions|jenkins",
    # ai
    "LangGraph": r"langgraph", "LangChain": r"langchain", "LlamaIndex": r"llama[- ]?index", "Google ADK": r"google[- ]adk|agent development kit",
    "CrewAI": r"crewai", "AutoGen": r"autogen", "RAG": AI_STRONG["RAG"], "Embeddings": r"embedding",
    "Vector DB": r"faiss|chroma|pinecone|pgvector|weaviate|qdrant|milvus", "Tool Calling": r"tool[- ]?call|function[- ]?call",
    "MCP": r"(?<![a-z])mcp(?![a-z])|model context protocol", "OpenAI": r"openai|gpt-?\d", "Gemini": r"gemini", "Claude": r"anthropic|claude",
    "HuggingFace": r"hugging ?face", "Fine-tuning": r"fine[- ]?tun|lora", "LLMs": r"(?<![a-z])llms?(?![a-z])|large language model",
    "scikit-learn": r"scikit|sklearn", "PyTorch": r"pytorch", "TensorFlow": r"tensorflow", "Pandas": r"pandas", "NumPy": r"numpy",
    "pytest": r"pytest",
}
# Skills with a case-sensitive pattern (applied without re.I)
CASE_SENSITIVE_SKILLS = {"RAG", "Go"}

# Section headers (lower-case) -> canonical section id
SECTION_ALIASES = {
    "summary": ["summary", "professional summary", "profile", "objective", "career objective", "about me", "about"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tech stack", "skills & tools", "key skills"],
    "experience": ["experience", "work experience", "professional experience", "internships", "internship experience", "employment", "work history", "professional experience & internships", "freelancing", "freelance"],
    "projects": ["projects", "key projects", "personal projects", "academic projects", "selected projects", "project experience", "notable projects", "technical projects"],
    "education": ["education", "academic background", "academics", "education & certifications"],
    "certifications": ["certifications", "certificates", "licenses & certifications", "courses", "training"],
    "achievements": ["achievements", "awards", "honors", "accomplishments", "extracurricular", "positions of responsibility", "activities", "publications", "leadership"],
    "coursework": ["relevant coursework", "coursework"],
}
# Sections that describe *what you built* (evidence of genuine use)
CONTEXT_SECTIONS = {"summary", "experience", "projects", "other"}
