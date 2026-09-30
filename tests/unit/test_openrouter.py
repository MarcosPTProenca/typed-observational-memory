import json

import pytest

from tom.observer.schemas import ObservedMemories
from tom.providers.openrouter import (
    OpenRouterStructuredLLM,
    _extract_json,
    _message_content,
    _strip_code_fence,
)


class FakeClient:
    def __init__(self, content: str, usage: dict | None = None) -> None:
        self.content = content
        self.model = "fake/model"
        self.last_usage = usage or {"prompt_tokens": 11, "completion_tokens": 3}
        self.last_model = "fake/model"

    async def complete(self, *, messages, response_format=None, require_parameters=False):
        return {"choices": [{"message": {"content": self.content}}], "usage": self.last_usage}


@pytest.mark.asyncio
async def test_structured_llm_parses_json_and_records_usage() -> None:
    client = FakeClient(json.dumps({"items": []}))
    llm = OpenRouterStructuredLLM(client=client)
    result = await llm.generate(messages=[], response_model=ObservedMemories)
    assert isinstance(result, ObservedMemories)
    assert llm.last_input_tokens == 11
    assert llm.last_output_tokens == 3


@pytest.mark.asyncio
async def test_structured_llm_strips_code_fence() -> None:
    client = FakeClient('```json\n{"items": []}\n```')
    llm = OpenRouterStructuredLLM(client=client)
    result = await llm.generate(messages=[], response_model=ObservedMemories)
    assert result.items == []


def test_message_content_raises_on_refusal() -> None:
    with pytest.raises(ValueError, match="refused"):
        _message_content({"choices": [{"message": {"refusal": "no"}}]})


def test_message_content_falls_back_to_reasoning() -> None:
    response = {"choices": [{"message": {"content": "", "reasoning": '{"items": []}'}}]}
    assert _message_content(response) == '{"items": []}'


def test_message_content_reports_finish_reason_when_empty() -> None:
    response = {"choices": [{"finish_reason": "length", "message": {"content": ""}}]}
    with pytest.raises(ValueError, match="finish_reason=length"):
        _message_content(response)


def test_extract_json_from_prose() -> None:
    assert _extract_json('Here you go: {"items": []} done') == '{"items": []}'


def test_strip_code_fence_plain() -> None:
    assert _strip_code_fence('{"a": 1}') == '{"a": 1}'


def test_post_with_retries_recovers_from_transient_error_body() -> None:
    from tom.providers.openrouter import OpenRouterClient

    client = OpenRouterClient(api_key="x", max_retries=3)
    calls = {"n": 0}

    def fake_post(body):
        calls["n"] += 1
        if calls["n"] < 3:
            return {"error": {"message": "ERROR"}}
        return {"choices": [{"message": {"content": '{"items": []}'}}]}

    client._post = fake_post  # type: ignore[method-assign]
    import time as _t
    monkey = _t.sleep
    _t.sleep = lambda *_: None
    try:
        result = client._post_with_retries({})
    finally:
        _t.sleep = monkey
    assert calls["n"] == 3
    assert result["choices"]


def test_post_with_retries_surfaces_hard_error() -> None:
    from tom.providers.openrouter import OpenRouterClient

    client = OpenRouterClient(api_key="x", max_retries=3)
    client._post = lambda body: {"error": {"message": "invalid_api_key"}}  # type: ignore[method-assign]
    result = client._post_with_retries({})
    assert result["error"]["message"] == "invalid_api_key"
