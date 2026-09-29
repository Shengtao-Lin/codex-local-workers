"""Frozen two-unit sample-identity localization experiment.

The phases deliberately stop between units for an independent Primary review.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

import localization_route_smoke as ROUTE
import stability_e2e as STABILITY

CASE = next(case for case in STABILITY.CASES if case.name == "sample-identity")
TASK_ID = "stability-sample-identity-split"
TEST = "tests/test_sample_identity.py"
UNITS = {
    "fingerprint": {
        "target": "src/evaluation_harness/canonical/fingerprint.py",
        "symbol": "content_fingerprint",
        "contracts": ["behavior-1"],
        "dependencies": [],
        "focused_tests": [
            f"{TEST}::test_content_fingerprint_ignores_row_identity",
            f"{TEST}::test_content_fingerprint_ignores_existing_volatile_fields",
        ],
        "scenarios": [
            "Changing sample_id leaves content_fingerprint unchanged.",
            "Changing labels and source_metadata leaves content_fingerprint unchanged.",
        ],
        "anchor": 'content = sample.model_dump(mode="json")',
        "guidance": (
            "The existing VOLATILE_CONTENT_FIELDS is the authoritative excluded "
            "set; use JSON-mode model serialization and preserve canonical hashing. "
            "Do not change score_reuse_key or the protected tests."
        ),
    },
    "reuse-key": {
        "target": "src/evaluation_harness/evaluations/dedup.py",
        "symbol": "score_reuse_key",
        "contracts": ["behavior-2", "behavior-3", "behavior-4"],
        "dependencies": ["fingerprint"],
        "focused_tests": [
            f"{TEST}::test_score_reuse_key_ignores_row_identity_and_mapping_order",
            f"{TEST}::test_score_reuse_key_preserves_source_metadata_as_scoring_input",
            f"{TEST}::test_fingerprint_ignores_source_metadata_but_reuse_key_preserves_it",
            f"{TEST}::test_fingerprint_ignores_labels_but_reuse_key_preserves_them",
        ],
        "scenarios": [
            "Changing sample_id or mapping key order leaves score_reuse_key unchanged.",
            "Changing source_metadata or labels changes score_reuse_key but not content_fingerprint.",
            "The scorer/config payload, cacheability guard, and digest format remain intact.",
        ],
        "anchor": '"sample": sample.model_dump(mode="json"),',
        "guidance": (
            "Exclude only sample_id from JSON-mode model serialization in the "
            "sample payload. Preserve source_metadata, labels, nested messages, "
            "scorer/config fields, sorted-key JSON, cacheability guard, and digest shape. "
            "Do not edit the already accepted fingerprint implementation or tests."
        ),
    },
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_module():
    spec = importlib.util.spec_from_file_location(
        "split_route_contract",
        STABILITY.KIT / ".local-agents" / "coordinator-contract.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def feature_plan(base_packet: dict) -> dict:
    contracts = copy.deepcopy(base_packet["required_behavior"])
    units = []
    for unit_id, choice in UNITS.items():
        units.append(
            {
                "unit_id": unit_id,
                "risk": "medium",
                "owner": "local-coder",
                "dependencies": choice["dependencies"],
                "owned_contract_ids": choice["contracts"],
                "scope_authority": {
                    "read_roots": ["src", "tests", "conftest.py"],
                    "modify": [choice["target"]],
                    "create": [],
                    "readonly": [TEST],
                    "forbidden": [],
                },
                "packet_contract": {
                    "acceptance_criteria": copy.deepcopy(
                        base_packet["acceptance_criteria"]
                    ),
                    "acceptance_scenarios": [
                        {
                            "id": f"{unit_id}-scenario-{index}",
                            "text": text,
                            "observables": {"protected_test_assertion": True},
                        }
                        for index, text in enumerate(choice["scenarios"], 1)
                    ],
                    "required_order": [],
                    "forbidden_orderings": [],
                    "validation_profile": "stability-strict",
                    "required_focused_tests": choice["focused_tests"],
                },
            }
        )
    return {
        "schema_version": 1,
        "plan_revision": 1,
        "task_id": TASK_ID,
        "feature_id": TASK_ID,
        "feature_risk": "medium",
        "integration_risk": "medium",
        "contracts": contracts,
        "units": units,
    }


def split_provenance() -> dict:
    source_config = read_json(STABILITY.KIT / ".local-agents" / "config.json")
    source_config["explorer_mode"] = "locate"
    return {
        **ROUTE.runtime_manifest(source_config),
        "case_input_sha256": ROUTE._sha256_json(
            {"case": asdict(CASE), "units": UNITS, "variant": "dependent-split"}
        ),
    }


def require_frozen_provenance(root: Path) -> None:
    recorded = read_json(root / ".agent" / "split-provenance.json")
    current = split_provenance()
    if (
        recorded.get("runtime_sha256") != current["runtime_sha256"]
        or recorded.get("case_input_sha256") != current["case_input_sha256"]
    ):
        raise ValueError("split fixture runtime, role config, or case input changed")


def prepare() -> Path:
    source_config = read_json(STABILITY.KIT / ".local-agents" / "config.json")
    source_config["explorer_mode"] = "locate"
    root = STABILITY.WORK / f"route-split-{uuid.uuid4().hex[:12]}" / CASE.name
    config_path, packet_path = STABILITY.prepare(CASE, root, source_config)
    STABILITY.write_json(root / ".agent" / "split-provenance.json", split_provenance())
    base_packet = read_json(packet_path)
    plan = feature_plan(base_packet)
    contracts = plan["contracts"]
    contract = contract_module()
    contract.validate_feature_plan(plan)
    STABILITY.write_json(root / ".agent" / "split-feature-plan.json", plan)
    for unit_id, choice in UNITS.items():
        proposal = {
            "unit_id": unit_id,
            "run_id": f"{unit_id}-a1",
            "attempt": 1,
            "packet_revision": 1,
            "goal": next(
                item["text"]
                for item in contracts
                if item["id"] == choice["contracts"][0]
            ),
            "scope": {
                "read": ["src", "tests", "conftest.py"],
                "modify": [choice["target"]],
                "create": [],
            },
            "edit_targets": [{"path": choice["target"], "anchor": choice["anchor"]}],
            "focused_tests": choice["focused_tests"],
            "supplemental_tests": [],
            "implementation_guidance": [choice["guidance"]],
        }
        packet = contract.materialize_bounded_packet(plan, proposal)
        STABILITY.write_json(root / ".agent" / f"split-{unit_id}-packet.json", packet)
        config = read_json(config_path)
        config["explorer_required_citation_paths"] = [TEST]
        STABILITY.write_json(root / ".agent" / f"split-{unit_id}-config.json", config)
    baseline = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", TEST, "-q"], 90
    )
    STABILITY.write_json(
        root / "split-baseline.json",
        {
            "baseline_failed": baseline.returncode != 0,
            "output_tail": baseline.stdout[-1000:],
        },
    )
    return root


def run_unit(root: Path, unit_id: str) -> dict:
    require_frozen_provenance(root)
    choice = UNITS[unit_id]
    plan_path = root / ".agent" / "split-feature-plan.json"
    if unit_id == "reuse-key":
        accepted = contract_module().accepted_units_from_archives(
            read_json(plan_path),
            root,
            {"fingerprint": {"task_id": TASK_ID, "run_id": "fingerprint-a1"}},
        )
        if accepted != {"fingerprint"}:
            raise ValueError("reuse-key requires accepted fingerprint archive")
    packet_path = root / ".agent" / f"split-{unit_id}-packet.json"
    config_path = root / ".agent" / f"split-{unit_id}-config.json"
    request_path = root / ".agent" / f"split-{unit_id}-request.json"
    report_path = root / ".agent" / f"split-{unit_id}-explorer-report.json"
    question = (
        f"Locate the implementation of {choice['symbol']} and the related assertions "
        f"in {TEST}. Use SEARCH and READ_FILE to cite actual file/line evidence. "
        "Return locations only, not a proposed repair."
    )
    STABILITY.write_json(
        request_path,
        {
            "capability": "localization_only",
            "task_id": TASK_ID,
            "unit_id": unit_id,
            "question": question,
        },
    )
    explorer = STABILITY.run_command(
        root,
        [
            sys.executable,
            str(STABILITY.KIT / ".local-agents" / "local-explore.py"),
            "--task",
            question,
            "--task-id",
            TASK_ID,
            "--config",
            str(config_path),
            "--report",
            str(report_path),
            "--full-report",
        ],
        600,
    )
    full = read_json(report_path) if report_path.is_file() else {}
    if explorer.returncode != 0:
        return {
            "stage": "explorer",
            "unit_id": unit_id,
            "status": full.get("status"),
            "report": str(report_path),
        }
    run_refs_path = root / ".agent" / "split-run-refs.json"
    if unit_id == "reuse-key":
        STABILITY.write_json(
            run_refs_path,
            {"fingerprint": {"task_id": TASK_ID, "run_id": "fingerprint-a1"}},
        )
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
            str(report_path),
            "--config",
            str(config_path),
            *(["--run-refs", str(run_refs_path)] if unit_id == "reuse-key" else []),
        ],
        1200,
    )
    try:
        routed = json.loads(route.stdout)
    except ValueError:
        routed = {"output_tail": (route.stdout + route.stderr)[-1000:]}
    focused = STABILITY.run_command(
        root, [sys.executable, "-m", "pytest", *choice["focused_tests"], "-q"], 90
    )
    result = {
        "unit_id": unit_id,
        "explorer_status": full.get("status"),
        "explorer_report": str(report_path),
        "route_exit": route.returncode,
        "route": routed,
        "independent_focused_passed": focused.returncode == 0,
        "independent_focused_tail": focused.stdout[-700:],
    }
    STABILITY.write_json(root / f"split-{unit_id}-result.json", result)
    return result


def verify(root: Path, *, record_integration: bool = False) -> dict:
    require_frozen_provenance(root)
    outcomes = {}
    checks = []
    for name, argv in {
        "integration_tests": [sys.executable, "-m", "pytest", TEST, "-q"],
        "ruff_check": [sys.executable, "-m", "ruff", "check", "src", "tests"],
        "ruff_format": [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "src",
            "tests",
        ],
    }.items():
        result = STABILITY.run_command(root, argv, 90)
        outcomes[name] = {
            "passed": result.returncode == 0,
            "output_tail": result.stdout[-600:],
        }
        checks.append(
            {
                "id": name,
                "argv": argv,
                "status": "passed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
            }
        )
    STABILITY.write_json(root / "split-integration-result.json", outcomes)
    if record_integration:
        if not all(item["passed"] for item in outcomes.values()):
            raise ValueError("failed integration checks cannot be archived as passed")
        plan = read_json(root / ".agent" / "split-feature-plan.json")
        contract = contract_module()
        run_refs = {
            unit_id: {"task_id": TASK_ID, "run_id": f"{unit_id}-a1"}
            for unit_id in UNITS
        }
        if contract.accepted_units_from_archives(plan, root, run_refs) != set(UNITS):
            raise ValueError("both units need archive-backed Primary acceptance")
        paths = [choice["target"] for choice in UNITS.values()] + [TEST, "conftest.py"]
        evidence = {
            "schema_version": 1,
            "feature_id": plan["feature_id"],
            "plan_revision": plan["plan_revision"],
            "primary_plan_sha256": contract.authority_fingerprint(plan),
            "integration_risk": plan["integration_risk"],
            "status": "passed",
            "checks": checks,
            "files": [
                {
                    "path": path,
                    "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest(),
                }
                for path in paths
            ],
        }
        integration_path = (
            root / ".agent" / "integration" / plan["feature_id"] / "validation.json"
        )
        if integration_path.exists():
            raise ValueError("integration archive already exists; never overwrite it")
        STABILITY.write_json(integration_path, evidence)
        contract.validate_decision_transition(
            plan,
            {"decision": "FEATURE_READY", "unit_id": "reuse-key"},
            repo_root=root,
            run_refs=run_refs,
        )
        outcomes["feature_ready_eligible"] = True
        outcomes["integration_archive"] = str(integration_path)
    return outcomes


def inspect_feature(root: Path) -> dict:
    """Replay the archive-backed gate without modifying a frozen snapshot."""
    argv = [
        sys.executable,
        str(STABILITY.KIT / ".local-agents" / "coordinator-localization.py"),
        "--plan",
        str(root / ".agent" / "split-feature-plan.json"),
        "--inspect-feature",
        "--unit-id",
        "reuse-key",
    ]
    for unit_id in UNITS:
        argv.extend(("--run-ref", unit_id, TASK_ID, f"{unit_id}-a1"))
    result = STABILITY.run_command(root, argv, 30)
    try:
        inspection = json.loads(result.stdout)
    except ValueError:
        inspection = {"output_tail": (result.stdout + result.stderr)[-1000:]}
    return {"inspection_exit": result.returncode, "inspection": inspection}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("first", "second", "verify", "inspect"))
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--record-integration", action="store_true")
    args = parser.parse_args()
    if args.record_integration and args.phase != "verify":
        parser.error("--record-integration is only valid with verify")
    if args.phase == "first":
        if args.workspace is not None:
            parser.error("first creates a fresh frozen workspace; omit --workspace")
        root = prepare()
        result = run_unit(root, "fingerprint")
    else:
        if args.workspace is None:
            parser.error("second, verify and inspect require --workspace")
        root = args.workspace.resolve()
        if not (root / ".agent" / "split-feature-plan.json").is_file():
            parser.error("workspace has no split feature plan")
        if args.phase == "second":
            result = run_unit(root, "reuse-key")
        elif args.phase == "verify":
            result = verify(root, record_integration=args.record_integration)
        else:
            result = inspect_feature(root)
    print(
        json.dumps(
            {"workspace": str(root), "phase": args.phase, "result": result},
            ensure_ascii=False,
        )
    )
    if args.phase == "verify":
        return (
            0
            if all(
                result[key]["passed"]
                for key in ("integration_tests", "ruff_check", "ruff_format")
            )
            else 1
        )
    if args.phase == "inspect":
        return 0 if result["inspection_exit"] == 0 else 1
    return (
        0
        if result.get("route_exit") == 0 and result["independent_focused_passed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
