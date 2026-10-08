"""Protection and scope checks for the new formal matrix, without models."""

import importlib.util
import json
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "matrix_cases", KIT / "benchmarks/qualification_matrix_cases.py"
)
CASES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CASES)
TEMPLATE = json.loads(
    (KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(encoding="utf-8")
)["cases"][0]


def test_six_cases_keep_reference_outside_scope():
    data, oracles = CASES.corpus(TEMPLATE)
    assert len(data["cases"]) == 6
    assert len({c["case_id"] for c in data["cases"]}) == 6
    for case in data["cases"]:
        assert case["feature_risk"] == "medium"
        assert "reference" not in case
        assert len(oracles[case["case_id"]]["mutants"]) == 2
        for unit in case["units"]:
            assert unit["risk"] == "medium"
            assert all(p.startswith("src/") for p in unit["paths"])
            assert all(t.startswith("tests/") for t in unit["tests"])


def test_dependency_is_separate_owned_contract_and_readonly_entry():
    data, _ = CASES.corpus(TEMPLATE)
    chain = next(c for c in data["cases"] if c["case_id"] == "async-receipt")
    producer, consumer = chain["units"]
    assert consumer["dependencies"] == [producer["unit_id"]]
    assert not set(producer["paths"]) & set(consumer["paths"])
    assert not set(producer["tests"]) & set(consumer["tests"])
    assert "src/product/entry.py" not in producer["paths"] + consumer["paths"]
    assert "test_receipt_roundtrip" in chain["files"]["tests/test_target.py"]


def test_contract_has_none_vs_absence_and_return_vs_exception():
    data, _ = CASES.corpus(TEMPLATE)
    cases = {c["case_id"]: c for c in data["cases"]}
    assert "None" in cases["display-default"]["goal"]
    assert "key absent" in cases["display-default"]["goal"]
    assert "KeyError" in cases["lookup-fallback"]["goal"]
    assert "every other exception unchanged" in cases["lookup-fallback"]["goal"]


def test_corpus_does_not_mutate_template():
    before = json.dumps(TEMPLATE, sort_keys=True)
    CASES.corpus(TEMPLATE)
    assert json.dumps(TEMPLATE, sort_keys=True) == before
