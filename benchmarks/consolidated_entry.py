"""One explicit entry for real Coder, preflight and no-network full unit replay."""

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

import capture_fixture_support as F
import consolidated_harness as H
import harness_protocol as P


class ReplayClient:
    offline = True
    structured_output = True
    native_tools = None
    typed_action_arguments = False
    action_schema = P.SCHEMA
    timeout = 180
    last_request_stats = None

    def __init__(self, responses, worker):
        self.responses = iter(responses)
        self.worker = worker

    def complete(self, _messages):
        value = next(self.responses)
        if isinstance(value, dict) and set(value) == {"_model_error"}:
            raise self.worker.ModelRequestError(
                value["_model_error"], "scripted transport control", {}
            )
        return value if isinstance(value, str) else json.dumps(value)


def client_at(worker, config):
    return worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["coder_model"],
        int(config.get("model_request_timeout_seconds", 180)),
        max_tokens=int(config.get("coder_max_tokens", 4096)),
        temperature=float(config.get("coder_temperature", 0.1)),
        top_p=float(config.get("coder_top_p", 0.9)),
        top_k=int(config.get("coder_top_k", 40)),
        min_p=float(config.get("coder_min_p", 0.0)),
        repeat_penalty=float(config.get("coder_repeat_penalty", 1.0)),
        structured_output=True,
        context_length=int(config["coder_context_length"]),
        context_safety_margin=int(config.get("model_context_safety_margin", 1024)),
        action_schema=copy.deepcopy(P.SCHEMA),
        schema_name="consolidated_proposal_v1",
    )


def read_review_decision(path):
    # All runtime archives are UTF-8, regardless of the Windows active codepage.
    report = json.loads(path.read_text(encoding="utf-8"))
    decision = report["decision"]
    if decision not in {
        "pass_to_primary",
        "rework",
        "escalate",
        "failed",
        "blocked",
        "interrupted",
    }:
        raise ValueError("Invalid Reviewer decision")
    return decision


