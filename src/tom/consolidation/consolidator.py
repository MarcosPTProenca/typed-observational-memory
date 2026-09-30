from datetime import UTC, datetime, timedelta
from typing import ClassVar

from tom.models import Importance, MemoryItem, MemoryStatus, RetentionPolicy


class Consolidator:
    """Apply deterministic, lossless lifecycle changes to memory items.

    Consolidation only merges byte-for-byte duplicate soft memories. It does not
    invent supersession relationships or rewrite protected content.
    """

    _importance_rank: ClassVar[dict[Importance, int]] = {
        Importance.CRITICAL: 0,
        Importance.HIGH: 1,
        Importance.MEDIUM: 2,
        Importance.LOW: 3,
    }

    def __init__(self, *, max_age: timedelta | None = None) -> None:
        if max_age is not None and max_age < timedelta(0):
            raise ValueError("max_age must not be negative")
        self.max_age = max_age

    def consolidate(
        self,
        memories: list[MemoryItem],
        *,
        now: datetime | None = None,
    ) -> list[MemoryItem]:
        """Return a new memory state without mutating the supplied items."""
        result = [memory.model_copy(deep=True) for memory in memories]
        by_id = {memory.id: memory for memory in result}

        # A superseding link is explicit evidence from the observer or caller.
        # Status changes preserve the old item and its source evidence.
        for memory in result:
            if memory.status != MemoryStatus.ACTIVE:
                continue
            for superseded_id in memory.supersedes:
                superseded = by_id.get(superseded_id)
                if superseded is not None and superseded.id != memory.id:
                    superseded.status = MemoryStatus.SUPERSEDED

        if self.max_age is not None:
            cutoff = (now or datetime.now(UTC)) - self.max_age
            for memory in result:
                if (
                    memory.status == MemoryStatus.ACTIVE
                    and memory.retention == RetentionPolicy.DISCARDABLE
                    and _memory_time(memory) < cutoff
                ):
                    memory.status = MemoryStatus.ARCHIVED

        # Exact memories are never merged or rewritten. Duplicate soft memories
        # retain all source IDs on the deterministic winner; the loser is archived.
        groups: dict[tuple[object, ...], list[MemoryItem]] = {}
        for memory in result:
            if (
                memory.status == MemoryStatus.ACTIVE
                and memory.retention != RetentionPolicy.EXACT
            ):
                groups.setdefault(_duplicate_key(memory), []).append(memory)

        for group in groups.values():
            if len(group) < 2:
                continue
            winner = min(group, key=_winner_key(self._importance_rank))
            for duplicate in group:
                if duplicate.id == winner.id:
                    continue
                winner.source_ids = sorted(set(winner.source_ids + duplicate.source_ids))
                winner.supersedes = sorted(set(winner.supersedes + duplicate.supersedes))
                duplicate.status = MemoryStatus.ARCHIVED

        return sorted(result, key=lambda memory: memory.id)


def consolidate_memories(
    memories: list[MemoryItem],
    *,
    max_age: timedelta | None = None,
    now: datetime | None = None,
) -> list[MemoryItem]:
    return Consolidator(max_age=max_age).consolidate(memories, now=now)


def _duplicate_key(memory: MemoryItem) -> tuple[object, ...]:
    return (
        memory.content,
        memory.knowledge_type,
        memory.retention,
        memory.topic,
        tuple(sorted(memory.scope)),
    )


def _winner_key(importance_rank: dict[Importance, int]):
    def key(memory: MemoryItem) -> tuple[int, float, str]:
        return (
            importance_rank[memory.importance],
            -_memory_time(memory).timestamp(),
            memory.id,
        )

    return key


def _memory_time(memory: MemoryItem) -> datetime:
    return memory.event_time or memory.created_at
