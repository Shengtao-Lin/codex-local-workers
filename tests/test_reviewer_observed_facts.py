"""Exact-version facts, no oracle, unchanged task inputs and no new tools."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_observed_facts as D
import reviewer_observed_facts as A
import reviewer_semantic_entry as V1
import reviewer_semantic_policy as OLD
import test_reviewer_semantic_entry as S


def create(row, suffix, adapter):
    root = Path(row["root"])
    module = D.R.load(
        root / ".local-agents/reviewer-runtime.py", "facts_control_" + suffix
    )
    runtime = adapter.install(module)(
        root,
        {**row["identity"], "review_id": "offline-" + suffix},
        D.B.read(root / ".agent/experiment-config.json"),
        S.Client(module),
    )
    return runtime, module


def test_all_twenty_only_gain_same_version_observations():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert len(rows) == 20
    with_facts = 0
    for row in rows:
        root = Path(row["root"])
        D.R.assert_files(root, row["files"])
        D.R.assert_files(Path(row["origin"]), row["origin_files"])
        assert row["identity"]["review_id"].startswith("facts-v1-")
        assert not (root / ".agent/current-task.json").exists()
        before, _ = create(row, row["id"] + "-old", OLD)
        after, _ = create(row, row["id"] + "-new", A)
        initial, changed = before.bundle(), after.bundle()
        facts = changed.pop("approved_observations")
        assert initial == changed
        assert before.client.native_tools == after.client.native_tools
        assert after.max_turns == 16 and after.max_protocol_errors == 4
        if row["group"] == "original-sixteen":
            assert facts == [] and after.observation_provenance is None
        else:
            with_facts += 1
            assert len(facts) == 1 and len(facts[0]["examples"]) == 6
            assert facts[0]["source"]["sha256"] == D.B.sha(root / A.OBS.TARGET)
            assert after.observation_provenance["cached"]
            for example in facts[0]["examples"]:
                assert set(example) == {"input", "outcome", "input_unchanged"}
                assert example["input_unchanged"] is True
                assert "expected" not in example and "verdict" not in example
            values = [e["input"]["parts"][1]["result"] for e in facts[0]["examples"]]
            assert [type(v) for v in values] == [type(None), bool, int, str, list, dict]
        D.R.assert_files(root, row["files"])
    assert with_facts == 4


@pytest.mark.parametrize("change", ["artifact", "target", "dependency"])
def test_stale_or_unmatched_fact_versions_fail_closed(change):
    row = next(
        r
        for r in D.B.read(D.BATCH / "registration.json")["cells"]
        if r["group"] == "exposed-real"
    )
    runtime, module = create(row, "negative-" + change, A)
    original_sha = A.OBS.B.sha
    seal = A.OBS.B.read(A.SEAL)
    path = (
        Path(seal["sources"][0]["observation"])
        if change == "artifact"
        else runtime.repo_root
        / (
            A.OBS.TARGET
            if change == "target"
            else "src/evaluation_harness/canonical/models.py"
        )
    )

    def sha(candidate):
        return "0" * 64 if Path(candidate) == path else original_sha(candidate)

    with patch.object(A.OBS.B, "sha", sha), pytest.raises(module.ReviewError):
        runtime.bundle()


def test_model_keeps_report_only_and_observations_are_not_auto_acceptance(tmp_path):
    request = S.H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(D.E.D.BATCH / "runtime/reviewer-runtime.py", "facts_fullrun")
    client = S.Client(
        module, [{"action": "REPORT", "arguments": S.judgment("contract_conflict")}]
    )
    client.temperature = 1
    runtime = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
            "reviewer_temperature": 1,
        },
        client,
    )
    report = runtime.run()
    assert report["decision"] == "escalate"
    assert report["approved_observation_protocol"] == A.PROTOCOL
    assert report["approved_observation_provenance"] is None
    assert client.native_tools == V1.TOOLS
    assert json.loads(client.messages[0][1]["content"])["approved_observations"] == []
    assert client.messages[0][0]["content"] == V1.SYSTEM
