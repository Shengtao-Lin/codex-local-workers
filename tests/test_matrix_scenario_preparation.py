"""Explicit Primary scenarios must reach both packet and authoritative plan."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import mixed_feature_benchmark as MIXED  # noqa: E402
import qualification_matrix_cases as CASES  # noqa: E402


def test_explicit_scenarios_survive_preparation(tmp_path, monkeypatch):
    template = json.loads(
        (MIXED.KIT / "benchmarks/fixtures/mixed-features-v1.json").read_text(
            encoding="utf-8"
        )
    )["cases"][0]
    data, _ = CASES.corpus(template)
    case = data["cases"][0]
    scenarios = [
        {
            "id": "present-none",
            "text": "A present name=None is returned as None, not the absence default.",
            "observables": {"input": {"name": None}, "return_value": None},
        },
        {
            "id": "absent",
            "text": "A missing name defaults to unnamed.",
            "observables": {"input": {}, "return_value": "unnamed"},
        },
    ]
    case["units"][0]["acceptance_scenarios"] = scenarios
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
    monkeypatch.setattr(MIXED, "CORPUS", path)
    monkeypatch.setattr(MIXED, "WORK", tmp_path / "runs")
    prepared = MIXED.prepare(
        case["case_id"],
        1,
        MIXED.KIT / ".local-agents/config.json",
        "scenario-preflight",
    )
    root = Path(prepared["root"])
    packet = json.loads(
        (root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
    )
    plan = json.loads((root / ".agent/feature-plan.json").read_text(encoding="utf-8"))
    assert packet["acceptance_scenarios"] == scenarios
    assert plan["units"][0]["packet_contract"]["acceptance_scenarios"] == scenarios
    assert packet["scope"]["modify"] == ["src/product/target.py"]
    assert packet["focused_tests"] == ["tests/test_target.py"]
