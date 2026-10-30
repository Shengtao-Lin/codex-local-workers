"""One bounded live trial on exact real modules; never accepts a feature itself."""

import argparse
import ast
import copy
import json
import shutil
import sys
from pathlib import Path

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
import coordinator_numeric_split as split
import localization_route_smoke as route
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "real-adapter-live-2"
SNAPSHOT = WORK / "real-adapter-live-baseline-1"
ROOT = BASE / "candidate"
FROZEN = KIT / "benchmarks/fixtures/real-adapter-datetime-v3"
PREPARED = WORK / "real-adapter-datetime-trial-3"
COMMON = "src/evaluation_harness/adapters/common.py"
UNIT = "normalize-unit"
IDENTITY = "coordinator-r1"
TESTS = [
    "tests/test_datetime_trial.py::" + name
    for name in (
        "test_datetime_identity",
        "test_utc_suffix",
        "test_offset_preserved",
        "test_naive_string_utc",
        "test_fallback_identity",
        "test_invalid_string",
        "test_real_adapter_roundtrip",
    )
] + [
    "tests/unit/test_adapters.py::" + name
    for name in (
        "test_generic_turn_mode_embeds_history",
        "test_generic_trace_mode_is_one_row",
        "test_runtime_kit_public_attributes_are_supported",
    )
]
QUESTION = (
    "Locate the existing private _datetime definition and the build_samples event_time "
    "assignment in src/evaluation_harness/adapters/common.py, the real normalize caller "
    "in src/evaluation_harness/adapters/generic_otel.py, and test_naive_string_utc, "
    "test_invalid_string and test_real_adapter_roundtrip assertions in tests/test_datetime_trial.py. "
    "One timestamp call-path localization question only. Use literal SEARCH for those "
    "symbols and bounded READ_FILE ranges, not repeated whole-file reads. The helper "
    "is near the end of common.py. Cite actual definition/caller/test lines, distinguish "
    "current faulty behavior from test requirements; locations only, no repair or validation prediction."
)


def case():
    return {
        "goal": "Restore the existing private timestamp normalization contract within exact real adapter modules and preserve trace/turn behavior; no broader public API or identity changes."
    }


def configure():
    pilot.BASE, pilot.SNAPSHOT = BASE, SNAPSHOT
    pilot.fixture = sys.modules[__name__]
    split.BASE, split.SNAPSHOT = BASE, SNAPSHOT
    split.QUESTIONS = {
        "flow": (
            [
                COMMON,
                "src/evaluation_harness/adapters/generic_otel.py",
                "tests/test_datetime_trial.py",
            ],
            QUESTION,
        )
    }
    return pilot.configure()


