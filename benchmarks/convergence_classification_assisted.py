"""C4: finite assisted qualification, reusing frozen runtime and C3 review gates."""

import argparse
import copy
import json
import runpy
import shutil
import sys
from pathlib import Path

import convergence_coder as paired
import convergence_coder_transport_results as review
import convergence_execution as controls
from convergence_coder import KIT, save
from convergence_decomposition import load
from convergence_protocol_audit import preservation
from system_convergence import junit_counts, read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/c4-assisted-20261011-1"
C3 = KIT / "benchmarks/work/system-convergence/c3-transport-20261011-1"
OLD = KIT / "benchmarks/work/system-convergence/execution-20261011-2"
PRIOR = OLD / "features/classification-shapes/B"
RUNTIME = C3 / "candidate-kit/.local-agents"
SOURCE = "src/evaluation_harness/telemetry/classification.py"


def bind():
    controls.BASE, controls.RUNTIME = BASE, RUNTIME
    paired.BASE, paired.ARMS = BASE, {"assisted": RUNTIME}
    review.trial = sys.modules[__name__]


def fallback_probe(root):
    raw = {"attributes": {"service.name": "evaluation-api"}}
    before = copy.deepcopy(raw)
    error = None
    try:
        actual = runpy.run_path(str(root / SOURCE))["is_internal_trace"](raw)
    except Exception as exc:  # noqa: BLE001 -- retain independent probe failures
        actual, error = None, f"{type(exc).__name__}: {exc}"
    return {
        "input": before,
        "expected": True,
        "actual": actual,
        "input_unchanged": raw == before,
        "passed": error is None and actual is True and raw == before,
        "error": error,
        "contract_id": "classification-shapes",
        "new_protected_tests_added": False,
    }


def prepare():
    if BASE.exists():
        raise FileExistsError("C4 identity already exists")
    proposal = read_object(C3 / "next-stage-proposal-1.json")
    assert read_object(C3 / "stage-decision-1.json")["decision"] == "ACCEPT_CHANGE"
    save(
        BASE / "authorization.json",
        {
            "stage": "C4",
            "user_message": "下一步吧",
            "user_authorized": True,
            "proposal": ref(C3, "next-stage-proposal-1.json"),
            "weekly_used_start": 4,
            "weekly_used_ceiling": 15,
            "preservation": preservation(),
        },
    )
    strategy = proposal["frozen_strategy_proposal"]
    save(
        BASE / "primary-strategy.json",
        {
            "text": strategy,
            "advisory": True,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "not_a_production_patch_or_permission": True,
        },
    )
    packet = read_object(PRIOR / ".agent/unit-1-packet.json")
    paths = read_object(PRIOR / ".agent/brief.json")["source_hashes"]
    parent = PRIOR / f".agent/tasks/{packet['task_id']}/runs/{packet['run_id']}"
    image = next(
        p
        for p in json.loads((parent / "preimages.json").read_text())
        if p["path"] == SOURCE
    )
    legacy = PRIOR / image["archive_path"]
    assert sha256(legacy) == paths[SOURCE] == image["sha256"]
    draft = PRIOR / SOURCE
    child = parent.parent / "d2-classification-shapes-b-unit-1-a2"
    assert (
        sha256(draft)
        == read_object(child / "post-state.json")["authorized_paths"][SOURCE]["sha256"]
    )
    cells = []
    for identity in ("legacy-r1", "draft-r1", "draft-r2", "legacy-r2"):
        kind = identity.split("-")[0]
        root = BASE / "cells" / identity
        for path, digest in paths.items():
            source = (
                (legacy if kind == "legacy" else draft)
                if path == SOURCE
                else PRIOR / path
            )
            if path != SOURCE:
                assert sha256(source) == digest
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        current = copy.deepcopy(packet)
        # This is a fresh Primary-authored packet, not reuse of old D2 approval.
        current.pop("primary_plan_sha256", None)
        task = "convergence-c4-" + identity
        current.update(
            task_id=task,
            feature_id=task,
            run_id=task + "-a1",
            implementation_guidance=[strategy],
            review_feedback=[],
        )
        config = read_object(C3 / "cells/normal-candidate/.agent/config.json")
        assert (
            config["coder_typed_action_arguments"] is True
            and config["coordinator_enabled"] is False
        )
        load("c4_packet_control", RUNTIME / "worker-runtime.py").validate_packet(
            current
        )
        save(root / ".agent/packet.json", current)
        save(root / ".agent/config.json", config)
        for name, argv in (
            ("initial-lint", ["-m", "ruff", "check", "src", "tests"]),
            ("initial-format", ["-m", "ruff", "format", "--check", "src", "tests"]),
            (
                "preimage-tests",
                [
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--junitxml=" + str(root / ".agent/preimage.xml"),
                ],
            ),
        ):
            expected = 1 if name == "preimage-tests" else 0
            assert (
                controls.command(root, argv, root / (".agent/" + name + ".json"))
                == expected
            )
        save(root / ".agent/preimage-fallback-probe.json", fallback_probe(root))
        cells.append(
            {
                "id": identity,
                "kind": kind,
                "arm": "assisted",
                "root": str(root),
                "identity": {k: current[k] for k in ("task_id", "unit_id", "run_id")},
                "inputs": [ref(root, p) for p in paths],
                "writable": current["scope"]["modify"],
                "packet": ref(root, ".agent/packet.json"),
                "config": ref(root, ".agent/config.json"),
                "origin": ref(
                    KIT,
                    (legacy if kind == "legacy" else draft).relative_to(KIT).as_posix(),
                ),
                "historical_feedback_supplied": [],
                "same_guidance": ref(BASE, "primary-strategy.json"),
            }
        )
    save(
        BASE / "preparation.json",
        {
            "cells": cells,
            "old_failure_archives": [
                ref(parent, "handoff.json"),
                ref(child, "handoff.json"),
            ],
            "old_counterexample": ref(
                PRIOR, ".agent/primary-semantic-counterexample.json"
            ),
            "runtime": read_object(C3 / "registration.json")["runtime"]["candidate"],
        },
    )


