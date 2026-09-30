import csv
import json

from tom.benchmarks.harness import BenchmarkCase
from tom.benchmarks.locomo_eval import locomo_official_f1, rescore_saved


def _case(category: str, answer: object) -> BenchmarkCase:
    return BenchmarkCase("case", "", answer, (), category)


def test_official_categories_and_sentence_answers():
    assert locomo_official_f1(_case("1", "Paris, 2024"), "Paris, 2024") == 1
    assert locomo_official_f1(_case("2", "run tests"), "Running the tests") == 1
    assert locomo_official_f1(_case("3", "adopted; speculation"), "Adopted") == 1
    assert 0 < locomo_official_f1(_case("4", "Aragorn"), "John likes Aragorn") < 1
    assert locomo_official_f1(_case("5", None), "It was not mentioned") == 1
    assert locomo_official_f1(_case("5", None), "I don't know") == 0


def test_rescore_is_offline_and_keeps_original_rows(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    original = json.dumps({
        "dataset": "locomo", "case_id": "q1", "strategy": "tom_jev", "category": "5",
        "answer": None, "hypothesis": "not mentioned", "score": False,
        "comparison_valid": True,
    }) + "\n"
    (raw / "tom_jev.jsonl").write_text(original)
    (raw / "tom.jsonl").write_text(original.replace('"strategy": "tom_jev"',
                                                  '"strategy": "tom"').replace(
        '"hypothesis": "not mentioned"', '"hypothesis": "I do not know"'))
    path = rescore_saved(tmp_path)
    assert (raw / "tom_jev.jsonl").read_text() == original
    with path.open() as handle:
        assert {row["strategy"]: row["official_f1"] for row in csv.DictReader(handle)} == {
            "tom_jev": "1.0", "tom": "0.0",
        }
    summary = json.loads((tmp_path / "tables/locomo-official-summary.json").read_text())
    assert summary["jev_minus_tom"] == 1.0
    assert summary["history_bootstrap_95"] == [1.0, 1.0]
