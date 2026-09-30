from collections import defaultdict

from tom.models import KnowledgeType, MemoryItem
from tom.observer.tokenizer import count_tokens


class Renderer:
    """Render memory items into stable markdown, optionally without IDs."""
    _sections = (
        ("Constraints", KnowledgeType.CONSTRAINT),
        ("Procedures", KnowledgeType.PROCEDURE),
        ("Current State", KnowledgeType.BELIEF),
        ("Preferences", KnowledgeType.PREFERENCE),
        ("Recent Relevant Events", KnowledgeType.EPISODIC),
    )

    def __init__(self, *, compact: bool = False) -> None:
        self.compact = compact

    def render(self, memories: list[MemoryItem]) -> str:
        grouped: dict[KnowledgeType, list[MemoryItem]] = defaultdict(list)
        for memory in memories:
            grouped[memory.knowledge_type].append(memory)

        sections: list[str] = []
        for title, kind in self._sections:
            items = grouped[kind]
            if not items:
                continue
            if self.compact:
                body = "\n".join(item.content for item in items)
                sections.append(f"{title}:\n{body}")
            else:
                body = "\n\n".join(f"[{item.id}]\n{item.content}" for item in items)
                sections.append(f"# {title}\n\n{body}")
        return "\n\n".join(sections)

    def content_token_count(self, memories: list[MemoryItem]) -> int:
        return count_tokens("\n".join(item.content for item in memories))

    def formatting_token_count(self, memories: list[MemoryItem]) -> int:
        sections = [title for title, kind in self._sections
                    if any(item.knowledge_type == kind for item in memories)]
        if self.compact:
            formatting = "\n\n".join(f"{title}:\n" for title in sections)
        else:
            formatting = "\n\n".join(f"# {title}\n\n" for title in sections)
            formatting += "\n".join(f"[{item.id}]\n" for item in memories)
        return count_tokens(formatting)
