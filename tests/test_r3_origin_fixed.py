"""No-model controls for the experiment-origin guard, not production changes."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_r3_origin_fixed as R


@pytest.mark.parametrize("task", ["repair", "presence"])
def test_expected_initial_failure_accepted(task):
    R.require_predicate(task, R.expected(task))


@pytest.mark.parametrize(
    "field,value",
    [
        ("exits", [0, 1, 0, 0]),
        ("exits", [0, 0, 0, 0]),
        ("tests", 0),
        ("tests", 10),
        ("lint", []),
        ("lint", [[R.B.SOURCE, "E501", 85, 101]]),
        ("failures", ["unexpected"]),
    ],
)
def test_wrong_repair_predicate_rejected(field, value):
    observation = copy.deepcopy(R.expected("repair"))
    observation[field] = value
    with pytest.raises(ValueError, match="Wrong initial failure"):
        R.require_predicate("repair", observation)


def test_presence_green_baseline_rejected():
    observation = R.expected("presence")
    observation.update(exits=[0, 0, 0, 0], failures=[])
    with pytest.raises(ValueError):
        R.require_predicate("presence", observation)


def test_identical_post_run_pairs_rejected():
    manifest = R.origins()["repair"]
    for name in ("repair-baseline-1", "repair-candidate-1"):
        root = R.PREVIOUS / "cases" / name / "isolated"
        with pytest.raises(ValueError, match="upstream pre-run"):
            R.O.require_origin(root, manifest)


def test_corrected_source_and_changed_protected_test(tmp_path):
    source = (
        R.B.KIT
        / "benchmarks/work/harness-convergence/r2-rendering-20261014-1/cases/json-1/isolated"
    )
    root = tmp_path / "isolated"
    R.P.copy_inputs(source, root)
    manifest = R.origins()["repair"]
    R.O.require_origin(root, manifest)
    test = root / "tests/test_get_many.py"
    test.write_text(test.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    with pytest.raises(ValueError, match="upstream pre-run"):
        R.O.require_origin(root, manifest)
