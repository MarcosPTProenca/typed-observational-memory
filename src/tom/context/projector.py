from datetime import datetime
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field

from tom.models import Importance, KnowledgeType, MemoryItem, MemoryStatus, RetentionPolicy
from tom.observer.tokenizer import count_tokens

from .budget import TokenBudget, UnsafeContextBudget
from .renderer import Renderer


class ProjectionPolicy(StrEnum):
    STANDARD = "standard"
    PAPER = "paper"


class SelectionPolicy(StrEnum):
    GREEDY = "greedy"
    TYPE_COMPACT = "type_compact"
    COVERAGE = "coverage"


class ProjectedContext(BaseModel):
    text: str
    memories: list[MemoryItem]
    token_count: int = Field(ge=0)
    content_token_count: int = Field(default=0, ge=0)
    formatting_token_count: int = Field(default=0, ge=0)
    unsafe: bool = False
    required_token_count: int = Field(default=0, ge=0)


class ContextProjector:
    """Select and render active memories without mutating the memory state."""

    _retention_rank: ClassVar[dict[RetentionPolicy, int]] = {
        RetentionPolicy.EXACT: 0,
        RetentionPolicy.HIGH_FIDELITY: 1,
        RetentionPolicy.COMPRESSIBLE: 2,
        RetentionPolicy.DISCARDABLE: 3,
    }
    _importance_rank: ClassVar[dict[Importance, int]] = {
        Importance.CRITICAL: 0,
        Importance.HIGH: 1,
        Importance.MEDIUM: 2,
        Importance.LOW: 3,
    }

    def __init__(self, renderer: Renderer | None = None,
                 *, policy: ProjectionPolicy = ProjectionPolicy.STANDARD,
                 selection: SelectionPolicy = SelectionPolicy.GREEDY) -> None:
        self.renderer = renderer or Renderer()
        self.policy = policy
        self.selection = selection

    def project(
        self, memories: list[MemoryItem], token_budget: int | TokenBudget
    ) -> ProjectedContext:
        budget = token_budget.max_tokens if isinstance(token_budget, TokenBudget) else token_budget
        if budget < 1:
            raise ValueError("token_budget must be positive")

        active = self._deduplicate(
            [memory for memory in memories if memory.status == MemoryStatus.ACTIVE]
        )
        ordered = sorted(active, key=self._sort_key)
        protected = [memory for memory in ordered if self._is_protected(memory)]
        protected_text = self.renderer.render(protected)
        protected_tokens = count_tokens(protected_text)
        if protected_tokens > budget:
            raise UnsafeContextBudget(
                f"protected memories require {protected_tokens} tokens, budget is {budget}",
                required_tokens=protected_tokens, budget=budget,
            )

        selected = protected.copy()
        candidates = [memory for memory in ordered if memory not in selected]
        if self.selection == SelectionPolicy.COVERAGE:
            candidates = self._coverage_order(candidates)
        elif self.selection == SelectionPolicy.TYPE_COMPACT:
            selected = self._type_compact_select(selected, candidates, budget)
            candidates = [memory for memory in candidates if memory not in selected]
        for memory in candidates:
            candidate = selected + [memory]
            if count_tokens(self.renderer.render(candidate)) <= budget:
                selected.append(memory)

        text = self.renderer.render(selected)
        return ProjectedContext(
            text=text,
            memories=selected,
            token_count=count_tokens(text),
            content_token_count=self.renderer.content_token_count(selected),
            formatting_token_count=self.renderer.formatting_token_count(selected),
            required_token_count=protected_tokens,
        )

    def project_best_effort(
        self, memories: list[MemoryItem], token_budget: int | TokenBudget
    ) -> ProjectedContext:
        """Return protected content above budget, explicitly marked unsafe."""
        try:
            return self.project(memories, token_budget)
        except UnsafeContextBudget as error:
            active = self._deduplicate(
                [memory for memory in memories if memory.status == MemoryStatus.ACTIVE]
            )
            protected = [memory for memory in sorted(active, key=self._sort_key)
                         if self._is_protected(memory)]
            text = self.renderer.render(protected)
            return ProjectedContext(
                text=text, memories=protected, token_count=count_tokens(text),
                content_token_count=self.renderer.content_token_count(protected),
                formatting_token_count=self.renderer.formatting_token_count(protected),
                unsafe=True, required_token_count=error.required_tokens,
            )

    def _coverage_order(self, candidates: list[MemoryItem]) -> list[MemoryItem]:
        first_by_type: list[MemoryItem] = []
        seen: set[KnowledgeType] = set()
        for memory in candidates:
            if memory.knowledge_type not in seen:
                first_by_type.append(memory)
                seen.add(memory.knowledge_type)
        return first_by_type + [memory for memory in candidates if memory not in first_by_type]

    def _type_compact_select(
        self, selected: list[MemoryItem], candidates: list[MemoryItem], budget: int,
    ) -> list[MemoryItem]:
        """Deterministic TypeCompact-style allocation, followed by spillover fill."""
        shares = {
            KnowledgeType.BELIEF: 0.50,
            KnowledgeType.PREFERENCE: 0.20,
            KnowledgeType.EPISODIC: 0.30,
        }
        remaining = budget - count_tokens(self.renderer.render(selected))
        quotas = {kind: int(remaining * share) for kind, share in shares.items()}
        used: dict[KnowledgeType, int] = {kind: 0 for kind in shares}
        for memory in candidates:
            if memory.knowledge_type not in shares:
                continue
            candidate = selected + [memory]
            cost = count_tokens(self.renderer.render(candidate)) - count_tokens(
                self.renderer.render(selected)
            )
            if used[memory.knowledge_type] + cost <= quotas[memory.knowledge_type]:
                selected.append(memory)
                used[memory.knowledge_type] += cost
        return selected

    def _is_protected(self, memory: MemoryItem) -> bool:
        return memory.retention == RetentionPolicy.EXACT or (
            self.policy == ProjectionPolicy.PAPER and
            memory.knowledge_type.value in {"constraint", "procedure"}
        )

    def _deduplicate(self, memories: list[MemoryItem]) -> list[MemoryItem]:
        unique: dict[tuple[str, str, tuple[str, ...], str], MemoryItem] = {}
        for memory in memories:
            key = (memory.content, memory.knowledge_type.value,
                   tuple(sorted(memory.scope)), memory.retention.value)
            previous = unique.get(key)
            if previous is None:
                unique[key] = memory
                continue
            unique[key] = previous.model_copy(update={
                "source_ids": list(dict.fromkeys([*previous.source_ids, *memory.source_ids])),
                "supersedes": list(dict.fromkeys([*previous.supersedes, *memory.supersedes])),
                "confidence": max(previous.confidence, memory.confidence),
            })
        return list(unique.values())

    def _sort_key(self, memory: MemoryItem) -> tuple[int, int, float, str]:
        timestamp = memory.event_time or memory.created_at
        return (
            self._retention_rank[memory.retention],
            self._importance_rank[memory.importance],
            -_timestamp_value(timestamp),
            memory.id,
        )


def _timestamp_value(value: datetime) -> float:
    return value.timestamp()
