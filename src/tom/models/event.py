from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, (dict, MappingProxyType)):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class EventType(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_CHANGE = "file_change"
    TEST_RESULT = "test_result"


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: EventType
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def freeze_metadata(self) -> "Event":
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        return self

    @field_serializer("metadata")
    def serialize_metadata(self, metadata: Any) -> Any:
        return _thaw(metadata)

