"""Consumer dispatch following verified accepted startup-recovered producer."""

import sys
from pathlib import Path

import qualification_matrix as MATRIX
from capability_fit import write
from inherited_context_recovery import digest, read


def run():
    cell = next(c for c in MATRIX.verify()["cells"] if c["id"] == "async-receipt-r1")
    root = Path(cell["root"])
    parent = read(root / ".agent/collect-unit-startup2-bound.json")
    packet = read(root / ".agent/qual-unit-bound.json")
    MATRIX.CHAIN.SNAPSHOT = MATRIX.SNAPSHOT
    contract = MATRIX.CHAIN.load_contract()
    plan = read(root / ".agent/feature-plan.json")
    contract.validate_unit_packet(plan, packet)
    refs = {"collect-unit": {k: parent[k] for k in ("task_id", "run_id")}}
    if contract.accepted_units_from_archives(plan, root, refs) != {"collect-unit"}:
        raise ValueError("actual producer is not verified accepted")
    archive = root / ".agent/tasks" / parent["task_id"] / "runs" / parent["run_id"]
    changes = read(archive / "handoff.json")["changed_files"]
    expected = dict(cell["hashes"])
    for change in changes:
        expected[change["path"]] = change["final_sha256"]
    MATRIX.SCOPE.FA.LAYER.verify_hashes(root, expected)
    write(
        root / ".agent/qual-unit-dependency-dispatch.json",
        {
            "accepted_dependencies": refs,
            "driver_sha256": digest(Path(__file__)),
            "inputs_verified": expected,
        },
    )
    MATRIX.SCOPE.invoke(
        root,
        "qual-unit-unit",
        [
            sys.executable,
            str(MATRIX.SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/qual-unit-bound.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/qual-unit-coder.json"),
            "--review-report",
            str(root / ".agent/qual-unit-reviewer.json"),
        ],
    )
    write(
        root / ".agent/qual-unit-primary-checks.json",
        MATRIX.SCOPE.FA.LAYER.check(root, "qual-unit-primary"),
    )
    print(read(root / ".agent/qual-unit-coder.json").get("status"), flush=True)


if __name__ == "__main__":
    run()
