from typing import Any, Protocol

from pydantic import BaseModel


class StructuredLLM(Protocol):
    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        ...
