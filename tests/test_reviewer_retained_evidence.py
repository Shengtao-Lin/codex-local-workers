import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reviewer_retained_evidence_adapter import install
from test_reviewer_staged_assessment_adapter import fixture_runtime


def request(path="src/example.py", start=1, end=3):
    return {"path": path, "start_line": start, "end_line": end}


def test_retained_actual_reads_survive_visibility_trimming_and_detect_drift(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.config["reviewer_provided_read_evidence"] = [request()]
    payload = runtime.initial_payload()
    evidence = payload["provided_read_evidence"]
    assert evidence[0]["path"] == "src/example.py"
    assert evidence[0]["content"]
    assert runtime.observed_read_hashes["src/example.py"]
    assert (runtime.review_root / "provided-read-evidence.json").is_file()
    runtime._update_active_read_context(
        [
            {"role": "system", "content": "instructions"},
            {"role": "user", "content": "LOCAL_REVIEW_INPUT\n" + json.dumps(payload)},
        ]
    )
    assert (
        runtime.active_read_lines["src/example.py"]
        == runtime.read_lines["src/example.py"]
    )
    assert runtime.initial_payload()["provided_read_evidence"] == evidence
    (tmp_path / "src/example.py").write_text("changed = True\n", encoding="utf-8")
    with pytest.raises(reviewer.ReviewError, match="changed"):
        runtime.initial_payload()


@pytest.mark.parametrize(
    "requests",
    [
        [request(start=True)],
        [request(end=161)],
        [request(path="outside.py")],
        [request(), request(path="outside.py")],
        [request()] * 7,
        {"path": "src/example.py"},
    ],
)
def test_invalid_provided_reads_abort_before_model_or_ledger(tmp_path, requests):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.config["reviewer_provided_read_evidence"] = requests
    with pytest.raises(reviewer.ReviewError):
        runtime.initial_payload()
    assert not runtime.read_paths
    assert not hasattr(runtime, "provided_read_evidence")
    assert not (runtime.review_root / "provided-read-evidence.json").exists()


def test_aggregate_budget_aborts_startup_without_publishing_evidence(tmp_path):
    reviewer, runtime = fixture_runtime(tmp_path, install_adapter=install)
    runtime.config["reviewer_provided_read_evidence"] = [request()]
    runtime.max_output = 60
    with pytest.raises(reviewer.ReviewError, match="fully displayed|aggregate"):
        runtime.initial_payload()
    assert not hasattr(runtime, "provided_read_evidence")
    assert not (runtime.review_root / "provided-read-evidence.json").exists()


def test_default_profile_has_no_provided_reads_or_artifact(tmp_path):
    _, runtime = fixture_runtime(tmp_path, install_adapter=install)
    assert "provided_read_evidence" not in runtime.initial_payload()
    assert not runtime.read_paths
    assert not (runtime.review_root / "provided-read-evidence.json").exists()
