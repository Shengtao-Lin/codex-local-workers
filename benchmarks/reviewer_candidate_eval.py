"""Read-only same-archive Reviewer candidate qualification.

The source and canonical Coder archive are never changed. Each review receives
its own immutable .agent review id. The configured Reviewer model is not edited.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = KIT / ".local-agents" / "reviewer-runtime.py"
SPEC = importlib.util.spec_from_file_location(
    "candidate_reviewer_runtime", RUNTIME_PATH
)
assert SPEC is not None and SPEC.loader is not None
REVIEWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REVIEWER
SPEC.loader.exec_module(REVIEWER)


def run(
    workspace: Path,
    model: str,
    repeats: int,
    output_dir: Path,
    approved_python_current: bool = False,
    bypass_startup_probe: bool = False,
    reviewer_native_tools: bool = False,
    request_timeout: int | None = None,
    reasoning_strength: str | None = None,
) -> Path:
    workspace = workspace.resolve()
    config = REVIEWER.load_object(workspace / ".local-agents" / "config.json")
    packet = REVIEWER.load_object(workspace / ".agent" / "packet.json")
    config["reviewer_model"] = model
    config["reviewer_native_tools"] = reviewer_native_tools
    if request_timeout is not None:
        config["model_request_timeout_seconds"] = request_timeout
    if reasoning_strength is not None:
        config["reviewer_reasoning_strength"] = reasoning_strength
    if approved_python_current:
        config["python"] = sys.executable
        for profile in config.get("validation_profiles", {}).values():
            profile["python"] = sys.executable
    results = []
    for index in range(1, repeats + 1):
        review_id = "candidate-" + uuid.uuid4().hex
        request = {
            "schema_version": 1,
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "run_id": packet["run_id"],
            "review_id": review_id,
        }
        client = REVIEWER.WORKER.LMStudioClient(
            config["lmstudio_base_url"],
            model,
            int(config.get("model_request_timeout_seconds", 180)),
            max_tokens=int(config.get("reviewer_max_tokens", 4096)),
            temperature=float(config.get("reviewer_temperature", 0.1)),
            top_p=float(config.get("reviewer_top_p", 0.9)),
            top_k=int(config.get("reviewer_top_k", 40)),
            min_p=float(config.get("reviewer_min_p", 0.0)),
            repeat_penalty=float(config.get("reviewer_repeat_penalty", 1.0)),
            structured_output=(
                False
                if reviewer_native_tools
                else bool(config.get("reviewer_structured_output", True))
            ),
            action_schema=REVIEWER.REVIEW_ACTION_SCHEMA,
            schema_name="local_reviewer_action",
            native_tools=(
                REVIEWER.REVIEW_NATIVE_TOOLS if reviewer_native_tools else None
            ),
            context_length=int(config["reviewer_context_length"]),
            context_safety_margin=int(config.get("model_context_safety_margin", 1024)),
        )
        if bypass_startup_probe:
            client.probe_structured_output = lambda: "diagnostic_startup_probe_bypassed"
        started = time.monotonic()
        try:
            report = REVIEWER.ReviewerRuntime(workspace, request, config, client).run()
            decision = report["decision"]
            reason = None
            infra_failure = False
            facts = report.get("runtime_facts", {})
        except (
            REVIEWER.ReviewError,
            REVIEWER.WORKER.WorkerError,
            REVIEWER.SAFE_EDIT.SafeEditError,
            OSError,
            ValueError,
        ) as exc:
            decision = "failed"
            reason = str(exc)[:400]
            infra_failure = isinstance(
                exc,
                (REVIEWER.WORKER.ModelRequestError, REVIEWER.WORKER.PreflightBlocked),
            ) or any(
                marker in reason
                for marker in ("HTTP Error", "timed out", "empty assistant")
            )
            facts = {}
        archive = (
            workspace / ".agent" / "tasks" / packet["task_id"] / "reviews" / review_id
        )
        result = {
            "repetition": index,
            "model": model,
            "review_id": review_id,
            "decision": decision,
            "failure_reason": reason,
            "infra_failure": infra_failure,
            "approved_python_override": approved_python_current,
            "startup_probe_bypassed": bypass_startup_probe,
            "reviewer_native_tools": reviewer_native_tools,
            "request_timeout_seconds": int(
                config.get("model_request_timeout_seconds", 180)
            ),
            "reasoning_strength": config.get("reviewer_reasoning_strength"),
            "seconds": round(time.monotonic() - started, 3),
            "review_archive": str(archive),
            "protocol_errors": facts.get("protocol_error_count"),
            "approved_execution": [
                {key: item.get(key) for key in ("kind", "id", "status", "exit_code")}
                for item in facts.get("approved_execution", [])
            ],
            "model_request": {
                key: value
                for key, value in client.last_request_stats.items()
                if key not in {"provider_response_body", "largest_prompt_sections"}
            },
        }
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (
        "candidate-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:6]
        + ".json"
    )
    path.write_text(
        json.dumps(
            {"workspace": str(workspace), "results": results},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--approved-python-current",
        action="store_true",
        help="Use this diagnostic process interpreter for approved execution when an old uv interpreter has expired",
    )
    parser.add_argument(
        "--bypass-startup-probe",
        action="store_true",
        help="Diagnostic only: inspect substantive review when the model fails the short startup probe",
    )
    parser.add_argument("--reviewer-native-tools", action="store_true")
    parser.add_argument(
        "--request-timeout",
        type=int,
        help="Diagnostic model-request timeout in seconds",
    )
    parser.add_argument(
        "--reasoning-strength", choices=("low", "medium", "high", "xhigh")
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=KIT / "benchmarks" / "results" / "reviewer-candidates",
    )
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    if args.request_timeout is not None and not 1 <= args.request_timeout <= 900:
        parser.error("--request-timeout must be between 1 and 900 seconds")
    print(
        run(
            args.workspace,
            args.model,
            args.repeats,
            args.output_dir,
            args.approved_python_current,
            args.bypass_startup_probe,
            args.reviewer_native_tools,
            args.request_timeout,
            args.reasoning_strength,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
