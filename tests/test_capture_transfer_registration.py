"""Pre-live registration, corrected baseline provenance and immutable pairing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_transfer_matrix as M


def test_fixed_registration_and_controls():
    registration = M.T.read(M.BATCH / "registration.json")
    assert registration["registered_units"] == len(registration["order"]) == 12
    assert registration["weekly_used_ceiling"] == 15
    assert registration["coder_budget"] == {
        "requests": 6,
        "edits": 3,
        "validation_runs": 3,
        "invocation_seconds": 900,
    }
    assert M.T.read(M.BATCH / "fixture-controls-approved.json")[
        "private_tests_add_detection"
    ]
    assert M.T.read(M.BATCH / "entry-controls.json")["model_calls"] == 0


def test_pairing_and_real_original_baseline_flags():
    rows = M.T.read(M.BATCH / "prepared-cells-v3.json")
    original = M.T.read(
        M.KIT
        / "benchmarks/work/harness-convergence/r1-r2-20261013-2/cases/failed-draft-formal-1/isolated/.agent/config.json"
    )
    for topic in M.TOPICS:
        for repeat in (1, 2):
            left, right = (
                Path(rows[f"{topic}-{arm}-{repeat}"]["root"])
                for arm in ("baseline", "candidate")
            )
            baseline, candidate = (
                M.T.read(left / ".agent/config.json"),
                M.T.read(right / ".agent/config.json"),
            )
            for field in ("coder_structured_output", "coder_typed_action_arguments"):
                assert baseline[field] is original[field] is True
                assert candidate[field] is False
            assert (
                baseline["coder_model"]
                == candidate["coder_model"]
                == "qwen/qwen3-coder-30b"
            )
            assert (
                baseline["reviewer_model"]
                == candidate["reviewer_model"]
                == "meta/muse-glimmer"
            )
            assert (
                not baseline["coordinator_enabled"]
                and not candidate["coordinator_enabled"]
            )
            assert M.T.sha(left / ".local-agents/reviewer-runtime.py") == M.T.sha(
                right / ".local-agents/reviewer-runtime.py"
            )


def test_all_inputs_unchanged_before_live():
    for row in M.T.read(M.BATCH / "prepared-cells-v3.json").values():
        assert all(
            M.T.sha(Path(row["root"]) / p) == sha for p, sha in row["files"].items()
        )
        assert not (Path(row["root"]).parent / "started.json").exists()
