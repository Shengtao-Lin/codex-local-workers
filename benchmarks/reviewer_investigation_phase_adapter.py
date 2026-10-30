"""Expose only feasible native actions while declared investigation is pending."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_anchored_catalog_adapter import install as install_anchors
from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_contract_test_read_adapter import install as install_test_reads
from reviewer_dependency_investigation_adapter import install as install_dependencies
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def pending_reads(runtime):
    runtime._assert_observed_sources_current()
    result = []
    for rule in runtime.config.get("reviewer_contract_test_reads", []):
        path, absolute = runtime._assert_read_allowed(rule["path"])
        count = len(absolute.read_text(encoding="utf-8").splitlines())
        missing = set(range(1, count + 1)) - runtime.read_lines.get(path, set())
        if missing:
            start = min(missing)
            result.append(
                {"path": path, "start_line": start, "end_line": min(start + 99, count)}
            )
    for rule in runtime.config.get("reviewer_dependency_evidence", []):
        path, absolute = runtime._assert_read_allowed(rule["path"])
        lines = absolute.read_text(encoding="utf-8").splitlines()
        displayed = "\n".join(
            line
            for number, line in enumerate(lines, 1)
            if number in runtime.read_lines.get(path, set())
        )
        if not all(anchor in displayed for anchor in rule["anchors"]):
            missing_anchor = next(
                anchor for anchor in rule["anchors"] if anchor not in displayed
            )
            location = next(
                (
                    number
                    for number, line in enumerate(lines, 1)
                    if missing_anchor in line
                ),
                None,
            )
            if location is None:
                raise ValueError(
                    "declared dependency anchor missing from actual source: " + path
                )
            start = max(1, location - 2)
            result.append(
                {
                    "path": path,
                    "start_line": start,
                    "end_line": min(start + 99, len(lines)),
                }
            )
    return result


def phase_tools(tools, pending, unrecorded):
    result = copy.deepcopy(tools)
    if pending:
        return [
            tool
            for tool in result
            if tool["function"]["name"] not in {"ASSESS_CONTRACT", "REPORT"}
        ]
    selected = []
    for tool in result:
        if tool["function"]["name"] == "ASSESS_CONTRACT":
            if not unrecorded:
                continue
            tool["function"]["parameters"]["properties"]["obligation_id"]["enum"] = (
                unrecorded
            )
        selected.append(tool)
    return selected


def install(reviewer):
    original_run = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete

        def feasible(messages):
            pending = pending_reads(runtime)
            unrecorded = [
                item["id"]
                for item in runtime.review_obligations()
                if item["id"] not in runtime.staged_assessments
            ]
            tools = runtime.client.native_tools
            try:
                if isinstance(tools, list) and tools:
                    runtime.client.native_tools = phase_tools(
                        tools, pending, unrecorded
                    )
                runtime.event(
                    "investigation_phase",
                    {
                        "pending_paths": [item["path"] for item in pending],
                        "unrecorded": unrecorded,
                        "automatic_acceptance": False,
                    },
                )
                return complete(
                    [
                        *messages,
                        {
                            "role": "user",
                            "content": "FEASIBLE_REVIEW_PHASE\n"
                            + json.dumps(
                                {
                                    "required_read_actions": pending,
                                    "unrecorded_obligations": unrecorded,
                                    "instruction": "Complete the listed actual READ_FILE actions before contract assessment or final report. Then assess unrecorded obligations only. Original contract, citations, statuses, findings and final gates remain unchanged; the phase never selects verified or accepts anything.",
                                }
                            ),
                        },
                    ]
                )
            finally:
                runtime.client.native_tools = tools

        runtime.client.complete = feasible
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.run = run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "investigation_phase_reviewer",
        args.snapshot / ".local-agents/reviewer-runtime.py",
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install_range(reviewer)
    install_dependencies(reviewer)
    install_catalog(reviewer)
    install_anchors(reviewer)
    install_test_reads(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
