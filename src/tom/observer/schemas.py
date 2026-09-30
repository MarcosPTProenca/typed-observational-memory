from pydantic import BaseModel, ConfigDict, Field

from tom.models.memory import MemoryItem


class ObservedMemories(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MemoryItem] = Field(default_factory=list)
