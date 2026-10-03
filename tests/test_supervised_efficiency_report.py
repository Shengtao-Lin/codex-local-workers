import importlib.util
import json
import sys
from pathlib import Path

import pytest

BENCHMARKS = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCHMARKS))
SPEC = importlib.util.spec_from_file_location(
    "efficiency_report_test", BENCHMARKS / "supervised_efficiency_report.py"
)
assert SPEC and SPEC.loader
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def test_open_count_correction_does_not_overwrite_original(tmp_path):
    original = {"decision": "accept", "protected_test_files_opened": 1}
    path = tmp_path / "primary-observation.json"
    path.write_text(json.dumps(original))
    (tmp_path / "primary-observation-correction.json").write_text(
        json.dumps(
            {
                "supersedes_fields_in": "primary-observation.json",
                "protected_test_files_opened": 0,
                "protected_test_files_reviewed": 1,
            }
        )
    )
    assert REPORT.observation(tmp_path)["protected_test_files_opened"] == 0
    assert json.loads(path.read_text()) == original


def test_observation_correction_cannot_change_authority(tmp_path):
    (tmp_path / "primary-observation.json").write_text('{"decision":"rework"}')
    (tmp_path / "primary-observation-correction.json").write_text(
        '{"supersedes_fields_in":"primary-observation.json","decision":"accept"}'
    )
    with pytest.raises(ValueError, match="acceptance or risk"):
        REPORT.observation(tmp_path)


def test_missing_token_usage_is_unknown_not_zero():
    totals = REPORT.model_totals(
        {
            "coder": {
                "requests": 2,
                "requests_missing_token_usage": 0,
                "reported_total_tokens": 9,
            },
            "coordinator": {
                "requests": 1,
                "requests_missing_token_usage": 1,
                "reported_total_tokens": None,
            },
        }
    )
    assert totals == {
        "requests": 3,
        "requests_missing_token_usage": 1,
        "reported_total_tokens": None,
    }


def test_actual_paired_report_requires_matching_inputs_before_acceptance(tmp_path):
    pair = tmp_path / REPORT.PAIRS[0]
    pair.mkdir()
    (pair / "freeze.json").write_text("{}")
    for mode in ("control", "coordinator"):
        (pair / mode).mkdir()
        (pair / mode / "paired-inputs.json").write_text(json.dumps({"mode": mode}))
    with pytest.raises(ValueError, match="actual inputs differ"):
        REPORT.report(tmp_path)


@pytest.mark.parametrize("names", [("a", "a", "b"), ("../a", "b", "c"), ("a", "b")])
def test_pair_selection_rejects_duplicate_escape_or_wrong_count(tmp_path, names):
    with pytest.raises(ValueError, match="three distinct direct"):
        REPORT.report(tmp_path, names)


def test_explicit_pairs_do_not_relabel_historical_defaults(tmp_path):
    original = REPORT.PAIRS
    names = ("current-a", "current-b", "current-c")
    pair = tmp_path / names[0]
    pair.mkdir()
    (pair / "freeze.json").write_text("{}")
    for mode in ("control", "coordinator"):
        (pair / mode).mkdir()
        (pair / mode / "paired-inputs.json").write_text(json.dumps({"mode": mode}))
    with pytest.raises(ValueError, match="actual inputs differ"):
        REPORT.report(tmp_path, names)
    assert REPORT.PAIRS == original
