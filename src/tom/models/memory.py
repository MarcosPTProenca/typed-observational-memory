from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .enums import Importance, KnowledgeType, MemoryStatus, RetentionPolicy


class MemoryItem(BaseModel):
    id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    knowledge_type: KnowledgeType
    retention: RetentionPolicy
    importance: Importance
    confidence: float = Field(ge=0.0, le=1.0)
    topic: str | None = None
    scope: list[str] = Field(default_factory=list)
    source_ids: list[str]
    created_at: datetime
    event_time: datetime | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    supersedes: list[str] = Field(default_factory=list)

    @field_validator("source_ids")
    @classmethod
    def require_sources(cls, source_ids: list[str]) -> list[str]:
        if not source_ids or any(not source_id.strip() for source_id in source_ids):
            raise ValueError("Every MemoryItem must reference at least one source Event")
        return source_ids
