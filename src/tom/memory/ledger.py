from pydantic import BaseModel

from tom.models.event import Event
from tom.models.memory import MemoryItem


class RecallResult(BaseModel):
    memory: MemoryItem
    sources: list[Event]
