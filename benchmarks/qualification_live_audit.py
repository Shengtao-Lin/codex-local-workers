"""Read-only current-file provenance audit; never grants role qualification."""

import argparse
from pathlib import Path

from capability_fit import write
from inherited_context_recovery import digest, read


def audit(matrix, controls, artifact):
    manifest = matrix.verify()
    rows = []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        expected = dict(cell["hashes"])
        for unit in cell["units"]:
            packet = read(root / f".agent/{unit}-bound.json")
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            handoff = read(archive / "handoff.json")
            assert all(
                handoff["identity"][key] == packet[key]
                for key in ("task_id", "run_id", "unit_id")
            )
            for change in handoff["changed_files"]:
                assert (
                    change["path"]
                    in packet["scope"]["modify"] + packet["scope"]["create"]
                )
                expected[change["path"]] = change["final_sha256"]
        matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        rows.append(
            {"id": cell["id"], "expected_files": expected, "current_files_match": True}
        )
    control_rows = []
    for cell in controls.verify()["controls"]:
        root = Path(cell["root"])
        packet = read(root / ".agent/qual-unit-reference.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        validation = read(archive / "handoff.json")["validation"]
        expected = {
            path: facts["sha256"]
            for path, facts in validation["focused_tests"]["input_facts"].items()
            if facts.get("exists")
        }
        assert expected
        matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
        control_rows.append(
            {
                "id": cell["id"],
                "expected_validation_inputs": expected,
                "current_files_match": True,
            }
        )
    write(
        matrix.BASE / artifact,
        {
            "cells": rows,
            "controls": control_rows,
            "driver_sha256": digest(Path(__file__)),
            "qualification_credit": False,
            "semantic_acceptance_not_inferred": True,
        },
    )
    print(
        "All current source/test/config files match frozen inputs and attributed canonical changes"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("cohort", choices=("3", "4"))
    parser.add_argument("artifact")
    args = parser.parse_args()
    if args.cohort == "3":
        import qualification_matrix_v3 as candidate
    else:
        import qualification_matrix_v4 as candidate
    candidate.configure()
    base = candidate if args.cohort == "3" else candidate.prior
    audit(base.MATRIX, base.CONTROLS, args.artifact)
