"""Re-execution of the paper's LineTOM-Jev projector on cached Jev labels (same as final_analysis)."""

from common import HERE, JevView, cache

from tom.benchmarks.knowledge_triage_repro import _events_from_text
from tom.context import ContextProjector, ProjectionPolicy, Renderer
from tom.context.budget import UnsafeContextBudget
from tom.models import Importance, KnowledgeType, MemoryItem, RetentionPolicy

J = JevView(cache(HERE / "jevprobs.jsonl"))


def replay_tom_jev_lines(text: str, budget: int) -> str:
    mems = []
    for e in _events_from_text(text):
        row = J.row(e.content)
        kind = KnowledgeType(row["type"])
        ret = (RetentionPolicy.EXACT if kind == KnowledgeType.CONSTRAINT else
               RetentionPolicy.HIGH_FIDELITY if kind == KnowledgeType.PROCEDURE else
               RetentionPolicy.COMPRESSIBLE)
        mems.append(MemoryItem(id=e.id, content=e.content, knowledge_type=kind, retention=ret,
                               importance=Importance(row["importance"]), confidence=1.0,
                               source_ids=[e.id], created_at=e.timestamp, event_time=e.timestamp))
    projector = ContextProjector(Renderer(compact=True), policy=ProjectionPolicy.STANDARD)
    try:
        return projector.project(mems, budget).text
    except UnsafeContextBudget:
        pinned = [m for m in mems if m.retention in (RetentionPolicy.EXACT,
                                                     RetentionPolicy.HIGH_FIDELITY)]
        return projector.renderer.render(pinned)
