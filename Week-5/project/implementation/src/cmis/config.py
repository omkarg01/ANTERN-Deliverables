from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql://cmis:cmis@localhost:5433/cmis"

# Shared pgvector dimension (I1 BGE-small-en-v1.5)
EMBEDDING_DIM = 384

DETERMINISTIC_EMBEDDING_MODEL = "deterministic-hash-v1"
BGE_MODEL_ID = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# I1: BGE combined_rank scores run higher; 0.62 drops marginal false positives (e.g. location facts)
BGE_DEFAULT_RELEVANCE_THRESHOLD = 0.62
DETERMINISTIC_DEFAULT_RELEVANCE_THRESHOLD = 0.3

# Cap memories injected after threshold filter (BGE runtime only unless overridden)
BGE_DEFAULT_MAX_INJECT_COUNT = 5

# I4 hybrid retrieval defaults
DEFAULT_RRF_K = 60
DEFAULT_RETRIEVAL_POOL = 50
DEFAULT_RERANK_TOP_K = 10


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "")


def load_dotenv_file() -> None:
    """Load implementation/.env when python-dotenv is installed (API/scripts only)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_embedder_kind() -> str:
    return os.environ.get("CMIS_EMBEDDER", "deterministic").strip().lower()


def get_relevance_threshold() -> float:
    explicit = os.environ.get("CMIS_RELEVANCE_THRESHOLD")
    if explicit is not None and explicit.strip() != "":
        return float(explicit)
    if get_embedder_kind() == "bge":
        return BGE_DEFAULT_RELEVANCE_THRESHOLD
    return DETERMINISTIC_DEFAULT_RELEVANCE_THRESHOLD


def get_max_inject_count() -> int | None:
    """Max memories to inject after ranking. None = no cap (pytest deterministic default)."""
    explicit = os.environ.get("CMIS_MAX_INJECT_COUNT")
    if explicit is not None:
        stripped = explicit.strip()
        if stripped == "" or stripped.lower() in ("none", "unlimited"):
            return None
        return max(1, int(stripped))
    if get_embedder_kind() == "bge":
        return BGE_DEFAULT_MAX_INJECT_COUNT
    return None


def is_query_normalize_enabled() -> bool:
    return _env_bool("CMIS_QUERY_NORMALIZE", True)


def is_hybrid_retrieval_enabled() -> bool:
    return _env_bool("CMIS_HYBRID_RETRIEVAL", True)


def get_rrf_k() -> int:
    explicit = os.environ.get("CMIS_RRF_K")
    if explicit is not None and explicit.strip() != "":
        return max(1, int(explicit))
    return DEFAULT_RRF_K


def get_retrieval_pool() -> int:
    explicit = os.environ.get("CMIS_RETRIEVAL_POOL")
    if explicit is not None and explicit.strip() != "":
        return max(1, int(explicit))
    return DEFAULT_RETRIEVAL_POOL


def get_rerank_top_k() -> int:
    explicit = os.environ.get("CMIS_RERANK_TOP_K")
    if explicit is not None and explicit.strip() != "":
        return max(1, int(explicit))
    return DEFAULT_RERANK_TOP_K


def get_reranker_kind() -> str:
    explicit = os.environ.get("CMIS_RERANKER")
    if explicit is not None and explicit.strip() != "":
        return explicit.strip().lower()
    if get_embedder_kind() == "bge":
        return "local"
    return "stub"


def is_auth_disabled() -> bool:
    """When true, HTTP API accepts tenant/user from query/body (pytest/local only)."""
    return _env_bool("CMIS_AUTH_DISABLED", False)


def get_jwt_secret() -> str:
    secret = os.environ.get("CMIS_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("CMIS_JWT_SECRET is required when auth is enabled")
    return secret


def get_jwt_issuer() -> str:
    return os.environ.get("CMIS_JWT_ISSUER", "cmis").strip()


def get_jwt_audience() -> str:
    return os.environ.get("CMIS_JWT_AUDIENCE", "cmis-api").strip()


def get_llm_provider() -> str:
    return os.environ.get("CMIS_LLM_PROVIDER", "mock").strip().lower()


def get_llm_api_key() -> str:
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise RuntimeError("LLM_API_KEY is required when CMIS_LLM_PROVIDER is not mock")
    return key


def get_llm_base_url() -> str:
    return os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()


def get_llm_model() -> str:
    return os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile").strip()


def is_temporal_enabled() -> bool:
    return _env_bool("CMIS_USE_TEMPORAL", False)


def get_temporal_host() -> str:
    return os.environ.get("CMIS_TEMPORAL_HOST", "localhost:7233").strip()


def get_temporal_namespace() -> str:
    return os.environ.get("CMIS_TEMPORAL_NAMESPACE", "default").strip()


def get_temporal_task_queue() -> str:
    return os.environ.get("CMIS_TEMPORAL_TASK_QUEUE", "cmis-background").strip()


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "").strip()


def is_context_cache_enabled() -> bool:
    if not get_redis_url():
        return False
    return _env_bool("CMIS_CONTEXT_CACHE", True)


def get_context_cache_ttl() -> int:
    explicit = os.environ.get("CMIS_CONTEXT_CACHE_TTL")
    if explicit is not None and explicit.strip() != "":
        return max(1, int(explicit))
    return 300
