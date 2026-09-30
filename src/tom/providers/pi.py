from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from .codex_bridge import CodexBridge


class PiStructuredLLM:
    """Structured generation through pi-ai's authenticated Codex provider."""

    def __init__(self, *, model: str | None = None, bridge: CodexBridge | None = None) -> None:
        self.bridge = bridge or CodexBridge(model=model)
        self.model = model

    async def generate(self, *, messages: list[dict[str, Any]], response_model: type[BaseModel]) -> BaseModel:
        prompt = (
            "Return only valid JSON matching this schema. No markdown.\n"
            + json.dumps(response_model.model_json_schema(), ensure_ascii=False)
            + "\n\n"
            + "\n\n".join(f"{m['role']}: {m['content']}" for m in messages)
        )
        raw = await self.bridge.prompt(prompt)
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Codex bridge did not return a JSON object")
        self.last_input_tokens = 0
        self.last_output_tokens = len(raw.split())
        return response_model.model_validate(json.loads(raw[start:end + 1]))
