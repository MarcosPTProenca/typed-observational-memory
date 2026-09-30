import sys
import types
from datetime import UTC, datetime

import pytest


def _install_fake_sdk() -> None:
    """typesafe-sdk is an optional external dep; provide a fake so imports resolve."""
    module = types.ModuleType("typesafe_sdk")

    class Choice:
        def __init__(self, *, instructions: str, criteria: dict) -> None:
            self.instructions = instructions
            self.criteria = criteria

    class Noul:
        def __init__(self, *, instructions: str) -> None:
            self.instructions = instructions

    class Score:
        def __init__(self, *, instructions: str, criteria: list) -> None:
            self.instructions = instructions
            self.criteria = criteria

    module.Choice = Choice
    module.Noul = Noul
    module.Score = Score
    module.AsyncTypeSafeClient = object
    sys.modules["typesafe_sdk"] = module


_install_fake_sdk()

from tom.models import Event, EventType, Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer import (
    JevLineObserver,
    JevRelabeler,
    ObservedMemories,
    SafetyScanner,
    TypedObserver,
)
from tom.providers import MockStructuredLLM
from tom.providers.jev import JevClassifier


class _Answer:
    def __init__(self, **fields: object) -> None:
        self.__dict__.update(fields)


class _Response:
    def __init__(self, *, choices=None, nouls=None, scores=None) -> None:
        self.choices = choices or {}
        self.nouls = nouls or {}
        self.scores = scores or {}


class FakeClient:
    def __init__(self, response: _Response) -> None:
        self._response = response
        self.calls: list[dict] = []

    async def system_one(self, *, state, questions):
        self.calls.append({"state": state, "questions": questions})
        return self._response


def _labels_response(
    knowledge_type="constraint", retention="compressible", importance="high", confidence=0.9
) -> _Response:
    return _Response(
        choices={
            "knowledge_type": _Answer(choice=knowledge_type),
            "retention": _Answer(choice=retention),
            "importance": _Answer(choice=importance),
        },
        nouls={"confidence": _Answer(noul=confidence)},
    )