def review(root, args, worker, report, config, offline):
    gate = F.load(args.runtime_dir / "local-unit.py", "consolidated_unit_gate")
    identity = gate.verify_handoff(root, report, config=config)
    archive = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
    request = {
        "schema_version": 1,
        **identity,
        "review_id": "auto-" + identity["run_id"],
        "execution_protocol": report["execution_protocol"],
    }
    review_config = {
        **config,
        "reviewer_compact_report": True,
        "reviewer_evidence_state": True,
    }
    worker.RUN_STATE.write_json_once(archive / "review-request.json", request)
    worker.RUN_STATE.write_json_once(archive / "review-config.json", review_config)
    command = [sys.executable]
    command += [
        "-B",
        str(F.KIT / "benchmarks/reviewer_capture_entry.py"),
        "--runtime-dir",
        str(args.runtime_dir),
        "--capture-policy",
        F.POLICY_PATH,
        "--capture-policy-sha256",
        config["experimental_capture_policy_sha256"],
        "--request",
        str(archive / "review-request.json"),
        "--config",
        str(archive / "review-config.json"),
        "--report",
        str(args.review_report),
    ]
    if offline:
        command.append("--inspect-only")
    if args.reviewer_forward_reasoning:
        command.append("--forward-reasoning-effort")
    result = subprocess.run(command, cwd=root, timeout=900, check=False)
    return {
        "reviewer_started": not offline,
        "reviewer_input_authenticated": result.returncode == 0,
        "reviewer_decision": "NOT_RUN"
        if offline
        else read_review_decision(args.review_report),
        "reviewer_exit": result.returncode,
    }


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--mode", choices=["preflight", "coder", "unit"], required=True)
    p.add_argument("--runtime-dir", type=Path, required=True)
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--replay", type=Path)
    p.add_argument("--review-report", type=Path)
    p.add_argument("--summary", type=Path)
    wire_format = p.add_mutually_exclusive_group()
    wire_format.add_argument("--preserve-existing-imports", action="store_true")
    wire_format.add_argument("--function-output", action="store_true")
    wire_format.add_argument("--bounded-source-output", action="store_true")
    p.add_argument("--literal-check-feedback", action="store_true")
    p.add_argument("--focused-repair", action="store_true")
    p.add_argument("--self-audit", action="store_true")
    p.add_argument("--static-focus", action="store_true")
    p.add_argument("--execution-memory", action="store_true")
    p.add_argument("--evidence-loop", action="store_true")
    p.add_argument("--failure-source", action="store_true")
    p.add_argument("--repair-start", action="store_true")
    p.add_argument("--reviewer-forward-reasoning", action="store_true")
    p.add_argument("--experimental-rework-permit", type=Path)
    p.add_argument("--experimental-rework-permit-sha256")
    args = p.parse_args()
    if args.literal_check_feedback and not args.function_output:
        p.error("literal-check-feedback requires function-output")
    if args.focused_repair and not args.bounded_source_output:
        p.error("focused-repair requires bounded-source-output")
    if args.self_audit and not args.focused_repair:
        p.error("self-audit requires focused-repair")
    if args.static_focus and (not args.focused_repair or args.self_audit):
        p.error("static-focus requires focused-repair and excludes self-audit")
    if args.execution_memory and not args.static_focus:
        p.error("execution-memory requires static-focus")
    if args.evidence_loop and (not args.static_focus or args.execution_memory):
        p.error("evidence-loop requires static-focus and excludes execution-memory")
    if args.failure_source and (
        not args.static_focus or args.execution_memory or args.evidence_loop
    ):
        p.error(
            "failure-source requires static-focus and excludes memory/evidence-loop"
        )
    if args.repair_start and not args.failure_source:
        p.error("repair-start requires failure-source")
    root = Path.cwd()
    worker = F.load(args.runtime_dir / "worker-runtime.py", "consolidated_worker")
    config = worker.load_json(args.config)
    if bool(args.experimental_rework_permit) != bool(
        args.experimental_rework_permit_sha256
    ):
        p.error("Experimental permit and digest must be supplied together")
    if args.experimental_rework_permit:
        import reviewer_rework_permit

        packet = reviewer_rework_permit.resolve(
            worker,
            root,
            worker.load_json(args.packet),
            args.experimental_rework_permit,
            args.experimental_rework_permit_sha256,
        )
    else:
        packet = worker.resolve_inherited_packet(root, worker.load_json(args.packet))
    offline = args.mode == "preflight" or args.replay is not None
    if args.mode == "unit" and (args.review_report is None or args.summary is None):
        p.error("unit requires review-report and summary")
    if offline:

        def deny_network(*_args, **_kwargs):
            raise AssertionError("Network forbidden in offline replay")

        worker.urllib.request.urlopen = deny_network
        responses = (
            json.loads(args.replay.read_text(encoding="utf-8")) if args.replay else []
        )
        if not isinstance(responses, list):
            p.error("replay must contain an array of scripted responses")
        client = ReplayClient(responses, worker)
    else:
        client = client_at(worker, config)
    if args.bounded_source_output:
        import bounded_source_rules

        rules = bounded_source_rules
        if args.focused_repair:
            import repair_phase_rules

            rules = repair_phase_rules
        if args.self_audit:
            import self_audit_rules

            rules = self_audit_rules
        if args.static_focus:
            import static_focus_rules

            rules = static_focus_rules
        if args.execution_memory:
            import continuity_rules

            rules = continuity_rules
        if args.evidence_loop:
            import evidence_loop_rules

            rules = evidence_loop_rules
            client.action_schema = copy.deepcopy(rules.SCHEMA)
        if args.failure_source:
            import failure_source_rules

            rules = failure_source_rules
        if args.repair_start:
            import initial_repair_rules

            rules = initial_repair_rules
        runtime = H.make_runtime(worker, proposal_rules=rules)(
            root, packet, config, client
        )
    elif args.function_output:
        import function_proposal_rules

        rules = function_proposal_rules
        if args.literal_check_feedback:
            import literal_feedback_rules

            rules = literal_feedback_rules
        runtime = H.make_runtime(worker, proposal_rules=rules)(
            root, packet, config, client
        )
    elif args.preserve_existing_imports:
        import preserved_import_guard

        runtime = H.make_runtime(worker, proposal_rules=preserved_import_guard)(
            root, packet, config, client
        )
    else:
        runtime = H.make_runtime(worker)(root, packet, config, client)
    if args.mode == "preflight":
        try:
            runtime.preflight()
            worker.RUN_STATE.write_json_once(
                args.report,
                {
                    "preflight": "passed",
                    "model_calls": 0,
                    "runtime_mro": [c.__name__ for c in type(runtime).__mro__],
                    "budget": H.BUDGET,
                },
            )
        finally:
            runtime.close()
        return 0
    if offline:
        runtime.preflight()
        report = runtime.run()
    else:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            runtime.preflight()
            report = runtime.run()
    if not worker.write_report(report, args.report, compact=False):
        return 1
    if args.mode == "coder" and args.summary is not None:
        worker.RUN_STATE.write_json_once(
            args.summary,
            {
                "coder_status": report["status"],
                "reviewer_started": False,
                "reviewer_decision": "NOT_RUN_DIAGNOSTIC",
                "automatic_coder_rework": False,
            },
        )
    if args.mode == "unit":
        summary = {
            "coder_status": report["status"],
            "reviewer_started": False,
            "reviewer_decision": "NOT_RUN",
            "automatic_coder_rework": False,
        }
        if report["status"] == "validation_passed_pending_review":
            summary.update(review(root, args, worker, report, config, offline))
        worker.RUN_STATE.write_json_once(args.summary, summary)
        if report["status"] == "validation_passed_pending_review":
            return (
                0
                if (
                    summary.get("reviewer_input_authenticated")
                    if offline
                    else summary.get("reviewer_decision") == "pass_to_primary"
                )
                else 2
            )
    return 0 if report["status"] == "validation_passed_pending_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
