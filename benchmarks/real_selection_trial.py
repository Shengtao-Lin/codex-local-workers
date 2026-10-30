"""Freeze a second real task family and run one experimental supervised chain."""

import argparse
import ast
import copy
import json
import shutil
import sys

import coordinator_label_evidence as evidence
import coordinator_label_pilot as pilot
import coordinator_numeric_split as split
import localization_route_smoke as route
import real_adapter_live as live
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "real-selection-trial-1"
ROOT = BASE / "candidate"
FROZEN = KIT / "benchmarks/fixtures/real-selection-v1"
SIBLING = KIT.parent / "agent-evaluation-harness"
COMMON = "src/evaluation_harness/datasets/selection.py"
EXTRA = "tests/test_selection_trial.py"
SUPPORT = KIT / "benchmarks/fixtures/real-selection-extra/test_selection_trial.py"
UNIT = "normalize-unit"
IDENTITY = "coordinator-r1"
COUNT = 24
TESTS = [
    EXTRA,
    "tests/unit/test_selection.py",
    "tests/unit/test_dataset_generator.py",
    "tests/unit/test_adapters.py",
]
BEHAVIOR = (
    "Restore existing select_records semantics only. all returns a new list preserving input order and object "
    "identity. limit sorts by (timestamp, identity), reverses the whole sorted order for newest, then slices "
    "to limit; timestamp ties must be independent of input order. random sorts by identity before private "
    "random.Random(seed) shuffle and slicing: exact seeded results replay across input permutations and global "
    "RNG state is unchanged. percentage preserves existing SHA256 seed:identity membership and input order. "
    "Empty/oversized-limit inputs work; callback exceptions propagate unchanged. Preserve input collections "
    "and the real generate_dataset request/manifest roundtrip; no schema/API, identity, network, SQL or "
    "other source behavior changes. All acceptance tests and other modules are read-only."
)


def case():
    return {"goal": BEHAVIOR}


def configure():
    pilot.BASE, pilot.SNAPSHOT, pilot.fixture = (
        BASE,
        live.SNAPSHOT,
        sys.modules[__name__],
    )
    split.BASE, split.SNAPSHOT = BASE, live.SNAPSHOT
    split.QUESTIONS = {
        "flow": (
            [COMMON, "src/evaluation_harness/datasets/generator.py", EXTRA],
            (
                "Locate select_records limit/random branches, the generate_dataset selection caller, and "
                "test_tie_break/test_random_permutation_replay/test_actual_dataset_selection_roundtrip. "
                "One selection call-path question; cite real read lines in each of the three named files. "
                "Use literal SEARCH and bounded reads. Distinguish faulty source from test requirements; "
                "no repair/validation prediction or broad exploration."
            ),
        )
    }
    return pilot.configure()


