"""Gateway tests with a mocked LiteLLM (no network/keys).

These exercise complete(), the fallback chain, retry-then-succeed, and structured
output. They depend on retry_with_backoff, so they pass once the [YOU-WRITE]
function in app/llm/retry.py is implemented.
"""

from types import SimpleNamespace
from typing import Any

import litellm
import pytest
from pydantic import BaseModel

from app.llm.gateway import AliasConfig, Gateway, LLMStructuredError


def _resp(content: str, prompt: int = 3, completion: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion),
    )


@pytest.fixture
def gw() -> Gateway:
    return Gateway(
        aliases={
            "fast": AliasConfig(models=("primary/model", "fallback/model"), timeout_s=4.0),
            "judge": AliasConfig(models=("judge/model",), timeout_s=30.0),
        },
        max_retries=2,
        retry_base_s=0.0,
        retry_max_delay_s=0.0,
    )


async def test_complete_returns_text_and_records_cost(
    gw: Gateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_acompletion(**kwargs: Any) -> SimpleNamespace:
        return _resp("hello")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **k: 0.0004)

    r = await gw.complete([{"role": "user", "content": "hi"}], alias="fast")
    assert r.text == "hello"
    assert r.model == "primary/model"
    assert r.cost_usd == 0.0004
    assert (r.tokens_in, r.tokens_out) == (3, 5)


async def test_timeout_triggers_fallback(gw: Gateway, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_acompletion(**kwargs: Any) -> SimpleNamespace:
        model = kwargs["model"]
        calls.append(model)
        if model == "primary/model":
            raise TimeoutError("too slow")
        return _resp("from-fallback")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **k: 0.0)

    r = await gw.complete([{"role": "user", "content": "hi"}], alias="fast")
    assert r.text == "from-fallback"
    assert r.model == "fallback/model"
    assert calls.count("primary/model") == 3  # max_retries + 1, before falling back
    assert "fallback/model" in calls


async def test_429_retries_then_succeeds(gw: Gateway, monkeypatch: pytest.MonkeyPatch) -> None:
    n = {"primary": 0}

    async def fake_acompletion(**kwargs: Any) -> SimpleNamespace:
        if kwargs["model"] == "primary/model":
            n["primary"] += 1
            if n["primary"] < 2:
                raise RuntimeError("429 rate limit")
            return _resp("recovered")
        return _resp("x")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **k: 0.0)

    r = await gw.complete([{"role": "user", "content": "hi"}], alias="fast")
    assert r.text == "recovered"
    assert r.model == "primary/model"
    assert n["primary"] == 2  # failed once, retried, succeeded


class Weather(BaseModel):
    city: str
    temp_c: int


async def test_structured_valid(gw: Gateway, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_acompletion(**kwargs: Any) -> SimpleNamespace:
        return _resp('{"city": "Pune", "temp_c": 30}')

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **k: 0.0)

    out = await gw.structured([{"role": "user", "content": "x"}], Weather, alias="judge")
    assert out.city == "Pune"
    assert out.temp_c == 30


async def test_structured_invalid_raises(gw: Gateway, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_acompletion(**kwargs: Any) -> SimpleNamespace:
        return _resp('{"city": "Pune"}')  # missing temp_c

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **k: 0.0)

    with pytest.raises(LLMStructuredError):
        await gw.structured([{"role": "user", "content": "x"}], Weather, alias="judge")
