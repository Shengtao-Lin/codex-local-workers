"""Read-only replay of paired measurements; no release or savings authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from supervised_candidate_audit import replay_refs, replay_validation
from supervised_efficiency import CONTRACT, ROUTE, STABILITY, read

PAIRS = (
    "efficiency-seed-pair-1",
    "efficiency-message-pair-1",
    "efficiency-metadata-pair-1",
)


def observation(root: Path) -> dict:
    value = read(root / "primary-observation.json")
    correction = root / "primary-observation-correction.json"
    if correction.exists():
        update = read(correction)
        if update.get("supersedes_fields_in") != "primary-observation.json":
            raise ValueError("unrecognized Primary observation correction")
        allowed = {
            "protected_test_files_opened",
            "protected_test_files_reviewed",
            "protected_test_evidence_reused_by_exact_hash",
        }
        if set(update) - allowed - {"schema_version", "supersedes_fields_in", "reason"}:
            raise ValueError("correction cannot change acceptance or risk")
        value.update({key: update[key] for key in allowed if key in update})
    return value


def model_totals(roles: dict) -> dict:
    missing = sum(role["requests_missing_token_usage"] for role in roles.values())
    return {
        "requests": sum(role["requests"] for role in roles.values()),
        "reported_total_tokens": (
            None
            if missing
            else sum(role["reported_total_tokens"] for role in roles.values())
        ),
        "requests_missing_token_usage": missing,
    }


def report(work: Path, pairs: tuple[str, ...] | None = None) -> dict:
    selected_pairs = PAIRS if pairs is None else pairs
    if (
        len(selected_pairs) != 3
        or len(set(selected_pairs)) != 3
        or any(
            name in {".", ".."} or Path(name).name != name or Path(name).is_absolute()
            for name in selected_pairs
        )
    ):
        raise ValueError("select three distinct direct pair directory names")
    bindings = {}

    def bind(path: Path) -> None:
        bindings[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

    arms = []
    runtime_hashes = set()
    for name in selected_pairs:
        pair = work / name
        freeze = read(pair / "freeze.json")
        bind(pair / "freeze.json")
        inputs = [
            read(pair / mode / "paired-inputs.json")
            for mode in ("control", "coordinator")
        ]
        if inputs[0] != inputs[1]:
            raise ValueError("paired actual inputs differ")
        for mode in ("control", "coordinator"):
            root = pair / mode
            measured = read(root / "measurement.json")
            if (
                not measured.get("qualified_execution")
                or measured["runtime_sha256"] != freeze["runtime"]["runtime_sha256"]
                or measured["inputs_sha256"] != ROUTE._sha256_json(inputs[0])
                or measured["mode"] != mode
                or measured["case"] != freeze["case"]
            ):
                raise ValueError("measurement/freeze/input identity mismatch")
            runtime_hashes.add(measured["runtime_sha256"])
            plan = read(root / ".agent/feature-plan.json")
            case = measured["case"]
            task = f"stability-{case}"
            run_id = f"{case}-a1"
            accepted = CONTRACT.accepted_units_from_archives(
                plan, root, {case: {"task_id": task, "run_id": run_id}}
            )
            if accepted != {case}:
                raise ValueError("missing actual Primary/Coder/Reviewer acceptance")
            unit = plan["units"][0]
            observed = observation(root)
            if (
                observed["decision"] != "accept"
                or observed["effective_risk"] != unit["risk"]
            ):
                raise ValueError(
                    "Primary observation conflicts with actual plan/review"
                )
            run = root / ".agent/tasks" / task / "runs" / run_id
            handoff = read(run / "handoff.json")
            review = read(run / "review.json")
            reviewer_root = (
                root / ".agent/tasks" / task / "reviews" / review["local_review_id"]
            )
            reviewer = read(reviewer_root / "handoff.json")
            actual_validation = replay_validation(root, run)
            explorer_path = (
                root / ".agent/explorer-report.json"
                if mode == "control"
                else root
                / ".agent/coordinator"
                / task
                / "proposals"
                / run_id
                / "explorer-report.json"
            )
            actual_refs = replay_refs(root, run, read(explorer_path))
            if actual_refs != measured["verified_explorer_source_refs"]:
                raise ValueError(
                    "paired Explorer reference count differs from real reads"
                )
            bind(explorer_path)
            bind(run / "validation.json")
            bind(root / read(run / "validation.json")["focused_tests"]["junit"]["path"])
            for path in (
                root / "measurement.json",
                root / "paired-inputs.json",
                root / "primary-observation.json",
                root / ".agent/feature-plan.json",
                *(
                    run / name
                    for name in (
                        "packet.json",
                        "handoff.json",
                        "completed.json",
                        "review.json",
                    )
                ),
                reviewer_root / "handoff.json",
                reviewer_root / "completed.json",
            ):
                bind(path)
            correction = root / "primary-observation-correction.json"
            if correction.exists():
                bind(correction)
            arms.append(
                {
                    "case": case,
                    "mode": mode,
                    "runtime_sha256": measured["runtime_sha256"],
                    "wall_seconds": measured["wall_seconds_including_model_switches"],
                    "model_usage": measured["model_usage"],
                    **model_totals(measured["model_usage"]),
                    "coder_local_repairs": handoff["repair_count"],
                    "coder_protocol_errors": handoff["protocol_error_count"],
                    "reviewer_protocol_errors": reviewer["runtime_facts"][
                        "protocol_error_count"
                    ],
                    "primary_observation": observed,
                    "canonical_accepted": True,
                    "actual_validation": actual_validation,
                    "verified_explorer_source_refs": actual_refs,
                }
            )
    if len(runtime_hashes) != 1:
        raise ValueError("pairs mix different frozen runtimes")
    totals = {}
    for mode in ("control", "coordinator"):
        selected = [arm for arm in arms if arm["mode"] == mode]
        totals[mode] = {
            "accepted_units": len(selected),
            "wall_seconds": sum(arm["wall_seconds"] for arm in selected),
            "requests": sum(arm["requests"] for arm in selected),
            "reported_total_tokens": (
                None
                if any(arm["reported_total_tokens"] is None for arm in selected)
                else sum(arm["reported_total_tokens"] for arm in selected)
            ),
            "coder_local_repairs": sum(arm["coder_local_repairs"] for arm in selected),
            "reviewer_protocol_errors": sum(
                arm["reviewer_protocol_errors"] for arm in selected
            ),
            "raw_source_opens": sum(
                arm["primary_observation"]["changed_source_files_opened"]
                for arm in selected
            ),
            "raw_protected_test_opens": sum(
                arm["primary_observation"]["protected_test_files_opened"]
                for arm in selected
            ),
            "diff_hunks_read": sum(
                arm["primary_observation"]["diff_hunks_read"] for arm in selected
            ),
            "manual_packet_edits": sum(
                arm["primary_observation"]["manual_packet_edit_count"]
                for arm in selected
            ),
            "manual_rework_interventions": sum(
                arm["primary_observation"]["manual_rework_interventions"]
                for arm in selected
            ),
            "primary_takeovers": sum(
                arm["primary_observation"]["primary_takeover"] for arm in selected
            ),
            "primary_review_seconds": None,
            "production_packet_authoring_seconds": None,
        }
    historical = work / "batch-ca7bba3a4104/summary.json"
    cells = read(historical)["results"]
    bind(historical)
    historical_audit = STABILITY.KIT / "benchmarks/V1.2-TWO-ROUND-AUDIT.md"
    bind(historical_audit)
    return {
        "schema_version": 1,
        "assessment": "observational_paired_comparison_not_release_acceptance",
        "measured_runtime_sha256": next(iter(runtime_hashes)),
        "arms": arms,
        "totals": totals,
        "phase0_historical": {
            "source": str(historical),
            "cells": len(cells),
            "qualified_cells": sum(bool(cell["qualified_pass"]) for cell in cells),
            "explorer_evidence_valid_cells": sum(
                bool(cell["explorer_evidence_valid"]) for cell in cells
            ),
            "coder_ready_cells": sum(
                cell["coder_status"] == "ready_for_review" for cell in cells
            ),
            "reviewer_pass_cells": sum(
                cell["reviewer_decision"] == "pass_to_primary" for cell in cells
            ),
            "infra_failure_cells": sum(bool(cell["infra_failure"]) for cell in cells),
            "summed_cell_wall_seconds": sum(cell["wall_seconds"] for cell in cells),
            "requests": {
                role: sum(
                    cell["metrics"]["context"][role]["requests"] for cell in cells
                )
                for role in ("explorer", "coder", "reviewer")
            },
            "comparability": "historical_only_different_roles_runtime_and_unit_decomposition",
        },
        "limitations": [
            "Three pairs, one observation per arm; no statistical causal inference.",
            "Wall time includes preparation, model switches and checks, excludes later Primary review.",
            "Primary human time and production packet-authoring effort were not measured.",
            "Raw file opens are order/cache-confounded; both arms retain risk-matched review obligations.",
            "Acceptance quality here is actual fixture validation/review, not production generalization.",
            "A later product delta needs its own qualification; these measurements retain their old hash.",
        ],
        "production_primary_work_savings": "not_established",
        "selected_pairs": list(selected_pairs),
        "default_enable_recommended": False,
        "feature_accepted": False,
        "artifact_sha256": bindings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--pairs",
        nargs=3,
        help="Explicit direct stability-work pair names; historical defaults remain unchanged.",
    )
    args = parser.parse_args()
    result = report(STABILITY.WORK, tuple(args.pairs) if args.pairs else None)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {
                "totals": result["totals"],
                "phase0_historical": result["phase0_historical"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
