from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RunMetrics(BaseModel):
    """Machine-readable metrics for one observation or experiment cycle."""

    run_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observer_input_tokens: int = Field(default=0, ge=0)
    observer_output_tokens: int = Field(default=0, ge=0)
    scanner_input_tokens: int = Field(default=0, ge=0)
    scanner_output_tokens: int = Field(default=0, ge=0)
    projected_tokens: int = Field(default=0, ge=0)
    active_memory_tokens: int = Field(default=0, ge=0)
    archived_memory_tokens: int = Field(default=0, ge=0)
    memory_items_created: int = Field(default=0, ge=0)
    constraints_created: int = Field(default=0, ge=0)
    procedures_created: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    jev_calls: int = Field(default=0, ge=0)
    jev_input_tokens: int = Field(default=0, ge=0)
    jev_output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    config: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_input_tokens(self) -> int:
        return self.observer_input_tokens + self.scanner_input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self.observer_output_tokens + self.scanner_output_tokens


class CostRates(BaseModel):
    """USD rates per one million input/output tokens."""

    input_per_million: float = Field(default=0.0, ge=0.0)
    output_per_million: float = Field(default=0.0, ge=0.0)


def new_run_id() -> str:
    return uuid4().hex
