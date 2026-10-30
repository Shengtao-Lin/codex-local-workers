"""Post-live preservation and exposed regressions, not additional live credit."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_dto as D

B = D.B


def test_frozen_candidate_and_every_input_unchanged():
    seal = B.read(D.BATCH / "live-freeze.json")
    assert B.sha(D.ADAPTER) == seal["adapter"]
    assert B.sha(B.KIT / "benchmarks/harness_r4_dto.py") == seal["driver"]
    assert B.sha(D.BATCH / "registration.json") == seal["registration"]
    assert (
        B.sha(B.KIT / "tests/test_reviewer_compact_dto.py") == seal["controls_source"]
    )
    D.R.assert_files(D.BATCH / "runtime", seal["runtime"])
    baseline = B.read(D.BATCH / "baseline.json")
    D.R.assert_files(B.KIT, baseline["frozen_runtime"])
    D.R.assert_files(D.OLD.H.BATCH, baseline["previous_stage"])
    for row in B.read(D.BATCH / "registration.json")["cells"]:
        D.R.assert_files(Path(row["root"]), row["files"])


def test_completion_indexes_are_new_not_prefilled():
    for row in B.read(D.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        cell = root.parent
        index = root / ".agent/current-task.json"
        assert ".agent/current-task.json" not in row["files"]
        report = B.read(cell / "reviewer.json")
        if report["decision"] == "failed":
            assert not index.exists()
            continue
        state = B.read(index)
        assert state["latest_review_id"] == row["identity"]["review_id"]
        assert state["usage"] == {"reviewer_calls": 1}
        assert len(state["recent_attempts"]) == 1
        assert state["recent_attempts"][0]["result"] == report["decision"]
        assert (
            datetime.fromisoformat(state["updated_at"]).timestamp()
            >= B.read(cell / "started.json")["at"]
        )


def test_no_primary_answer_leakage():
    for row in B.read(D.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        assert not (root / "primary-adjudications.json").exists()
        for path in (root.parent / "wire").glob("*-request.json"):
            messages = B.read(path).get("body", {}).get("messages", [])
            text = json.dumps([m for m in messages if m.get("role") != "assistant"])
            for token in (
                "expected_decision",
                "expected_defect_primary_only",
                "primary-adjudications.json",
                ".agent/current-task.json",
            ):
                assert token not in text


def test_fixed_denominator_and_failed_loop_are_retained():
    rows = B.read(D.BATCH / "primary-adjudications.json")
    assert len(rows) == 16 and sum(row["correct"] for row in rows) == 15
    assert [row["id"] for row in rows if not row["correct"]] == ["required-coverage-r1"]
    audit = B.read(D.BATCH / "failure-observation-audit.json")
    assert audit["report_attempts"] == 0
    assert audit["test"]["lines"] == 5
    assert not audit["eof_exposed_by_read"] and not audit["total_lines_exposed_by_read"]
    actions = [a["action"] for call in audit["actions"] for a in call["actions"]]
    assert actions.count("READ_FILE") == 6 and actions.count("non_json") == 1


@pytest.mark.parametrize("arm", ["reference", "candidate"])
def test_exposed_none_semantic_counterexample_still_reproduces(tmp_path, arm):
    old = D.OLD.H.BATCH
    root = (
        old / "prepared-fixtures/collect_tools/private-reference"
        if arm == "reference"
        else old / "cases/collect_tools-candidate-1/isolated"
    )
    source = root / "src/evaluation_harness/adapters/common.py"
    prior = B.read(old / f"{arm}-falsy-probe.json")
    assert B.sha(source) == prior["source_sha256"]
    output = tmp_path / f"{arm}-probe.json"
    process = subprocess.run(
        [
            "F:/ChatGPT/agent-evaluation-harness/.venv/Scripts/python.exe",
            "-B",
            str(B.KIT / "benchmarks/harness_r4_falsy_probe.py"),
            "--root",
            str(root),
            "--output",
            str(output),
        ],
        cwd=B.KIT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    result = B.read(output)

    # The archived candidate calls datetime.now for these two fields. Preserve
    # timestamp presence/type, but compare semantics rather than wall-clock value.
    def stable_observation(value):
        normalized = json.loads(json.dumps(value))
        for row in normalized["rows"]:
            for call in row["observed"]:
                for field in ("started_at", "ended_at"):
                    if call[field] is not None:
                        datetime.fromisoformat(call[field])
                        call[field] = "<valid runtime timestamp>"
        return normalized

    assert stable_observation(result) == stable_observation(prior)
    assert B.sha(source) == prior["source_sha256"]
    bad = [
        row for row in result["rows"] if not row["satisfies_explicit_falsy_contract"]
    ]
    if arm == "reference":
        assert not bad
    else:
        # This is a successful detection of the old failure, never a task PASS.
        assert len(bad) == 1 and bad[0]["input_result"] is None
        assert bad[0]["observed"][0]["status"] == "requested"
    assert all(row["input_unchanged"] for row in result["rows"])


def test_old_r4_remains_hold_not_rehabilitated():
    decision = B.read(D.OLD.H.BATCH / "decision.json")
    assert decision["qualification"] == "HOLD"
    assert not decision["r5_admitted"] and not decision["product_default_enabled"]
    old = B.read(D.OLD.BATCH / "grid-results.json")
    assert (
        len(old) == 16
        and sum(row["primary_adjudication"]["correct"] for row in old) == 15
    )
