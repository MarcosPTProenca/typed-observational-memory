import asyncio

import pytest

from tom.benchmarks.kt_cascade import Meter
from tom.benchmarks.kt_faithful import jev_budget_compactor
from tom.context.budgeted import select_lines
from tom.providers.jev import JevClassifier


class _Answer:
    def __init__(self, **fields: object) -> None:
        self.__dict__.update(fields)


class _Response:
    def __init__(self, choices) -> None:
        self.choices = choices
        self.usage = {"input_tokens": 100, "output_tokens": 0}


class TypeClient:
    """Constraint probability grows with the number of 'never' in the line."""

    async def system_one(self, *, state, questions):
        pc = min(1.0, 0.3 * state.lower().count("never"))
        top = "constraint" if pc >= 0.5 else "belief"
        return _Response({"knowledge_type": _Answer(
            choice=top, probabilities={"constraint": pc, "belief": 1 - pc})})


def dist(top: str, pc: float) -> dict[str, float]:
    return {top: max(pc, 1 - pc), "constraint": pc} if top != "constraint" else {"constraint": pc}


def test_select_lines_always_fits_and_keeps_document_order() -> None:
    lines = ["intro text here", "never push to main", "run make test", "never never leak keys"]
    dists = [dist("belief", 0.1), dist("constraint", 0.7), dist("procedure", 0.2),
             dist("constraint", 0.9)]
    for budget in (0, 10, 25, 45, 1000):
        out = select_lines(lines, dists, budget)
        assert len(out) <= budget
        kept = out.split("\n") if out else []
        assert kept == [line for line in lines if line in kept]
    # the higher-probability constraint wins when only one fits
    assert select_lines(lines, dists, 22) == "never never leak keys"
    # constraints, then procedures, before beliefs
    assert select_lines(lines, dists, 55) == "never push to main\nrun make test\nnever never leak keys"


def test_select_lines_rejects_misaligned_inputs() -> None:
    with pytest.raises(ValueError):
        select_lines(["a"], [], 10)


@pytest.mark.asyncio
async def test_type_distribution_returns_choice_probabilities() -> None:
    jev = JevClassifier(client=TypeClient())
    assert await jev.type_distribution("never never do it") == {"constraint": 0.6,
                                                                 "belief": 0.4}
    assert jev.last_calls == 1 and jev.last_input_tokens == 100


def test_jev_budget_compactor_is_valid_and_metered(monkeypatch) -> None:
    import tom.benchmarks.kt_faithful as kf

    monkeypatch.setattr(kf, "JevClassifier", lambda client=None: JevClassifier(TypeClient()))
    meter = Meter(1.0)
    text = "background paragraph about the project\nnever never commit secrets\nmore prose"
    out, cost = asyncio.run(jev_budget_compactor(meter)(text, 8))
    assert out == "never never commit secrets" and len(out) <= 32
    assert cost == pytest.approx(3 * 100 * kf.JEV_PER_MILLION / 1e6) and meter.spent == cost
