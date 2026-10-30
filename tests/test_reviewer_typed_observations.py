"""Exact event presence, outputs and source binding; no semantic answer added."""

import copy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_typed_observations as D
import reviewer_observation_accounting as OLD
import reviewer_typed_observations as A
import test_reviewer_semantic_entry as S


def runtime(row, adapter, suffix):
    root = Path(row["root"])
    module = D.R.load(root / ".local-agents/reviewer-runtime.py", "typed_" + suffix)
    return adapter.install(module)(
        root,
        {**row["identity"], "review_id": "offline-" + suffix},
        D.B.read(root / ".agent/experiment-config.json"),
        S.Client(module),
    ), module


def test_all_twenty_preserve_task_and_restore_actual_typed_input_before_live():
    real = 0
    for row in D.B.read(D.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        assert not (root / ".agent/current-task.json").exists()
        assert row["identity"]["review_id"].startswith("typed-v1-")
        D.R.assert_files(root, row["files"])
        before, _ = runtime(row, OLD, "old-" + row["id"])
        after, _ = runtime(row, A, "new-" + row["id"])
        original, changed = before.bundle(), after.bundle()
        if row["group"] == "original-sixteen":
            assert original == changed and after.typed_input_provenance == []
        else:
            real += 1
            old = original["approved_observations"][0]
            new = changed["approved_observations"][0]
            seal = A.REAL.OBS.B.read(A.REAL.SEAL)
            source = next(
                s
                for s in seal["sources"]
                if s["source_manifest"]
                == after.observation_provenance["source_manifest"]
            )
            request = A.REAL.OBS.B.read(Path(source["request"]))
            for i, example in enumerate(new["examples"]):
                assert example["input"] == request["cases"][i]
                assert example["input"]["parts"][1]["type"] == "tool_result"
                assert len(example["input"]["parts"]) == 2
                assert example["outcome"] == old["examples"][i]["outcome"]
                assert "expected" not in example and "verdict" not in example
            assert new["examples"][0]["input"]["parts"][1]["result"] is None
            restored = copy.deepcopy(new)
            restored["shared_setup"] = old["shared_setup"]
            for example in restored["examples"]:
                example["result_input"] = example.pop("input")["parts"][1]["result"]
            assert restored == old
            original.pop("approved_observations")
            changed.pop("approved_observations")
            assert original == changed
        assert after.expected_observations == before.expected_observations
    assert real == 4


@pytest.mark.parametrize("change", ["request", "projection", "outcome"])
def test_mutated_inputs_or_projection_rejected(change):
    row = D.B.read(D.BATCH / "registration.json")["cells"][16]
    target, module = runtime(row, A, "drift-" + change)
    profiles = super(type(target), target).bundle()["approved_observations"]
    if change == "request":
        seal = A.REAL.OBS.B.read(A.REAL.SEAL)
        path = Path(seal["sources"][0]["request"])
        sha = A.REAL.OBS.B.sha
        with (
            patch.object(
                A.REAL.OBS.B,
                "sha",
                side_effect=lambda p: "0" * 64 if Path(p) == path else sha(p),
            ),
            pytest.raises(module.ReviewError),
        ):
            A.restore(target, profiles, module.ReviewError)
    else:
        example = profiles[0]["examples"][0]
        if change == "projection":
            example["result_input"] = "changed"
        else:
            example["outcome"] = {"kind": "returned", "value": []}
        with pytest.raises(module.ReviewError):
            A.restore(target, profiles, module.ReviewError)
