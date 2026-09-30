import json
import sqlite3
from pathlib import Path

from tom.models.enums import MemoryStatus
from tom.models.event import Event, _thaw
from tom.models.memory import MemoryItem

from .ledger import RecallResult


class SQLiteMemoryStore:
    def __init__(self, database: str | Path = ":memory:") -> None:
        self._db = sqlite3.connect(str(database))
        self._db.row_factory = sqlite3.Row
        self._db.executescript("""
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, type TEXT NOT NULL, content TEXT NOT NULL, timestamp TEXT NOT NULL, metadata_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memory_items (id TEXT PRIMARY KEY, content TEXT NOT NULL, knowledge_type TEXT NOT NULL, retention TEXT NOT NULL, importance TEXT NOT NULL, confidence REAL NOT NULL, topic TEXT, created_at TEXT NOT NULL, event_time TEXT, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memory_sources (memory_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(memory_id, event_id));
        CREATE TABLE IF NOT EXISTS memory_scopes (memory_id TEXT NOT NULL, scope TEXT NOT NULL, PRIMARY KEY(memory_id, scope));
        CREATE TABLE IF NOT EXISTS memory_supersedes (memory_id TEXT NOT NULL, superseded_memory_id TEXT NOT NULL, PRIMARY KEY(memory_id, superseded_memory_id));
        CREATE TABLE IF NOT EXISTS processed_events (session_id TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY(session_id, event_id));
        """)
        self._db.commit()

    async def add_events(self, events: list[Event]) -> None:
        with self._db:
            self._db.executemany(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                [
                    (e.id, e.type.value, e.content, e.timestamp.isoformat(), json.dumps(_thaw(e.metadata)))
                    for e in events
                ],
            )

    async def add_memory_items(self, items: list[MemoryItem]) -> None:
        # Validate the whole batch before writing so one bad source cannot leave a partial ledger.
        event_ids = {row[0] for row in self._db.execute("SELECT id FROM events")}
        for memory in items:
            unknown = set(memory.source_ids) - event_ids
            if unknown:
                raise ValueError(
                    f"Memory {memory.id} references unknown event IDs: {sorted(unknown)}"
                )

        with self._db:
            for m in items:
                self._db.execute(
                    "INSERT INTO memory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        m.id,
                        m.content,
                        m.knowledge_type.value,
                        m.retention.value,
                        m.importance.value,
                        m.confidence,
                        m.topic,
                        m.created_at.isoformat(),
                        m.event_time.isoformat() if m.event_time else None,
                        m.status.value,
                    ),
                )
                self._db.executemany(
                    "INSERT INTO memory_sources VALUES (?, ?)", [(m.id, sid) for sid in m.source_ids]
                )
                self._db.executemany(
                    "INSERT INTO memory_scopes VALUES (?, ?)", [(m.id, s) for s in m.scope]
                )
                self._db.executemany(
                    "INSERT INTO memory_supersedes VALUES (?, ?)",
                    [(m.id, sid) for sid in m.supersedes],
                )

    async def list_events(self, session_id: str | None = None) -> list[Event]:
        events = [
            Event(id=row["id"], type=row["type"], content=row["content"],
                  timestamp=row["timestamp"], metadata=json.loads(row["metadata_json"]))
            for row in self._db.execute("SELECT * FROM events ORDER BY timestamp, id")
        ]
        if session_id is None:
            return events
        return [event for event in events if event.metadata.get("session_id") == session_id]

    async def list_memory_items(self, session_id: str | None = None) -> list[MemoryItem]:
        memories = [await self._materialize(row)
                    for row in self._db.execute("SELECT * FROM memory_items ORDER BY id")]
        if session_id is None:
            return memories
        prefix = f"{session_id}:"
        return [memory for memory in memories if memory.id.startswith(prefix)]

    async def mark_events_processed(self, session_id: str, event_ids: list[str]) -> None:
        with self._db:
            self._db.executemany(
                "INSERT OR IGNORE INTO processed_events VALUES (?, ?)",
                [(session_id, event_id) for event_id in event_ids],
            )

    async def processed_event_ids(self, session_id: str) -> set[str]:
        return {row[0] for row in self._db.execute(
            "SELECT event_id FROM processed_events WHERE session_id=?", (session_id,)
        )}

    async def get_event(self, event_id: str) -> Event | None:
        row = self._db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return Event(id=row["id"], type=row["type"], content=row["content"], timestamp=row["timestamp"], metadata=json.loads(row["metadata_json"])) if row else None

    async def get_memory(self, memory_id: str) -> MemoryItem | None:
        row = self._db.execute("SELECT * FROM memory_items WHERE id=?", (memory_id,)).fetchone()
        if not row: return None
        return await self._materialize(row)

    async def _materialize(self, row: sqlite3.Row) -> MemoryItem:
        ids = [r[0] for r in self._db.execute("SELECT event_id FROM memory_sources WHERE memory_id=? ORDER BY event_id", (row["id"],))]
        scopes = [r[0] for r in self._db.execute("SELECT scope FROM memory_scopes WHERE memory_id=? ORDER BY scope", (row["id"],))]
        supersedes = [r[0] for r in self._db.execute("SELECT superseded_memory_id FROM memory_supersedes WHERE memory_id=? ORDER BY superseded_memory_id", (row["id"],))]
        return MemoryItem(id=row["id"], content=row["content"], knowledge_type=row["knowledge_type"], retention=row["retention"], importance=row["importance"], confidence=row["confidence"], topic=row["topic"], scope=scopes, source_ids=ids, created_at=row["created_at"], event_time=row["event_time"], status=row["status"], supersedes=supersedes)

    async def list_active_memory(self) -> list[MemoryItem]:
        return [await self._materialize(r) for r in self._db.execute("SELECT * FROM memory_items WHERE status=? ORDER BY id", (MemoryStatus.ACTIVE.value,))]

    async def update_status(self, memory_id: str, status: MemoryStatus) -> None:
        cur = self._db.execute("UPDATE memory_items SET status=? WHERE id=?", (status.value, memory_id))
        if cur.rowcount == 0: raise KeyError(memory_id)
        self._db.commit()

    async def get_sources(self, memory_id: str) -> list[Event]:
        return [
            event
            for row in self._db.execute(
                "SELECT event_id FROM memory_sources WHERE memory_id=? ORDER BY event_id",
                (memory_id,),
            )
            if (event := await self.get_event(row[0])) is not None
        ]

    async def recall(self, memory_id: str) -> RecallResult:
        memory = await self.get_memory(memory_id)
        if memory is None:
            raise KeyError(memory_id)
        return RecallResult(memory=memory, sources=await self.get_sources(memory_id))
