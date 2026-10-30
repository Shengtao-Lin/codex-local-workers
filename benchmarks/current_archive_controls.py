"""Create-only counterfactuals on copied real accepted archives, never live scores."""

import copy
import json
import shutil
from pathlib import Path

import bounded_evidence_support as S
import capture_fixture_support as F

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/current-archive-controls-20261022-1"
)
SOURCE = (
    S.KIT / "benchmarks/work/harness-convergence/installed-identity-repeats-20261022-1"
)
CHAIN = SOURCE / "chain-1"
BRIDGE = F.load(
    S.KIT / ".local-agents/coordinator-bounded.py", "real_archive_control_bridge"
)
CASES = [
    "unchanged",
    "source",
    "protected-test",
    "config",
    "foreign-review",
    "primary-replan",
    "dependency-bytes",
]


def inventory(root):
    return {
        p.relative_to(root).as_posix(): S.sha(p)
        for p in root.rglob("*")
        if p.is_file()
        and not set(p.parts) & {"__pycache__", ".pytest_cache", ".ruff_cache"}
    }


def clone(origin, target):
    assert not target.exists()
    shutil.copytree(
        origin,
        target,
        ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc"
        ),
    )


def run():
    assert not BATCH.exists(), "create-only control batch"
    assert S.read(SOURCE / "decision.json")["accepted_chains"] == 2
    bindings = {
        topic: S.read(CHAIN / "units" / topic / "binding.json")
        for topic in ("encode", "append")
    }
    originals = {topic: inventory(Path(row["root"])) for topic, row in bindings.items()}
    plan, catalog = S.read(CHAIN / "approved-plan.json"), S.read(CHAIN / "catalog.json")
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "current-real-archive-integrity",
            "risk": "high",
            "risk_rationale": "Final evidence/transfer rejection; no production writes or approval",
            "cases": CASES,
            "gate": "Unchanged copied current archive verifies; six mutations rejected; historical sources unchanged",
            "live_calls": 0,
            "weekly_used_start": 27,
            "weekly_used_stop": 30,
            "source": str(CHAIN),
            "source_decision_sha256": S.sha(SOURCE / "decision.json"),
            "candidate_pins": {
                str(p): S.sha(p)
                for p in (
                    Path(__file__),
                    S.KIT / ".local-agents/coordinator-bounded.py",
                    S.KIT / ".local-agents/local-unit.py",
                )
            },
            "scope": "Fresh copies only, actual canonical accepted archives; no synthetic positive review and no new task-family or semantic detection score",
        },
    )
    S.save(BATCH / "source-manifests.json", originals)
    results = []
    for case in CASES:
        cell = BATCH / "cases" / case
        root = cell / "producer"
        origin = Path(bindings["encode"]["root"])
        clone(origin, root)
        packet = bindings["encode"]["packet"]
        config = copy.deepcopy(bindings["encode"]["config"])
        ref = {k: packet[k] for k in ("task_id", "run_id")}
        run_root = root / ".agent/tasks" / ref["task_id"] / "runs" / ref["run_id"]
        review = S.read(run_root / "review.json")["local_review_id"]
        mutation = None

        def verify(root=root, packet=packet, ref=ref, config=config):
            return BRIDGE.verify_accepted_unit(
                plan,
                root,
                packet["unit_id"],
                ref,
                config,
                catalog,
                bridge_profile="bounded-v1",
            )

        # Every negative starts from a separately verified positive copy.
        try:
            positive = verify()
        except (ValueError, OSError, BRIDGE.GATE.HandoffError) as exc:
            results.append({"case": case, "preflight_failed": True, "error": str(exc)})
            S.save(cell / "preflight.json", results[-1])
            break
        assert positive == S.read(CHAIN / "units/encode/acceptance.json")
        if case in {"source", "protected-test"}:
            relative = (
                config["coder_single_function"]["path"]
                if case == "source"
                else packet["focused_tests"][0].split("::", 1)[0]
            )
            path = root / relative
            before = S.sha(path)
            path.write_bytes(path.read_bytes() + b"\n# Counterfactual input drift\n")
            mutation = {"path": relative, "before": before, "after": S.sha(path)}
        elif case == "config":
            config["max_validation_runs"] = 99
            mutation = {"max_validation_runs": 99}
        elif case == "foreign-review":
            second = S.read(SOURCE / "chain-2/units/encode/binding.json")
            other = Path(second["root"]) / ".agent/tasks" / second["packet"]["task_id"]
            other_review = S.read(
                other / "runs" / second["packet"]["run_id"] / "review.json"
            )["local_review_id"]
            source_report = other / "reviews" / other_review / "handoff.json"
            path = (
                root
                / ".agent/tasks"
                / ref["task_id"]
                / "reviews"
                / review
                / "handoff.json"
            )
            before = S.sha(path)
            shutil.copyfile(source_report, path)
            mutation = {
                "copied_from": str(source_report),
                "before": before,
                "after": S.sha(path),
            }
        elif case == "primary-replan":
            path = run_root / "review.json"
            document = S.read(path)
            document["decision"] = "replan"
            path.write_text(json.dumps(document, indent=2), encoding="utf-8")
            mutation = {"Primary_decision": "replan", "path": str(path)}
        elif case == "dependency-bytes":
            consumer = cell / "consumer"
            clone(Path(bindings["append"]["root"]), consumer)
            target = config["coder_single_function"]["path"]
            downstream = bindings["append"]

            def dependency(
                consumer=consumer,
                downstream=downstream,
                packet=packet,
                ref=ref,
                config=config,
                root=root,
                cell=cell,
                target=target,
            ):
                return BRIDGE.dependency_readiness(
                    plan,
                    consumer,
                    downstream["packet"],
                    downstream["config"],
                    catalog,
                    {packet["unit_id"]: ref},
                    {packet["unit_id"]: config},
                    bridge_profile="bounded-v1",
                    dependency_roots={packet["unit_id"]: root},
                    evidence_root=cell,
                    transfer_paths={
                        packet["unit_id"]: {"source": target, "destination": target}
                    },
                )

            assert dependency()["eligible_for_primary_dispatch"] is True
            path = consumer / target
            before = S.sha(path)
            path.write_bytes(
                path.read_bytes() + b"\n# Changed transferred dependency\n"
            )
            mutation = {"path": target, "before": before, "after": S.sha(path)}
            verify = dependency
        try:
            receipt = verify()
            result = {
                "case": case,
                "rejected": False,
                "receipt": receipt,
                "mutation": mutation,
            }
        except (ValueError, OSError, BRIDGE.GATE.HandoffError) as exc:
            result = {
                "case": case,
                "rejected": True,
                "error": str(exc),
                "mutation": mutation,
            }
        S.save(cell / "result.json", result)
        results.append(result)
        print(case, "rejected" if result["rejected"] else "verified", flush=True)
        if case == "unchanged" and result["rejected"]:
            break
    unchanged = all(
        inventory(Path(bindings[k]["root"])) == value for k, value in originals.items()
    )
    good = (
        len(results) == len(CASES)
        and unchanged
        and all(row["rejected"] == (row["case"] != "unchanged") for row in results)
    )
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_CURRENT_REAL_ARCHIVE_CONTROLS"
            if good
            else "HOLD_EVIDENCE_CONTROLS",
            "executed": len(results),
            "not_run": len(CASES) - len(results),
            "unchanged_history": unchanged,
            "live_calls": 0,
            "meaning": "Current canonical integrity and exact-byte dependency rejection only; not model defect detection, adversarial host attestation or new live accepts",
            "results": results,
        },
    )
    assert good, results


if __name__ == "__main__":
    run()