def preflight():
    prep = read_object(BASE / "preparation.json")
    reference = OLD / "features/classification-shapes/A" / SOURCE
    mutations = {
        "positive": reference.read_text(),
        "legacy-negative": Path(KIT / prep["cells"][0]["origin"]["path"]).read_text(),
        "draft-negative": (PRIOR / SOURCE).read_text(),
        "fallback-negative": reference.read_text().replace(
            'resource.get("service.name") or attributes.get("service.name")',
            'resource.get("service.name")',
        ),
    }
    outcomes = []
    for name, text in mutations.items():
        root = BASE / "controls" / name
        for path in read_object(PRIOR / ".agent/brief.json")["source_hashes"]:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if path == SOURCE:
                target.write_text(text, encoding="utf-8")
            else:
                shutil.copyfile(PRIOR / path, target)
        code = controls.command(
            root,
            [
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=" + str(root / ".agent/tests.xml"),
            ],
            root / ".agent/tests.json",
        )
        probe = fallback_probe(root)
        expected_code = 0 if name in {"positive", "fallback-negative"} else 1
        assert code == expected_code
        assert probe["passed"] == (name in {"positive", "legacy-negative"})
        outcomes.append(
            {
                "name": name,
                "tests": junit_counts(root / ".agent/tests.xml"),
                "fallback_probe": probe,
            }
        )
    save(
        BASE / "preflight.json",
        {
            "outcomes": outcomes,
            "all_expected": True,
            "fallback_negative_passes_old_tests_but_fails_independent_contract_probe": True,
            "oracles_outside_worker_scope": True,
        },
    )


def register():
    prep = read_object(BASE / "preparation.json")
    assert read_object(BASE / "preflight.json")["all_expected"]
    counts = junit_counts(BASE / "adapter-controls-1.xml")
    assert (
        counts["executed"] == 14
        and counts["failures"] == counts["errors"] == counts["skipped"] == 0
    )
    for item in prep["runtime"]:
        assert sha256(RUNTIME / item["path"]) == item["sha256"]
    save(
        BASE / "registration.json",
        {
            "stage": "C4",
            "registered_calls": 4,
            "cells": prep["cells"],
            "driver": ref(KIT, "benchmarks/convergence_coder.py"),
            "wrapper": ref(KIT, "benchmarks/convergence_classification_assisted.py"),
            "review_adapter": ref(
                KIT, "benchmarks/convergence_coder_transport_results.py"
            ),
            "runtime": {"assisted": prep["runtime"]},
            "strategy": ref(BASE, "primary-strategy.json"),
            "preparation": ref(BASE, "preparation.json"),
            "preflight": ref(BASE, "preflight.json"),
            "adapter_controls": ref(BASE, "adapter-controls-1.xml"),
            "adapter_tests": ref(
                KIT, "tests/test_convergence_classification_assisted.py"
            ),
            "reuse_unchanged_runtime_full_regression": ref(C3, "full-regression-2.xml"),
            "new_runtime_candidate": False,
            "new_full_regression_claim": False,
            "weekly_used_start": 4,
            "weekly_used_ceiling": 15,
            "order": [c["id"] for c in prep["cells"]],
            "acceptance": "All four original protected tests/checks/current validation, fresh Reviewer and Primary acceptance; independently restore the original attribute service-name fallback counterexample. No Primary business implementation or external rework",
            "stop": "Safety failure, two consecutive identical no-progress semantic failures, or weekly used 15. Unrun cells stay in registered denominator",
            "same_hard_contract_and_protection": True,
            "intervention": "One prereviewed advisory strategy, no code patch, same empty historical feedback in all four cells. No per-attempt prompt changes, resampling or external rework",
            "scope": "One medium-risk telemetry predicate in an isolated fixture, not an authorization-policy change. Runtime evidence/permission logic is Primary-owned",
            "exposure": "Already-exposed classification task; known original and failed draft, same Primary memory. No blind transfer or causal comparison to old unassisted flat-transport D2",
            "old_D2_remains_HOLD": True,
            "I1": "BLOCKED_BY_D2",
            "economics": "UNMEASURED",
        },
    )


