"""Registered failure injection; only subsequent live calls earn model credit."""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import coordinator_numeric_case as numeric
import mixed_feature_benchmark as mixed
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-failure-recovery-2"
SNAPSHOT = WORK / "coordinator-report-baseline-2"
CASE = "zero-key-recovery"
QUESTION = "Locate the current normalize_labels definition in src/product/labels.py, the separate parse_code definition in src/product/schema.py, and the actual test_normalize/test_empty_labels assertions in tests/test_target.py. Read those three files and cite small actual ranges. Locations only, not repairs or predicted validation."


def module():
    spec = importlib.util.spec_from_file_location(
        "failure_supervised", SNAPSHOT / ".local-agents/coordinator-supervised.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def prepare():
    BASE.mkdir(exist_ok=False)
    files = {
        **numeric.INITIAL,
        **numeric.REFERENCE,
        "tests/test_target.py": numeric.TESTS,
    }
    # Primary fixture seed, not an accepted Coder implementation or leaked oracle.
    files["src/product/labels.py"] = (
        "from product.schema import parse_code\n\ndef normalize_labels(labels):\n    return [parse_code(text.strip()) for text in labels if text.strip() and text.strip() != '0']\n"
    )
    case = numeric.case()
    case.update(
        case_id=CASE,
        origin="registered-zero-key-failure-rework-composition",
        files=files,
        goal="Repair normalization while preserving the full decimal-key async receipt pipeline and all public error/boundary behavior.",
    )
    unit = case["units"][0]
    unit.update(
        unit_id="repair-unit",
        paths=["src/product/labels.py"],
        anchors={"src/product/labels.py": "normalize_labels"},
        tests=["tests/test_target.py"],
        contract="normalize_labels strips and drops only blank strings and returns base-10 integer keys via the existing parse_code, preserving order, duplicates and input; invalid values propagate ValueError before any fetch. Preserve the read-only public receipt pipeline, false result values/types, sequential error identity/stop and empty-input zero I/O. Existing schema, collector, receipt, public entry and protected tests are read-only.",
    )
    case["units"] = [unit]
    write(BASE / "corpus.json", {"cases": [case]})
    config = read(WORK / "coordinator-numeric-pilot-4/coordinator-config.json")
    config["explorer_required_citation_paths"] = [
        "src/product/labels.py",
        "src/product/schema.py",
        "tests/test_target.py",
    ]
    write(BASE / "config.json", config)
    mixed.CORPUS, mixed.WORK = BASE / "corpus.json", BASE / "runs"
    root = Path(
        mixed.prepare(CASE, 1, BASE / "config.json", "failure1-coordinator")["root"]
    )
    supervised = module()
    plan = read(root / ".agent/feature-plan.json")
    packet = read(root / ".agent/repair-unit-reference.json")
    packet["primary_plan_sha256"] = supervised.CONTRACT.authority_fingerprint(plan)
    packet = supervised.CONTRACT.validate_unit_packet(plan, packet)
    load_worker(SNAPSHOT).validate_packet(packet)
    write(root / ".agent/initial-bound.json", packet)
    write(
        BASE / "registration.json",
        {
            "driver_sha256": digest(Path(__file__)),
            "root": str(root),
            "snapshot": str(SNAPSHOT),
            "weekly_used_ceiling": 15,
            "qualification_risk": "high",
            "functional_risk": "medium",
            "initial_scripted_worker_model_credit": False,
            "initial_defect": "incorrectly drops the valid integer zero key",
            "previous_preparation_failure": "coordinator-failure-recovery-1: missing import correctly rejected by required initial Ruff check, no model calls",
            "fixture_seed_is_not_accepted_model_code": True,
            "required_stages": [
                "fresh localization",
                "scripted real-runtime validation failure",
                "live Coordinator escalation without recovery grant",
                "Primary verified terminal recovery grant",
                "fresh localization",
                "live authorized decision/proposal/Coder/Reviewer",
                "Primary review and seven-test integration",
            ],
            "files": {p: digest(root / p) for p in files},
            "production": read(SNAPSHOT / "freeze.json")["files"],
        },
    )
    print(json.dumps({"registered": True, "root": str(root)}))


def context():
    registration = read(BASE / "registration.json")
    if digest(Path(__file__)) != registration["driver_sha256"]:
        raise ValueError("registered driver drift")
    if any(digest(KIT / p) != h for p, h in registration["production"].items()):
        raise ValueError("production drift")
    root = Path(registration["root"])
    return (
        root,
        module(),
        read(root / ".agent/feature-plan.json"),
        read(root / ".agent/initial-bound.json"),
        read(root / ".agent/config.json"),
    )


def explore(label):
    root, _, _, packet, _ = context()
    argv = [
        sys.executable,
        str(SNAPSHOT / ".local-agents/local-explore.py"),
        "--task",
        QUESTION,
        "--task-id",
        packet["task_id"],
        "--config",
        str(root / ".agent/config.json"),
        "--report",
        str(root / f".agent/{label}-explorer.json"),
        "--full-report",
    ]
    result = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
    write(
        root / f".agent/{label}-explorer-invocation.json",
        {"exit": result.returncode, "output": result.stdout + result.stderr},
    )
    report = read(root / f".agent/{label}-explorer.json")
    print(
        json.dumps(
            {
                "status": report["status"],
                "source_refs": report["source_refs"],
                "failure_reason": report["failure_reason"],
            }
        )
    )


def adjudicate(label, summary):
    root, _, _, _, config = context()
    report = read(root / f".agent/{label}-explorer.json")
    if (
        report["status"] != "success"
        or report["cache"]["hit"]
        or report["uncertainties"]
        or not summary
    ):
        raise ValueError("fresh qualified localization and Primary judgment required")
    for ref in report["source_refs"]:
        source = root / ref["path"]
        lines = source.read_text(encoding="utf-8").splitlines()
        a, b = ref["start_line"], ref["end_line"]
        if (
            digest(source) != ref["source_hash"]
            or not 1 <= a <= b <= len(lines)
            or ref["quote"] != "\n".join(lines[a - 1 : b])
        ):
            raise ValueError("invalid citation")
    if not set(config["explorer_required_citation_paths"]) <= {
        r["path"] for r in report["source_refs"]
    }:
        raise ValueError("missing required path")
    write(
        root / f".agent/{label}-explorer-primary.json",
        {
            "success": True,
            "report_sha256": digest(root / f".agent/{label}-explorer.json"),
            "summary": summary,
        },
    )


def proof(root, label):
    primary = read(root / f".agent/{label}-explorer-primary.json")
    path = root / f".agent/{label}-explorer.json"
    if not primary["success"] or digest(path) != primary["report_sha256"]:
        raise ValueError("Primary localization approval missing/stale")
    return read(path)


def inject():
    root, supervised, plan, _packet, config = context()
    worker = load_worker(SNAPSHOT)

    def scripted(repo, packet_path, config_path, coder_report_path, review_report_path):
        class Client:
            def complete(self, _messages):
                return json.dumps(next(self.actions))

        client = Client()
        runtime = worker.WorkerRuntime(repo, read(packet_path), config, client)
        source = "src/product/labels.py"
        client.actions = iter(
            [
                {"action": "READ_FILE", "arguments": {"path": source}},
                {
                    "action": "SAFE_REPLACE",
                    "arguments": {
                        "path": source,
                        "expected_sha256": digest(repo / source),
                        "find": 'text.strip() != "0"',
                        "replace": "parse_code(text.strip()) != 0",
                    },
                },
                *[
                    {
                        "action": "VALIDATE",
                        "arguments": {
                            "contract_check": runtime.contract_check_template()
                        },
                    }
                    for _ in range(2)
                ],
            ]
        )
        runtime.preflight()
        report = runtime.run()
        worker.write_report(report, coder_report_path, compact=True)
        if report["status"] != "failed" or "validation" not in report:
            raise ValueError("scripted failure did not create real validation failure")
        return 1, {"status": "failed", "fault_injected": True, "model_credit": False}

    state = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    explorer = proof(root, "initial")
    request = {
        "task_id": plan["task_id"],
        "unit_id": "repair-unit",
        "capability": "localization_only",
        "question": explorer["task"],
    }
    code, result = supervised.ROUTE.run_localization_unit(
        repo_root=root,
        plan=plan,
        packet_path=root / ".agent/initial-bound.json",
        request=request,
        explorer_report=explorer,
        state_path=state,
        run_refs={},
        config_path=root / ".agent/config.json",
        coder_report_path=root / ".agent/injected-coder.json",
        review_report_path=root / ".agent/injected-reviewer.json",
        unit_runner=scripted,
    )
    write(
        root / ".agent/injection-result.json",
        {"exit": code, "result": result, "local_llm_coder_credit": False},
    )
    print(json.dumps(result))


def step(recover):
    root, supervised, plan, packet, config = context()
    old = packet["run_id"]
    identity = {
        k: packet[k] for k in ("unit_id", "run_id", "attempt", "packet_revision")
    }
    identity.update(run_id=old.replace("-a1", "-a2"), attempt=2, packet_revision=2)
    label = "recovery" if recover else "initial"
    explorer = proof(root, label)
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    state = supervised.CONTRACT.load_coordinator_state(plan, root, state_path)
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / old
    handoff = read(archive / "handoff.json")
    context_data = {
        "identity": identity,
        "goal": "Repair the actual failed unit without changing its protected pipeline contract or scope.",
        "source_refs": explorer["source_refs"],
        "observed_failure": {
            "failure_reason": handoff.get("failure_reason"),
            "validation": handoff.get("validation"),
        },
    }
    client = supervised.MODEL.WORKER.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        structured_output=False,
        timeout=config["coordinator_request_timeout_seconds"],
        max_tokens=config["coordinator_max_tokens"],
        context_length=config["coordinator_context_length"],
    )
    authorization = (
        root
        / ".agent/primary-reviews"
        / plan["feature_id"]
        / "recovery"
        / (old + ".json")
    )
    code, result = supervised.run_step(
        root=root,
        plan=plan,
        context=context_data,
        request={
            "task_id": packet["task_id"],
            "unit_id": "repair-unit",
            "capability": "localization_only",
            "question": explorer["task"],
        },
        explorer=explorer,
        run_refs={},
        config=config,
        config_path=root / ".agent/config.json",
        authorized=True,
        expected_sequence=state["sequence"],
        client=client,
        recovery_authorization_path=authorization if recover else None,
        proposal_id="authorized-recovery"
        if recover
        else "unapproved-failure-observation",
    )
    write(root / f".agent/{label}-step-result.json", {"exit": code, "result": result})
    print(json.dumps(result))