def make_memory(content: str, retention: RetentionPolicy) -> MemoryItem:
    return MemoryItem(
        id="m1",
        content=content,
        knowledge_type=KnowledgeType.EPISODIC,
        retention=retention,
        importance=Importance.LOW,
        confidence=0.2,
        topic="deploys",
        scope=["ci"],
        source_ids=["e1"],
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_classify_labels_maps_response_to_enums() -> None:
    client = FakeClient(_labels_response("constraint", "exact", "critical", 0.87))
    jev = JevClassifier(client=client)

    labels = await jev.classify_labels("Never deploy on Friday")

    assert labels.knowledge_type == KnowledgeType.CONSTRAINT
    assert labels.retention == RetentionPolicy.EXACT
    assert labels.importance == Importance.CRITICAL
    assert labels.confidence == 0.87
    assert jev.last_calls == 1
    assert jev.last_input_tokens > 0
    assert client.calls[0]["state"] == "Never deploy on Friday"


@pytest.mark.asyncio
async def test_observer_jev_labels_before_verbatim_and_counts_calls() -> None:
    event = Event(
        id="e1", type=EventType.USER, content="Never force push to main",
        timestamp=datetime.now(UTC),
    )
    observed = make_memory("Don't rewrite main", RetentionPolicy.DISCARDABLE)
    llm = MockStructuredLLM(ObservedMemories(items=[observed]))
    client = FakeClient(_labels_response("constraint", "exact", "critical", 0.95))
    observer = TypedObserver(llm, relabeler=JevRelabeler(JevClassifier(client=client)))

    items = await observer.observe_chunks([[event]])

    assert items[0].content == event.content
    assert items[0].knowledge_type == KnowledgeType.CONSTRAINT
    assert observer.last_metrics.jev_calls == 1
    assert observer.last_metrics.jev_input_tokens > 0
    assert observer.last_metrics.constraints_created == 1
    assert client.calls[0]["state"] == "Don't rewrite main"


@pytest.mark.asyncio
async def test_jev_records_billed_usage_and_effective_model() -> None:
    response = _labels_response()
    response.usage = _Answer(input_tokens=777, output_tokens=33)
    response.model = "jev-1.13.0"
    jev = JevClassifier(client=FakeClient(response))

    await jev.classify_labels("short")

    assert jev.last_input_tokens == 777
    assert jev.last_output_tokens == 33
    assert jev.model == "jev-1.13.0"


@pytest.mark.asyncio
async def test_line_observer_uses_jev_type_but_pins_only_paper_protected_types() -> None:
    class Client:
        async def system_one(self, *, state, questions):
            return (_labels_response("constraint", "compressible") if state.startswith("Never")
                    else _labels_response("belief", "exact"))

    events = [Event(id=f"e{i}", type=EventType.USER, content=text, timestamp=datetime.now(UTC))
              for i, text in enumerate(["Never delete production", "A fact about a path"])]
    observer = JevLineObserver(JevClassifier(client=Client()))
    items = await observer.observe_chunks([events])

    assert [item.source_ids for item in items] == [["e0"], ["e1"]]
    assert [item.retention for item in items] == [RetentionPolicy.EXACT, RetentionPolicy.COMPRESSIBLE]
    assert observer.last_metrics.jev_calls == 2
    assert observer.last_metrics.llm_calls == 0


@pytest.mark.asyncio
async def test_confirm_critical_returns_noul_probability() -> None:
    client = FakeClient(_Response(nouls={"gate": _Answer(noul=0.73)}))
    jev = JevClassifier(client=client)

    prob = await jev.confirm_critical("Approval required before merging")

    assert prob == 0.73
    assert "gate" in client.calls[0]["questions"]


@pytest.mark.asyncio
async def test_relabeler_overwrites_labels_but_preserves_content_and_sources() -> None:
    item = make_memory("do not force-push to main", RetentionPolicy.DISCARDABLE)
    jev = JevClassifier(client=FakeClient(_labels_response("constraint", "exact", "critical", 0.95)))

    result = await JevRelabeler(jev).relabel([item])

    assert result[0].content == "do not force-push to main"
    assert result[0].source_ids == ["e1"]
    assert result[0].topic == "deploys"
    assert result[0].knowledge_type == KnowledgeType.CONSTRAINT
    assert result[0].retention == RetentionPolicy.EXACT
    assert result[0].importance == Importance.CRITICAL
    assert result[0].confidence == 0.95


@pytest.mark.asyncio
async def test_relabeler_no_items_is_noop() -> None:
    jev = JevClassifier(client=FakeClient(_labels_response()))
    assert await JevRelabeler(jev).relabel([]) == []


@pytest.mark.asyncio
async def test_safety_scanner_gate_pins_confirmed_items_to_exact() -> None:
    event = Event(
        id="e1", type=EventType.USER, content="Approval required", timestamp=datetime.now(UTC)
    )
    scanned = make_memory("Approval required", RetentionPolicy.COMPRESSIBLE)
    llm = MockStructuredLLM(ObservedMemories(items=[scanned]))
    gate = JevClassifier(client=FakeClient(_Response(nouls={"gate": _Answer(noul=0.9)})))

    scanner = SafetyScanner(llm, gate=gate, gate_threshold=0.5)
    result = await scanner.scan([event])

    assert result[0].retention == RetentionPolicy.EXACT
    assert result[0].confidence == 0.9


@pytest.mark.asyncio
async def test_safety_scanner_gate_leaves_low_probability_items_untouched() -> None:
    event = Event(
        id="e1", type=EventType.USER, content="chatty aside", timestamp=datetime.now(UTC)
    )
    scanned = make_memory("chatty aside", RetentionPolicy.COMPRESSIBLE)
    llm = MockStructuredLLM(ObservedMemories(items=[scanned]))
    gate = JevClassifier(client=FakeClient(_Response(nouls={"gate": _Answer(noul=0.1)})))

    scanner = SafetyScanner(llm, gate=gate, gate_threshold=0.5)
    result = await scanner.scan([event])

    assert result[0].retention == RetentionPolicy.COMPRESSIBLE
