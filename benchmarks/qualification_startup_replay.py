"""Retry only the observed no-model-turn role-lock launch, with new artifacts."""

import argparse
import json
import sys
from pathlib import Path

import qualification_matrix as MATRIX
from capability_fit import write
from inherited_context_recovery import digest, read


def replay(action):
    cell = next(c for c in MATRIX.verify()["cells"] if c["id"] == "async-receipt-r1")
    root = Path(cell["root"])
    MATRIX.SCOPE.FA.LAYER.verify_hashes(root, cell["hashes"])
    parent = read(root / ".agent/collect-unit-bound.json")
    old = read(
        root / ".agent/explorer.json"
        if action == "explore"
        else root / ".agent/collect-unit-coder.json"
    )
    if old.get("blocked", {}).get("reason_code") != "model_switch_lock_held":
        raise ValueError("only pre-model role-lock replay authorized")
    write(
        root / f".agent/{action}-startup2-provenance.json",
        {
            "reason": "previous unrelated Reviewer session now completed; original launch reached no model turn",
            "old_report": old,
            "driver_sha256": digest(Path(__file__)),
            "classification": "infrastructure recovery, original record retained",
        },
    )
    if action == "explore":
        argv = [
            sys.executable,
            str(MATRIX.SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            old["task"],
            "--task-id",
            parent["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/explorer-startup2.json"),
            "--full-report",
        ]
    else:
        if (
            old.get("evidence_refs")
            or old.get("identity", {}).get("attempt") is not None
        ):
            raise ValueError("old unit has model/archive evidence")
        parent["run_id"] = parent["run_id"] + "-startup2"
        write(root / ".agent/collect-unit-startup2-bound.json", parent)
        argv = [
            sys.executable,
            str(MATRIX.SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/collect-unit-startup2-bound.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/collect-unit-startup2-coder.json"),
            "--review-report",
            str(root / ".agent/collect-unit-startup2-reviewer.json"),
        ]
    MATRIX.SCOPE.invoke(root, action + "-startup2", argv)
    output = root / (
        ".agent/explorer-startup2.json"
        if action == "explore"
        else ".agent/collect-unit-startup2-coder.json"
    )
    print(json.dumps(read(output)), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("explore", "unit"))
    replay(parser.parse_args().action)
