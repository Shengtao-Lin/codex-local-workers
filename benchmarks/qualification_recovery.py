"""One evidence-driven inherited recovery per failed matrix unit, separate credit."""

import argparse
import json
import sys
from pathlib import Path

import qualification_matrix as MATRIX
import supervised_scope_check as SCOPE
from capability_fit import write
from inherited_context_recovery import read

FEEDBACK = {
    "display-default": "Primary verified tests/test_target.py::test_present and current target.py: input {'name': None} returns 'unnamed', but the hard contract requires None. Key absence and a present None are distinct states. Preserve the already passing empty-string and missing-key behavior. Make a narrow correction; no test or scope changes.",
    "lookup-fallback": "Primary verified tests/test_target.py::test_values[None] and current target.py: fetch returning None without an exception is incorrectly replaced by default. Every successful result, including None, must be returned unchanged; only a raised KeyError selects default. Preserve non-KeyError propagation and exactly-one call. Make a narrow correction; no test or scope changes.",
}


def run(identity):
    cell = next(c for c in MATRIX.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    case = cell["case"]
    if case not in FEEDBACK:
        raise ValueError("unregistered recovery")
    parent = read(root / ".agent/qual-unit-bound.json")
    archive = root / ".agent/tasks" / parent["task_id"] / "runs" / parent["run_id"]
    if read(archive / "review.json")["decision"] != "rework":
        raise ValueError("Primary rework required")
    child = {
        k: parent[k] for k in ("schema_version", "task_id", "unit_id", "plan_revision")
    }
    child.update(
        run_id=parent["run_id"].removesuffix("-a1") + "-a2",
        parent_run_id=parent["run_id"],
        attempt=2,
        packet_revision=2,
        preserve_contract=True,
        review_feedback=[
            {
                "finding_id": case + "-none-conflation",
                "contract_id": "qual-unit",
                "text": FEEDBACK[case],
            }
        ],
    )
    write(root / ".agent/guided-a2.json", child)
    write(
        root / ".agent/guided-a2-provenance.json",
        {
            "classification": "guided recovery, excluded from autonomous qualification",
            "runtime_changed": False,
            "scope_changed": False,
            "tests_changed": False,
        },
    )
    SCOPE.invoke(
        root,
        "guided-a2-unit",
        [
            sys.executable,
            str(MATRIX.SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/guided-a2.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/guided-a2-coder.json"),
            "--review-report",
            str(root / ".agent/guided-a2-reviewer.json"),
        ],
    )
    write(
        root / ".agent/guided-a2-primary-checks.json",
        SCOPE.FA.LAYER.check(root, "guided-a2-primary"),
    )
    print(json.dumps(read(root / ".agent/guided-a2-coder.json")))
    report = root / ".agent/guided-a2-reviewer.json"
    if report.exists():
        print(json.dumps(read(report)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    run(parser.parse_args().identity)
