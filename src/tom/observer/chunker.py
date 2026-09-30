from tom.models.event import Event

from .tokenizer import count_tokens


class EventChunker:
    """Split events without reordering; an oversized event is its own chunk."""

    @staticmethod
    def count_tokens(events: list[Event]) -> int:
        return sum(count_tokens(event.content) for event in events)

    def chunk(self, events: list[Event], max_tokens: int) -> list[list[Event]]:
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")

        chunks: list[list[Event]] = []
        current: list[Event] = []
        current_tokens = 0
        for event in events:
            event_tokens = self.count_tokens([event])
            if current and current_tokens + event_tokens > max_tokens:
                chunks.append(current)
                current = []
                current_tokens = 0
            current.append(event)
            current_tokens += event_tokens
        if current:
            chunks.append(current)
        return chunks

    def token_counts(self, chunks: list[list[Event]]) -> list[int]:
        return [self.count_tokens(chunk) for chunk in chunks]
