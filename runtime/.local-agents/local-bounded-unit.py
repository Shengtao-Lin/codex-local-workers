"""Explicit bounded-v1 unit entry; uses the existing editor, gates and archives."""

import argparse
import copy
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

from bounded import capture_fixture_support as F
from bounded import compatibility_profile as COMPAT
from bounded import consolidated_harness as H
from bounded import harness_protocol as P
from bounded import primary_receipt as RECEIPT
from bounded import static_focus_rules as RULES

ROOT = Path(__file__).resolve().parent


def write_coder_report(worker, report, args):
    if not args.compact_output:
        return worker.write_report(report, args.report, compact=False)
    # Preserve the original full report writer and file contents. Only its
    # redundant stdout copy is replaced by a final unit-level receipt.
    with contextlib.redirect_stdout(io.StringIO()):
        return worker.write_report(report, args.report, compact=False)


def emit_receipt(report, summary, args):
    if not args.compact_output:
        return
    reviewer = None
    if args.review_report.exists() and summary.get("reviewer_input_authenticated") is True:
        reviewer = json.loads(args.review_report.read_text(encoding="utf-8"))
    receipt = RECEIPT.build(
        report,
        summary,
        reviewer,
        {
            "full_coder_report": str(args.report),
            "full_reviewer_report": str(args.review_report)
            if args.review_report.exists()
            else None,
            "unit_summary": str(args.summary),
        },
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)


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


def bound_review_result(root, request, report_path, exit_code, offline):
    """Convenience files do not establish a successful current review."""
    decision = "NOT_RUN" if offline else "failed"
    error = None
    reported_decision = None
    try:
        value = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("reviewer_report_not_object")
        reported_decision = value.get("decision")
        if exit_code != 0:
            raise ValueError("reviewer_process_failed")
        if offline:
            if (
                value.get("mode") != "offline-input-inspection"
                or type(value.get("model_calls")) is not int
                or value["model_calls"] != 0
                or value.get("reviewer_dispatched") is not False
                or value.get("reviewer_acceptance") is not False
            ):
                raise ValueError("invalid_offline_inspection")
        else:
            expected = {k: request[k] for k in ("task_id", "unit_id", "run_id", "review_id")}
            if value.get("identity") != expected:
                raise ValueError("reviewer_identity_mismatch")
            archive = root / ".agent/tasks" / request["task_id"] / "reviews" / request["review_id"]
            canonical = json.loads((archive / "handoff.json").read_text(encoding="utf-8"))
            completed = json.loads((archive / "completed.json").read_text(encoding="utf-8"))
            if canonical != value or not isinstance(completed, dict):
                raise ValueError("reviewer_canonical_mismatch")
            observed = value.get("decision")
            if (
                observed not in {"pass_to_primary", "rework", "escalate"}
                or completed.get("decision") != observed
            ):
                raise ValueError("reviewer_completion_mismatch")
            decision = observed
    except (OSError, ValueError, TypeError) as exc:
        error = str(exc)
    result = {
        "reviewer_started": not offline,
        "reviewer_input_authenticated": error is None,
        "reviewer_decision": decision,
        "reviewer_exit": exit_code,
        "reviewer_reported_decision": reported_decision,
    }
    if error is not None:
        result["reviewer_result_error"] = error
    return result


