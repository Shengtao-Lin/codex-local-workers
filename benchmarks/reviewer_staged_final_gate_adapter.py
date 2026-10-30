"""Experimental final-only phase after explicit provisional obligations are complete."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe
from reviewer_staged_assessment_adapter import install as install_staged


def final_phase(runtime):
    expected = {item["id"] for item in runtime.review_obligations()}
    if not expected or set(runtime.staged_assessments) != expected:
        return False
    if (
        runtime.config.get("reviewer_require_search", False)
        and runtime.search_count < 1
    ):
        return False
    if runtime.config.get("reviewer_require_source_and_test_reads", False):
        tests = runtime.focused_test_paths()
        changed = [
            path
            for path in runtime.diff_paths()
            if path not in tests and path.endswith(".py")
        ]
        if changed and not any(runtime.read_lines.get(path) for path in changed):
            return False
        if tests and not any(runtime.read_lines.get(path) for path in tests):
            return False
    if runtime.config.get("reviewer_require_approved_execution", False):
        required = {
            ("static_check", item["id"])
            for item in runtime.validation.get("configured_checks", [])
        }
        if runtime.packet["focused_tests"]:
            required.add(("test", "focused-tests"))
        passed = {
            (item.get("kind"), item.get("id"))
            for item in runtime.approved_execution
            if item.get("status") == "passed"
        }
        if not required <= passed:
            return False
    return True


def install(reviewer):
    install_staged(reviewer)
    original_run = reviewer.ReviewerRuntime.run
    original_prompt = reviewer.ReviewerRuntime.system_prompt
    original_validate = reviewer.ReviewerRuntime.validate_report

    def prompt(runtime):
        text = original_prompt(runtime)
        start = text.index("REPORT arguments:")
        end = text.index("For a contract obligation spanning", start)
        return (
            text[:start]
            + "REPORT has two stages. stage=assessment records one provisional assessment with obligation_id,status,source_ref or source_refs,evidence, plus optional findings. Each status is verified, violated or uncertain. Citations must name actually read ranges. stage=final supplies decision, findings, verified_contract_ids, unverified_claims, ordering_review, verified_check_ids and assessment_ids selecting recorded entries; do not supply contract_review again. Pass requires no findings, all original owned contracts, configured checks and ordering constraints verified. Each finding needs id,severity,category,path,line,evidence,contract_id,suggested_fix. Required order needs read source; forbidden order may use read source or cumulative diff. All original final acceptance gates remain in force. Missing evidence is not a verified claim.\n"
            + text[end:]
            + "\nFINAL_PHASE: Once all assessments and original mandatory reads/search/execution are complete, only stage=final REPORT is permitted. Retain any recorded finding unchanged. This phase does not certify correctness or force pass: final rework/escalate remain legal. Do not repeat optional validation or read actions in final phase."
        )

    def validate(runtime, args):
        if final_phase(runtime) and args.get("stage") != "final":
            raise reviewer.ReviewError("final phase permits only REPORT stage=final")
        return original_validate(runtime, args)

    def guard(method):
        def guarded(runtime, args):
            if final_phase(runtime):
                raise reviewer.ReviewError(
                    "final phase permits only REPORT stage=final"
                )
            return method(runtime, args)

        return guarded

    def run(runtime):
        complete = runtime.client.complete

        def with_gate(messages):
            if not final_phase(runtime):
                return complete(messages)
            tools = getattr(runtime.client, "native_tools", None)
            try:
                if isinstance(tools, list) and tools:
                    final_tools = copy.deepcopy(
                        [tool for tool in tools if tool["function"]["name"] == "REPORT"]
                    )
                    if not final_tools:
                        raise reviewer.ReviewError(
                            "final phase has no registered REPORT tool"
                        )
                    schema = final_tools[0]["function"]["parameters"]
                    schema["properties"]["stage"]["enum"] = ["final"]
                    schema["required"] = [
                        "stage",
                        "assessment_ids",
                        "decision",
                        "findings",
                        "ordering_review",
                    ]
                    runtime.client.native_tools = final_tools
                runtime.event(
                    "staged_final_gate",
                    {"final_only": True, "automatic_acceptance": False},
                )
                return complete(
                    [
                        *messages,
                        {
                            "role": "user",
                            "content": "FINAL_PHASE: Submit stage=final REPORT now, subject to every original gate. Do not claim pass if uncertain or defective. Recorded assessment_ids: "
                            + json.dumps(list(runtime.staged_assessments)),
                        },
                    ]
                )
            finally:
                runtime.client.native_tools = tools

        runtime.client.complete = with_gate
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.system_prompt = prompt
    reviewer.ReviewerRuntime.validate_report = validate
    for name in (
        "read_file",
        "search",
        "run_approved_test",
        "run_approved_static_check",
    ):
        setattr(
            reviewer.ReviewerRuntime,
            name,
            guard(getattr(reviewer.ReviewerRuntime, name)),
        )
    reviewer.ReviewerRuntime.run = run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "staged_final_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
