"""Offline qualification of diagnostics: not model capability scores."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
import layer_isolation as layer  # noqa: E402 -- repository benchmark import
from layer_isolation_cases import corpus  # noqa: E402


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"files": []},
        {"files": [{"path": "../escape", "content": "x"}]},
        {"files": [{"path": "a", "content": "x"}, {"path": "a", "content": "y"}]},
        {"files": [{"path": "a", "content": 3}]},
        {"files": [{"path": "a", "content": "x", "extra": True}]},
    ],
)
def test_patch_rejects_all_before_writes(value):
    with pytest.raises(ValueError):
        layer.parse_patch(json.dumps(value), ["a"])


def test_complete_patch_and_hash_guard(tmp_path):
    patch = [{"path": "a", "content": "x"}]
    assert layer.parse_patch(json.dumps({"files": patch}), ["a"]) == patch
    (tmp_path / "a").write_text("x")
    with pytest.raises(ValueError, match="drift"):
        layer.verify_hashes(tmp_path, {"a": "bad"})


def test_corpus_has_eight_families_and_protected_oracles():
    template = json.loads(
        (ROOT / "benchmarks/fixtures/mixed-features-v1.json").read_text()
    )["cases"][0]
    data, oracles = corpus(template)
    assert len(data["cases"]) == len(oracles) == 8
    assert sum(c["exposure"] == "known-semantic-family" for c in data["cases"]) == 2
    for case in data["cases"]:
        unit = case["units"][0]
        assert unit["risk"] == "medium"
        assert "tests/test_target.py" not in unit["paths"]
        assert set(oracles[case["case_id"]]["reference"]) == set(unit["paths"])
        assert "reference" not in case


def test_incomplete_never_promotes(monkeypatch, tmp_path):
    monkeypatch.setattr(layer, "BASE", tmp_path)
    cells = [{"id": f"c{i}-r{r}", "case": f"c{i}"} for r in (1, 2) for i in range(8)]
    for c in cells[:-1]:
        layer.write(
            tmp_path / (c["id"] + "-result.json"),
            {
                "case": c["case"],
                "format_pass": True,
                "semantic_pass": True,
                "static_pass": False,
            },
        )
    summary = layer.decision({"cells": cells})
    assert summary["decision"] == "incomplete"
    assert summary["semantic_pass"] == 15
    assert summary["static_pass"] == 0
    assert summary["coordinator_released"] is False


def test_output_audit_removes_only_complete_fence():
    from layer_output_audit import unwrap_fence

    assert unwrap_fence('```json\n{"files": []}\n```') == ('{"files": []}', True)
    assert unwrap_fence("text\n```json\n{}\n```")[1] is False
    with pytest.raises(ValueError, match="nested"):
        unwrap_fence("```json\n```\n{}\n```")
    raw, removed = unwrap_fence('```json\n{"files": invalid}\n```')
    assert removed is True
    with pytest.raises(ValueError):
        layer.parse_patch(raw, ["a"])


def test_independent_encoding_assertion_rejects_roundtrip_only_mutant():
    from layer_output_audit import BOUNDARY_TEST

    assert '"a%2Bb"' in BOUNDARY_TEST
    from urllib.parse import quote, unquote

    # Reversible encoding alone cannot establish the contract's exact format.
    assert unquote(quote("a+b", safe="+")) == "a+b"
    assert quote("a+b", safe="+") != "a%2Bb"
    assert quote("a+b", safe="") == "a%2Bb"


def test_future_fixture_reference_and_near_correct_mutant(tmp_path):
    from layer_isolation_followup import strengthened_corpus

    template = json.loads(
        (ROOT / "benchmarks/fixtures/mixed-features-v1.json").read_text()
    )["cases"][0]
    original, _ = corpus(template)
    data, oracles = strengthened_corpus(template)
    assert sum(c["exposure"] == "known-semantic-family" for c in data["cases"]) == 3
    old = next(c for c in original["cases"] if c["case_id"] == "encoded-path")
    case = next(c for c in data["cases"] if c["case_id"] == "encoded-path")
    assert "test_canonical_encoding" not in old["files"]["tests/test_target.py"]
    assert len(oracles["encoded-path"]["mutants"]) == 2
    for relative, text in case["files"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / ".agent").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["src"]\n'
        '[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
        encoding="utf-8",
    )
    for index, source in enumerate(
        [
            oracles["encoded-path"]["reference"],
            oracles["encoded-path"]["mutants"][-1],
        ]
    ):
        for relative, text in source.items():
            (tmp_path / relative).write_text(text, encoding="utf-8")
        result = layer.check(tmp_path, f"oracle-{index}")
        assert result["semantic_pass"] is (index == 0)
