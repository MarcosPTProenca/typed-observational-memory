"""Scope-aware partitioning of protected memory."""

import re
from collections import defaultdict
from collections.abc import Iterable

from tom.models import KnowledgeType, MemoryItem, MemoryStatus, RetentionPolicy

GLOBAL_SCOPE = "global"
_PROTECTED_TYPES = {KnowledgeType.CONSTRAINT, KnowledgeType.PROCEDURE}
_PROTECTED_RETENTION = {RetentionPolicy.EXACT, RetentionPolicy.HIGH_FIDELITY}


def is_protected(memory: MemoryItem) -> bool:
    return memory.knowledge_type in _PROTECTED_TYPES or memory.retention in _PROTECTED_RETENTION


def decompose_protected(memories: Iterable[MemoryItem]) -> dict[str, list[MemoryItem]]:
    """Partition active protected memories by scope without mutating them.

    An item with several scopes is deliberately present in every partition. Items
    without a scope are global, as are items explicitly tagged ``global``.
    """
    partitions: dict[str, list[MemoryItem]] = defaultdict(list)
    for memory in memories:
        if memory.status != MemoryStatus.ACTIVE or not is_protected(memory):
            continue
        scopes = normalized_scopes(memory)
        if not scopes or GLOBAL_SCOPE in scopes:
            partitions[GLOBAL_SCOPE].append(memory)
        for scope in scopes - {GLOBAL_SCOPE}:
            partitions[scope].append(memory)
    return {scope: sorted(items, key=lambda item: item.id) for scope, items in sorted(partitions.items())}


def relevant_scopes(
    memories: Iterable[MemoryItem], query_terms: set[str]
) -> list[str]:
    """Return scopes whose names or item topics match the query."""
    partitions = decompose_protected(memories)
    result: set[str] = set()
    for scope, items in partitions.items():
        if scope == GLOBAL_SCOPE:
            continue
        if _terms(scope) & query_terms or any(_terms(item.topic or "") & query_terms for item in items):
            result.add(scope)
    return sorted(result)


def normalized_scopes(memory: MemoryItem) -> set[str]:
    return {scope.strip().casefold() for scope in memory.scope if scope.strip()}


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[\w]+", value.casefold()) if len(term) > 1}
