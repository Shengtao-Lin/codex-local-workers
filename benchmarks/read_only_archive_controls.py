"""Read-only counterfactual authority inputs; copy only an unaccepted consumer."""

import copy
from pathlib import Path

import current_archive_controls as A

S, BRIDGE = A.S, A.BRIDGE
BATCH = A.BATCH.with_name("read-only-archive-controls-20261022-1")
CASES = [
    "unchanged",
    "config",
    "plan-contract",
    "unknown-family",
    "wrong-symbol",
    "wrong-run",
    "dependency-bytes",
]


def run():
    assert not BATCH.exists()
    bindings = {
        topic: S.read(A.CHAIN / "units" / topic / "binding.json")
        for topic in ("encode", "append")
    }
    before = {k: A.inventory(Path(b["root"])) for k, b in bindings.items()}
    root = Path(bindings["encode"]["root"])
    packet = bindings["encode"]["packet"]
    original_plan, original_catalog = (
        S.read(A.CHAIN / "approved-plan.json"),
        S.read(A.CHAIN / "catalog.json"),
    )
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "real-archive-read-only-authority",
            "risk": "high",
            "cases": CASES,
            "gate": "Original positive remains accepted; six changed authority/transfer inputs rejected; originals unchanged",
            "live_calls": 0,
            "weekly_used_stop": 30,
            "scope": "Never write original archives; in-memory copies of trusted call arguments, fresh consumer file copy only",
            "prior": "current-archive-controls-20261022-1 HOLD: copied archive does not retain original execution-root binding; six negatives NOT_RUN",
            "pins": {
                str(p): S.sha(p)
                for p in (
                    Path(__file__),
                    Path(A.__file__),
                    S.KIT / ".local-agents/coordinator-bounded.py",
                )
            },
            "limits": "No fake acceptance records, no root-binding relaxation, no semantic model detection score",
        },
    )
    S.save(BATCH / "source-manifests.json", before)
    rows = []
    for case in CASES:
        config = copy.deepcopy(bindings["encode"]["config"])
        plan, catalog = copy.deepcopy(original_plan), copy.deepcopy(original_catalog)
        ref = {k: packet[k] for k in ("task_id", "run_id")}

        def verify(plan=plan, ref=ref, config=config, catalog=catalog):
            return BRIDGE.verify_accepted_unit(
                plan,
                root,
                packet["unit_id"],
                ref,
                config,
                catalog,
                bridge_profile="bounded-v1",
            )

        assert verify() == S.read(A.CHAIN / "units/encode/acceptance.json")
        mutation = {}
        if case == "config":
            config["max_validation_runs"] = 99
            mutation = {"max_validation_runs": 99}
        elif case == "plan-contract":
            plan["contracts"][0]["text"] += " Additional unapproved requirement."
            mutation = {"contract_text_changed": True}
        elif case == "unknown-family":
            catalog["encode"]["family"] = "arbitrary-algorithm"
            mutation = {"family": "arbitrary-algorithm"}
        elif case == "wrong-symbol":
            catalog["encode"]["symbol"] = "another_function"
            mutation = {"symbol": "another_function"}
        elif case == "wrong-run":
            ref["run_id"] = "different-nonexistent-run"
            mutation = dict(ref)
        elif case == "dependency-bytes":
            consumer = BATCH / "consumer"
            target = config["coder_single_function"]["path"]
            copied = consumer / target
            copied.parent.mkdir(parents=True)
            assert not copied.exists()
            copied.write_bytes((root / target).read_bytes())
            downstream = bindings["append"]

            def dependency(
                consumer=consumer,
                downstream=downstream,
                config=config,
                plan=plan,
                catalog=catalog,
                ref=ref,
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
                    evidence_root=S.KIT / "benchmarks/work/harness-convergence",
                    transfer_paths={
                        packet["unit_id"]: {"source": target, "destination": target}
                    },
                )

            assert dependency()["eligible_for_primary_dispatch"] is True
            digest = S.sha(copied)
            copied.write_bytes(
                copied.read_bytes() + b"\n# Changed dependency counterfactual\n"
            )
            mutation = {"path": str(copied), "before": digest, "after": S.sha(copied)}
            verify = dependency
        try:
            receipt = verify()
            row = {
                "case": case,
                "rejected": False,
                "receipt": receipt,
                "mutation": mutation,
            }
        except (ValueError, OSError, BRIDGE.GATE.HandoffError) as exc:
            row = {
                "case": case,
                "rejected": True,
                "error": str(exc),
                "mutation": mutation,
            }
        S.save(BATCH / "results" / (case + ".json"), row)
        rows.append(row)
        print(case, "rejected" if row["rejected"] else "verified", flush=True)
    unchanged = all(
        A.inventory(Path(bindings[k]["root"])) == hashes for k, hashes in before.items()
    )
    good = unchanged and all(r["rejected"] == (r["case"] != "unchanged") for r in rows)
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_READ_ONLY_AUTHORITY_CONTROLS"
            if good
            else "HOLD_AUTHORITY_CONTROLS",
            "executed": len(rows),
            "not_run": 0,
            "original_history_unchanged": unchanged,
            "live_calls": 0,
            "results": rows,
            "meaning": "One authentic original positive and six invalid-argument/exact-transfer negative controls; not replacement coverage for six NOT_RUN relocated-archive mutations",
        },
    )
    assert good, rows


if __name__ == "__main__":
    run()
