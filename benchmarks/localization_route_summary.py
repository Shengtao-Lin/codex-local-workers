"""Summarize explicitly selected frozen route snapshots without hiding failures."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected a JSON object: {path}")
    return value


def manifest_hash(manifest: dict) -> str:
    encoded = json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def rework_runs(workspace: Path, case: str) -> list[dict]:
    task_id = f"stability-{case}"
    runs_root = workspace / ".agent" / "tasks" / task_id / "runs"
    observations = []
    if not runs_root.is_dir():
        return observations
    for run_root in sorted(runs_root.iterdir()):
        packet_path = run_root / "packet.json"
        completed_path = run_root / "completed.json"
        if not packet_path.is_file() or not completed_path.is_file():
            continue
        packet = read_json(packet_path)
        if packet.get("task_id") != task_id or packet.get("unit_id") != case:
            raise ValueError(f"unrelated run under frozen task: {run_root}")
        if packet.get("attempt", 0) <= 1:
            continue
        completed = read_json(completed_path)
        reviewer_pass = False
        for request_name in (
            "auto-review-request.json",
            "auto-review-retry-request.json",
        ):
            request_path = run_root / request_name
            if not request_path.is_file():
                continue
            review_id = read_json(request_path).get("review_id")
            if not isinstance(review_id, str) or not review_id.startswith("auto-"):
                continue
            handoff_path = (
                workspace
                / ".agent"
                / "tasks"
                / task_id
                / "reviews"
                / review_id
                / "handoff.json"
            )
            if not handoff_path.is_file():
                continue
            handoff = read_json(handoff_path)
            identity = handoff.get("identity") or {}
            if (
                identity.get("task_id") == task_id
                and identity.get("unit_id") == case
                and identity.get("run_id") == packet["run_id"]
                and identity.get("review_id") == review_id
                and handoff.get("decision") == "pass_to_primary"
            ):
                reviewer_pass = True
        observations.append(
            {
                "run_id": packet["run_id"],
                "attempt": packet["attempt"],
                "coder_status": completed.get("status"),
                "reviewer_pass": reviewer_pass,
            }
        )
    return sorted(observations, key=lambda item: item["attempt"])


def summarize(
    results: list[dict], *, question_version: int, require_frozen_manifest: bool = False
) -> dict:
    if not results:
        raise ValueError("at least one route result is required")
    workspaces = set()
    by_case: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    counts: dict[str, int] = defaultdict(int)
    cells = []
    runtime_sha256: str | None = None
    case_input_sha256: dict[str, str] = {}
    for item in results:
        workspace = Path(item["workspace"]).resolve()
        case = item["case"]
        if str(workspace) in workspaces:
            raise ValueError(f"duplicate frozen workspace: {workspace}")
        workspaces.add(str(workspace))
        if item.get("unknown_location") is not True:
            raise ValueError(
                "this cohort requires independent unknown-location Explorer calls"
            )
        if item.get("question_version") != question_version:
            raise ValueError(
                "mixed or missing question versions cannot form one cohort"
            )
        if require_frozen_manifest:
            provenance = item.get("provenance")
            if not isinstance(provenance, dict):
                raise ValueError("frozen cohort requires provenance for every cell")
            runtime_hash = provenance.get("runtime_sha256")
            case_hash = provenance.get("case_input_sha256")
            manifest = provenance.get("runtime_manifest")
            if (
                not isinstance(runtime_hash, str)
                or not isinstance(case_hash, str)
                or len(case_hash) != 64
                or not isinstance(manifest, dict)
                or runtime_hash != manifest_hash(manifest)
                or item.get("runtime_changed_during_run") is not False
            ):
                raise ValueError(
                    "frozen cohort has incomplete or changed runtime provenance"
                )
            if runtime_sha256 is not None and runtime_hash != runtime_sha256:
                raise ValueError("frozen cohort mixes runtime or role configuration")
            if case in case_input_sha256 and case_hash != case_input_sha256[case]:
                raise ValueError(f"frozen cohort changes the input for case: {case}")
            runtime_sha256 = runtime_hash
            case_input_sha256[case] = case_hash
        route = item.get("route") or {}
        unit = route.get("unit_result") or {}
        review_attempts = unit.get("review_attempts") or []
        infra = bool(
            item.get("explorer_infra_failure")
            or route.get("stage") == "unit_launch"
            or unit.get("infra_failure")
            or any(attempt.get("infra_failure") for attempt in review_attempts)
        )
        flags = {
            "baseline_failed": item.get("baseline_failed") is True,
            "explorer_valid": item.get("explorer_evidence_valid") is True,
            "coder_ready": unit.get("status") == "ready_for_review",
            "reviewer_reached": bool(review_attempts),
            "reviewer_pass": unit.get("reviewer_decision") == "pass_to_primary",
            "e2e_first_pass": item.get("qualified_pass") is True,
            "explicit_infra_failure": infra,
        }
        if flags["e2e_first_pass"] and not all(
            flags[key]
            for key in (
                "baseline_failed",
                "explorer_valid",
                "coder_ready",
                "reviewer_pass",
            )
        ):
            raise ValueError(
                f"qualified_pass conflicts with role evidence: {workspace}"
            )
        for key, value in flags.items():
            counts[key] += int(value)
            by_case[case][key] += int(value)
        runs = rework_runs(workspace, case)
        counts["rework_coder_calls"] += len(runs)
        counts["rework_coder_ready"] += sum(
            run["coder_status"] == "ready_for_review" for run in runs
        )
        counts["rework_reviewer_pass"] += sum(run["reviewer_pass"] for run in runs)
        counts["rework_units_with_reviewer_pass"] += int(
            any(run["reviewer_pass"] for run in runs)
        )
        cells.append(
            {
                "case": case,
                "workspace": str(workspace),
                **flags,
                "coder_status": unit.get("status"),
                "reviewer_decision": unit.get("reviewer_decision"),
                "rework_runs": runs,
            }
        )
    return {
        "assessment": "observational_only_not_v1_2_or_v2_1_gate",
        "question_version": question_version,
        "frozen_manifest_checked": require_frozen_manifest,
        "runtime_sha256": runtime_sha256,
        "attempts": len(cells),
        "distinct_cases": len(by_case),
        "counts": dict(counts),
        "by_case": {case: dict(values) for case, values in sorted(by_case.items())},
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--question-version", type=int, default=2)
    parser.add_argument("--require-frozen-manifest", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = summarize(
        [read_json(path) for path in args.results],
        question_version=args.question_version,
        require_frozen_manifest=args.require_frozen_manifest,
    )
    rendered = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
