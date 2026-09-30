from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel


class OpenRouterClient:
    """Small OpenRouter Chat Completions client with no extra dependency."""

    # A fixed free model, for reproducible benchmark runs
    # (openrouter/free routes non-deterministically).
    DEFAULT_MODEL = "stealth/union-alpha"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = "https://openrouter.ai/api/v1/chat/completions",
        timeout: float = 120.0,
        max_retries: int = 4,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("Set OPENROUTER_API_KEY before using OpenRouter")
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_usage: dict[str, Any] | None = None
        self.last_model: str | None = None

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        require_parameters: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.model, "messages": messages}
        if response_format is not None:
            body["response_format"] = response_format
            if require_parameters:
                body["provider"] = {"require_parameters": True}
        response = await asyncio.to_thread(self._post_with_retries, body)
        self.last_usage = response.get("usage")
        self.last_model = response.get("model")
        return response

    def _post_with_retries(self, body: dict[str, Any]) -> dict[str, Any]:
        # Free-tier endpoints intermittently fail with a transient 429/5xx, a
        # body with no choices, or an in-body error field (HTTP 200). Retry all
        # of those with exponential backoff; only a non-transient error aborts.
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._post(body)
                error = response.get("error")
                if error:
                    message = error.get("message") if isinstance(error, dict) else str(error)
                    if not _is_transient(str(message)):
                        return response  # surfaced by _message_content as a hard error
                    last_error = RuntimeError(f"OpenRouter error: {message}")
                elif response.get("choices"):
                    return response
                else:
                    last_error = RuntimeError("OpenRouter returned no choices")
            except RuntimeError as exc:
                if not _is_transient(str(exc)):
                    raise
                last_error = exc
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)
        assert last_error is not None
        raise last_error

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/typed-observational-memory",
                "X-Title": "typed-observational-memory",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc


class OpenRouterStructuredLLM:
    def __init__(
        self,
        client: OpenRouterClient | None = None,
        *,
        model: str = OpenRouterClient.DEFAULT_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.client = client or OpenRouterClient(api_key=api_key, model=model)
        self.model = model
        self.last_input_tokens = 0
        self.last_output_tokens = 0

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        schema = response_model.model_json_schema()
        # Ask for the schema in the prompt too, so models without native
        # json_schema support (json_object only) still produce the right shape.
        guided = [
            {
                "role": "system",
                "content": "Return ONLY a JSON object matching this schema, no prose:\n"
                + json.dumps(schema, ensure_ascii=False),
            },
            *messages,
        ]
        response = await self.client.complete(
            messages=guided,
            response_format={"type": "json_object"},
        )
        usage = self.client.last_usage or {}
        self.last_input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        self.last_output_tokens = int(usage.get("completion_tokens", 0) or 0)
        content = _message_content(response)
        return response_model.model_validate_json(_extract_json(content))


def _is_transient(message: str) -> bool:
    text = str(message).lower()
    return any(sig in text for sig in (
        "429", "500", "502", "503", "504",
        "no choices", "request failed", "timed out", "timeout",
        "rate limit", "overloaded", "unavailable", "error",
    ))


def _message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        error = response.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else error
            raise ValueError(f"OpenRouter error: {message}")
        raise ValueError("OpenRouter returned no choices")
    choice = choices[0]
    message = choice.get("message") or {}
    if message.get("refusal"):
        raise ValueError(f"OpenRouter refused the request: {message['refusal']}")
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    # Some free reasoning models leave content empty and emit the JSON inside
    # the reasoning trace; use it as a fallback so the run does not fail.
    if not content:
        content = message.get("reasoning") or ""
    if not content.strip():
        finish = choice.get("finish_reason") or choice.get("native_finish_reason")
        raise ValueError(f"OpenRouter returned no message content (finish_reason={finish})")
    return content


def _extract_json(content: str) -> str:
    """Return the JSON object embedded in a model response.

    Free models wrap JSON in prose or code fences; take the outermost {...}.
    """
    content = _strip_code_fence(content)
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        raise ValueError("OpenRouter response did not contain a JSON object")
    return content[start:end + 1]


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()
        if content.startswith("json"):
            content = content[4:].lstrip()
    return content


__all__ = ["OpenRouterClient", "OpenRouterStructuredLLM"]
