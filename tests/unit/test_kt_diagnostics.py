import json
from pathlib import Path

import pytest

from tom.benchmarks.knowledge_triage_repro import load_configs
from tom.benchmarks.kt_cascade import _key
from tom.benchmarks.kt_diagnostics import analyze
from tom.context import Renderer
from tom.models import Importance, KnowledgeType, MemoryItem, RetentionPolicy
from tom.observer.tokenizer import count_tokens


@pytest.mark.skipif(not Path("data/aac/sample").exists(), reason="AAC sample not installed")
def test_agreement_and_unsafe_fallback_are_auditable(tmp_path):
    cfg = load_configs("data/aac/sample", n_configs=1, seed=11)[0]
    cascade, jev = tmp_path / "cascade.jsonl", tmp_path / "jev.jsonl"
    lines = list(dict.fromkeys(i.text for i in cfg.kb.items))
    with cascade.open("w") as gt, jev.open("w") as pred:
        for n, line in enumerate(lines):
            gt.write(
                json.dumps(
                    {
                        "key": _key(line),
                        "type": "constraint" if n == 0 else "procedural" if n == 2 else "belief",
                        "decided_by": "llm",
                    }
                )
                + "\n"
            )
            pred.write(
                json.dumps(
                    {
                        "key": _key(line),
                        "type": "constraint" if n < 2 else "procedure" if n == 2 else "belief",
                        "importance": "critical",
                    }
                )
                + "\n"
            )
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC)
    memories = [
        MemoryItem(
            id=str(n),
            content=line,
            knowledge_type=KnowledgeType.PROCEDURE if n == 2 else KnowledgeType.CONSTRAINT,
            retention=RetentionPolicy.HIGH_FIDELITY if n == 2 else RetentionPolicy.EXACT,
            importance=Importance.CRITICAL,
            confidence=1,
            source_ids=[str(n)],
            created_at=timestamp,
        )
        for n, line in enumerate(lines[:3])
    ]
    fallback = Renderer(compact=True).render(memories)
    root = tmp_path / "benchmark" / "curves"
    root.mkdir(parents=True)
    budget = max(1, count_tokens(Renderer(compact=True).render(memories[:2])) - 1)
    (root / f"tom_jev_lines--0.1--{cfg.label}.json").write_text(
        json.dumps(
            {"budget": budget, "raw_chars": len(fallback), "output_text": fallback[: budget * 4]}
        )
    )
    result = analyze([cfg], cascade, jev, root.parent)
    assert result["per_type"]["constraint"]["recall"] == 1
    assert result["per_type"]["constraint"]["precision"] < 1
    assert result["per_type"]["procedural"]["recall"] == 1
    assert result["agreement"] > 0.9
    assert result["budget_audit"]["exact_exceeds_budget"] == 1
    assert result["budget_audit"]["fallback_matches_raw_chars"] == 1