def authorize(summary):
    root, supervised, plan, packet, _ = context()
    state_path = root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    state = supervised.CONTRACT.load_coordinator_state(plan, root, state_path)
    old = packet["run_id"]
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / old
    if not summary or read(archive / "completed.json")["status"] != "failed":
        raise ValueError("Primary reviewed terminal failure rationale required")
    target = (
        root
        / ".agent/primary-reviews"
        / plan["feature_id"]
        / "recovery"
        / (old + ".json")
    )
    write(
        target,
        {
            "schema_version": 1,
            "feature_id": plan["feature_id"],
            "task_id": plan["task_id"],
            "unit_id": "repair-unit",
            "failed_run_id": old,
            "new_run_id": old.replace("-a1", "-a2"),
            "primary_plan_sha256": supervised.CONTRACT.authority_fingerprint(plan),
            "failed_packet_sha256": digest(root / ".agent/initial-bound.json"),
            "archived_packet_sha256": digest(archive / "packet.json"),
            "completed_sha256": digest(archive / "completed.json"),
            "expected_sequence": state["sequence"],
            "decision": "REWORK_LOCAL",
            "reason_code": "focused-validation-failure",
            "primary_rationale": summary,
        },
    )
    result = supervised.ROUTE.recover_terminal_failed_unit(
        repo_root=root,
        plan=plan,
        failed_packet_path=root / ".agent/initial-bound.json",
        state_path=state_path,
        authorization_path=target,
        run_refs={},
    )
    write(root / ".agent/primary-recovery-transition.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "inject",
            "observe",
            "authorize",
            "recover",
        ),
    )
    parser.add_argument("--label", default="initial", choices=("initial", "recovery"))
    parser.add_argument("--summary")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "explore":
        explore(args.label)
    elif args.action == "adjudicate":
        adjudicate(args.label, args.summary)
    elif args.action == "inject":
        inject()
    elif args.action == "authorize":
        authorize(args.summary)
    else:
        step(args.action == "recover")
