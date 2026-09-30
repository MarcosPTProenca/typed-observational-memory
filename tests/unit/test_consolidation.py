from datetime import UTC, datetime, timedelta

from tom.consolidation import Consolidator
from tom.models import Importance, KnowledgeType, MemoryItem, MemoryStatus, RetentionPolicy

NOW = datetime(2025, 1, 1, tzinfo=UTC)


def memory(
    ident: str,
    content: str,
    *,
    retention: RetentionPolicy = RetentionPolicy.COMPRESSIBLE,
    importance: Importance = Importance.MEDIUM,
    created_at: datetime = NOW,
    supersedes: list[str] | None = None,
) -> MemoryItem:
    return MemoryItem(
        id=ident,
        content=content,
        knowledge_type=KnowledgeType.BELIEF,
        retention=retention,
        importance=importance,
        confidence=1,
        source_ids=[f"event-{ident}"],
        created_at=created_at,
        supersedes=supersedes or [],
    )


def test_duplicate_soft_memories_are_merged_without_losing_sources() -> None:
    items = [
        memory("older", "backend uses PostgreSQL", created_at=NOW - timedelta(days=1)),
        memory("newer", "backend uses PostgreSQL", importance=Importance.HIGH),
    ]

    result = Consolidator().consolidate(items)

    winner = next(item for item in result if item.id == "newer")
    assert winner.status == MemoryStatus.ACTIVE
    assert winner.source_ids == ["event-newer", "event-older"]
    assert next(item for item in result if item.id == "older").status == MemoryStatus.ARCHIVED
    assert items[0].status == MemoryStatus.ACTIVE


def test_exact_memories_are_not_deduplicated() -> None:
    result = Consolidator().consolidate([
        memory("a", "do not edit generated files", retention=RetentionPolicy.EXACT),
        memory("b", "do not edit generated files", retention=RetentionPolicy.EXACT),
    ])

    assert [item.status for item in result] == [MemoryStatus.ACTIVE, MemoryStatus.ACTIVE]


def test_explicit_supersession_preserves_old_memory() -> None:
    old = memory("old", "backend uses MySQL")
    new = memory("new", "backend uses PostgreSQL", supersedes=["old"])

    result = Consolidator().consolidate([old, new])

    assert next(item for item in result if item.id == "old").status == MemoryStatus.SUPERSEDED
    assert next(item for item in result if item.id == "new").status == MemoryStatus.ACTIVE


def test_discardable_memory_expires_to_archive() -> None:
    old = memory(
        "old",
        "temporary note",
        retention=RetentionPolicy.DISCARDABLE,
        created_at=NOW - timedelta(days=10),
    )

    result = Consolidator(max_age=timedelta(days=7)).consolidate([old], now=NOW)

    assert result[0].status == MemoryStatus.ARCHIVED