def prepare():
    preparation = read(PREPARED / "preflight.json")
    if (
        not preparation["passed"]
        or not read(FROZEN / "trial-summary.json")["fixture_ready"]
    ):
        raise ValueError("accepted deterministic fixture preparation required")
    provenance = read(FROZEN / "provenance.json")
    original = provenance["copied_original_files"]
    for path, sha in original.items():
        if digest(FROZEN / path) != sha:
            raise ValueError("frozen source drift")
    extra = provenance["primary_added_test"]
    if digest(FROZEN / extra["path"]) != extra["sha256"]:
        raise ValueError("protected acceptance drift")
    if SNAPSHOT.exists():
        pilot.matrix.SCOPE.FA.LAYER.verify_hashes(
            SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"]
        )
    else:
        freeze(SNAPSHOT.name)
    contract = configure()
    ROOT.mkdir(parents=True, exist_ok=False)
    paths = [*original, extra["path"]]
    for path in paths:
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        source = PREPARED / "combined" / path
        shutil.copyfile(source, target)
        expected = digest(FROZEN / path) if path != COMMON else digest(source)
        if digest(target) != expected:
            raise ValueError("candidate copy differs from protected source")
    config = read(
        WORK
        / "coordinator-sample-task-1/runs/v1/sampletask1/labelled-receipt-round-1/.agent/config.json"
    )
    config["coordinator_enabled"] = True
    config["explorer_required_citation_paths"] = split.QUESTIONS["flow"][0]
    config["validation_profiles"]["mixed-strict"]["pytest_argv"] += [
        "--basetemp=" + str(ROOT / ".agent/validation-temp")
    ]
    write(ROOT / ".agent/config.json", config)
    packet = copy.deepcopy(
        read(
            WORK
            / "coordinator-sample-task-1/runs/v1/sampletask1/labelled-receipt-round-1/.agent/normalize-unit-bound.json"
        )
    )
    task_id = "real-adapter-live-2"
    packet.update(
        task_id=task_id,
        feature_id=task_id,
        run_id=task_id + "-normalize-unit-a1",
        scope={
            "read": ["src", "tests"],
            "modify": [COMMON],
            "create": [],
            "readonly": [
                p for p in paths if p != COMMON and p.startswith(("src/", "tests/"))
            ],
            "forbidden": [".git", ".agent", ".local-agents"],
        },
        edit_targets=[{"path": COMMON, "anchor": "_datetime", "line_hint": 251}],
        focused_tests=TESTS,
        dependencies=[],
        implementation_guidance=[],
        review_feedback=[],
    )
    behavior = (
        "Restore only existing private _datetime(value, default) in common.py. Existing datetime "
        "objects, including naive ones, return unchanged by identity. Parse strings after Z->+00:00; "
        "preserve aware offsets/wall time, attach UTC only to parsed naive strings. Invalid strings "
        "propagate ValueError, never silently fallback. All other inputs return default by identity. "
        "Preserve inputs and real GenericOtelAdapter.normalize/build_samples trace/turn results, "
        "message roles, sample IDs and timestamp JSON roundtrip. No other function/class/import "
        "semantics, schemas, public adapter version/compatibility, network or storage changes. "
        "All tests and other source files are read-only."
    )
    packet.update(
        goal=behavior,
        risk={
            "feature": "medium",
            "unit": "medium",
            "integration": "medium",
            "reasons": [
                "Existing private normalization restoration; public models, identity and adapter call paths protected and unchanged."
            ],
        },
        required_behavior=[{"id": UNIT, "risk_floor": "medium", "text": behavior}],
        acceptance_scenarios=[
            {
                "id": "normal",
                "text": "Real adapters preserve samples and aware offsets.",
                "observables": {
                    "datetime_identity": True,
                    "offset_minutes": 330,
                    "real_adapter_modes": ["trace", "turn"],
                },
            },
            {
                "id": "error",
                "text": "Invalid timestamp rejected through real adapter.",
                "observables": {"exception": "ValueError", "silent_fallback": False},
            },
            {
                "id": "boundary",
                "text": "Naive string UTC and fallback identity.",
                "observables": {
                    "naive_string_tz": "UTC",
                    "non_string_default_identity": True,
                },
            },
        ],
    )
    packet.pop("primary_plan_sha256", None)
    plan = route.primary_plan_for_packet(packet)
    packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
    packet = contract.validate_unit_packet(plan, packet)
    load_worker(SNAPSHOT).validate_packet(packet)
    write(ROOT / ".agent/feature-plan.json", plan)
    write(ROOT / ".agent/normalize-unit-bound.json", packet)
    paths += [
        ".agent/config.json",
        ".agent/feature-plan.json",
        ".agent/normalize-unit-bound.json",
    ]
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": [
                {
                    "id": IDENTITY,
                    "arm": "coordinator",
                    "case": "real-datetime",
                    "root": str(ROOT),
                    "units": [UNIT],
                    "hashes": {p: digest(ROOT / p) for p in paths},
                }
            ],
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, pilot.__file__, evidence.__file__, split.__file__)
            },
        },
    )
    baseline = pilot.matrix.SCOPE.FA.LAYER.check(ROOT, "baseline")
    counts = evidence.counts(ROOT / ".agent/baseline.xml")
    expected = {"tests": 10, "failures": 3, "errors": 0, "skipped": 0}
    write(
        BASE / "preflight-1.json",
        {
            "all_pass": counts == expected,
            "baseline": baseline,
            "junit": counts,
            "reference_preflight": str(PREPARED / "preflight.json"),
            "initial_F401": "UTC import unused only because injected naive-time defect removed its use; restore helper instead of dropping needed import",
        },
    )
    write(
        BASE / "registration.json",
        {
            "weekly_used_start": 10,
            "weekly_used_ceiling": 18,
            "expected": "One fresh accepted Explorer, one bounded Coordinator proposal, one real Coder unit and automatic fresh Reviewer, Primary review and ten-test independent real adapter integration",
            "source_provenance_sha256": digest(FROZEN / "provenance.json"),
            "scope": "Previously qualified private normalization only; exact current dirty sibling modules frozen. No production bug/deployment/public compatibility qualification claimed.",
            "reference_excluded": "Frozen original and preflight variants outside worker root/read scope",
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "environment_limits": "pytest9.1.1 vs sibling constraint <9; missing pytest-asyncio warning and no Pyright; no install",
        },
    )
    if counts != expected:
        raise ValueError(
            "candidate must execute ten tests with only three intended semantic failures"
        )
    print(json.dumps({"prepared": str(ROOT), "junit": counts}))


