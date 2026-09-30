"""Refine discrete labels on already-extracted memory items using Jev.

Complements the generative observer without replacing it: ``content``/``topic``/
``scope``/``source_ids`` stay exactly as the observer produced them, while Jev
reassigns ``knowledge_type``/``retention``/``importance``/``confidence`` from the
item's own text.
"""

from __future__ import annotations

import asyncio

from tom.models.memory import MemoryItem
from tom.providers.jev import JevClassifier


class JevRelabeler:
    def __init__(self, jev: JevClassifier) -> None:
        self.jev = jev

    async def relabel(self, items: list[MemoryItem]) -> list[MemoryItem]:
        if not items:
            return items
        labels = await asyncio.gather(*(self.jev.classify_labels(item.content) for item in items))
        for item, label in zip(items, labels, strict=True):
            item.knowledge_type = label.knowledge_type
            item.retention = label.retention
            item.importance = label.importance
            item.confidence = label.confidence
        return items
