"""Application settings: one typed place for all environment-driven config.

Follows 12-factor: configuration comes from the environment. Every tunable has
a default here and can be overridden by an env var (or the repo-root ``.env``
file locally). Code reads config through :func:`get_settings`, never ``os.getenv``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[2] is the repo root, where .env lives.
_REPO_ROOT = Path(__file__).resolve().parents[2]

Environment = Literal["local", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Typed settings loaded from the environment.

    Field names map case-insensitively to env vars (``app_env`` <- ``APP_ENV``).
    LLM, voice and auth settings are added in their own tickets (M0-T6, M5, M7)
    to avoid carrying config that nothing reads yet.
    """

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- App ----------
    app_env: Environment = "local"
    log_level: LogLevel = "INFO"
    eval_mode: bool = False
    dev_auth: bool = True
    public_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # ---------- Data ----------
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    blob_backend: Literal["local", "azure"] = "local"
    blob_local_dir: str = "./.data/blobs"

    # ---------- LLM providers and aliases ----------
    gemini_api_key: str = ""
    groq_api_key: str = ""
    # LiteLLM model strings; empty until keys/models are configured. Fallbacks
    # are comma-separated and split in the gateway.
    llm_fast_model: str = ""
    llm_fast_fallbacks: str = ""
    llm_strong_model: str = ""
    llm_strong_fallbacks: str = ""
    llm_judge_model: str = ""
    llm_followup_model: str = ""
    llm_generator_model: str = ""
    llm_timeout_fast_s: float = 4.0
    llm_timeout_strong_s: float = 20.0
    llm_timeout_judge_s: float = 30.0
    llm_max_retries: int = 2
    llm_retry_base_s: float = 0.5
    llm_retry_max_delay_s: float = 8.0

    # ---------- RAG / knowledge base ----------
    kb_version: int = 1
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    embed_model: str = "BAAI/bge-small-en-v1.5"
    sparse_model: str = "Qdrant/bm25"
    embed_dim: int = 384
    qdrant_collection: str = "kb_chunks"
    retrieve_top_k: int = 30
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    rerank_top_n: int = 6
    rerank_enabled: bool = True
    # Abstain when the top rerank score is below this (tuned on the golden set).
    abstain_threshold: float = 0.0

    # ---------- Observability ----------
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    otel_exporter_otlp_endpoint: str = ""

    # ---------- Budgets and quotas ----------
    budget_usd_per_user_day: float = 0.50
    budget_usd_global_day: float = 3.00
    budget_usd_per_eval_run: float = 1.00
    quota_voice_minutes_per_user_day: int = 30
    rate_limit_per_min: int = 30

    @property
    def is_prod(self) -> bool:
        """True when running in the production environment."""
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance (the environment is read once)."""
    return Settings()
