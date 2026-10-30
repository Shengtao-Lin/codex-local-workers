"""Independent registered repetitions with a stronger, protected error contract."""

import argparse
import ast
import copy
import json
import shutil

import real_adapter_live as live
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

EXTRA = "tests/test_datetime_fidelity.py"
SUPPORT = (
    KIT / "benchmarks/fixtures/real-adapter-datetime-extra/test_datetime_fidelity.py"
)
TESTS = live.TESTS + [EXTRA]
EXPECTED_COUNT = 47
BEHAVIOR = (
    "Restore only private _datetime. Existing datetime objects return by identity; "
    "strings use existing Z replacement and ISO parsing, preserving aware wall time and offset, "
    "attaching UTC to naive parsed strings. Other inputs return default by identity. "
    "Invalid strings must propagate the original parser exception object, type, args and message "
    "unchanged, with no added exception cause/context or wrapper. Preserve real trace/turn "
    "adapter behavior and raw inputs. Do not change any other source behavior, public schema, "
    "identity, storage or network logic. All tests and other source files are read-only."
)


def configure(round_number):
    live.BASE = WORK / f"real-adapter-fidelity-r{round_number}"
    live.ROOT = live.BASE / "candidate"
    live.TESTS = TESTS
    return live.configure()


def prepare(round_number):
    contract = configure(round_number)
    root, base = live.ROOT, live.BASE
    root.mkdir(parents=True, exist_ok=False)
    provenance = read(live.FROZEN / "provenance.json")
    paths = [
        *provenance["copied_original_files"],
        provenance["primary_added_test"]["path"],
    ]
    for path in paths:
        source = live.PREPARED / "combined" / path
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    shutil.copyfile(SUPPORT, root / EXTRA)
    paths.append(EXTRA)
    old = WORK / "real-adapter-live-2/candidate/.agent"
    config = read(old / "config.json")
    argv = config["validation_profiles"]["mixed-strict"]["pytest_argv"]
    config["validation_profiles"]["mixed-strict"]["pytest_argv"] = [
        a for a in argv if not a.startswith("--basetemp=")
    ] + ["--basetemp=" + str(root / ".agent/validation-temp")]
    write(root / ".agent/config.json", config)
    packet = copy.deepcopy(read(old / "normalize-unit-bound.json"))
    identity = base.name
    packet.update(
        task_id=identity,
        feature_id=identity,
        run_id=identity + "-unit-a1",
        goal=BEHAVIOR,
        focused_tests=TESTS,
        required_behavior=[{"id": live.UNIT, "risk_floor": "medium", "text": BEHAVIOR}],
    )
    packet["scope"]["readonly"].append(EXTRA)
    packet["acceptance_scenarios"][1].update(
        text="Preserve exact parser error through helper and both real adapter modes.",
        observables={
            "exception": "ValueError",
            "same_exception_object": True,
            "same_args_message": True,
            "added_cause_context": False,
        },
    )
    packet.pop("primary_plan_sha256", None)
    plan = live.route.primary_plan_for_packet(packet)
    packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
    packet = contract.validate_unit_packet(plan, packet)
    load_worker(live.SNAPSHOT).validate_packet(packet)
    write(root / ".agent/feature-plan.json", plan)
    write(root / ".agent/normalize-unit-bound.json", packet)
    paths += [
        ".agent/config.json",
        ".agent/feature-plan.json",
        ".agent/normalize-unit-bound.json",
    ]
    write(
        base / "manifest.json",
        {
            "runtime": str(live.SNAPSHOT),
            "cells": [
                {
                    "id": live.IDENTITY,
                    "arm": "coordinator",
                    "case": "real-datetime",
                    "root": str(root),
                    "units": [live.UNIT],
                    "hashes": {p: digest(root / p) for p in paths},
                }
            ],
            "drivers": {
                str(p): digest(p)
                for p in (
                    KIT / "benchmarks/real_adapter_fidelity.py",
                    SUPPORT,
                    KIT / "benchmarks/real_adapter_live.py",
                    KIT / "benchmarks/coordinator_label_pilot.py",
                    KIT / "benchmarks/coordinator_label_evidence.py",
                    KIT / "benchmarks/coordinator_numeric_split.py",
                )
            },
        },
    )
    checks = live.pilot.matrix.SCOPE.FA.LAYER.check(root, "baseline")
    counts = live.evidence.counts(root / ".agent/baseline.xml")
    # Fault injection should fail semantically, not during collection/import.
    passed = (
        counts["tests"] == EXPECTED_COUNT
        and counts["failures"] > 0
        and not (counts["errors"] or counts["skipped"])
    )
    write(
        base / "preflight-1.json",
        {"all_pass": passed, "baseline": checks, "junit": counts},
    )
    write(
        base / "registration.json",
        {
            "round": round_number,
            "cohort_rounds": [1, 2, 3],
            "stop": "Three bounded repetitions or actionable failure or weekly used >=18%",
            "contract": BEHAVIOR,
            "expected_tests": EXPECTED_COUNT,
            "protected_test_sha256": digest(SUPPORT),
            "historical_decisions_unchanged": True,
            "environment_limits": "pytest9 vs sibling <9; pytest-asyncio and Pyright absent",
        },
    )
    if not passed:
        raise ValueError(f"invalid baseline: {counts}")
    print(json.dumps({"root": str(root), "baseline": counts}))


def integrate():
    contract, cell, root, plan = live.evidence.context(live.IDENTITY)
    expected, refs, _ = live.evidence.provenance(contract, cell, root, plan, True)
    packet = read(root / ".agent/normalize-unit-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]

    def rest(path):
        return [
            ast.dump(n)
            for n in ast.parse(path.read_text(encoding="utf-8")).body
            if not (isinstance(n, ast.FunctionDef) and n.name == "_datetime")
        ]

    if rest(archive / "preimages" / live.COMMON) != rest(root / live.COMMON):
        raise ValueError("non-helper source changed")
    checks = live.pilot.matrix.SCOPE.FA.LAYER.check(root, "feature-integration")
    live.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    junit = root / ".agent/feature-integration.xml"
    counts = live.evidence.counts(junit)
    passed = checks["all_checks_pass"] and counts == {
        "tests": EXPECTED_COUNT,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    write(
        root / ".agent/feature-integration.json",
        {
            "passed": passed,
            "checks": checks,
            "junit": counts,
            "non_helper_AST_unchanged": True,
            "primary_feature_accepted": False,
        },
    )
    if not passed:
        raise ValueError("integration failed")
    write(
        root / ".agent/integration" / plan["feature_id"] / "validation.json",
        {
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
        },
    )
    contract.verify_integration_archive(plan, root, refs)
    print(json.dumps({"passed": passed, "junit": counts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=("prepare", "explore", "adjudicate", "run", "record", "integrate"),
    )
    parser.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--summary")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.round)
    else:
        configure(args.round)
        live.pilot.matrix.verify()
        if args.action == "explore":
            live.split.explore(live.IDENTITY, "flow")
        elif args.action == "adjudicate":
            live.split.adjudicate(live.IDENTITY, "flow", args.summary)
        elif args.action == "run":
            live.run()
        elif args.action == "record":
            import qualification_controls as controls

            controls.record(live.IDENTITY, live.UNIT, "accept", args.summary)
        else:
            integrate()
