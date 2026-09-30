from datetime import UTC, datetime

import pytest

from tom.models import Event, EventType, Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer import (
    EventChunker,
    ObservedMemories,
    SafetyScanner,
    TypedObserver,
    enforce_verbatim_content,
    merge_observations,
)
from tom.observer.tokenizer import count_tokens
from tom.providers import MockStructuredLLM


def make_event(event_id: str, content: str) -> Event:
    return Event(id=event_id, type=EventType.USER, content=content, timestamp=datetime.now(UTC))


def make_memory(source_id: str) -> MemoryItem:
    return MemoryItem(
        id="m1",
        content="Never edit generated files",
        knowledge_type=KnowledgeType.CONSTRAINT,
        retention=RetentionPolicy.EXACT,
        importance=Importance.CRITICAL,
        confidence=1,
        source_ids=[source_id],
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_observer_returns_structured_items_and_preserves_sources() -> None:
    event = make_event("e1", "Never edit generated files")
    llm = MockStructuredLLM(ObservedMemories(items=[make_memory("e1")]))

    result = await TypedObserver(llm).observe([event])

    assert result[0].source_ids == ["e1"]
    assert llm.calls[0]["response_model"] is ObservedMemories


@pytest.mark.asyncio
async def test_observer_overwrites_paraphrased_content_for_exact_and_high_fidelity() -> None:
    """RetentionPolicy=EXACT must mean the source wording survives, not just
    that the item is never evicted at budget time."""
    event = make_event("e1", "php - 8.4.17")
    paraphrased = make_memory("e1").model_copy(update={"content": "Use PHP version 8.4.17."})
    llm = MockStructuredLLM(ObservedMemories(items=[paraphrased]))

    result = await TypedObserver(llm).observe([event])

    assert result[0].content == "php - 8.4.17"


@pytest.mark.asyncio
async def test_observer_keeps_llm_wording_for_compressible_items() -> None:
    event = make_event("e1", "Users seem to prefer dark mode over light mode lately.")
    paraphrased = make_memory("e1").model_copy(
        update={"content": "User prefers dark mode.", "retention": RetentionPolicy.COMPRESSIBLE}
    )
    llm = MockStructuredLLM(ObservedMemories(items=[paraphrased]))

    result = await TypedObserver(llm).observe([event])

    assert result[0].content == "User prefers dark mode."


def test_enforce_verbatim_content_joins_multiple_sources() -> None:
    events = [make_event("e1", "line one"), make_event("e2", "line two")]
    item = make_memory("e1").model_copy(
        update={"content": "a paraphrase", "source_ids": ["e1", "e2"]}
    )

    enforce_verbatim_content([item], events)

    assert item.content == "line one\nline two"


@pytest.mark.asyncio
async def test_observer_rejects_sources_outside_chunk() -> None:
    llm = MockStructuredLLM(ObservedMemories(items=[make_memory("missing")]))

    with pytest.raises(ValueError, match="unknown event IDs"):
        await TypedObserver(llm).observe([make_event("e1", "fact")])


def test_observer_schema_rejects_extra_fields_and_empty_content() -> None:
    with pytest.raises(ValueError):
        ObservedMemories.model_validate({"items": [], "unexpected": True})

    with pytest.raises(ValueError):
        MemoryItem.model_validate(
            {**make_memory("e1").model_dump(mode="json"), "content": ""}
        )


def test_event_chunker_is_ordered_and_does_not_split_events() -> None:
    events = [make_event("e1", "one two"), make_event("e2", "three four"), make_event("e3", "five")]

    chunks = EventChunker().chunk(events, max_tokens=count_tokens("one two"))

    assert [[event.id for event in chunk] for chunk in chunks] == [["e1"], ["e2"], ["e3"]]
    assert EventChunker().token_counts(chunks) == [
        count_tokens("one two"),
        count_tokens("three four"),
        count_tokens("five"),
    ]


@pytest.mark.asyncio
async def test_empty_observation_does_not_call_provider() -> None:
    llm = MockStructuredLLM(ObservedMemories())
    observer = TypedObserver(llm)

    assert await observer.observe([]) == []
    assert llm.calls == []


@pytest.mark.asyncio
async def test_safety_scanner_records_scanner_metrics() -> None:
    event = make_event("e1", "Never deploy without approval")
    item = make_memory("e1")
    scanner = SafetyScanner(MockStructuredLLM(ObservedMemories(items=[item])))

    result = await scanner.scan([event])

    assert result == [item]
    assert scanner.last_metrics.scanner_input_tokens > 0
    assert scanner.last_metrics.constraints_created == 1


@pytest.mark.asyncio
async def test_empty_safety_scan_resets_previous_metrics() -> None:
    event = make_event("e1", "Never deploy without approval")
    scanner = SafetyScanner(MockStructuredLLM(ObservedMemories(items=[make_memory("e1")])))

    await scanner.scan([event])
    await scanner.scan([])

    assert scanner.last_input_tokens == 0
    assert scanner.last_output_tokens == 0
    assert scanner.last_llm_calls == 0
    assert scanner.last_metrics.scanner_input_tokens == 0
    assert scanner.last_metrics.memory_items_created == 0


def test_merge_observations_deduplicates_and_preserves_evidence() -> None:
    first = make_memory("e1")
    second = make_memory("e2")

    result = merge_observations([first], [second])

    assert len(result) == 1
    assert result[0].source_ids == ["e1", "e2"]
