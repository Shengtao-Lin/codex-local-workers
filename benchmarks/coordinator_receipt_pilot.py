"""Fresh paired receipt pilot; Primary acceptance remains explicit and external."""

import argparse
import copy
import importlib.util
import json
import time
from pathlib import Path

import qualification_matrix as matrix
from capability_fit import WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-receipt-pilot-2"
SNAPSHOT = WORK / "qualification-matrix-baseline-6"
SOURCE = WORK / "qualification-matrix-6"


def configure():
    matrix.BASE, matrix.SNAPSHOT = BASE, SNAPSHOT
    matrix.MIXED.CORPUS, matrix.MIXED.WORK = SOURCE / "corpus.json", BASE / "runs"
    matrix.CHAIN.SNAPSHOT = SNAPSHOT
    return matrix.CHAIN.load_contract()


def prepare():
    contract = configure()
    BASE.mkdir(exist_ok=False)
    if (
        not read(SOURCE / "preflight-1.json")["all_pass"]
        or not read(SOURCE / "assessment-initial-1.json")["qualification_gate"]
    ):
        raise ValueError("E/C/R qualification missing")
    cells = []
    source_manifest = read(SOURCE / "manifest.json")
    source_cell = next(
        c for c in source_manifest["cells"] if c["id"] == "async-receipt-r1"
    )
    source_root = Path(source_cell["root"])
    for repetition in (1, 2):
        for arm in ("control", "coordinator"):
            config = read(source_root / ".agent/config.json")
            config["coordinator_enabled"] = arm == "coordinator"
            config_path = BASE / f"{arm}-r{repetition}-config.json"
            write(config_path, config)
            root = Path(
                matrix.MIXED.prepare(
                    "async-receipt", repetition, config_path, "pilot2-" + arm
                )["root"]
            )
            plan = read(root / ".agent/feature-plan.json")
            for unit in ("collect-unit", "qual-unit"):
                packet = read(root / f".agent/{unit}-reference.json")
                packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
                packet = contract.validate_unit_packet(plan, packet)
                load_worker(SNAPSHOT).validate_packet(packet)
                write(root / f".agent/{unit}-bound.json", packet)
            paths = list(source_cell["hashes"])
            cells.append(
                {
                    "id": f"{arm}-r{repetition}",
                    "case": "async-receipt",
                    "round": repetition,
                    "arm": arm,
                    "root": str(root),
                    "units": ["collect-unit", "qual-unit"],
                    "explorer_required": True,
                    "hashes": {p: digest(root / p) for p in paths},
                }
            )
            for path in paths:
                if (
                    path.startswith(("src/", "tests/")) or path == "pyproject.toml"
                ) and digest(root / path) != source_cell["hashes"][path]:
                    raise ValueError(
                        "initial fixture differs from qualified cohort: " + path
                    )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "drivers": {str(Path(__file__).resolve()): digest(Path(__file__))},
            "cells": cells,
            "feature_id": "coordinator-receipt-pilot",
            "feature_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": [
                "bounded-dispatch",
                "accepted-dependency",
                "independent-review",
                "no-auto-acceptance",
            ],
            "risk_rationale": "Qualification authority is Primary-owned high risk; functional receipt units retain medium risk.",
        },
    )
    write(
        BASE / "preflight-1.json",
        {
            "all_pass": True,
            "basis": "Same registered corpus and discriminating 18-variant cohort-6 preflight; four actual fresh baselines failed as expected, source/test hashes verified",
            "new_model_credit": False,
        },
    )
    write(
        BASE / "registration.json",
        {
            "driver_sha256": digest(Path(__file__)),
            "source_corpus_sha256": digest(SOURCE / "corpus.json"),
            "order": ["coordinator-r1", "control-r1", "control-r2", "coordinator-r2"],
            "weekly_used_ceiling": 10,
            "changed_axis": "Coordinator decision/proposal versus direct Primary dispatch; only coordinator_enabled differs in role configuration",
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "quality_does_not_imply_cost_savings": True,
        },
    )
    print(
        "Registered four fresh receipt chains; source/tests and E/C/R settings retained"
    )


