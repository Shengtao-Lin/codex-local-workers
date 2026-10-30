"""Register and collect frozen worker experiments without launching workers.

Canonical reports establish historical outcomes. Current hashes establish whether
their evidence can still be used. Missing metrics remain unknown. All outputs are
new files under benchmarks/work/system-convergence; source archives are read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PureWindowsPath
from typing import Any


class CollectionError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise CollectionError("paths must be nonempty relative POSIX paths")
    if Path(relative).is_absolute() or PureWindowsPath(relative).is_absolute():
        raise CollectionError("absolute paths are not allowed")
    if ".." in Path(relative).parts or ":" in relative:
        raise CollectionError("path traversal is not allowed")
    root = root.resolve()
    candidate = root / relative
    for component in (candidate, *candidate.parents):
        if component == root:
            break
        if component.exists() or component.is_symlink():
            metadata = component.lstat()
            if component.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
                raise CollectionError("symlink/reparse paths are not allowed")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise CollectionError("path is outside the workspace")
    return resolved


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise CollectionError(f"cannot read JSON object: {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise CollectionError(f"expected JSON object: {path.name}")
    return value


def write_output(workspace: Path, relative: str, value: dict[str, Any]) -> None:
    path = inside(workspace, relative)
    allowed = inside(workspace, "benchmarks/work/system-convergence")
    if not path.is_relative_to(allowed) or path == allowed or path.suffix != ".json":
        raise CollectionError("output must be a new JSON file under system-convergence")
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError as error:
        raise CollectionError("output already exists; choose a new output identity") from error


def identity(value: dict[str, Any]) -> dict[str, str]:
    result = {}
    for key in ("task_id", "unit_id", "run_id"):
        item = value.get(key)
        if not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", item):
            raise CollectionError(f"invalid {key}")
        result[key] = item
    return result


def ref(root: Path, relative: str) -> dict[str, str]:
    path = inside(root, relative)
    return {"path": relative, "sha256": sha256(path)}


def build_registration(
    workspace: Path,
    batches: list[str],
    baseline: str,
    experiment_id: str,
    expectations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", experiment_id):
        raise CollectionError("invalid experiment_id")
    result: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "stage": "P1",
        "mode": "historical_read_only",
        "worker_launch_allowed": False,
        "baseline": ref(workspace, baseline),
        "source_batches": [],
        "cells": [],
    }
    for batch in batches:
        batch_root = inside(workspace, batch)
        registration = read_object(batch_root / "registration.json")
        result["source_batches"].append(ref(workspace, batch + "/registration.json"))
        for original in registration["cells"]:
            root = Path(original["root"]).resolve()
            if not root.is_relative_to(batch_root):
                raise CollectionError("registered cell is outside its source batch")
            relative_root = root.relative_to(workspace.resolve()).as_posix()
            root = inside(workspace, relative_root)
            archive = f".agent/tasks/{original['task_id']}/runs/{original['run_id']}"
            packet = read_object(inside(root, archive + "/packet.json"))
            expected_identity = identity(packet)
            if any(original.get(key) != value for key, value in expected_identity.items()):
                raise CollectionError("original registration and packet identities differ")
            paths = {
                label: archive + "/" + filename
                for label, filename in {
                    "packet": "packet.json",
                    "coder": "handoff.json",
                    "completed": "completed.json",
                    "validation": "validation.json",
                    "post_state": "post-state.json",
                    "primary": "review.json",
                    "changes": "changes.json",
                    "diff": "cumulative.diff",
                    "baseline": "baseline.json",
                    "preimages": "preimages.json",
                }.items()
            }
            optional = {
                "compact": ".agent/coder.json",
                "config": ".agent/config.json",
                "primary_audit": ".agent/independent-repeat-audit.json",
                "independent_audit": ".agent/independent-audit.json",
            }
            for label, path in optional.items():
                if inside(root, path).is_file():
                    paths[label] = path
            for attempt in sorted(inside(root, archive).glob("validation-attempt-*.json")):
                if not re.fullmatch(r"validation-attempt-[0-9]+\.json", attempt.name):
                    raise CollectionError("invalid validation attempt name")
                paths[attempt.stem] = archive + "/" + attempt.name
            primary = read_object(inside(root, paths["primary"]))
            if primary.get("local_review_id"):
                review_id = primary["local_review_id"]
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", review_id):
                    raise CollectionError("invalid review_id")
                paths["reviewer"] = (
                    f".agent/tasks/{packet['task_id']}/reviews/{review_id}/handoff.json"
                )
                paths["reviewer_compact"] = ".agent/reviewer.json"
            for name in ("repeat", "repair"):
                path = f".agent/{name}-live-invocation.json"
                if inside(root, path).is_file():
                    paths["local_invocation"] = path
            artifacts = {label: ref(root, path) for label, path in paths.items()}
            writable = set(packet["scope"]["modify"] + packet["scope"]["create"])
            protected = {
                path: digest for path, digest in original["paths"].items() if path not in writable
            }
            for name in ("packet", "config", "pyright"):
                digest = original.get(name + "_sha256")
                if digest:
                    protected[f".agent/{name}.json"] = digest
            validation = read_object(inside(root, paths["validation"]))
            junit_path = (validation.get("focused_tests") or {}).get("junit", {}).get("path")
            if junit_path:
                artifacts["junit"] = ref(root, junit_path)
            for name in ("primary-repeat", "primary-tests"):
                if inside(root, f".agent/{name}.xml").is_file():
                    artifacts["independent_junit"] = ref(root, f".agent/{name}.xml")
            config = read_object(inside(root, paths["config"])) if "config" in paths else {}
            cell_id = batch_root.name + "." + original["id"]
            result["cells"].append(
                {
                    "cell_id": cell_id,
                    "root": relative_root,
                    "identity": expected_identity,
                    "arm": "historical",
                    "roles": {
                        role: {
                            "model": config.get(role + "_model"),
                            "context_length": config.get(role + "_context_length"),
                        }
                        for role in ("explorer", "coder", "reviewer", "coordinator")
                    },
                    "artifacts": artifacts,
                    "protected_hashes": protected,
                    "validation_inputs": read_object(inside(root, paths["post_state"]))[
                        "validation_inputs"
                    ],
                    "expected": expectations[cell_id],
                    "contract_ids": packet["owned_contract_ids"],
                    "focused_tests": packet["focused_tests"],
                    "required_behavior": packet["required_behavior"],
                    "acceptance_scenarios": packet.get("acceptance_scenarios", []),
                    "validation_profile": packet["validation_profile"],
                    "preimage_evidence": ref(root, archive + "/preimages.json"),
                    "baseline_evidence": ref(root, archive + "/baseline.json"),
                    "budgets": {
                        "packet": packet.get("budgets", {}),
                        "config": {
                            key: config.get(key)
                            for key in (
                                "max_local_repairs",
                                "max_model_turns",
                                "hard_max_model_turns",
                                "invocation_timeout_seconds",
                                "model_request_timeout_seconds",
                            )
                        },
                    },
                    "allowed_intervention": "historical only; no new calls or writes",
                }
            )
    return result


def junit_counts(path: Path) -> dict[str, int]:
    try:
        root = ET.fromstring(path.read_bytes())
    except (OSError, ET.ParseError) as error:
        raise CollectionError("invalid JUnit evidence") from error
    cases = list(root.iter("testcase"))
    skipped = sum(case.find("skipped") is not None for case in cases)
    return {
        "tests": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": skipped,
        "executed": len(cases) - skipped,
    }


def nullable_number(value: Any) -> int | float | None:
    return value if type(value) in {int, float} and math.isfinite(value) and value >= 0 else None


def token_evidence(path: Path | None) -> dict[str, Any]:
    unknown = {
        key: None
        for key in (
            "primary_tokens",
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "token_source",
        )
    }
    if path is None:
        return {**unknown, "status": "unknown", "reason": "no attributable CLI stream"}
    spec = importlib.util.spec_from_file_location(
        "convergence_codex_usage", Path(__file__).with_name("codex_usage.py")
    )
    assert spec is not None and spec.loader is not None
    usage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(usage)
    try:
        return {**usage.extract(path), "status": "measured"}
    except (usage.UsageError, OSError, UnicodeError) as error:
        return {**unknown, "status": "unknown", "reason": str(error)}


def collect_cell(workspace: Path, cell: dict[str, Any]) -> dict[str, Any]:
    root = inside(workspace, cell["root"])
    expected_identity = identity(cell["identity"])
    issues: list[str] = []
    warnings: list[str] = []
    records: dict[str, dict[str, Any]] = {}
    xml_counts: dict[str, dict[str, int]] = {}
    for label, artifact in cell["artifacts"].items():
        path = inside(root, artifact["path"])
        if not path.is_file():
            issues.append(f"missing:{label}")
            continue
        if sha256(path) != artifact["sha256"]:
            issues.append(f"hash_mismatch:{label}")
            continue
        if path.suffix == ".json" and label != "preimages":
            try:
                records[label] = read_object(path)
            except CollectionError:
                issues.append(f"invalid_json:{label}")
        elif label in {"junit", "independent_junit"}:
            try:
                xml_counts[label] = junit_counts(path)
            except CollectionError:
                issues.append(f"invalid_junit:{label}")
    for label in ("packet", "coder", "completed", "validation", "post_state", "primary"):
        if label not in records:
            issues.append(f"required_record_unavailable:{label}")
    for label in ("packet", "coder", "primary", "reviewer", "compact", "reviewer_compact"):
        if label not in records:
            continue
        record = records[label]
        source = record.get("identity", record)
        if not isinstance(source, dict) or any(
            source.get(k) != v for k, v in expected_identity.items()
        ):
            issues.append(f"identity_mismatch:{label}")
    coder = records.get("coder", {})
    primary = records.get("primary", {})
    reviewer = records.get("reviewer", {})
    reviewer_outcome = reviewer.get("decision", "not_started")
    compact_failure = records.get("reviewer_compact", {})
    if not reviewer and compact_failure.get("decision") == "failed":
        # Failure telemetry is not an acceptance substitute for a canonical report.
        reviewer_outcome = "failed"
        issues.append("canonical_reviewer_failure_binding_unavailable")
        warnings.append("reviewer_failure_observed_in_compact_only")
    status = coder.get("status")
    if status not in {"ready_for_review", "failed", "blocked", "interrupted", "policy_violation"}:
        issues.append("missing_or_invalid_coder_status")
    if records.get("completed", {}).get("status") != status:
        issues.append("completion_status_mismatch")
    if "compact" in records and records["compact"].get("status") != status:
        issues.append("compact_status_mismatch")
    if (
        "reviewer" in records
        and "reviewer_compact" in records
        and (
            reviewer.get("decision") != records["reviewer_compact"].get("decision")
            or reviewer.get("identity") != records["reviewer_compact"].get("identity")
        )
    ):
        issues.append("reviewer_pointer_mismatch")
    if primary.get("decision") not in {"accept", "rework", "replan", "takeover"}:
        issues.append("missing_or_invalid_primary_decision")
    if primary.get("worker_status") != status:
        issues.append("primary_worker_status_mismatch")
    if primary.get("local_review_id") and primary["local_review_id"] != reviewer.get(
        "identity", {}
    ).get("review_id"):
        issues.append("primary_review_binding_mismatch")
    protected = all(
        inside(root, path).is_file() and sha256(inside(root, path)) == digest
        for path, digest in cell.get("protected_hashes", {}).items()
    )
    if not protected:
        issues.append("protected_input_changed")
    inputs = records.get("post_state", {}).get("validation_inputs")
    current: bool | None = None
    if isinstance(inputs, dict) and inputs:
        current = all(
            isinstance(fact, dict)
            and fact.get("exists") is True
            and inside(root, path).is_file()
            and sha256(inside(root, path)) == fact.get("sha256")
            for path, fact in inputs.items()
        )
        if not current:
            issues.append("validation_input_changed")
    else:
        warnings.append("validation_inputs_unknown")
    validation = records.get("validation", {})
    focused = validation.get("focused_tests") or {}
    counts = focused.get("junit") or {}
    runtime_counts = {
        key: counts.get(key) for key in ("tests", "failures", "errors", "skipped", "executed")
    }
    if "junit" in xml_counts and runtime_counts != xml_counts["junit"]:
        issues.append("runtime_junit_mismatch")
    if status == "ready_for_review" and "junit" not in xml_counts:
        issues.append("missing_executed_junit")
    checks = [
        {"id": check.get("id"), "status": check.get("status")}
        for check in validation.get("configured_checks", [])
    ]
    for role, value in (
        ("coder", coder.get("protocol_error_count")),
        ("reviewer", reviewer.get("runtime_facts", {}).get("protocol_error_count")),
    ):
        if value is None:
            warnings.append(f"{role}_protocol_count_unknown")
    passed = (
        status == "ready_for_review"
        and validation.get("status") == "passed"
        and focused.get("status") == "passed"
        and focused.get("inputs_unchanged") is True
        and type(counts.get("executed")) is int
        and counts["executed"] > 0
        and counts.get("failures") == 0
        and counts.get("errors") == 0
        and all(check["status"] == "passed" for check in checks)
        and current is True
        and protected
    )
    if status == "ready_for_review" and not passed:
        issues.append("readiness_evidence_incomplete")
    invocation = records.get("local_invocation", {})
    cost = {
        "loading_seconds": None,
        "inference_seconds": None,
        "validation_seconds": None,
        "local_unit_wall_seconds": nullable_number(invocation.get("seconds")),
        "primary_preparation_seconds": None,
        "primary_intervention_seconds": None,
        "primary_review_seconds": None,
        "primary_active_seconds": None,
        "cloud": token_evidence(None),
        "savings": "unmeasured",
    }
    if "cloud_stream" in cell["artifacts"] and not any(
        issue.endswith(":cloud_stream") for issue in issues
    ):
        cost["cloud"] = token_evidence(inside(root, cell["artifacts"]["cloud_stream"]["path"]))
    infra = coder.get("infra_failure") or reviewer.get("infra_failure")
    if infra:
        warnings.append("historical_infrastructure_failure")
    return {
        "cell_id": cell["cell_id"],
        "identity": expected_identity,
        "collection_status": "complete" if not issues else "incomplete",
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
        "protocol_valid": None if issues else True,
        "protocol_valid_definition": "stored report shape, identity and provenance only",
        "coder_status": status,
        "semantic_outcome": primary.get("decision"),
        "validation_current": current,
        "validation_status": validation.get("status"),
        "runtime_junit": runtime_counts,
        "configured_checks": checks,
        "actual_runtime_junit": xml_counts.get("junit"),
        "independent_junit": xml_counts.get("independent_junit"),
        "protected_inputs_unchanged": protected,
        "reviewer_outcome": reviewer_outcome,
        "primary_decision": primary.get("decision"),
        "coder_protocol_errors": coder.get("protocol_error_count"),
        "reviewer_protocol_errors": reviewer.get("runtime_facts", {}).get("protocol_error_count"),
        "infra_failure": infra,
        "failure_signature": coder.get("failure_signature"),
        "repair_count": coder.get("repair_count"),
        "cost": cost,
        "validation_attempts": [
            {
                "artifact": label,
                "status": value.get("status"),
                "edit_revision": value.get("edit_revision"),
                "focused_tests": value.get("focused_tests"),
            }
            for label, value in records.items()
            if label.startswith("validation-attempt-")
        ],
        "expected_matches": status == cell["expected"].get("coder_status")
        and primary.get("decision") == cell["expected"].get("primary_decision")
        and reviewer_outcome == cell["expected"].get("reviewer_outcome"),
        "historical_acceptance_evidence_eligible": bool(
            not issues
            and not infra
            and passed
            and reviewer.get("decision") == "pass_to_primary"
            and primary.get("decision") == "accept"
        ),
    }


def collect(workspace: Path, registration: dict[str, Any]) -> dict[str, Any]:
    if (
        registration.get("schema_version") != 1
        or registration.get("worker_launch_allowed") is not False
    ):
        raise CollectionError("only schema-v1 read-only registrations are supported")
    cells = registration.get("cells")
    if not isinstance(cells, list) or not cells:
        raise CollectionError("registration needs cells")
    if len({cell["cell_id"] for cell in cells}) != len(cells):
        raise CollectionError("duplicate cell_id")
    refs = [registration["baseline"], *registration.get("source_batches", [])]
    if registration.get("expectations_source"):
        refs.append(registration["expectations_source"])
    for artifact in refs:
        if sha256(inside(workspace, artifact["path"])) != artifact["sha256"]:
            raise CollectionError("registration source changed")
    results = [collect_cell(workspace, cell) for cell in cells]
    return {
        "schema_version": 1,
        "experiment_id": registration["experiment_id"],
        "stage": "P1",
        "collector_sha256": sha256(Path(__file__)),
        "registered_cells": len(cells),
        "collected_cells": len(results),
        "worker_calls": 0,
        "replayed_historical_outcomes": True,
        "cells": results,
        "complete_cells": sum(item["collection_status"] == "complete" for item in results),
        "historical_primary_accepts": sum(item["primary_decision"] == "accept" for item in results),
        "historical_primary_rework": sum(item["primary_decision"] == "rework" for item in results),
        "unknown_cloud_cost_cells": sum(
            item["cost"]["cloud"]["status"] == "unknown" for item in results
        ),
        "all_expected_match": all(item["expected_matches"] for item in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "collect"))
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", required=True)
    parser.add_argument("--registration")
    parser.add_argument("--baseline")
    parser.add_argument("--batch", action="append", default=[])
    parser.add_argument("--experiment-id")
    parser.add_argument("--expectations")
    args = parser.parse_args()
    try:
        if args.action == "register":
            if (
                not args.baseline
                or not args.batch
                or not args.experiment_id
                or not args.expectations
            ):
                raise CollectionError(
                    "register requires baseline, batches, experiment-id, expectations"
                )
            expected = read_object(inside(args.workspace, args.expectations))
            result = build_registration(
                args.workspace, args.batch, args.baseline, args.experiment_id, expected
            )
            result["expectations_source"] = ref(args.workspace, args.expectations)
        else:
            if not args.registration:
                raise CollectionError("collect requires registration")
            result = collect(args.workspace, read_object(inside(args.workspace, args.registration)))
        write_output(args.workspace, args.output, result)
        print(
            json.dumps(
                {
                    "output": args.output,
                    "cells": len(result["cells"]),
                    "worker_calls": 0,
                    "complete_cells": result.get("complete_cells"),
                }
            )
        )
        return 0
    except (CollectionError, OSError, KeyError, TypeError) as error:
        print(f"convergence collection failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
