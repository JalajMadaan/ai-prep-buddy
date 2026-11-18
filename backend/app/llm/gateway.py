"""LLM gateway: the single entry point for every model call.

Resolves an alias (``fast``/``strong``/``judge``/``followup``/``generator``) to a
model plus fallback chain, retries each model on transient errors (via the
[YOU-WRITE] :func:`app.llm.retry.retry_with_backoff`), falls back to the next
model when one is exhausted, and records cost + latency. Tested with a mocked
LiteLLM, so no network or API keys are needed.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any

import litellm
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.core.errors import AppError, UpstreamError
from app.core.logging import get_logger
from app.llm.retry import retry_with_backoff

Message = dict[str, str]

logger = get_logger("llm.gateway")


class AllModelsFailedError(UpstreamError):
    """Every model in an alias's fallback chain failed."""

    code = "LLM_ALL_MODELS_FAILED"


class LLMStructuredError(UpstreamError):
    """The model's output did not validate against the requested schema."""

    code = "LLM_STRUCTURED_INVALID"


@dataclass(frozen=True)
class AliasConfig:
    """A model alias: the primary model plus fallbacks, and a per-call timeout."""

    models: tuple[str, ...]
    timeout_s: float


@dataclass(frozen=True)
class LLMResult:
    """The outcome of a completion, with cost/latency for logging and budgets."""

    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float


def _split(csv: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in csv.split(",") if part.strip())


def _nonempty(models: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(m for m in models if m)


def _export_provider_keys(s: Settings) -> None:
    """Bridge provider keys from settings into os.environ so LiteLLM finds them."""
    for name, value in (("GEMINI_API_KEY", s.gemini_api_key), ("GROQ_API_KEY", s.groq_api_key)):
        if value and not os.environ.get(name):
            os.environ[name] = value


def _build_aliases(s: Settings) -> dict[str, AliasConfig]:
    return {
        "fast": AliasConfig(
            _nonempty((s.llm_fast_model, *_split(s.llm_fast_fallbacks))), s.llm_timeout_fast_s
        ),
        "strong": AliasConfig(
            _nonempty((s.llm_strong_model, *_split(s.llm_strong_fallbacks))), s.llm_timeout_strong_s
        ),
        "judge": AliasConfig(_nonempty((s.llm_judge_model,)), s.llm_timeout_judge_s),
        "followup": AliasConfig(
            _nonempty((s.llm_followup_model or s.llm_fast_model,)), s.llm_timeout_fast_s
        ),
        "generator": AliasConfig(
            _nonempty((s.llm_generator_model or s.llm_strong_model,)), s.llm_timeout_strong_s
        ),
    }


def _compute_cost(response: Any) -> float:
    try:
        return float(litellm.completion_cost(completion_response=response))
    except Exception:
        return 0.0


def _to_result(model: str, response: Any, latency_ms: float) -> LLMResult:
    try:
        text = response.choices[0].message.content or ""
    except Exception:
        text = ""
    usage = getattr(response, "usage", None)
    return LLMResult(
        text=text,
        model=model,
        tokens_in=int(getattr(usage, "prompt_tokens", 0) or 0),
        tokens_out=int(getattr(usage, "completion_tokens", 0) or 0),
        cost_usd=_compute_cost(response),
        latency_ms=latency_ms,
    )


def _chunk_text(chunk: Any) -> str:
    try:
        return chunk.choices[0].delta.content or ""
    except Exception:
        return ""


class Gateway:
    """Config-driven LLM gateway. Inject ``aliases`` to test without env config."""

    def __init__(
        self,
        *,
        aliases: dict[str, AliasConfig] | None = None,
        max_retries: int | None = None,
        retry_base_s: float | None = None,
        retry_max_delay_s: float | None = None,
    ) -> None:
        s = get_settings()
        _export_provider_keys(s)
        self._aliases = aliases if aliases is not None else _build_aliases(s)
        self._max_retries = s.llm_max_retries if max_retries is None else max_retries
        self._retry_base_s = s.llm_retry_base_s if retry_base_s is None else retry_base_s
        self._retry_max_delay_s = (
            s.llm_retry_max_delay_s if retry_max_delay_s is None else retry_max_delay_s
        )

    def _resolve(self, alias: str) -> AliasConfig:
        cfg = self._aliases.get(alias)
        if cfg is None:
            raise AppError(f"Unknown LLM alias: {alias}")
        if not cfg.models:
            raise AppError(f"LLM alias '{alias}' has no configured model")
        return cfg

    async def _attempt(
        self, model: str, messages: Sequence[Message], timeout_s: float, extra: dict[str, Any]
    ) -> Any:
        return await litellm.acompletion(
            model=model, messages=list(messages), timeout=timeout_s, **extra
        )

    async def complete(
        self, messages: Sequence[Message], *, alias: str, **kwargs: Any
    ) -> LLMResult:
        """Run a completion, retrying each model and falling back across the chain."""
        cfg = self._resolve(alias)
        last_exc: Exception | None = None
        for model in cfg.models:
            call = partial(self._attempt, model, messages, cfg.timeout_s, kwargs)
            try:
                started = time.perf_counter()
                response = await retry_with_backoff(
                    call,
                    attempts=self._max_retries + 1,
                    base=self._retry_base_s,
                    max_delay=self._retry_max_delay_s,
                    jitter=True,
                )
                result = _to_result(model, response, (time.perf_counter() - started) * 1000)
                logger.info(
                    "llm_call",
                    alias=alias,
                    model=model,
                    cost_usd=result.cost_usd,
                    latency_ms=round(result.latency_ms, 1),
                    tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out,
                )
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning("llm_model_failed", alias=alias, model=model, error=str(exc))
        raise AllModelsFailedError(f"All models failed for alias '{alias}'") from last_exc

    async def structured[SchemaT: BaseModel](
        self, messages: Sequence[Message], schema: type[SchemaT], *, alias: str, **kwargs: Any
    ) -> SchemaT:
        """Run a completion and validate the JSON output against ``schema``."""
        result = await self.complete(
            messages, alias=alias, response_format={"type": "json_object"}, **kwargs
        )
        try:
            return schema.model_validate_json(result.text)
        except ValidationError as exc:
            raise LLMStructuredError(f"LLM output failed schema {schema.__name__}") from exc

    async def stream(
        self, messages: Sequence[Message], *, alias: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream a completion token by token (primary model only; used by SSE in M1)."""
        cfg = self._resolve(alias)
        model = cfg.models[0]
        response = await litellm.acompletion(
            model=model, messages=list(messages), timeout=cfg.timeout_s, stream=True, **kwargs
        )
        async for chunk in response:
            token = _chunk_text(chunk)
            if token:
                yield token
