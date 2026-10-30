"""One opt-in format recovery; never retry a completed semantic judgment."""

import argparse
import copy
import sys
import time
from pathlib import Path

import capture_fixture_support as F
import reviewer_contract_first as CORE


def action_schema(tools):
    if len(tools) != 1 or tools[0]["function"]["name"] != "REPORT":
        raise ValueError("JSON recovery is only for REPORT")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": {"type": "string", "enum": ["REPORT"]},
            "arguments": copy.deepcopy(tools[0]["function"]["parameters"]),
        },
        "required": ["action", "arguments"],
    }


def json_once(runtime, module, messages, tools):
    remaining = runtime.deadline - time.monotonic()
    if (
        remaining <= 0
        or runtime.actual_requests >= runtime.max_turns
        or runtime.protocol_errors + len(runtime.output_failures)
        >= runtime.max_protocol_errors
    ):
        raise module.ReviewError("Shared budget exhausted before JSON recovery")
    runtime._assert_inputs_current()
    runtime.json_recovery_used = True
    client = runtime.client
    attributes = (
        "native_tools",
        "native_tool_choice",
        "structured_output",
        "action_schema",
        "schema_name",
        "timeout",
        "reasoning_effort",
    )
    missing = object()
    old = {k: getattr(client, k, missing) for k in attributes}
    pending = copy.deepcopy(messages)
    pending[-1]["content"] += (
        '\nOUTPUT_FORMAT_RECOVERY\nNo complete prior REPORT was accepted. Return one JSON object {"action":"REPORT","arguments":...} using the unchanged REPORT schema and evidence. No partial result is acceptance.'
    )
    client.native_tools = None
    client.native_tool_choice = "auto"
    client.structured_output = True
    client.action_schema = action_schema(tools)
    client.schema_name = "reviewer_report_recovery_v1"
    client.timeout = min(client.timeout, remaining)
    client.reasoning_effort = "low"
    runtime.actual_requests += 1
    request = runtime.actual_requests
    runtime.request_profiles.append(
        {
            "request": request,
            "stage": "source_review_json_recovery",
            "fallback_active": True,
            "tool_choice": None,
            "reasoning_effort": "low",
            "structured_output": True,
        }
    )
    module.RUN_STATE.write_json_once(
        runtime.review_root / "json-recovery-input.json",
        {
            "messages": pending,
            "schema": client.action_schema,
            "reason": "Two output-limit failures, no completed semantic report; one changed-format recovery inside shared budget",
        },
    )
    try:
        raw = client.complete(pending)
        module.RUN_STATE.write_json_once(
            runtime.review_root / f"phase-response-{request}.json",
            {
                "stage": "source_review_json_recovery",
                "raw": raw,
                "request_stats": client.last_request_stats,
            },
        )
        runtime._assert_inputs_current()
        return raw
    except module.WORKER.ModelRequestError as exc:
        if exc.reason_code == "output_token_limit":
            failure = {
                "request": request,
                "stage": "source_review_json_recovery",
                "reason_code": exc.reason_code,
                "diagnostics": copy.deepcopy(exc.diagnostics),
                "partial_action_executed": False,
            }
            runtime.output_failures.append(failure)
            module.RUN_STATE.write_json_once(
                runtime.review_root
                / f"output-limit-failure-{len(runtime.output_failures)}.json",
                failure,
            )
        raise
    finally:
        for key, value in old.items():
            if value is missing:
                delattr(client, key)
            else:
                setattr(client, key, value)


def wrap(base, module):
    class JsonRecovery(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.json_recovery_used = False

        def _request_phase_completion(self, messages, tools, stage):
            if self.json_recovery_used:
                raise module.ReviewError(
                    "One-shot JSON recovery already consumed; no report resampling"
                )
            try:
                return super()._request_phase_completion(messages, tools, stage)
            except module.WORKER.ModelRequestError as exc:
                if (
                    exc.reason_code != "output_token_limit"
                    or stage != "source_review"
                    or len(self.output_failures) != 2
                ):
                    raise
                return json_once(self, module, messages, tools)

    return JsonRecovery


def install(module):
    base = CORE.install(module, forward_reasoning_effort=True)
    module.ReviewerRuntime = wrap(base, module)
    return module.ReviewerRuntime


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    path = args.runtime_dir / "reviewer-runtime.py"
    module = F.load(path, "json_recovery_reviewer")
    install(module)
    sys.argv = [str(path), *remaining]
    raise SystemExit(module.main())
