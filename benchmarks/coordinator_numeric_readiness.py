"""Verify evidence for Primary to authorize, not auto-accept, mixed testing."""

import json
from pathlib import Path

import coordinator_numeric_split as split
from capability_fit import KIT, write
from inherited_context_recovery import digest, read


def main():
    contract = split.configure()
    manifest = split.candidate.numeric.pilot.matrix.verify()
    explorer_rows = []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        for mode in split.QUESTIONS:
            p = root / f".agent/{mode}-explorer.json"
            report = read(p)
            accepted = read(root / f".agent/{mode}-explorer-primary.json")
            if not accepted["success"] or digest(p) != accepted["report_sha256"]:
                raise ValueError("Explorer adjudication/report mismatch")
            if (
                report["status"] != "success"
                or report["cache"]["hit"]
                or report["uncertainties"]
            ):
                raise ValueError("Explorer is unqualified")
            for ref in report["source_refs"]:
                source = root / ref["path"]
                if digest(source) != ref["source_hash"]:
                    matches = [
                        p
                        for p in (root / ".agent/tasks").glob(
                            "*/runs/*/preimages/" + ref["path"]
                        )
                        if digest(p) == ref["source_hash"]
                    ]
                    if not matches:
                        raise ValueError("missing original read source")
                    source = matches[0]
                lines = source.read_text(encoding="utf-8").splitlines()
                start, end = ref["start_line"], ref["end_line"]
                if not 1 <= start <= end <= len(lines) or ref["quote"] != "\n".join(
                    lines[start - 1 : end]
                ):
                    raise ValueError("invalid citation")
            explorer_rows.append(
                {
                    "cell": cell["id"],
                    "mode": mode,
                    "fresh": True,
                    "success": True,
                    "references": len(report["source_refs"]),
                    "single_six_path_call_credit": False,
                }
            )
    root = split.root_for("control-r1")
    cell = next(c for c in manifest["cells"] if c["id"] == "control-r1")
    plan = read(root / ".agent/feature-plan.json")
    _, refs, accepted = split.candidate.numeric.evidence.provenance(
        contract, cell, root, plan, True
    )
    contract.verify_integration_archive(plan, root, refs)
    units = []
    for uid in cell["units"]:
        packet = read(root / f".agent/{uid}-bound.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        handoff = read(archive / "handoff.json")
        primary = read(archive / "review.json")
        reviewer = read(
            root
            / ".agent/tasks"
            / packet["task_id"]
            / "reviews"
            / primary["local_review_id"]
            / "handoff.json"
        )
        independent = read(root / f".agent/{uid}-independent-1.json")
        if (
            handoff["status"] != "ready_for_review"
            or reviewer["decision"] != "pass_to_primary"
            or primary["decision"] != "accept"
            or not independent["passed"]
            or not reviewer["runtime_facts"]["inputs_unchanged"]
        ):
            raise ValueError("control unit not qualified")
        units.append(
            {
                "unit": uid,
                "coder": handoff["status"],
                "reviewer": reviewer["decision"],
                "primary": primary["decision"],
                "independent_checks": True,
            }
        )
    integration = read(root / ".agent/feature-integration.json")
    if integration["junit"] != {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError("incomplete control integration")
    coordinator = split.root_for("coordinator-r1")
    coordinator_cell = next(c for c in manifest["cells"] if c["id"] == "coordinator-r1")
    split.candidate.numeric.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
        coordinator, coordinator_cell["hashes"]
    )
    if list((coordinator / ".agent").glob("*-coder.json")):
        raise ValueError("Coordinator arm already ran")
    frozen = read(split.SNAPSHOT / "freeze.json")["files"]
    if any(digest(KIT / p) != h for p, h in frozen.items()):
        raise ValueError("production drift")
    result = {
        "status": "eligible_for_primary_coordinator_test_authorization",
        "explorers": explorer_rows,
        "control_units": units,
        "control_accepted_units": sorted(accepted),
        "control_integration_tests": 7,
        "coordinator_arm_pristine": True,
        "production_freeze_verified": True,
        "coordinator_tests_not_yet_executed": True,
        "full_release_or_cost_claim": False,
        "driver_sha256": digest(Path(__file__)),
    }
    write(split.BASE / "readiness-facts-1.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
