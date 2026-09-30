from typing import Any

from pydantic import BaseModel


class OpenAIStructuredLLM:
    def __init__(self, client: Any | None = None, *, model: str = "gpt-5-mini") -> None:
        if client is None:
            try:
                module = __import__("openai", fromlist=["AsyncOpenAI"])
                client = module.AsyncOpenAI()
            except ImportError as exc:
                raise ImportError("Install the optional 'openai' package to use OpenAIStructuredLLM") from exc
        self.client: Any = client
        self.model = model

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_model,
        )
        usage = response.usage
        self.last_input_tokens = usage.prompt_tokens if usage else 0
        self.last_output_tokens = usage.completion_tokens if usage else 0
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned no structured response")
        return response_model.model_validate(parsed)