def prepare():
    contract = configure()
    originals = list(read(live.FROZEN / "provenance.json")["copied_original_files"])
    originals += [
        "src/evaluation_harness/datasets/" + p
        for p in ("__init__.py", "models.py", "selection.py", "generator.py")
    ]
    originals += [
        "src/evaluation_harness/telemetry/__init__.py",
        "src/evaluation_harness/telemetry/classification.py",
        "tests/unit/test_selection.py",
        "tests/unit/test_dataset_generator.py",
    ]
    FROZEN.mkdir(parents=True, exist_ok=False)
    for path in originals:
        target = FROZEN / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SIBLING / path, target)
    shutil.copyfile(SUPPORT, FROZEN / EXTRA)
    write(
        FROZEN / "provenance.json",
        {
            "source": str(SIBLING),
            "source_git": pilot.matrix.SCOPE.FA.LAYER.command(
                SIBLING, ["git", "rev-parse", "HEAD"]
            ),
            "source_status": pilot.matrix.SCOPE.FA.LAYER.command(
                SIBLING, ["git", "status", "--short"]
            ),
            "original_files": {p: digest(FROZEN / p) for p in originals},
            "primary_test": {"path": EXTRA, "sha256": digest(SUPPORT)},
            "faults": [
                "Remove identity tie-break",
                "Shuffle input without stable identity order",
            ],
            "production_bug_claimed": False,
        },
    )
    roots = {}
    for name in ("reference", "candidate"):
        root = BASE / name
        root.mkdir(parents=True, exist_ok=False)
        for path in [*originals, EXTRA]:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FROZEN / path, target)
        roots[name] = root
    # Only the frozen candidate's one authorized module is fault-injected.
    source = (ROOT / COMMON).read_text(encoding="utf-8")
    source = source.replace(
        "key=lambda item: (timestamp(item), identity(item))", "key=timestamp"
    )
    source = source.replace(
        "ordered = sorted(eligible, key=identity)", "ordered = list(eligible)"
    )
    # Fault injection is an explicit benchmark preparation operation, not a worker edit.
    (ROOT / COMMON).write_text(source, encoding="utf-8")
    config = read(WORK / "real-adapter-live-2/candidate/.agent/config.json")
    config["explorer_required_citation_paths"] = split.QUESTIONS["flow"][0]
    config["validation_profiles"]["mixed-strict"]["pytest_argv"] = [
        "-B",
        "-m",
        "pytest",
        "--basetemp=" + str(ROOT / ".agent/validation-temp"),
    ]
    write(ROOT / ".agent/config.json", config)
    packet = copy.deepcopy(
        read(WORK / "real-adapter-live-2/candidate/.agent/normalize-unit-bound.json")
    )
    packet.update(
        task_id=BASE.name,
        feature_id=BASE.name,
        run_id=BASE.name + "-unit-a1",
        goal=BEHAVIOR,
        focused_tests=TESTS,
        edit_targets=[{"path": COMMON, "anchor": "select_records", "line_hint": 17}],
        required_behavior=[{"id": UNIT, "risk_floor": "medium", "text": BEHAVIOR}],
        acceptance_scenarios=[
            {
                "id": "normal",
                "text": "Replay tie ordering and exact seeded random selection.",
                "observables": {
                    "input_permutation_invariant": True,
                    "actual_dataset_manifest_replay": True,
                },
            },
            {
                "id": "error",
                "text": "Callback errors and malformed policies retain original rejection.",
                "observables": {
                    "same_callback_exception": True,
                    "invalid_limit_rejected": True,
                },
            },
            {
                "id": "boundary",
                "text": "Empty inputs, limits above size, all/percentage preservation.",
                "observables": {"input_unchanged": True, "global_rng_unchanged": True},
            },
        ],
    )
    packet["scope"]["modify"] = [COMMON]
    packet["scope"]["readonly"] = [
        p
        for p in [*originals, EXTRA]
        if p != COMMON and p.startswith(("src/", "tests/"))
    ]
    packet.pop("primary_plan_sha256", None)
    plan = route.primary_plan_for_packet(packet)
    packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
    packet = contract.validate_unit_packet(plan, packet)
    load_worker(live.SNAPSHOT).validate_packet(packet)
    write(ROOT / ".agent/feature-plan.json", plan)
    write(ROOT / ".agent/normalize-unit-bound.json", packet)
    paths = [
        *originals,
        EXTRA,
        ".agent/config.json",
        ".agent/feature-plan.json",
        ".agent/normalize-unit-bound.json",
    ]
    write(
        BASE / "manifest.json",
        {
            "runtime": str(live.SNAPSHOT),
            "cells": [
                {
                    "id": IDENTITY,
                    "arm": "coordinator",
                    "case": "real-selection",
                    "root": str(ROOT),
                    "units": [UNIT],
                    "hashes": {p: digest(ROOT / p) for p in paths},
                }
            ],
            "drivers": {
                str(p): digest(p)
                for p in (KIT / "benchmarks/real_selection_trial.py", SUPPORT)
            },
        },
    )
    outcomes = []
    for name, root in roots.items():
        checks = pilot.matrix.SCOPE.FA.LAYER.check(root, "preflight")
        counts = evidence.counts(root / ".agent/preflight.xml")
        valid = counts["tests"] == COUNT and not (counts["errors"] or counts["skipped"])
        valid = valid and (
            checks["all_checks_pass"] if name == "reference" else counts["failures"] > 0
        )
        outcomes.append(
            {"name": name, "checks": checks, "junit": counts, "valid": valid}
        )
    passed = all(o["valid"] for o in outcomes)
    write(BASE / "preflight-1.json", {"all_pass": passed, "outcomes": outcomes})
    write(
        BASE / "registration.json",
        {
            "scope": "Held-out exploratory family, no release expansion",
            "feature_unit_integration_risk": "medium",
            "risk_rationale": "Restore pure selection only; public schemas and real generator protected. No persistence, concurrency or API changes.",
            "models_unchanged": True,
            "single_model_residency": True,
            "weekly_ceiling": 18,
            "stop": "One observed chain and independent checks or actionable failure",
            "limitations": "pytest9 vs <9; no Pyright/async plugin; faults injected, not original bug",
        },
    )
    print(json.dumps([{k: v for k, v in o.items() if k != "checks"} for o in outcomes]))
    if not passed:
        raise ValueError("reference/candidate preflight not valid")


def run():
    accepted = read(ROOT / ".agent/flow-explorer-primary.json")
    if (
        not accepted["success"]
        or digest(ROOT / ".agent/flow-explorer.json") != accepted["report_sha256"]
    ):
        raise ValueError("fresh accepted Explorer required")
    original = pilot.read
    pilot.read = lambda p: original(
        ROOT / ".agent/flow-explorer.json" if p == ROOT / ".agent/explorer.json" else p
    )
    pilot.run(IDENTITY, UNIT)


def integrate():
    contract, cell, root, plan = evidence.context(IDENTITY)
    expected, _refs, _ = evidence.provenance(contract, cell, root, plan, True)
    packet = read(root / ".agent/normalize-unit-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]

    def rest(path):
        return [
            ast.dump(n)
            for n in ast.parse(path.read_text(encoding="utf-8")).body
            if not (isinstance(n, ast.FunctionDef) and n.name == "select_records")
        ]

    if rest(root / COMMON) != rest(archive / "preimages" / COMMON):
        raise ValueError("edit escaped selection function")
    checks = pilot.matrix.SCOPE.FA.LAYER.check(root, "feature-integration")
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    counts = evidence.counts(root / ".agent/feature-integration.xml")
    passed = checks["all_checks_pass"] and counts == {
        "tests": COUNT,
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
            "non_selection_AST_unchanged": True,
            "primary_feature_accepted": False,
        },
    )
    print(json.dumps({"passed": passed, "junit": counts}))
    if not passed:
        raise ValueError("integration failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=("prepare", "explore", "adjudicate", "run", "record", "integrate"),
    )
    parser.add_argument("--summary")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "takeover"), default="accept"
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
        elif args.action == "record":
            import qualification_controls as controls

            controls.record(IDENTITY, UNIT, args.decision, args.summary)
        else:
            integrate()
