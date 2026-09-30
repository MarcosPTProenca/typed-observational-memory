import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tom import Event, EventType, Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.memory import SQLiteMemoryStore


def event(i="e1"):
    return Event(id=i, type=EventType.USER, content="Never delete evidence", timestamp=datetime.now(UTC))


def memory():
    return MemoryItem(id="m1", content="Never delete evidence", knowledge_type=KnowledgeType.CONSTRAINT, retention=RetentionPolicy.EXACT, importance=Importance.CRITICAL, confidence=1, source_ids=["e1"], created_at=datetime.now(UTC))


def test_memory_requires_source():
    fields = {
        "id": "m1", "content": "x", "knowledge_type": KnowledgeType.CONSTRAINT,
        "retention": RetentionPolicy.EXACT, "importance": Importance.CRITICAL,
        "confidence": 1, "created_at": datetime.now(UTC),
    }
    with pytest.raises(ValidationError):
        MemoryItem(source_ids=[], **fields)
    with pytest.raises(ValidationError):
        MemoryItem(source_ids=["   "], **fields)


def test_memory_defaults_and_metadata():
    item = memory()
    assert item.topic is None
    assert item.scope == []
    assert item.event_time is None
    assert item.status.value == "active"
    assert item.supersedes == []


def test_events_are_immutable():
    current = event()
    with pytest.raises(ValidationError):
        current.content = "changed"

    current = Event(
        id=current.id,
        type=current.type,
        content=current.content,
        timestamp=current.timestamp,
        metadata={"nested": {"source": "chat"}},
    )
    with pytest.raises(TypeError):
        current.metadata["source"] = "chat"
    with pytest.raises(TypeError):
        current.metadata["nested"]["source"] = "unsafe"


@pytest.mark.asyncio
async def test_sqlite_persists_and_recalls_sources():
    store = SQLiteMemoryStore()
    await store.add_events([event()])
    await store.add_memory_items([memory()])
    result = await store.recall("m1")
    assert result.sources[0].content == "Never delete evidence"
    assert (await store.get_sources("m1"))[0].id == "e1"


@pytest.mark.asyncio
async def test_events_are_append_only():
    store = SQLiteMemoryStore()
    original = event()
    await store.add_events([original])

    with pytest.raises(sqlite3.IntegrityError):
        await store.add_events([original])

    assert await store.get_event(original.id) == original


@pytest.mark.asyncio
async def test_memory_batch_rolls_back_when_a_source_is_unknown():
    store = SQLiteMemoryStore()
    await store.add_events([event()])
    valid = memory()
    invalid = valid.model_copy(update={"id": "m2", "source_ids": ["missing"]})

    with pytest.raises(ValueError):
        await store.add_memory_items([valid, invalid])

    assert await store.get_memory("m1") is None
