"""Bounded packet-preparation transfer; no complete packet forwarded to Muse."""

import argparse
import copy
import importlib.util
import json
import sys
import time
from pathlib import Path

import coordinator_label_case as fixture
import qualification_matrix as matrix
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-label-pilot-3"
SNAPSHOT = WORK / "qualification-matrix-baseline-6"
SOURCE = WORK / "qualification-matrix-6"


def configure():
    matrix.BASE, matrix.SNAPSHOT = BASE, SNAPSHOT
    matrix.MIXED.CORPUS, matrix.MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    matrix.CHAIN.SNAPSHOT = SNAPSHOT
    return matrix.CHAIN.load_contract()


def prepare():
    contract = configure()
    BASE.mkdir(exist_ok=False)
    data = {"cases": [fixture.case()]}
    write(BASE / "corpus.json", data)
    mutant_collector = fixture.REFERENCE["src/product/collector.py"].replace(
        "values.append(await fetch(key))",
        "value=await fetch(key)\n        if value:\n            values.append(value)",
    )
    write(
        BASE / "primary-oracles.json",
        {
            "labelled-receipt": {
                "reference": fixture.REFERENCE,
                "mutants": [
                    {
                        **fixture.REFERENCE,
                        "src/product/labels.py": fixture.INITIAL[
                            "src/product/labels.py"
                        ],
                    },
                    {**fixture.REFERENCE, "src/product/collector.py": mutant_collector},
                    {
                        **fixture.REFERENCE,
                        "src/product/target.py": fixture.INITIAL[
                            "src/product/target.py"
                        ],
                    },
                ],
            }
        },
    )
    config = read(
        SOURCE / "runs/v1/qualification653/async-receipt-round-1/.agent/config.json"
    )
    config["explorer_required_citation_paths"] = [
        "src/product/entry.py",
        "src/product/target.py",
        "src/product/labels.py",
        "src/product/collector.py",
        "tests/test_target.py",
    ]
    cells = []
    for repetition in (1, 2):
        for arm in ("coordinator", "control"):
            settings = copy.deepcopy(config)
            settings["coordinator_enabled"] = arm == "coordinator"
            path = BASE / f"{arm}-r{repetition}-config.json"
            write(path, settings)
            root = Path(
                matrix.MIXED.prepare(
                    "labelled-receipt", repetition, path, "label3-" + arm
                )["root"]
            )
            plan = read(root / ".agent/feature-plan.json")
            paths = [
                *fixture.case()["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/feature-plan.json",
            ]
            for unit in plan["units"]:
                uid = unit["unit_id"]
                packet = read(root / f".agent/{uid}-reference.json")
                packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
                packet = contract.validate_unit_packet(plan, packet)
                load_worker(SNAPSHOT).validate_packet(packet)
                write(root / f".agent/{uid}-bound.json", packet)
                paths.append(f".agent/{uid}-bound.json")
            cells.append(
                {
                    "id": f"{arm}-r{repetition}",
                    "case": "labelled-receipt",
                    "arm": arm,
                    "root": str(root),
                    "units": [u["unit_id"] for u in plan["units"]],
                    "explorer_required": True,
                    "hashes": {p: digest(root / p) for p in paths},
                }
            )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(Path(__file__).resolve()): digest(Path(__file__)),
                str(Path(fixture.__file__).resolve()): digest(Path(fixture.__file__)),
            },
            "feature_id": "coordinator-labelled-receipt",
            "feature_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "bounded-packet-preparation",
                "protected-roundtrip",
                "immutable-role-evidence",
            ],
            "risk_rationale": "Primary-owned qualification authority high; functional cross-unit composition medium.",
        },
    )
    write(
        BASE / "registration.json",
        {
            "order": ["coordinator-r1", "control-r1", "control-r2", "coordinator-r2"],
            "weekly_used_ceiling": 10,
            "units_per_arm": 6,
            "classification": "New composition of qualified families, not unseen repository benchmark",
            "coordinator_context": "Primary hard plan/identity/goal + real unchanged Explorer source refs only; no complete reference packet, anchors, guidance or reference implementation",
            "production_changes": False,
            "cost_measurement": "provider tokens/local elapsed observed; cloud tokens and Primary active minutes unknown; automated Primary fixture packets cannot measure real-project effort savings",
        },
    )
    matrix.preflight()


