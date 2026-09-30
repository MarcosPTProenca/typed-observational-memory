from datetime import UTC, datetime

import pytest

from tom.context import UnsafeContextBudget
from tom.models import Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.retrieval import TypeAwareRetriever


def memory(
    ident: str,
    content: str,
    kind: KnowledgeType = KnowledgeType.BELIEF,
    retention: RetentionPolicy = RetentionPolicy.COMPRESSIBLE,
    scope: list[str] | None = None,
) -> MemoryItem:
    return MemoryItem(
        id=ident,
        content=content,
        knowledge_type=kind,
        retention=retention,
        importance=Importance.HIGH,
        confidence=1,
        scope=scope or [],
        source_ids=[f"event-{ident}"],
        created_at=datetime.now(UTC),
    )


def test_retrieval_pins_global_constraints_and_fills_by_relevance() -> None:
    result = TypeAwareRetriever().retrieve(
        [
            memory("constraint", "Never expose secrets.", KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT),
            memory("irrelevant", "The project uses Python."),
            memory("relevant", "The database migration uses PostgreSQL."),
        ],
        "database migration",
        40,
    )

    assert [item.id for item in result.memories][:2] == ["constraint", "relevant"]
    assert result.token_count <= 40


def test_retrieval_selects_scoped_protected_memory_without_text_match() -> None:
    result = TypeAwareRetriever().retrieve(
        [memory("auth", "Rotate credentials regularly.", KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT, ["auth"])],
        "auth implementation",
        30,
    )

    assert [item.id for item in result.memories] == ["auth"]
    assert result.scopes == ["auth"]


def test_unrelated_scoped_protected_memory_is_not_pinned() -> None:
    result = TypeAwareRetriever().retrieve(
        [memory("db", "Use parameterized queries.", KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT, ["database"])],
        "frontend styling",
        30,
    )

    assert result.memories == []


def test_scope_matching_normalizes_whitespace_case_and_punctuation() -> None:
    item = memory(
        "auth", "Rotate credentials regularly.",
        KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT, [" Auth / API "],
    )

    result = TypeAwareRetriever().retrieve([item], "auth api", 30)

    assert [selected.id for selected in result.memories] == ["auth"]


def test_topic_selects_scope_and_multi_scope_memory() -> None:
    auth_db = memory(
        "auth-db", "Protect credentials and database access.",
        KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT, ["auth", "database"],
    )
    auth_db.topic = "authentication"
    result = TypeAwareRetriever().retrieve([auth_db], "authentication", 40)

    assert [item.id for item in result.memories] == ["auth-db"]
    assert result.scopes == ["auth", "database"]


def test_decomposition_keeps_multiscoped_items_in_each_partition() -> None:
    item = memory(
        "shared", "Use the same credentials.",
        KnowledgeType.PROCEDURE, RetentionPolicy.HIGH_FIDELITY, ["auth", "deployment"],
    )

    from tom.memory import decompose_protected

    partitions = decompose_protected([item])
    assert partitions["auth"] == [item]
    assert partitions["deployment"] == [item]


def test_relevance_includes_topic_and_prioritizes_critical_memory() -> None:
    topic_match = memory("topic", "Keep the service stable.")
    topic_match.topic = "database migration"
    critical = memory("critical", "The service uses PostgreSQL.")
    critical.importance = Importance.CRITICAL

    result = TypeAwareRetriever().retrieve(
        [topic_match, critical], "database", 40
    )

    assert [item.id for item in result.memories] == ["critical", "topic"]


def test_pinned_exact_memory_cannot_exceed_budget() -> None:
    item = memory("exact", "This constraint must always be preserved.", KnowledgeType.CONSTRAINT, RetentionPolicy.EXACT)

    with pytest.raises(UnsafeContextBudget):
        TypeAwareRetriever().retrieve([item], "anything", 1)
