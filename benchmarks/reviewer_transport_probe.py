"""Compare bounded LM Studio Reviewer requests without running a review.

The probe reads one already validated disposable Coder archive. It never edits
source files or saves model output; results retain only response metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KIT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = KIT / ".local-agents" / "reviewer-runtime.py"
SPEC = importlib.util.spec_from_file_location("transport_probe_reviewer", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
REVIEWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REVIEWER
SPEC.loader.exec_module(REVIEWER)

COMPACT_SYSTEM_PROMPT = """You are a read-only code reviewer. Use one JSON action per turn:
READ_FILE, SEARCH, RUN_APPROVED_TEST, RUN_APPROVED_STATIC_CHECK, or REPORT.
Review the actual cumulative diff and executed validation against the packet; Coder
claims are not evidence. Read changed source and focused tests, follow relevant callers,
error paths and side effects, and report concrete bugs or test gaps beyond listed
obligations. Escalate missing readable context or conflicting architecture/security
evidence. Never edit, use arbitrary commands, Git, or delegation. Execute only ids
listed in approved_execution and never claim an unexecuted check passed.

REPORT arguments: decision, findings, verified_contract_ids, unverified_claims,
ordering_review, contract_review, verified_check_ids. Pass requires no findings,
all owned contracts and configured checks verified. Each finding needs id,
severity, category, path, line, evidence, contract_id, suggested_fix. For high
risk or verify_in_review feedback, give one contract_review per required
review_obligation with an actually read path/line, exact source_quote, and
whole-obligation explanation. Otherwise contract_review may be []. Use the short
constraint_id values from ordering_constraints. Required order needs read source
evidence; forbidden order may use read source or cumulative diff. Pass only when
all constraints are verified. If evidence is missing, choose rework or escalate.
"""


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def run(
    workspace: Path,
    repeats: int,
    max_tokens: int,
    output_dir: Path,
    selected_variants: set[str] | None = None,
    model: str | None = None,
) -> Path:
    workspace = workspace.resolve()
    config = REVIEWER.load_object(workspace / ".local-agents" / "config.json")
    if model is not None:
        config["reviewer_model"] = model
    packet = REVIEWER.load_object(workspace / ".agent" / "packet.json")
    request = {
        "schema_version": 1,
        "task_id": packet["task_id"],
        "unit_id": packet["unit_id"],
        "run_id": packet["run_id"],
        "review_id": "transport-probe-" + uuid.uuid4().hex,
    }
    runtime = REVIEWER.ReviewerRuntime(workspace, request, config, object())
    full_payload = runtime.initial_payload()
    full_messages = [
        {"role": "system", "content": runtime.system_prompt()},
        {
            "role": "user",
            "content": "LOCAL_REVIEW_INPUT\n"
            + json.dumps(full_payload, ensure_ascii=False),
        },
    ]
    minimal_messages = [
        {"role": "system", "content": "Reply with exactly one JSON action object."},
        {
            "role": "user",
            "content": '{"action":"READ_FILE","arguments":{"path":"src/slug.py"}}',
        },
    ]
    validation = runtime.validation
    focused = validation.get("focused_tests") or {}
    compact_payload = {
        **full_payload,
        "runtime_validation": {
            "status": validation.get("status"),
            "py_compile_status": (validation.get("py_compile") or {}).get("status"),
            "focused_tests": {
                "status": focused.get("status"),
                "junit": focused.get("junit"),
                "inputs_unchanged": focused.get("inputs_unchanged"),
            },
            "configured_checks": [
                {
                    "id": item.get("id"),
                    "status": item.get("status"),
                    "exit_code": item.get("exit_code"),
                }
                for item in validation.get("configured_checks", [])
            ],
        },
    }
    compact_messages = [
        full_messages[0],
        {
            "role": "user",
            "content": "LOCAL_REVIEW_INPUT\n"
            + json.dumps(compact_payload, ensure_ascii=False),
        },
    ]
    compact_system_messages = [
        {"role": "system", "content": COMPACT_SYSTEM_PROMPT},
        full_messages[1],
    ]
    anti_native_messages = [
        {
            "role": "system",
            "content": (
                runtime.system_prompt()
                + "\nActions are JSON data for this application, not native tool calls. "
                "Never emit recipient syntax such as to=READ_FILE, channel markers, "
                "or special chat-template tokens. Your entire response is one JSON object.\n"
            ),
        },
        full_messages[1],
    ]
    variants = [
        ("minimal_plain", minimal_messages, False),
        ("full_plain", full_messages, False),
        ("minimal_structured", minimal_messages, True),
        ("full_structured", full_messages, True),
        ("compact_validation_plain", compact_messages, False),
        ("compact_validation_structured", compact_messages, True),
        ("compact_system_plain", compact_system_messages, False),
        ("compact_system_structured", compact_system_messages, True),
        ("compact_lowtemp_structured", compact_system_messages, True),
        ("compact_zero_structured", compact_system_messages, True),
        ("anti_native_plain", anti_native_messages, False),
        ("anti_native_structured", anti_native_messages, True),
        (
            "full_system_minimal_user",
            [full_messages[0], minimal_messages[1]],
            False,
        ),
        (
            "minimal_system_full_user",
            [minimal_messages[0], full_messages[1]],
            False,
        ),
    ]
    if selected_variants is not None:
        variants = [item for item in variants if item[0] in selected_variants]
        if len(variants) != len(selected_variants):
            raise ValueError("unknown Reviewer transport variant")
    records: list[dict[str, Any]] = []
    section_sizes = {
        "system_prompt_chars": len(full_messages[0]["content"]),
        "payload_fields": {
            key: len(json.dumps(value, ensure_ascii=False))
            for key, value in full_payload.items()
        },
    }
    for repetition in range(1, repeats + 1):
        ordered = variants if repetition % 2 else list(reversed(variants))
        for name, messages, structured in ordered:
            temperature = (
                0.0
                if name == "compact_zero_structured"
                else 0.1
                if name == "compact_lowtemp_structured"
                else float(config.get("reviewer_temperature", 0.1))
            )
            client = REVIEWER.WORKER.LMStudioClient(
                config["lmstudio_base_url"],
                config["reviewer_model"],
                int(config.get("model_request_timeout_seconds", 180)),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=float(config.get("reviewer_top_p", 0.9)),
                top_k=int(config.get("reviewer_top_k", 40)),
                min_p=float(config.get("reviewer_min_p", 0.0)),
                repeat_penalty=float(config.get("reviewer_repeat_penalty", 1.0)),
                structured_output=structured,
                action_schema=REVIEWER.REVIEW_ACTION_SCHEMA,
                schema_name="local_reviewer_action",
                context_length=int(config["reviewer_context_length"]),
                context_safety_margin=int(
                    config.get("model_context_safety_margin", 1024)
                ),
            )
            record: dict[str, Any] = {
                "repetition": repetition,
                "variant": name,
                "model": client.model,
                "message_sha256": _digest(messages),
                "schema_sha256": _digest(client.action_schema) if structured else None,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            started = time.monotonic()
            try:
                response = client.complete(messages)
                try:
                    parsed_action = REVIEWER.WORKER.parse_action(response)["action"]
                except REVIEWER.WORKER.WorkerError:
                    parsed_action = None
                record.update(
                    {
                        "status": "response",
                        "parsed_action": parsed_action,
                        "response_chars": len(response),
                        "response_sha256": hashlib.sha256(
                            response.encode()
                        ).hexdigest(),
                    }
                )
            except REVIEWER.WORKER.WorkerError as exc:
                detail = str(exc)
                record.update(
                    {
                        "status": "error",
                        "reason_code": getattr(exc, "reason_code", type(exc).__name__),
                        "peg_native_error": "peg-native format" in detail,
                        "empty_response": "empty assistant message" in detail,
                    }
                )
            record["seconds"] = round(time.monotonic() - started, 3)
            record["request_stats"] = {
                key: value
                for key, value in client.last_request_stats.items()
                if key not in {"provider_response_body", "largest_prompt_sections"}
            }
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (
        "reviewer-transport-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:6]
        + ".json"
    )
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(
            {
                "workspace": str(workspace),
                "section_sizes": section_sizes,
                "records": records,
            },
            stream,
            ensure_ascii=False,
            indent=2,
        )
        stream.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument(
        "--model", help="Diagnostic model override; does not edit config"
    )
    parser.add_argument(
        "--variants",
        help="Comma-separated variant names; default runs every variant.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=KIT / "benchmarks" / "results" / "reviewer-transport",
    )
    args = parser.parse_args()
    if args.repeats < 0 or args.max_tokens < 512:
        parser.error("repeats must be non-negative and max-tokens at least 512")
    selected = set(args.variants.split(",")) if args.variants else None
    print(
        run(
            args.workspace,
            args.repeats,
            args.max_tokens,
            args.output_dir,
            selected,
            args.model,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
