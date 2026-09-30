"""Deterministic classification observer: no LLM, regex-based, isolates whether
TOM's compaction mechanism (vs its LLM classifier) explains the recall gap
against Knowledge Triage's TypeCompact.
"""

from datetime import UTC, datetime

import pytest

from tom.models import Event, EventType, KnowledgeType, RetentionPolicy
from tom.observer import DeterministicObserver


def make_event(event_id: str, content: str) -> Event:
    return Event(id=event_id, type=EventType.USER, content=content, timestamp=datetime.now(UTC))


@pytest.mark.asyncio
async def test_deterministic_observer_classifies_constraint_verbatim() -> None:
    event = make_event("e1", "Never commit secrets to .env files.")

    items = await DeterministicObserver().observe([event])

    assert len(items) == 1
    assert items[0].content == event.content  # regex never rewrites
    assert items[0].knowledge_type == KnowledgeType.CONSTRAINT
    assert items[0].retention == RetentionPolicy.EXACT
    assert items[0].source_ids == ["e1"]


@pytest.mark.asyncio
async def test_deterministic_observer_classifies_procedure_as_high_fidelity() -> None:
    event = make_event("e1", "Run npm test before deploy.")

    items = await DeterministicObserver().observe([event])

    assert items[0].knowledge_type == KnowledgeType.PROCEDURE
    assert items[0].retention == RetentionPolicy.HIGH_FIDELITY


@pytest.mark.asyncio
async def test_deterministic_observer_is_reproducible_across_calls() -> None:
    events = [make_event("e1", "Never commit secrets."), make_event("e2", "The app prefers dark mode.")]

    first = await DeterministicObserver().observe(events)
    second = await DeterministicObserver().observe(events)

    assert [(i.content, i.knowledge_type, i.retention) for i in first] == [
        (i.content, i.knowledge_type, i.retention) for i in second
    ]
    assert DeterministicObserver().last_metrics.llm_calls == 0


@pytest.mark.asyncio
async def test_deterministic_observer_observe_chunks_flattens_all_events() -> None:
    chunks = [
        [make_event("e1", "Never commit secrets."), make_event("e2", "Run npm test.")],
        [make_event("e3", "The app prefers dark mode.")],
    ]

    items = await DeterministicObserver().observe_chunks(chunks)

    assert [item.source_ids for item in items] == [["e1"], ["e2"], ["e3"]]