def frozen():
    record = read_object(BASE / "registration.json")
    for item in (record["wrapper"], record["driver"], record["review_adapter"]):
        assert sha256(KIT / item["path"]) == item["sha256"]
    assert sha256(BASE / record["strategy"]["path"]) == record["strategy"]["sha256"]
    return record


def adjudicate(identity, decision, note):
    frozen()
    _, root, _, _, _ = review.cell_records(identity)
    probe = fallback_probe(root)
    save(root / ".agent/independent-fallback-probe.json", probe)
    if decision == "accept" and not probe["passed"]:
        raise ValueError("original valid dictionary fallback not restored")
    review.adjudicate(identity, decision, note)


def stage_decision(accepted, executed, used):
    if accepted == executed == 4:
        return "PASS_LIMITED_ASSISTED"
    if used >= 15 and executed < 4:
        return "INCOMPLETE_BUDGET"
    return "HOLD_CAPABILITY_PRIMARY_OWNED"


def collect(used):
    record = frozen()
    results = []
    for cell in record["cells"]:
        root = Path(cell["root"])
        if not (root / "invocation.json").exists():
            results.append({"cell": cell["id"], "status": "not_run"})
            continue
        _, root, archive, _, handoff = review.cell_records(cell["id"])
        reviewer = (
            read_object(root / ".agent/reviewer.json")
            if (root / ".agent/reviewer.json").exists()
            else {}
        )
        results.append(
            {
                "cell": cell["id"],
                "start": cell["kind"],
                "coder": handoff["status"],
                "failure_reason": handoff.get("failure_reason"),
                "protocol_errors": handoff.get("protocol_error_count"),
                "protocol_error_details": handoff.get("protocol_error_details"),
                "repairs": handoff.get("repair_count"),
                "current_validation": handoff.get("validation"),
                "reviewer": reviewer.get("decision", "not_started"),
                "reviewer_protocol_errors": reviewer.get("runtime_facts", {}).get(
                    "protocol_error_count"
                ),
                "primary": read_object(archive / "review.json")["decision"],
                "handoff": ref(archive, "handoff.json"),
                "independent": read_object(root / ".agent/primary-adjudication.json")[
                    "independent"
                ],
                "fallback_probe": read_object(
                    root / ".agent/independent-fallback-probe.json"
                ),
                "invocation": read_object(root / "invocation.json"),
            }
        )
    executed = [r for r in results if "coder" in r]
    accepted = sum(r["primary"] == "accept" for r in executed)
    decision = stage_decision(accepted, len(executed), used)
    save(
        BASE / "stage-decision-1.json",
        {
            "stage": "C4",
            "decision": decision,
            "registered": 4,
            "executed": len(executed),
            "accepted": accepted,
            "results": results,
            "role_calls": {
                "coder": len(executed),
                "reviewer": sum(r["reviewer"] != "not_started" for r in executed),
                "explorer": 0,
                "coordinator": 0,
            },
            "weekly_used_start": 4,
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "preservation": preservation(),
            "registration": ref(BASE, "registration.json"),
            "old_D2": "HOLD 2/3, not replaced by this assisted qualification",
            "I1": "BLOCKED_BY_D2",
            "primary_strategy_cost": read_object(BASE / "primary-strategy.json"),
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "economics": "UNMEASURED",
            "external_rework": 0,
            "primary_business_edits": False,
            "production_promoted": False,
            "no_general_stability_transfer_or_savings_claim": True,
        },
    )
    print(decision, accepted, "/4", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("prepare", "preflight", "register", "run", "adjudicate", "collect"),
    )
    parser.add_argument("cell", nargs="?")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--note")
    parser.add_argument("--weekly-used", type=int)
    args = parser.parse_args()
    bind()
    if args.action == "prepare":
        prepare()
    elif args.action == "preflight":
        preflight()
    elif args.action == "register":
        register()
    elif args.action == "run":
        frozen()
        paired.run(args.cell)
    elif args.action == "adjudicate":
        adjudicate(args.cell, args.decision, args.note)
    else:
        collect(args.weekly_used)
