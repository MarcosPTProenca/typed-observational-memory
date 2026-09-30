import re
from collections.abc import Iterable

from pydantic import Field

from tom.context import ContextProjector, ProjectedContext
from tom.memory.decomposition import is_protected, normalized_scopes, relevant_scopes
from tom.models import Importance, KnowledgeType, MemoryItem, MemoryStatus, RetentionPolicy
from tom.observer.tokenizer import count_tokens


class RetrievedContext(ProjectedContext):
    """Context selected for a query, including the scopes used for pinning."""

    scopes: list[str] = Field(default_factory=list)


class TypeAwareRetriever:
    """Select applicable protected memory before filling the budget by relevance.

    Retrieval is deliberately lexical: it is deterministic, dependency-free, and
    keeps constraints/procedures from being lost just because their wording differs
    from the query.
    """

    def __init__(self, projector: ContextProjector | None = None) -> None:
        self.projector = projector or ContextProjector()

    def retrieve(
        self,
        memories: Iterable[MemoryItem],
        query: str,
        token_budget: int,
    ) -> RetrievedContext:
        if token_budget < 1:
            raise ValueError("token_budget must be positive")

        active = [m for m in memories if m.status == MemoryStatus.ACTIVE]
        terms = _terms(query)
        scopes = relevant_scopes(active, terms)

        protected = [
            memory
            for memory in active
            if self._is_protected(memory) and self._applicable(memory, terms, scopes)
        ]
        protected.sort(key=self._protected_key)
        selected = self._fit_required(protected, token_budget)

        ordinary = [
            memory
            for memory in active
            if memory not in selected and not self._is_protected(memory)
        ]
        ordinary.sort(key=lambda memory: self._relevance_key(memory, terms))
        for memory in ordinary:
            candidate = selected + [memory]
            if self._tokens(candidate) <= token_budget:
                selected.append(memory)

        projected = self.projector.project(selected, token_budget)
        return RetrievedContext(
            text=projected.text,
            memories=projected.memories,
            token_count=projected.token_count,
            scopes=scopes,
        )

    def _is_protected(self, memory: MemoryItem) -> bool:
        return is_protected(memory)

    @staticmethod
    def _applicable(memory: MemoryItem, terms: set[str], scopes: list[str]) -> bool:
        memory_scopes = normalized_scopes(memory)
        if not memory_scopes or "global" in memory_scopes:
            return True
        if set(scopes) & memory_scopes:
            return True
        # A scoped item can still be selected when its subject is explicitly named.
        return bool(_terms(memory.topic or "") & terms)

    @staticmethod
    def _protected_key(memory: MemoryItem) -> tuple[int, int, str]:
        return (
            0 if memory.retention == RetentionPolicy.EXACT else 1,
            0 if memory.knowledge_type == KnowledgeType.CONSTRAINT else 1,
            memory.id,
        )

    def _fit_required(self, memories: list[MemoryItem], budget: int) -> list[MemoryItem]:
        exact = [m for m in memories if m.retention == RetentionPolicy.EXACT]
        if self._tokens(exact) > budget:
            # Let the existing projector provide the stable domain error/message.
            self.projector.project(exact, budget)
        selected = exact.copy()
        for memory in memories:
            if memory in selected:
                continue
            if self._tokens(selected + [memory]) <= budget:
                selected.append(memory)
        return selected

    def _relevance_key(self, memory: MemoryItem, terms: set[str]) -> tuple[int, int, int, str]:
        overlap = len((_terms(memory.content) | _terms(memory.topic or "")) & terms)
        return (
            -overlap,
            0 if memory.importance == Importance.CRITICAL else 1,
            0 if memory.retention == RetentionPolicy.HIGH_FIDELITY else 1,
            memory.id,
        )

    def _tokens(self, memories: list[MemoryItem]) -> int:
        return count_tokens(self.projector.renderer.render(memories))


def retrieve_memories(
    memories: Iterable[MemoryItem], query: str, token_budget: int
) -> RetrievedContext:
    return TypeAwareRetriever().retrieve(memories, query, token_budget)


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[\w]+", value.casefold()) if len(term) > 1}
