"""Free diagnostic: TOM pipeline fed the cascade (ground-truth) labels instead of LLM/Jev labels."""
import asyncio, json, statistics as st, math
from pathlib import Path
from openai import OpenAI
from knowledge_triage.classifier import KnowledgeType as K
from tom.benchmarks.knowledge_triage_repro import (TypedTOMCompactor, load_configs, per_type_preservation,
                                                   truncate_to_tokens, _events_from_text)
from tom.benchmarks.kt_cascade import cascade_relabel
from tom.context import ContextProjector, ProjectionPolicy, Renderer
from tom.context.budget import UnsafeContextBudget
from tom.observer.deterministic_observer import DeterministicObserver, _TYPE_MAP

class OracleObserver(DeterministicObserver):
    def __init__(self, labels): super().__init__(); self.labels = labels
    def _classify(self, event):
        import tom.observer.deterministic_observer as d
        orig = d.classify_instruction
        d.classify_instruction = lambda text: self.labels.get(text.strip(), K.BELIEF)
        try: return super()._classify(event)
        finally: d.classify_instruction = orig

async def run(cfgs, policy, ratio):
    proj = ContextProjector(Renderer(compact=True), policy=policy); out = []
    for c in cfgs:
        labels = {i.text.strip(): i.type for i in c.kb.items}
        b = max(64, int(c.kb.total_tokens * ratio)); m = TypedTOMCompactor(OracleObserver(labels), proj)
        await m.ingest("x", _events_from_text(c.text)); await m.compact("x", b)
        try: t = await m.context("x", "", b)
        except UnsafeContextBudget: t = m.unsafe_protected_text("x")
        out.append(per_type_preservation(c.kb, truncate_to_tokens(t, b)))
    return out

cfgs, _ = cascade_relabel(load_configs('data/aac/sample', n_configs=50, seed=11), Path('results/kt-faithful/cascade-labels.jsonl'), OpenAI(), cap_usd=0.05)
for name, pol in (("oracle TOM protege-tudo", ProjectionPolicy.PAPER), ("oracle TOM com orcamento", ProjectionPolicy.STANDARD)):
    for r in (0.5, 0.25, 0.1):
        res = asyncio.run(run(cfgs, pol, r))
        f = lambda k: round(st.mean(x[k] for x in res if not math.isnan(x[k])), 3)
        print(name, r, 'constraint', f('constraint'), 'procedural', f('procedural'))
