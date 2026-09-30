from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Self


class CodexBridge:
    """Persistent Node bridge using pi-ai's Codex OAuth provider, not the pi CLI."""

    def __init__(self, *, model: str | None = None, provider: str | None = None,
                 bridge: str | Path | None = None, timeout: float = 120.0) -> None:
        self.provider = provider or os.environ.get("PI_PROVIDER", "openai-codex")
        self.model = model or os.environ.get("PI_MODEL", "gpt-5.6-luna")
        default_bridge = "kiro_bridge.mjs" if self.provider == "kiro" else "codex_bridge.mjs"
        script = bridge or os.environ.get("TOM_CODEX_BRIDGE") or Path(__file__).parents[3] / "scripts" / default_bridge
        self.timeout = timeout
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.process = subprocess.Popen(
            ["node", str(script)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self._lock = asyncio.Lock()
        self._next_id = 0
        self.last_usage: dict[str, Any] | None = None

    async def prompt(self, text: str) -> str:
        async with self._lock:
            self._next_id += 1
            request = {"id": self._next_id, "provider": self.provider, "model": self.model, "prompt": text}
            assert self.process.stdin and self.process.stdout
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            try:
                line = await asyncio.wait_for(
                    asyncio.to_thread(self.process.stdout.readline), self.timeout
                )
            except TimeoutError as exc:
                self.process.kill()
                await asyncio.to_thread(self.process.wait)
                raise TimeoutError(f"Codex request timed out after {self.timeout:g}s") from exc
            if not line:
                raise RuntimeError("Codex bridge exited without a response")
            try:
                response: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("Codex bridge returned invalid JSON") from exc
            if response.get("id") != request["id"]:
                raise RuntimeError(
                    f"Codex bridge response ID mismatch: expected {request['id']}, got {response.get('id')}"
                )
            if response.get("error"):
                raise RuntimeError(response["error"])
            if not isinstance(response.get("answer"), str):
                raise TypeError("Codex bridge response has no text answer")
            self.last_usage = response.get("usage")
            return response["answer"]

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