def explore(identity):
    cell = next(c for c in matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    matrix.SCOPE.FA.LAYER.verify_hashes(root, cell["hashes"])
    question = "Locate run_batch in src/product/entry.py through labelled_receipt to normalize_labels and collect_values. Cite the actual entry, receipt, labels helper and collector files plus protected public roundtrip assertion in tests/test_target.py. One call-chain investigation only; return locations, not repairs or predicted validation."
    packet = read(root / ".agent/normalize-unit-bound.json")
    matrix.SCOPE.invoke(
        root,
        "explorer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            question,
            "--task-id",
            packet["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
    )
    print(json.dumps(read(root / ".agent/explorer.json")))


def run(identity, unit):
    contract = configure()
    if not read(BASE / "preflight-1.json")["all_pass"]:
        raise ValueError("preflight missing")
    cell = next(c for c in matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / f".agent/{unit}-bound.json")
    plan = read(root / ".agent/feature-plan.json")
    refs, expected = {}, dict(cell["hashes"])
    for uid in cell["units"]:
        prior = read(root / f".agent/{uid}-bound.json")
        archive = root / ".agent/tasks" / prior["task_id"] / "runs" / prior["run_id"]
        if not (archive / "review.json").exists():
            continue
        refs[uid] = {k: prior[k] for k in ("task_id", "run_id")}
        for change in read(archive / "handoff.json")["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
    accepted = contract.accepted_units_from_archives(plan, root, refs)
    if unit in accepted or not set(packet["dependencies"]) <= accepted:
        raise ValueError("unit replay or missing accepted dependencies")
    matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    explorer = read(root / ".agent/explorer.json")
    bounded = copy.deepcopy(explorer)
    bounded["source_refs"] = [
        r
        for r in explorer["source_refs"]
        if digest(root / r["path"]) == r["source_hash"]
    ]
    request = {
        "capability": "localization_only",
        "task_id": packet["task_id"],
        "unit_id": unit,
        "question": explorer["task"],
    }
    contract.validate_localization_dispatch(
        plan, packet, request, bounded, repo_root=root
    )
    spec = importlib.util.spec_from_file_location(
        "label_supervised", SNAPSHOT / ".local-agents/coordinator-supervised.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = read(root / ".agent/config.json")
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    state = contract.load_coordinator_state(plan, root, state_path)
    started = time.monotonic()
    active_path = root / f".agent/{unit}-bound.json"
    if cell["arm"] == "coordinator":
        client = module.MODEL.WORKER.LMStudioClient(
            config["lmstudio_base_url"],
            config["coordinator_model"],
            structured_output=False,
            timeout=config["coordinator_request_timeout_seconds"],
            max_tokens=config["coordinator_max_tokens"],
            context_length=config["coordinator_context_length"],
        )
        context = {
            "identity": {
                k: packet[k]
                for k in ("unit_id", "run_id", "attempt", "packet_revision")
            },
            "feature_goal": fixture.case()["goal"],
            "source_refs": bounded["source_refs"],
            "question": "Prepare one bounded implementation proposal for this authorized unit from the Primary hard plan and actual source evidence. Choose useful symbol anchors and required focused tests. No scope expansion, test edits, acceptance, reference code or architecture.",
        }
        write(root / f".agent/{unit}-proposal-input.json", context)
        with module.MODEL.RESIDENCY.role_model_lease(client, config):
            proposal = module.MODEL.probe(
                plan,
                context,
                "proposal",
                client,
                reasoning_strength=config["coordinator_reasoning_strength"],
            )
        write(root / f".agent/{unit}-proposal.json", proposal)
        if proposal["status"] != "protocol_valid":
            write(
                root / f".agent/{unit}-invocation.json",
                {
                    "seconds": time.monotonic() - started,
                    "stage": "proposal",
                    "passed": False,
                },
            )
            print(json.dumps(proposal))
            return
        actual = contract.materialize_bounded_packet(plan, proposal["output"])
        if any(
            actual[k] != packet[k]
            for k in ("unit_id", "run_id", "attempt", "packet_revision")
        ):
            raise ValueError("proposal differs from authorized identity")
        active_path = root / f".agent/{unit}-coordinator-packet.json"
        write(active_path, actual)
    code, result = module.ROUTE.run_localization_unit(
        repo_root=root,
        plan=plan,
        packet_path=active_path,
        request=request,
        explorer_report=bounded,
        state_path=state_path,
        run_refs=refs,
        config_path=root / ".agent/config.json",
        coder_report_path=root / f".agent/{unit}-coder.json",
        review_report_path=root / f".agent/{unit}-reviewer.json",
        authorized_sequence=state["sequence"],
    )
    write(
        root / f".agent/{unit}-invocation.json",
        {"seconds": time.monotonic() - started, "exit": code, "result": result},
    )
    print(json.dumps(result))
    if code == 0 and unit == "receipt-unit":
        write(
            root / f".agent/{unit}-primary-checks.json",
            matrix.SCOPE.FA.LAYER.check(root, unit + "-primary"),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "action", choices=("prepare", "explore", "run", "record", "adjudicate-explorer")
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    elif args.action == "explore":
        explore(args.identity)
    elif args.action == "run":
        run(args.identity, args.unit)
    else:
        import qualification_controls as controls
        import qualification_evidence as evidence

        if args.action == "record":
            controls.record(args.identity, args.unit, args.decision, args.summary)
        else:
            evidence.explorer(args.identity, args.summary)
