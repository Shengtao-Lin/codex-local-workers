"""One frozen, Primary-authored localization-only Coordinator route smoke."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import uuid
from dataclasses import asdict

import stability_e2e as STABILITY


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def runtime_manifest(config: dict) -> dict:
    """Bind a route cell to the kit code, role config, and Python version."""
    paths = [
        STABILITY.KIT / "benchmarks" / "stability_e2e.py",
        STABILITY.KIT / "benchmarks" / "sample_identity_split_route.py",
        STABILITY.KIT / "benchmarks" / "localization-cohort-v2.1.json",
        *(STABILITY.KIT / "benchmarks").glob("localization_route_*.py"),
        *(STABILITY.KIT / ".local-agents").glob("*.py"),
        *(STABILITY.KIT / ".local-agents").glob("*.ps1"),
    ]
    files = {
        path.relative_to(STABILITY.KIT).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(paths)
    }
    manifest = {
        "schema_version": 1,
        "files": files,
        "role_config_sha256": _sha256_json(config),
        "python_version": list(sys.version_info[:3]),
    }
    return {"runtime_sha256": _sha256_json(manifest), "runtime_manifest": manifest}


def primary_plan_for_packet(packet: dict) -> dict:
    """Freeze Primary authority before invoking either local model worker."""
    scope = packet["scope"]
    return {
        "schema_version": 1,
        "plan_revision": packet["plan_revision"],
        "task_id": packet["task_id"],
        "feature_id": packet["feature_id"],
        "feature_risk": packet["risk"]["feature"],
        "integration_risk": packet["risk"]["integration"],
        "contracts": [
            {"id": item["id"], "risk_floor": item["risk_floor"], "text": item["text"]}
            for item in packet["required_behavior"]
        ],
        "units": [
            {
                "unit_id": packet["unit_id"],
                "risk": packet["risk"]["unit"],
                "owner": "local-coder",
                "dependencies": copy.deepcopy(packet["dependencies"]),
                "owned_contract_ids": copy.deepcopy(packet["owned_contract_ids"]),
                "scope_authority": {
                    "read_roots": copy.deepcopy(scope["read"]),
                    "modify": copy.deepcopy(scope["modify"]),
                    "create": copy.deepcopy(scope["create"]),
                    "readonly": copy.deepcopy(scope["readonly"]),
                    "forbidden": copy.deepcopy(scope["forbidden"]),
                },
                "packet_contract": {
                    "acceptance_criteria": copy.deepcopy(packet["acceptance_criteria"]),
                    "acceptance_scenarios": copy.deepcopy(
                        packet["acceptance_scenarios"]
                    ),
                    "required_order": copy.deepcopy(packet["required_order"]),
                    "forbidden_orderings": copy.deepcopy(packet["forbidden_orderings"]),
                    "validation_profile": packet["validation_profile"],
                    "required_focused_tests": copy.deepcopy(packet["focused_tests"]),
                },
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="mapping-message-sequence")
    parser.add_argument("--unknown-location", action="store_true")
    args = parser.parse_args()
    cases = {case.name: case for case in STABILITY.CASES}
    if args.case not in cases:
        parser.error(f"unknown frozen case: {args.case}")
    case = cases[args.case]
    source_config = json.loads(
        (STABILITY.KIT / ".local-agents" / "config.json").read_text(
            encoding="utf-8-sig"
        )
    )
    source_config["explorer_mode"] = "locate"
    provenance = runtime_manifest(source_config)
    variant = "unknown" if args.unknown_location else "known"
    root = STABILITY.WORK / f"route-{variant}-{uuid.uuid4().hex[:12]}" / case.name
    config_path, packet_path = STABILITY.prepare(case, root, source_config)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["required_order"] = []
    packet["forbidden_orderings"] = []
    plan = primary_plan_for_packet(packet)
    sys.path.insert(0, str(STABILITY.KIT / ".local-agents"))
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "frozen_route_contract",
        STABILITY.KIT / ".local-agents" / "coordinator-contract.py",
    )
    assert spec is not None and spec.loader is not None
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    packet = contract.materialize_bounded_packet(
        plan,
        {
            "unit_id": packet["unit_id"],
            "run_id": packet["run_id"],
            "attempt": packet["attempt"],
            "packet_revision": packet["packet_revision"],
            "goal": packet["goal"],
            "scope": {
                key: packet["scope"][key] for key in ("read", "modify", "create")
            },
            "edit_targets": packet["edit_targets"],
            "focused_tests": packet["focused_tests"],
            "supplemental_tests": packet.get("supplemental_tests", []),
            "implementation_guidance": packet["implementation_guidance"],
        },
    )
    STABILITY.write_json(packet_path, packet)
    plan_path = root / ".agent" / "feature-plan.json"
    STABILITY.write_json(plan_path, plan)
    test_path = f"tests/test_{case.name.replace('-', '_')}.py"
    if args.unknown_location:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["explorer_required_citation_paths"] = [test_path]
        STABILITY.write_json(config_path, config)
        symbols = (
            "content_fingerprint and score_reuse_key"
            if case.name == "sample-identity"
            else case.anchor.split("=", 1)[0].strip()
        )
        question = (
            f"Locate each implementation of {symbols} that controls the behavior in "
            f"{test_path}. Find the real files and line ranges with READ_FILE/SEARCH, "
            "and cite the focused test assertions. Return locations only, not a repair "
            "or a prediction that tests pass."
        )
    else:
        question = STABILITY.explorer_task(case, test_path, "locate")
    provenance["case_input_sha256"] = _sha256_json(
        {
            "case": asdict(case),
            "question": question,
            "unknown_location": args.unknown_location,
        }
    )
    request_path = root / ".agent" / "localization-request.json"
    STABILITY.write_json(
        request_path,
        {
            "capability": "localization_only",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": question,
        },
    )
    baseline = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", test_path, "-q"], 90
    )
    baseline_lint = (
        STABILITY.run_command(
            root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
        )
        if case.baseline_static_rule is not None
        else None
    )
    baseline_failed = baseline.returncode != 0 or (
        baseline_lint is not None and baseline_lint.returncode != 0
    )
    explorer_path = root / ".agent" / "explorer-full-report.json"
    explorer = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(STABILITY.KIT / ".local-agents" / "local-explore.py"),
            "--task",
            question,
            "--task-id",
            packet["task_id"],
            "--config",
            str(config_path),
            "--report",
            str(explorer_path),
            "--full-report",
        ],
        600,
    )
    full = (
        json.loads(explorer_path.read_text(encoding="utf-8"))
        if explorer_path.is_file()
        else {}
    )
    if explorer.returncode != 0 or not STABILITY.explorer_has_line_evidence(
        full, case, test_path
    ):
        result = {
            "workspace": str(root),
            "case": case.name,
            "unknown_location": args.unknown_location,
            "question_version": 2,
            "question": question,
            "stage": "explorer",
            "baseline_failed": baseline_failed,
            "explorer_status": full.get("status"),
            "explorer_evidence_valid": False,
            "explorer_report": str(explorer_path),
            "explorer_infra_failure": full.get("infra_failure"),
            "route_exit": None,
            "route": None,
            "independent_tests_passed": None,
            "independent_format_passed": None,
            "independent_lint_passed": None,
            "qualified_pass": False,
            "provenance": provenance,
            "runtime_changed_during_run": (
                runtime_manifest(source_config)["runtime_sha256"]
                != provenance["runtime_sha256"]
            ),
        }
        STABILITY.write_json(root / "route-result.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return 2
    route = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(STABILITY.KIT / ".local-agents" / "coordinator-localization.py"),
            "--plan",
            str(plan_path),
            "--packet",
            str(packet_path),
            "--request",
            str(request_path),
            "--explorer-report",
            str(explorer_path),
            "--config",
            str(config_path),
        ],
        1200,
    )
    try:
        routed = json.loads(route.stdout)
    except ValueError:
        routed = {"output_tail": (route.stdout + route.stderr)[-1000:]}
    independent = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", test_path, "-q"], 90
    )
    fmt = STABILITY.run_command(
        root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"], 90
    )
    lint = STABILITY.run_command(
        root, [sys.executable, "-m", "ruff", "check", "src", "tests"], 90
    )
    result = {
        "workspace": str(root),
        "case": case.name,
        "unknown_location": args.unknown_location,
        "question_version": 2,
        "question": question,
        "stage": "route",
        "baseline_failed": baseline_failed,
        "explorer_status": full.get("status"),
        "explorer_evidence_valid": True,
        "explorer_report": str(explorer_path),
        "explorer_infra_failure": full.get("infra_failure"),
        "route_exit": route.returncode,
        "route": routed,
        "independent_tests_passed": independent.returncode == 0,
        "independent_format_passed": fmt.returncode == 0,
        "independent_lint_passed": lint.returncode == 0,
        "provenance": provenance,
        "runtime_changed_during_run": (
            runtime_manifest(source_config)["runtime_sha256"]
            != provenance["runtime_sha256"]
        ),
    }
    result["qualified_pass"] = (
        result["baseline_failed"]
        and route.returncode == 0
        and routed.get("status") == "primary_review_required"
        and routed.get("unit_result", {}).get("reviewer_decision") == "pass_to_primary"
        and result["independent_tests_passed"]
        and result["independent_format_passed"]
        and result["independent_lint_passed"]
        and not result["runtime_changed_during_run"]
    )
    STABILITY.write_json(root / "route-result.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["qualified_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
