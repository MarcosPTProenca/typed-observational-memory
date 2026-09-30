"""Ground-truth labels for the Knowledge Triage reproduction.

The paper labels every AAC line with a regex -> encoder -> LLM cascade
(``knowledge_triage.classifier_cascade``). This module reuses that code and only
swaps the two services it cannot reach here: the encoder (octen-embedding-8b ->
text-embedding-3-large) and the metering (real list prices, hard cap).
"""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from knowledge_triage.classifier import KnowledgeType as KTType
from knowledge_triage.classifier_cascade import CascadeClassifier, EncoderClassifier
from knowledge_triage.kb import Item as KTItem
from knowledge_triage.kb import KnowledgeBase as KTKnowledgeBase

from .knowledge_triage_repro import AACConfig

EMBEDDING_MODEL = "text-embedding-3-large"
LABELER_LLM = "gpt-5.4-mini"
# USD per million tokens (input, output), OpenAI list prices.
PRICES = {
    EMBEDDING_MODEL: (0.13, 0.0),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5.6-luna": (0.20, 1.20),
}


class CostCapExceeded(RuntimeError):
    pass


class Meter:
    def __init__(self, cap_usd: float) -> None:
        self.cap_usd, self.spent, self.calls = cap_usd, 0.0, 0
        self._lock = threading.Lock()

    def charge(self, model: str, input_tokens: int, output_tokens: int) -> None:
        rate_in, rate_out = PRICES[model]
        with self._lock:
            self.spent += (input_tokens * rate_in + output_tokens * rate_out) / 1e6
            self.calls += 1
            if self.spent >= self.cap_usd:
                raise CostCapExceeded(f"spent ${self.spent:.4f} >= cap ${self.cap_usd:.2f}")


class _MeteredEmbeddings:
    def __init__(self, client: Any, meter: Meter) -> None:
        self._client, self._meter = client, meter

    def create(self, *, model: str, input: list[str]) -> Any:
        response = self._client.embeddings.create(model=EMBEDDING_MODEL, input=input)
        self._meter.charge(EMBEDDING_MODEL, response.usage.prompt_tokens, 0)
        return response


class MeteredEmbedder:
    def __init__(self, client: Any, meter: Meter) -> None:
        self.embeddings = _MeteredEmbeddings(client, meter)


class MeteredChat:
    """Chat client with the ``complete`` interface the upstream code expects."""

    def __init__(self, client: Any, model: str, meter: Meter) -> None:
        self._client, self.model, self._meter = client, model, meter

    def complete(
        self, messages: list[dict[str, str]], *, max_tokens: int = 1024, **_ignored: Any
    ) -> SimpleNamespace:
        response = self._client.chat.completions.create(
            model=self.model, messages=messages, max_completion_tokens=max_tokens
        )
        usage = response.usage
        self._meter.charge(self.model, usage.prompt_tokens, usage.completion_tokens)
        return SimpleNamespace(
            text=response.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )


@dataclass
class LabelStats:
    by_stage: dict[str, int]
    spent_usd: float


def _key(text: str) -> str:
    return hashlib.sha1(f"cascade-v1::{text}".encode()).hexdigest()[:16]


def cascade_relabel(
    configs: list[AACConfig], cache_path: Path, client: Any, *, cap_usd: float, workers: int = 8
) -> tuple[list[AACConfig], LabelStats]:
    """Return copies of ``configs`` typed by the upstream cascade (cached on disk)."""
    cache: dict[str, dict[str, str]] = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            record = json.loads(line)
            cache[record["key"]] = record
    meter = Meter(cap_usd)
    encoder = EncoderClassifier()
    encoder.fit(MeteredEmbedder(client, meter))
    cascade = CascadeClassifier(encoder=encoder, llm_client=MeteredChat(client, LABELER_LLM, meter))
    lock = threading.Lock()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    def label(text: str) -> None:
        key = _key(text)
        if key in cache:
            return
        result = cascade.predict(text)
        record = {"key": key, "type": result.type.value, "decided_by": result.decided_by}
        with lock:
            cache[key] = record
            with cache_path.open("a") as handle:
                handle.write(json.dumps(record) + "\n")

    texts = sorted({item.text for config in configs for item in config.kb.items})
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(label, texts))

    relabeled = []
    for config in configs:
        items = [
            KTItem(text=item.text, type=KTType(cache[_key(item.text)]["type"]), topic=item.topic)
            for item in config.kb.items
        ]
        relabeled.append(replace(config, kb=KTKnowledgeBase(items=items)))
    stages: dict[str, int] = {}
    for text in texts:
        stage = cache[_key(text)]["decided_by"]
        stages[stage] = stages.get(stage, 0) + 1
    return relabeled, LabelStats(stages, round(meter.spent, 4))