def run(identity, unit):
    contract = configure()
    registration = read(BASE / "registration.json")
    if digest(Path(__file__)) != registration["driver_sha256"]:
        raise ValueError("pilot driver drift")
    cell = next(c for c in matrix.verify()["cells"] if c["id"] == identity)
    if cell["arm"] == "control":
        return matrix.run(identity, unit)
    root = Path(cell["root"])
    packet = read(root / f".agent/{unit}-bound.json")
    plan = read(root / ".agent/feature-plan.json")
    refs = {}
    expected = dict(cell["hashes"])
    for dependency in packet["dependencies"]:
        dep = read(root / f".agent/{dependency}-bound.json")
        refs[dependency] = {k: dep[k] for k in ("task_id", "run_id")}
        archive = root / ".agent/tasks" / dep["task_id"] / "runs" / dep["run_id"]
        for change in read(archive / "handoff.json")["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
    if not set(packet["dependencies"]) <= contract.accepted_units_from_archives(
        plan, root, refs
    ):
        raise ValueError("dependency acceptance missing")
    matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    explorer = read(root / ".agent/explorer.json")
    # Reuse only unchanged, actually read evidence; never mint a fresh citation.
    bounded = copy.deepcopy(explorer)
    bounded["source_refs"] = [
        r
        for r in explorer["source_refs"]
        if digest(root / r["path"]) == r["source_hash"]
    ]
    write(root / f".agent/{unit}-locator-input.json", bounded)
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
        "receipt_supervised", SNAPSHOT / ".local-agents/coordinator-supervised.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = read(root / ".agent/config.json")
    client = module.MODEL.WORKER.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        structured_output=False,
        timeout=config["coordinator_request_timeout_seconds"],
        max_tokens=config["coordinator_max_tokens"],
        context_length=config["coordinator_context_length"],
    )
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    state = contract.load_coordinator_state(plan, root, state_path)
    context = {
        "identity": {
            k: packet[k] for k in ("unit_id", "run_id", "attempt", "packet_revision")
        },
        "primary_approved_packet": packet,
        "goal": packet["goal"],
        "question": "Recommend only the Primary-authorized ready unit. Preserve its readable/writable scope, focused tests and anchors; no architecture, acceptance, repair instructions or expanded scope.",
    }

    def router(**kwargs):
        kwargs["coder_report_path"] = root / f".agent/{unit}-coder.json"
        kwargs["review_report_path"] = root / f".agent/{unit}-reviewer.json"
        return module.ROUTE.run_localization_unit(**kwargs)

    started = time.monotonic()
    code, result = module.run_step(
        root=root,
        plan=plan,
        context=context,
        request=request,
        explorer=bounded,
        run_refs=refs,
        config=config,
        config_path=root / ".agent/config.json",
        authorized=True,
        expected_sequence=state["sequence"],
        client=client,
        router=router,
    )
    write(
        root / f".agent/{unit}-coordinator-invocation.json",
        {"exit": code, "seconds": time.monotonic() - started, "result": result},
    )
    print(json.dumps(result), flush=True)
    if code:
        return
    checks = (
        matrix.SCOPE.FA.LAYER.check(root, unit + "-primary")
        if packet["dependencies"]
        else None
    )
    if checks:
        write(root / f".agent/{unit}-primary-checks.json", checks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "run",
            "evidence",
            "record",
            "adjudicate-explorer",
            "integrate",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="collect-unit")
    parser.add_argument("--summary")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        prepare()
    elif args.action == "explore":
        matrix.explore(args.identity)
    elif args.action == "run":
        run(args.identity, args.unit)
    else:
        import qualification_controls as controls
        import qualification_evidence as evidence

        if args.action == "evidence":
            controls.evidence(args.identity, args.unit)
        elif args.action == "record":
            controls.record(args.identity, args.unit, args.decision, args.summary)
        elif args.action == "adjudicate-explorer":
            evidence.explorer(args.identity, args.summary)
        else:
            evidence.integrate(args.identity)
