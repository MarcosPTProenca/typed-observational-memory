"""TypeSafe/Jev System One classifier as a label provider for TOM.

Jev does not generate text; it evaluates a ``state`` against typed questions and
returns calibrated answers (Choice/Score/Noul). We use it as a complement to the
generative observer: the LLM extracts ``content``/``topic``/``source_ids`` and Jev
assigns the discrete labels (``knowledge_type``/``retention``/``importance``/
``confidence``) in a single parallel request via the official ``typesafe_sdk``.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from tom.metrics import CostRates
from tom.models import Importance, KnowledgeType, RetentionPolicy

# Published TypeSafe pricing: $0.042 per million input tokens, output free.
JEV_COST_RATES = CostRates(input_per_million=0.042, output_per_million=0.0)

_KNOWLEDGE_TYPE_CRITERIA = {
    KnowledgeType.CONSTRAINT: "A rule, requirement, prohibition, or limit on future actions.",
    KnowledgeType.PROCEDURE: "A sequence of steps or instructions for how to do something.",
    KnowledgeType.BELIEF: "A factual claim about the world the agent should hold as true.",
    KnowledgeType.PREFERENCE: "A user or system preference about how things should be done.",
    KnowledgeType.EPISODIC: "A record of a specific event or interaction that occurred.",
}

_RETENTION_CRITERIA = {
    RetentionPolicy.EXACT: (
        "The exact wording carries binding meaning that paraphrasing would corrupt: "
        "rules, prohibitions, approvals, credentials, identifiers, version numbers, "
        "file paths, commands, or any constraint whose violation has real consequences."
    ),
    RetentionPolicy.HIGH_FIDELITY: (
        "Meaning must be preserved accurately but the exact words do not matter; "
        "minor rewording is safe. Facts and procedures with no binding wording."
    ),
    RetentionPolicy.COMPRESSIBLE: "Can be summarized or shortened without losing anything essential.",
    RetentionPolicy.DISCARDABLE: "Low value chit-chat or context; safe to drop entirely.",
}

_IMPORTANCE_CRITERIA = {
    Importance.CRITICAL: "Loss would materially break or misdirect future behavior.",
    Importance.HIGH: "Strongly affects future behavior or decisions.",
    Importance.MEDIUM: "Moderately useful for future behavior.",
    Importance.LOW: "Marginally useful; rarely needed.",
}

_CONFIDENCE_INSTRUCTIONS = (
    "The information reads as a definite, unconditional statement rather than a "
    "hedged, uncertain, or speculative one (no 'maybe', 'might', 'I think', 'possibly')."
)

SAFETY_GATE_INSTRUCTIONS = (
    "Losing this information would materially alter or break the agent's future "
    "behavior (for example a constraint, approval, prohibition, security requirement, "
    "or critical current state)."
)


class ItemLabels(BaseModel):
    knowledge_type: KnowledgeType
    retention: RetentionPolicy
    importance: Importance
    confidence: float
    # Full Choice distribution over knowledge types; empty when the provider omits it.
    type_probabilities: dict[str, float] = Field(default_factory=dict)


class _Client(Protocol):
    async def system_one(self, *, state: Any, questions: dict[str, Any]) -> Any: ...


class JevClassifier:
    """Wraps the official ``typesafe_sdk.AsyncTypeSafeClient`` for label classification.

    ``client`` is injectable so tests can pass a fake exposing ``system_one``; when
    omitted an ``AsyncTypeSafeClient`` is created lazily (it reads ``TYPESAFE_API_KEY``)
    and entered on first use. Call :meth:`aclose` to release an owned client.
    """

    def __init__(self, client: _Client | None = None, *, cost_rates: CostRates | None = None) -> None:
        self._client: Any = client
        self._owns_client = client is None
        self._entered = False
        self.cost_rates = cost_rates or JEV_COST_RATES
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_calls = 0
        self.model: str | None = None

    async def classify_labels(self, content: str) -> ItemLabels:
        from typesafe_sdk import Choice, Noul  # type: ignore[import-not-found]

        questions = {
            "knowledge_type": Choice(
                instructions="What kind of knowledge does this information represent?",
                criteria={k.value: v for k, v in _KNOWLEDGE_TYPE_CRITERIA.items()},
            ),
            "retention": Choice(
                instructions="How faithfully must this information be retained?",
                criteria={k.value: v for k, v in _RETENTION_CRITERIA.items()},
            ),
            "importance": Choice(
                instructions="How important is this information for future behavior?",
                criteria={k.value: v for k, v in _IMPORTANCE_CRITERIA.items()},
            ),
            "confidence": Noul(instructions=_CONFIDENCE_INSTRUCTIONS),
        }
        response = await self._invoke(content, questions)
        return ItemLabels(
            knowledge_type=KnowledgeType(response.choices["knowledge_type"].choice),
            retention=RetentionPolicy(response.choices["retention"].choice),
            importance=Importance(response.choices["importance"].choice),
            confidence=float(response.nouls["confidence"].noul),
            type_probabilities=_probabilities(response.choices["knowledge_type"]),
        )

    async def type_distribution(self, content: str) -> dict[str, float]:
        """One knowledge-type Choice only: ~30% fewer input tokens than ``classify_labels``."""
        from typesafe_sdk import Choice  # type: ignore[import-not-found]

        question = Choice(
            instructions="What kind of knowledge does this information represent?",
            criteria={k.value: v for k, v in _KNOWLEDGE_TYPE_CRITERIA.items()},
        )
        answer = (await self._invoke(content, {"knowledge_type": question})).choices[
            "knowledge_type"
        ]
        return _probabilities(answer) or {answer.choice: 1.0}

    async def confirm_critical(self, content: str, *, instructions: str = SAFETY_GATE_INSTRUCTIONS) -> float:
        from typesafe_sdk import Noul  # type: ignore[import-not-found]

        response = await self._invoke(content, {"gate": Noul(instructions=instructions)})
        return float(response.nouls["gate"].noul)

    async def _invoke(self, state: Any, questions: dict[str, Any]) -> Any:
        client = await self._get_client()
        response = await client.system_one(state=state, questions=questions)
        self._record(state, response)
        return response

    async def _get_client(self) -> Any:
        if self._client is None:
            from typesafe_sdk import AsyncTypeSafeClient  # type: ignore[import-not-found]

            self._client = AsyncTypeSafeClient()
        if self._owns_client and not self._entered:
            await self._client.__aenter__()
            self._entered = True
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._entered and self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._entered = False

    def _record(self, state: Any, response: Any) -> None:
        from tom.observer.tokenizer import count_tokens

        usage = getattr(response, "usage", None)
        input_tokens = usage.get("input_tokens") if isinstance(usage, dict) else getattr(usage, "input_tokens", None)
        output_tokens = usage.get("output_tokens") if isinstance(usage, dict) else getattr(usage, "output_tokens", None)
        self.last_input_tokens += input_tokens if input_tokens is not None else count_tokens(
            state if isinstance(state, str) else str(state)
        )
        self.last_output_tokens += output_tokens or 0
        self.model = getattr(response, "model", self.model)
        self.last_calls += 1

    def reset_metrics(self) -> None:
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_calls = 0


def _probabilities(answer: Any) -> dict[str, float]:
    return {str(k): float(v) for k, v in (getattr(answer, "probabilities", None) or {}).items()}
