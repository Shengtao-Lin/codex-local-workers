"""Original semantic control identity and current Reviewer integration checks."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r4_reviewer as H


def test_exact_original_sixteen_controls_and_verdicts():
    registry = H.B.read(H.BATCH / "registration.json")
    original = H.B.read(H.H.REVIEWER_REGISTRATION)
    adjudicated = H.B.read(
        H.H.REVIEWER_REGISTRATION.parent / "primary-adjudications-1.json"
    )
    assert [row["id"] for row in registry["cells"]] == [
        row["id"] for row in original["cells"]
    ]
    assert {row["id"]: row["expected_decision"] for row in registry["cells"]} == {
        row["id"]: row["expected"] for row in adjudicated
    }
    assert Counter(row["expected_decision"] for row in registry["cells"]) == {
        "pass_to_primary": 6,
        "rework": 8,
        "escalate": 2,
    }


def test_source_tests_and_canonical_archives_identical():
    registry = H.B.read(H.BATCH / "registration.json")
    original = {row["id"]: row for row in H.B.read(H.H.REVIEWER_REGISTRATION)["cells"]}
    for row in registry["cells"]:
        root = Path(row["root"])
        source = Path(original[row["id"]]["root"])
        H.R.assert_files(root, row["files"])
        for path, digest in row["files"].items():
            if (
                path.startswith(("src/", "tests/", ".agent/tasks/"))
                or path == "pyproject.toml"
            ):
                assert H.B.sha(source / path) == digest


def test_no_expected_answer_or_history_index_in_worker_root():
    for row in H.B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        for path in (
            ".agent/primary-control-adjudication.json",
            ".agent/current-task.json",
            "registration.json",
        ):
            assert not (root / path).exists()
        assert row["identity"]["review_id"].startswith("r4-frozen-")


def test_identical_reviewer_runtime_model_and_protocol():
    current = H.B.read(
        H.H.S.BATCH / "cases/presence-candidate-1/isolated/.agent/config.json"
    )
    for row in H.B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        config = H.B.read(root / ".agent/config.json")
        assert H.B.sha(root / ".local-agents/reviewer-runtime.py") == H.B.sha(
            H.B.KIT / ".local-agents/reviewer-runtime.py"
        )
        assert {
            key: value for key, value in config.items() if key.startswith("reviewer_")
        } == {
            key: value for key, value in current.items() if key.startswith("reviewer_")
        }
        assert config["single_model_residency"] is True