def review(root, args, worker, report, config, offline):
    gate = F.load(ROOT / "local-unit.py", "bounded_unit_gate")
    identity = gate.verify_handoff(root, report, config=config)
    archive = root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
    request = {
        "schema_version": 1,
        **identity,
        "review_id": "auto-" + identity["run_id"],
        "execution_protocol": report["execution_protocol"],
    }
    review_config = {**config, "reviewer_compact_report": True, "reviewer_evidence_state": True}
    worker.RUN_STATE.write_json_once(archive / "review-request.json", request)
    worker.RUN_STATE.write_json_once(archive / "review-config.json", review_config)
    command = [
        sys.executable,
        "-B",
        str(ROOT / "local-bounded-review.py"),
        "--request",
        str(archive / "review-request.json"),
        "--config",
        str(archive / "review-config.json"),
        "--report",
        str(args.review_report),
    ]
    if offline:
        command.append("--inspect-only")
    if args.compact_output:
        with (archive / "reviewer-process.stdout.log").open("x", encoding="utf-8") as stdout:
            with (archive / "reviewer-process.stderr.log").open("x", encoding="utf-8") as stderr:
                result = subprocess.run(
                    command, cwd=root, timeout=900, check=False, stdout=stdout, stderr=stderr
                )
    else:
        result = subprocess.run(command, cwd=root, timeout=900, check=False)
    return bound_review_result(root, request, args.review_report, result.returncode, offline)


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--mode", choices=("preflight", "coder", "unit"), default="unit")
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--review-report", type=Path)
    p.add_argument("--summary", type=Path)
    p.add_argument(
        "--compact-output",
        action="store_true",
        help="Unit stdout receipt only; full reports and canonical evidence remain unchanged",
    )
    p.add_argument(
        "--replay", type=Path, help="Offline diagnostic responses; never model acceptance"
    )
    args = p.parse_args()
    if args.mode == "unit" and (args.review_report is None or args.summary is None):
        p.error("unit requires review-report and summary")
    if args.compact_output and args.mode != "unit":
        p.error("compact-output requires unit mode")
    root = Path.cwd().resolve()
    worker = F.load(ROOT / "worker-runtime.py", "bounded_installed_worker")
    config = worker.load_json(args.config)
    if config.get("bounded_evidence_profile") == "pytest-source-v1" and (
        args.mode == "unit" or (args.mode == "coder" and args.replay is None)
    ):
        raise worker.WorkerError(
            "Generic source profile requires explicit native direct-Primary route; legacy live/Reviewer routes are disabled"
        )
    if config.get("bounded_execution_profile") != "bounded-v1":
        raise worker.WorkerError("Explicit bounded-v1 profile required")
    rules = COMPAT.proposal_rules(config, RULES)
    packet = worker.resolve_inherited_packet(root, worker.load_json(args.packet))
    offline = args.mode == "preflight" or args.replay is not None
    if offline:

        def deny_network(*_args, **_kwargs):
            raise AssertionError("Network forbidden in offline replay")

        worker.urllib.request.urlopen = deny_network
        values = json.loads(args.replay.read_text(encoding="utf-8")) if args.replay else []
        if not isinstance(values, list):
            p.error("replay must contain an array")
        client = ReplayClient(values, worker)
        client.action_schema = copy.deepcopy(rules.SCHEMA)
    else:
        client = worker.LMStudioClient(
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
            action_schema=copy.deepcopy(rules.SCHEMA),
            schema_name="consolidated_proposal_v1",
        )
    runtime = H.make_runtime(worker, proposal_rules=rules)(root, packet, config, client)
    try:
        capture_preflight = F.preflight_material(runtime)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        worker.WorkerError,
        worker.SafeEditError,
    ) as exc:
        runtime.close()
        report = {
            "schema_version": 2,
            "status": "blocked",
            "preflight": "blocked",
            "model_calls": 0,
            "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
            "failure_reason": str(exc),
            "infra_failure": {"reason_code": "bounded_capture_preflight", "reason": str(exc)},
            "next_action_required": "primary_preparation_correction",
        }
        if not write_coder_report(worker, report, args):
            return 1
        if args.mode == "unit":
            summary = {
                "coder_status": "blocked",
                "reviewer_started": False,
                "reviewer_decision": "NOT_RUN",
                "automatic_coder_rework": False,
            }
            worker.RUN_STATE.write_json_once(args.summary, summary)
            emit_receipt(report, summary, args)
        return 2
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
                    "capture_preflight": capture_preflight,
                },
            )
        finally:
            runtime.close()
        return 0
    if offline:
        runtime.preflight()
        report = runtime.run()
    else:
        try:
            with worker.MODEL_RESIDENCY.role_model_lease(client, config):
                runtime.preflight()
                report = runtime.run()
        except worker.MODEL_RESIDENCY.ModelResidencyError as exc:
            runtime.close()
            report = {
                "schema_version": 2,
                "status": "blocked",
                "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
                "failure_reason": str(exc),
                "blocked": {"reason_code": exc.reason_code, "reason": str(exc)},
                "infra_failure": {"reason_code": exc.reason_code, "reason": str(exc)},
                "next_action_required": "primary_environment_decision",
            }
    if not write_coder_report(worker, report, args):
        return 1
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
        emit_receipt(report, summary, args)
        if report["status"] == "validation_passed_pending_review":
            return (
                0
                if (
                    summary["reviewer_input_authenticated"]
                    if offline
                    else summary["reviewer_decision"] == "pass_to_primary"
                )
                else 2
            )
    return 0 if report["status"] == "validation_passed_pending_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
