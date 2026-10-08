"""Read-only gate status: failed initial cells cannot be overwritten by recovery."""

import json
from pathlib import Path

import qualification_controls as CONTROLS
import qualification_matrix as MATRIX
from inherited_context_recovery import digest, read


def optional(path):
    return read(path) if path.exists() else {}


def qualified(units, explorers, controls, integration):
    cases = (
        "display-default",
        "public-fields",
        "lookup-fallback",
        "async-first-present",
        "label-rollup",
        "async-receipt",
    )
    expected_units = {
        f"{case}-r{repetition}/{unit}"
        for case in cases
        for repetition in (1, 2)
        for unit in (
            ("collect-unit", "qual-unit") if case == "async-receipt" else ("qual-unit",)
        )
    }
    expected_explorers = {
        f"{case}-r{r}" for case in ("label-rollup", "async-receipt") for r in (1, 2)
    }
    expected_controls = {
        f"{case}-{variant}-r{r}"
        for case in ("display-default", "lookup-fallback")
        for variant in ("a", "b")
        for r in (1, 2)
    }
    expected_integrations = {"async-receipt-r1", "async-receipt-r2"}
    for items, expected, field in (
        (units, expected_units, "accepted_initial"),
        (explorers, expected_explorers, "success"),
        (controls, expected_controls, "effective"),
        (integration, expected_integrations, "passed"),
    ):
        if len(items) != len(expected) or {i["id"] for i in items} != expected:
            return False
        if not all(i.get(field) is True for i in items):
            return False
    return True


def status():
    manifest = MATRIX.verify()
    units = []
    explorers = []
    integration = []
    for cell in manifest["cells"]:
        root = Path(cell["root"])
        for unit in cell["units"]:
            prefix = (
                unit + "-startup2"
                if (root / f".agent/{unit}-startup2-bound.json").exists()
                else unit
            )
            packet = read(root / f".agent/{prefix}-bound.json")
            archive = (
                root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
            )
            coder = optional(root / f".agent/{prefix}-coder.json")
            reviewer = optional(root / f".agent/{prefix}-reviewer.json")
            primary = optional(archive / "review.json")
            finished = optional(archive / "completed.json")
            handoff = optional(archive / "handoff.json")
            validation = coder.get("validation_summary", {})
            unchanged = all(
                digest(root / change["path"]) == change["final_sha256"]
                for change in handoff.get("changed_files", [])
            )
            accepted = (
                coder.get("status") == "ready_for_review"
                and finished.get("status") == "ready_for_review"
                and primary.get("decision") == "accept"
                and reviewer.get("decision") == "pass_to_primary"
                and validation.get("status") == "passed"
                and validation.get("executed", 0) > 0
                and validation.get("inputs_unchanged") is True
                and unchanged
            )
            units.append(
                {
                    "id": cell["id"] + "/" + unit,
                    "coder": coder.get("status", "pending"),
                    "reviewer": reviewer.get("decision", "N/A"),
                    "primary": primary.get("decision", "pending"),
                    "accepted_initial": accepted,
                    "run_id": packet["run_id"],
                }
            )
        if cell["explorer_required"]:
            report = optional(root / ".agent/explorer-startup2.json") or optional(
                root / ".agent/explorer.json"
            )
            adjudication = optional(root / ".agent/explorer-primary-adjudication.json")
            explorers.append(
                {
                    "id": cell["id"],
                    "status": report.get("status", "pending"),
                    "success": report.get("status") == "success"
                    and adjudication.get("success") is True
                    and adjudication.get("qualification_credit", True) is True,
                }
            )
        if len(cell["units"]) == 2:
            evidence = optional(root / ".agent/feature-integration.json")
            integration.append(
                {
                    "id": cell["id"],
                    "passed": evidence.get("checks", {}).get("all_checks_pass") is True
                    and evidence.get("inputs_unchanged") is True,
                }
            )
    controls = []
    for cell in CONTROLS.verify()["controls"]:
        root = Path(cell["root"])
        report = optional(root / ".agent/reviewer.json")
        adjudication = optional(root / ".agent/primary-control-adjudication.json")
        controls.append(
            {
                "id": cell["id"],
                "has_defect": cell["has_defect_primary_only"],
                "reviewer": report.get("decision", "pending"),
                "effective": adjudication.get("effective") is True,
            }
        )
    gate = qualified(units, explorers, controls, integration)
    return {
        "units": units,
        "explorers": explorers,
        "integration": integration,
        "controls": controls,
        "accepted_initial_units": sum(u["accepted_initial"] for u in units),
        "initial_units_required": 14,
        "explorer_success": sum(e["success"] for e in explorers),
        "explorer_required": 4,
        "reviewer_effective_controls": sum(c["effective"] for c in controls),
        "reviewer_required": 8,
        "qualification_gate": gate,
        "coordinator_may_start": gate,
        "guided_recovery_restores_initial_credit": False,
    }


if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
