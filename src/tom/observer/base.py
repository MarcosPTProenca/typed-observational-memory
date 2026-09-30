from typing import Protocol

from tom.models.event import Event
from tom.models.memory import MemoryItem


class Observer(Protocol):
    async def observe(self, events: list[Event]) -> list[MemoryItem]:
        ...
