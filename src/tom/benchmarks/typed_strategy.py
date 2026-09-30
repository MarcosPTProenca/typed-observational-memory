import asyncio
from hashlib import sha256
from time import perf_counter

from tom.context import ContextProjector
from tom.memory import SQLiteMemoryStore
from tom.models import Event, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer import EventChunker, TypedObserver
from tom.retrieval import TypeAwareRetriever


class TypedTOMMemory:
    """Online TOM adapter: append events, observe bounded chunks, retrieve on read."""

    def __init__(
        self,
        observer: TypedObserver,
        projector: ContextProjector,
        *,
        store: SQLiteMemoryStore | None = None,
        observation_tokens: int = 2_048,
        use_retrieval: bool = True,
        background: bool = False,
        max_pending_chunks: int = 8,
    ) -> None:
        if observation_tokens < 1:
            raise ValueError("observation_tokens must be positive")
        if max_pending_chunks < 1:
            raise ValueError("max_pending_chunks must be positive")
        self.observer = observer
        self.projector = projector
        self.retriever = TypeAwareRetriever(projector)
        self.store = store or SQLiteMemoryStore()
        self.chunker = EventChunker()
        self.observation_tokens = observation_tokens
        self.use_retrieval = use_retrieval
        self.comparison_label = (
            "tom_jev" if getattr(observer, "relabeler", None) is not None else
            "tom_typed" if use_retrieval else "tom_typed_no_retrieval"
        )
        self.pending: dict[str, list[Event]] = {}
        self.memories: dict[str, list[MemoryItem]] = {}
        self._restored: set[str] = set()
        self.last_metrics = observer.last_metrics
        self.background = background
        self.max_pending_chunks = max_pending_chunks
        self._queues: dict[str, asyncio.Queue] = {}
        self._workers: dict[str, asyncio.Task] = {}
        self._barriers: dict[str, list[asyncio.Future]] = {}
        self._scheduled: dict[str, set[str]] = {}
        self.background_metrics: dict[str, float | int] = {
            "ingest_wait_ms": 0.0, "observation_ms": 0.0,
            "barrier_wait_ms": 0.0, "pending_chunks": 0,
        }
        self.last_background_error: BaseException | None = None

    async def _restore(self, session_id: str) -> None:
        if session_id in self._restored:
            return
        events = await self.store.list_events(session_id)
        processed = await self.store.processed_event_ids(session_id)
        memories = await self.store.list_memory_items(session_id)
        self.memories[session_id] = memories
        self.pending[session_id] = [event for event in events if event.id not in processed]
        self._restored.add(session_id)

    @staticmethod
    def _stable_event(session_id: str, event: Event) -> Event:
        sequence = event.metadata.get("session_sequence", event.id)
        event_id = f"{session_id}:event:{sequence}"
        metadata = dict(event.metadata)
        metadata.update({"session_id": session_id, "session_sequence": str(sequence),
                         "original_event_id": event.id})
        return event.model_copy(update={"id": event_id, "metadata": metadata})

    async def _worker(self, session_id: str) -> None:
        queue = self._queues[session_id]
        while True:
            events, barrier = await queue.get()
            try:
                started = perf_counter()
                await self._process_events(session_id, events)
                self.last_background_error = None
                self.background_metrics["observation_ms"] = (
                    self.background_metrics["observation_ms"] + (perf_counter() - started) * 1000
                )
                barrier.set_result(None)
            except Exception as exc:  # noqa: BLE001 - worker must forward provider/storage errors
                self.last_background_error = exc
                for event in events:
                    self._scheduled.setdefault(session_id, set()).discard(event.id)
                if not barrier.done():
                    barrier.set_exception(exc)
            finally:
                queue.task_done()

    def _ensure_worker(self, session_id: str) -> None:
        if session_id in self._workers:
            return
        self._queues[session_id] = asyncio.Queue(maxsize=self.max_pending_chunks)
        self._barriers[session_id] = []
        self._scheduled[session_id] = set()
        self._workers[session_id] = asyncio.create_task(self._worker(session_id))

    async def _enqueue(self, session_id: str, events: list[Event]) -> None:
        self._ensure_worker(session_id)
        loop = asyncio.get_running_loop()
        barrier = loop.create_future()
        started = perf_counter()
        await self._queues[session_id].put((events, barrier))
        self.background_metrics["ingest_wait_ms"] = (
            self.background_metrics["ingest_wait_ms"] + (perf_counter() - started) * 1000
        )
        self._barriers[session_id].append(barrier)
        self._scheduled[session_id].update(event.id for event in events)
        self.background_metrics["pending_chunks"] = self._queues[session_id].qsize()

    async def _schedule_pending(self, session_id: str) -> None:
        pending = [event for event in self.pending.get(session_id, [])
                   if event.id not in self._scheduled.setdefault(session_id, set())]
        for chunk in self.chunker.chunk(pending, self.observation_tokens):
            await self._enqueue(session_id, chunk)

    async def ingest(self, session_id: str, events: list[Event]) -> None:
        if not events:
            return
        await self._restore(session_id)
        normalized = [self._stable_event(session_id, event) for event in events]
        existing = {event.id for event in await self.store.list_events(session_id)}
        new_events = [event for event in normalized if event.id not in existing]
        if new_events:
            await self.store.add_events(new_events)
            self.pending.setdefault(session_id, []).extend(new_events)
            if self.background:
                unscheduled = [event for event in self.pending[session_id]
                               if event.id not in self._scheduled.setdefault(session_id, set())]
                if self.chunker.token_counts([unscheduled])[0] >= self.observation_tokens:
                    await self._schedule_pending(session_id)

    async def _process_events(self, session_id: str, pending: list[Event]) -> None:
        source_ids = {event.metadata.get("original_event_id", event.id): event.id
                      for event in pending}
        observer_events = [event.model_copy(update={
            "id": event.metadata.get("original_event_id", event.id),
        }) for event in pending]
        items = await self.observer.observe_chunks(
            self.chunker.chunk(observer_events, self.observation_tokens)
        )
        items = [item.model_copy(update={
            "source_ids": [source_ids.get(source_id, source_id) for source_id in item.source_ids],
        }) for item in items]
        stable_items = []
        for item in items:
            source_key = ":".join(item.source_ids)
            stable_id = f"{session_id}:memory:{sha256((source_key + item.id).encode()).hexdigest()[:16]}"
            stable_items.append(item.model_copy(update={"id": stable_id}))
        existing_ids = {item.id for item in await self.store.list_memory_items(session_id)}
        new_items = [item for item in stable_items if item.id not in existing_ids]
        if new_items:
            await self.store.add_memory_items(new_items)
        await self.store.mark_events_processed(session_id, [event.id for event in pending])
        done = {event.id for event in pending}
        self.pending[session_id] = [event for event in self.pending.get(session_id, [])
                                    if event.id not in done]
        self._scheduled.setdefault(session_id, set()).difference_update(done)
        self.memories.setdefault(session_id, []).extend(new_items)
        self._accumulate(self.observer.last_metrics)

    async def compact(self, session_id: str, budget: int) -> None:
        await self._restore(session_id)
        if self.background:
            await self._schedule_pending(session_id)
            started = perf_counter()
            barriers = self._barriers.setdefault(session_id, [])
            self._barriers[session_id] = []
            if barriers:
                try:
                    await asyncio.gather(*barriers)
                except Exception:
                    self.last_background_error = None
                    raise
            self.background_metrics["barrier_wait_ms"] = (
                self.background_metrics["barrier_wait_ms"] + (perf_counter() - started) * 1000
            )
            self.background_metrics["pending_chunks"] = self._queues[session_id].qsize() if session_id in self._queues else 0
            if self.pending.get(session_id):
                raise RuntimeError("background observer barrier completed with pending events")
            return
        pending = self.pending.get(session_id, [])
        if pending:
            await self._process_events(session_id, pending)

    async def aclose(self) -> None:
        """Drain accepted chunks and surface worker failures to the caller."""
        errors: list[Exception] = []
        for session_id in list(self._workers):
            barriers = self._barriers.get(session_id, [])
            if barriers:
                results = await asyncio.gather(*barriers, return_exceptions=True)
                errors.extend(result for result in results if isinstance(result, Exception))
            await self._queues[session_id].join()
            self._workers[session_id].cancel()
            try:
                await self._workers[session_id]
            except asyncio.CancelledError:
                pass
        if errors:
            raise errors[0]
        if self.last_background_error is not None:
            raise self.last_background_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def context(self, session_id: str, query: str, budget: int) -> str:
        await self._restore(session_id)
        memories = self.memories.get(session_id, [])
        projected = (self.retriever.retrieve(memories, query, budget) if self.use_retrieval
                     else self.projector.project(memories, budget))
        self.selected_memory_source_ids = [source_id for item in projected.memories
                                           for source_id in item.source_ids]
        self.last_metrics = self.last_metrics.model_copy(
            update={
                "projected_tokens": projected.token_count,
                "active_memory_tokens": projected.token_count,
            }
        )
        return projected.text

    def _accumulate(self, current) -> None:
        previous = self.last_metrics
        self.last_metrics = previous.model_copy(update={
            "observer_input_tokens": previous.observer_input_tokens + current.observer_input_tokens,
            "observer_output_tokens": previous.observer_output_tokens + current.observer_output_tokens,
            "scanner_input_tokens": previous.scanner_input_tokens + current.scanner_input_tokens,
            "scanner_output_tokens": previous.scanner_output_tokens + current.scanner_output_tokens,
            "memory_items_created": previous.memory_items_created + current.memory_items_created,
            "constraints_created": previous.constraints_created + current.constraints_created,
            "procedures_created": previous.procedures_created + current.procedures_created,
            "llm_calls": previous.llm_calls + current.llm_calls,
            "jev_calls": previous.jev_calls + current.jev_calls,
            "jev_input_tokens": previous.jev_input_tokens + current.jev_input_tokens,
            "jev_output_tokens": previous.jev_output_tokens + current.jev_output_tokens,
            "estimated_cost_usd": previous.estimated_cost_usd + current.estimated_cost_usd,
            "latency_ms": previous.latency_ms + current.latency_ms,
        })


class UntypedTOMMemory(TypedTOMMemory):
    """Ablation that removes type/retention semantics at projection time."""

    comparison_label = "tom_untyped_no_retrieval"

    def __init__(self, observer, projector, **kwargs):
        super().__init__(observer, projector, use_retrieval=False, **kwargs)
        self.comparison_label = "tom_untyped_no_retrieval"

    async def context(self, session_id: str, query: str, budget: int) -> str:
        await self._restore(session_id)
        memories = [item.model_copy(update={"knowledge_type": KnowledgeType.EPISODIC, "retention": RetentionPolicy.COMPRESSIBLE})
                    for item in self.memories.get(session_id, [])]
        projected = self.projector.project(memories, budget)
        self.selected_memory_source_ids = [source_id for item in projected.memories
                                           for source_id in item.source_ids]
        self.last_metrics = self.last_metrics.model_copy(update={
            "projected_tokens": projected.token_count,
            "active_memory_tokens": projected.token_count,
        })
        return projected.text

