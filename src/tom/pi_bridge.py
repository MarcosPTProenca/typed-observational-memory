"""Small JSON bridge used by the Pi extension.

The bridge keeps Pi-specific wiring out of TOM. State is durable in SQLite and
observation is deterministic for the first local integration, so loading this
module never calls an LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime

from tom.benchmarks.typed_strategy import TypedTOMMemory
from tom.context import ContextProjector
from tom.memory import SQLiteMemoryStore
from tom.models import Event, EventType
from tom.observer.deterministic_observer import DeterministicObserver
from tom.observer.typed_observer import TypedObserver
from tom.providers.codex_bridge import CodexBridge
from tom.providers.pi import PiStructuredLLM


def make_memory(database: str, observer_mode: str | None = None) -> TypedTOMMemory:
    mode = observer_mode or os.environ.get("PI_TOM_OBSERVER", "deterministic")
    if mode == "llm":
        provider = os.environ.get("PI_TOM_PROVIDER", "kiro")
        model = os.environ.get("PI_TOM_MODEL", "qwen3-coder-next")
        observer = TypedObserver(PiStructuredLLM(
            model=model,
            bridge=CodexBridge(model=model, provider=provider),
        ))
    elif mode == "deterministic":
        observer = DeterministicObserver()
    else:
        raise ValueError(f"unknown observer mode: {mode!r}")
    return TypedTOMMemory(
        observer,
        ContextProjector(),
        store=SQLiteMemoryStore(database),
        use_retrieval=True,
        background=os.environ.get("PI_TOM_BACKGROUND", "1") != "0",
        observation_tokens=int(os.environ.get("PI_TOM_OBSERVATION_TOKENS", "10000")),
    )


async def handle(memory: TypedTOMMemory, request: dict) -> dict:
    session_id = str(request.get("session_id", "pi"))
    command = request.get("command")
    if command == "ingest":
        events = [
            Event(
                id=str(item["id"]),
                type=EventType(item.get("type", "user")),
                content=str(item["content"]),
                timestamp=datetime.fromisoformat(item["timestamp"])
                if item.get("timestamp")
                else datetime.now(UTC),
                metadata=item.get("metadata", {}),
            )
            for item in request.get("events", [])
        ]
        await memory.ingest(session_id, events)
        return {"ok": True, "ingested": len(events), "llm_calls": 0}
    if command == "context":
        text = await memory.context(session_id, str(request.get("query", "")), int(request.get("budget", 2048)))
        return {"ok": True, "text": text, "llm_calls": 0}
    if command == "compact":
        await memory.compact(session_id, int(request.get("budget", 2048)))
        return {"ok": True, "llm_calls": 0}
    raise ValueError(f"unknown command: {command!r}")


async def serve(database: str) -> None:
    memory = make_memory(database)
    while line := await asyncio.to_thread(sys.stdin.readline):
        try:
            result = await handle(memory, json.loads(line))
            print(json.dumps(result), flush=True)
        except Exception as exc:  # noqa: BLE001 - bridge errors must reach the extension
            print(json.dumps({"ok": False, "error": str(exc)}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    asyncio.run(serve(args.db))


if __name__ == "__main__":
    main()