def run():
    accepted = read(ROOT / ".agent/flow-explorer-primary.json")
    if (
        not accepted["success"]
        or digest(ROOT / ".agent/flow-explorer.json") != accepted["report_sha256"]
    ):
        raise ValueError("fresh independently accepted localization required")
    original = pilot.read
    pilot.read = lambda path: original(
        ROOT / ".agent/flow-explorer.json"
        if Path(path) == ROOT / ".agent/explorer.json"
        else path
    )
    pilot.run(IDENTITY, UNIT)


def integrate():
    contract, cell, root, plan = evidence.context(IDENTITY)
    expected, refs, _ = evidence.provenance(contract, cell, root, plan, True)
    packet = read(ROOT / ".agent/normalize-unit-bound.json")
    archive = ROOT / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    before = (archive / "preimages" / COMMON).read_text(encoding="utf-8")
    after = (ROOT / COMMON).read_text(encoding="utf-8")

    def rest(text):
        return [
            ast.dump(n)
            for n in ast.parse(text).body
            if not (isinstance(n, ast.FunctionDef) and n.name == "_datetime")
        ]

    if rest(before) != rest(after):
        raise ValueError("edit escaped private helper")
    checks = pilot.matrix.SCOPE.FA.LAYER.check(ROOT, "feature-integration")
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    junit = ROOT / ".agent/feature-integration.xml"
    counts = evidence.counts(junit)
    passed = checks["all_checks_pass"] and counts == {
        "tests": 10,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    write(
        ROOT / ".agent/feature-integration.json",
        {
            "checks": checks,
            "junit": counts,
            "passed": passed,
            "non_helper_AST_unchanged": True,
            "inputs_unchanged": True,
            "primary_feature_accepted": False,
        },
    )
    if not passed:
        raise ValueError("independent real adapter integration failed")
    validation = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": contract.authority_fingerprint(plan),
        "integration_risk": plan["integration_risk"],
        "status": "passed",
        "checks": [
            {"id": "integration-" + str(i), "status": "passed", "exit_code": 0}
            for i, _ in enumerate(checks["checks"])
        ],
        "files": [{"path": p, "sha256": sha} for p, sha in expected.items()],
        "junit_sha256": digest(junit),
        "source_evidence": ".agent/feature-integration.json",
        "primary_feature_accepted": False,
    }
    write(
        ROOT / ".agent/integration" / plan["feature_id"] / "validation.json", validation
    )
    contract.verify_integration_archive(plan, root, refs)
    print(
        json.dumps(
            {"passed": passed, "junit": counts, "non_helper_AST_unchanged": True}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "run",
            "check",
            "record",
            "integrate",
        ),
    )
    parser.add_argument("--summary")
    parser.add_argument(
        "--decision",
        choices=("accept", "rework", "replan", "takeover"),
        default="accept",
    )
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        configure()
        pilot.matrix.verify()
        if args.action == "explore":
            split.explore(IDENTITY, "flow")
        elif args.action == "adjudicate":
            split.adjudicate(IDENTITY, "flow", args.summary)
        elif args.action == "run":
            run()
        elif args.action == "check":
            evidence.unit_check(IDENTITY, UNIT)
        elif args.action == "record":
            import qualification_controls as controls

            controls.record(IDENTITY, UNIT, args.decision, args.summary)
        else:
            integrate()
