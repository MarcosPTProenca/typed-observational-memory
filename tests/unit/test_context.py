from datetime import UTC, datetime, timedelta

import pytest

from tom.context import ContextProjector, ProjectionPolicy, SelectionPolicy, UnsafeContextBudget
from tom.context.renderer import Renderer
from tom.models import Importance, KnowledgeType, MemoryItem, MemoryStatus, RetentionPolicy
from tom.observer.tokenizer import count_tokens


def memory(
    ident: str,
    content: str,
    kind: KnowledgeType = KnowledgeType.BELIEF,
    retention: RetentionPolicy = RetentionPolicy.COMPRESSIBLE,
    importance: Importance = Importance.MEDIUM,
    age: int = 0,
) -> MemoryItem:
    return MemoryItem(
        id=ident,
        content=content,
        knowledge_type=kind,
        retention=retention,
        importance=importance,
        confidence=1,
        source_ids=["event-" + ident],
        created_at=datetime.now(UTC) - timedelta(seconds=age),
    )


def test_projection_is_deterministic_and_budgeted() -> None:
    memories = [
        memory("b", "The backend uses PostgreSQL."),
        memory("c", "Run integration tests.", KnowledgeType.PROCEDURE, RetentionPolicy.HIGH_FIDELITY),
        memory("a", "Never edit generated files.", KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT, Importance.CRITICAL),
    ]
    projector = ContextProjector()

    first = projector.project(memories, 30)
    second = projector.project(memories, 30)

    assert first == second
    assert first.token_count <= 30
    assert "[a]" in first.text
    assert first.text.index("# Constraints") < first.text.index("# Procedures")


def test_compact_renderer_preserves_content_and_provenance_outside_prompt() -> None:
    memories = [memory("long-id", "Never edit generated files.", KnowledgeType.CONSTRAINT,
                       RetentionPolicy.EXACT, Importance.CRITICAL)]
    result = ContextProjector(Renderer(compact=True)).project(memories, 30)
    original = ContextProjector().project(memories, 30)

    assert "Never edit generated files." in result.text
    assert result.token_count < original.token_count
    assert "long-id" not in result.text
    assert result.memories[0].id == "long-id"
    assert result.token_count == count_tokens(result.text)
    assert result.content_token_count > 0
    assert result.formatting_token_count > 0


def test_paper_policy_protects_constraints_and_procedures() -> None:
    procedure = memory("procedure", "Run the complete deployment verification procedure.",
                      KnowledgeType.PROCEDURE, RetentionPolicy.HIGH_FIDELITY)
    with pytest.raises(UnsafeContextBudget):
        ContextProjector(policy=ProjectionPolicy.PAPER).project([procedure], 1)


def test_coverage_selection_keeps_one_item_per_type_when_budget_allows() -> None:
    memories = [
        memory("belief", "A belief about the system.", KnowledgeType.BELIEF),
        memory("preference", "A preference about the system.", KnowledgeType.PREFERENCE),
        memory("episode", "An event that happened recently.", KnowledgeType.EPISODIC),
    ]
    result = ContextProjector(selection=SelectionPolicy.COVERAGE).project(memories, 100)

    assert {item.knowledge_type for item in result.memories} == {
        KnowledgeType.BELIEF, KnowledgeType.PREFERENCE, KnowledgeType.EPISODIC,
    }


def test_type_compact_selection_is_budgeted_and_deterministic() -> None:
    memories = [
        memory("belief", "A belief about the system.", KnowledgeType.BELIEF),
        memory("preference", "A preference about the system.", KnowledgeType.PREFERENCE),
        memory("episode", "An event that happened recently.", KnowledgeType.EPISODIC),
    ]
    projector = ContextProjector(selection=SelectionPolicy.TYPE_COMPACT)
    first = projector.project(memories, 30)
    second = projector.project(memories, 30)

    assert first == second
    assert first.token_count <= 30


def test_projection_deduplicates_compatible_content_and_merges_sources() -> None:
    first = memory("first", "The service uses PostgreSQL.")
    second = memory("second", "The service uses PostgreSQL.")
    result = ContextProjector().project([first, second], 100)

    assert result.text.count("The service uses PostgreSQL.") == 1
    assert set(result.memories[0].source_ids) == {"event-first", "event-second"}


def test_projection_keeps_incompatible_scopes_distinct() -> None:
    first = memory("first", "Use the production database.")
    second = memory("second", "Use the production database.")
    second.scope = ["staging"]
    result = ContextProjector().project([first, second], 100)

    assert result.text.count("Use the production database.") == 2


def test_best_effort_projection_is_explicitly_unsafe() -> None:
    item = memory("exact", "This protected evidence must remain.",
                  KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT)
    result = ContextProjector().project_best_effort([item], 1)

    assert result.unsafe is True
    assert result.required_token_count > result.token_count - 1
    assert "This protected evidence must remain." in result.text


def test_exact_memory_cannot_be_dropped() -> None:
    item = memory(
        "exact", "This is protected evidence that must remain.",
        KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT,
    )

    with pytest.raises(UnsafeContextBudget):
        ContextProjector().project([item], 1)


def test_superseded_memory_is_not_projected() -> None:
    old = memory("old", "The backend uses MySQL.")
    current = memory("new", "The backend uses PostgreSQL.")
    old.status = MemoryStatus.SUPERSEDED

    result = ContextProjector().project([old, current], 100)

    assert "MySQL" not in result.text
    assert "PostgreSQL" in result.text
