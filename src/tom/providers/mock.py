from collections.abc import Awaitable, Callable
from typing import Any, cast

from pydantic import BaseModel


class MockStructuredLLM:
    """Deterministic structured provider for tests."""

    def __init__(
        self,
        response: BaseModel | Callable[[list[dict[str, Any]], type[BaseModel]], BaseModel | Awaitable[BaseModel]],
    ) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        self.calls.append({"messages": messages, "response_model": response_model})
        result = self.response(messages, response_model) if callable(self.response) else self.response
        if hasattr(result, "__await__"):
            result = await cast(Awaitable[BaseModel], result)
        return response_model.model_validate(result)
