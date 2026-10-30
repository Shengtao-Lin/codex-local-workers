"""One model citation array, compatible repair schemas and explicit dependency evidence."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_dependency_evidence_adapter import install as install_dependencies
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe
from reviewer_staged_final_gate_adapter import final_phase
from reviewer_staged_final_gate_adapter import install as install_gate


def model_tools(tools, final_only):
    result = copy.deepcopy(tools)
    report = next(tool for tool in result if tool["function"]["name"] == "REPORT")
    params = report["function"]["parameters"]
    assessment = params["properties"].pop("assessment")
    ranges = assessment["properties"].pop("source_refs")
    assessment["properties"].pop("source_ref", None)
    assessment["properties"]["source_ranges"] = ranges
    assessment["required"] = ["obligation_id", "status", "source_ranges", "evidence"]
    params["properties"].pop("stage")
    params["required"] = [item for item in params["required"] if item != "stage"]
    params["required"] = list(
        dict.fromkeys(
            [
                *params["required"],
                "decision",
                "findings",
                "ordering_review",
                "assessment_ids",
            ]
        )
    )
    if not final_only:
        assessment["properties"]["findings"] = copy.deepcopy(
            params["properties"]["findings"]
        )
        result.append(
            {
                "type": "function",
                "function": {
                    "name": "ASSESS_CONTRACT",
                    "description": "Record ONE provisional source-backed obligation assessment. Not a final review or acceptance.",
                    "parameters": assessment,
                },
            }
        )
    return result


def route(raw, allowed_assessment):
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw
    if not isinstance(envelope, dict) or not isinstance(
        envelope.get("arguments"), dict
    ):
        return raw
    name, args = envelope.get("action"), envelope["arguments"]
    if name == "ASSESS_CONTRACT":
        if set(args) - allowed_assessment:
            return raw  # Unknown fields are not silently dropped or granted permission.
        entry = copy.deepcopy(args)
        findings = entry.pop("findings", [])
        entry["source_refs"] = entry.pop("source_ranges", None)
        envelope = {
            "action": "REPORT",
            "arguments": {
                "stage": "assessment",
                "assessment": entry,
                "findings": findings,
            },
        }
    elif name == "REPORT":
        if "stage" in args:
            envelope = {
                "action": "INVALID_MODEL_REPORT_FIELDS",
                "arguments": copy.deepcopy(args),
            }
        else:
            envelope = {"action": "REPORT", "arguments": {**args, "stage": "final"}}
    else:
        return raw
    return json.dumps(envelope, ensure_ascii=False)


def install(reviewer):
    canonical_prompt = reviewer.ReviewerRuntime.system_prompt
    install_gate(reviewer)
    reviewer.REVIEW_ACTION_SCHEMA = copy.deepcopy(reviewer.REVIEW_ACTION_SCHEMA)
    reviewer.REVIEW_ACTION_SCHEMA["properties"]["action"]["enum"].append(
        "ASSESS_CONTRACT"
    )
    original_run = reviewer.ReviewerRuntime.run
    original_template = reviewer.ReviewerRuntime.report_template
    original_repair = reviewer.ReviewerRuntime.report_repair
    params = next(
        tool
        for tool in reviewer.REVIEW_NATIVE_TOOLS
        if tool["function"]["name"] == "REPORT"
    )["function"]["parameters"]
    allowed = (
        set(params["properties"]["assessment"]["properties"])
        - {"source_ref", "source_refs"}
    ) | {"source_ranges", "findings"}
    original_citation_tools = reviewer.canonical_citation_tools

    def citation_tools(tools):
        if any(
            "contract_review"
            in tool.get("function", {}).get("parameters", {}).get("properties", {})
            for tool in tools
        ):
            return original_citation_tools(tools)
        result = copy.deepcopy(tools)
        for tool in result:
            props = tool.get("function", {}).get("parameters", {}).get("properties", {})
            item = props.get("assessment")
            if isinstance(item, dict):
                item["properties"].pop("source_ref", None)
                item["required"] = [
                    "obligation_id",
                    "status",
                    "source_refs",
                    "evidence",
                ]
        return result

    reviewer.canonical_citation_tools = citation_tools

    def prompt(runtime):
        text = canonical_prompt(runtime)
        start = text.index("REPORT arguments:")
        end = text.index("For a contract obligation spanning", start)
        return (
            text[:start]
            + (
                "ASSESS_CONTRACT arguments: obligation_id,status,source_ranges,evidence,optional findings. source_ranges is exactly one array of 1 to 3 {path,start_line,end_line} objects, each at most 20 actually read lines. Never send source_ref or source_refs to this model tool. Submit exactly one pending obligation supported by actually read lines. This record is provisional only. Status must be verified, violated or uncertain; a genuine contract defect is violated.\n"
                "REPORT is FINAL: decision,findings,verified_contract_ids,unverified_claims,ordering_review,verified_check_ids,assessment_ids selecting your recorded entries. Never send stage,assessment or contract_review in either model tool. Pass requires every original obligation, all owned contracts/configured checks/order constraints verified and no findings. Findings need id,severity,category,path,line,evidence,contract_id,suggested_fix. Retain previously recorded findings unchanged. Required order needs read source; forbidden order may use read source or diff. Diff evidence line must be null.\n"
                "Once all assessments and original mandatory reads/search/executions are complete, only final REPORT is allowed. Rework/escalate remain legal; completion does not certify semantic truth or force pass. Original final gates and total budget remain unchanged.\n"
            )
            + text[end:]
        )

    def template(runtime):
        result = original_template(runtime)
        result["arguments"].pop("stage", None)
        return result

    def repair(runtime, error, args):
        result = original_repair(runtime, error, args)
        result.pop("stage_instruction", None)
        result["protocol_instruction"] = (
            "Use ASSESS_CONTRACT with flat obligation_id,status,source_ranges,evidence,optional findings; or final REPORT with assessment_ids and original final fields. Never send stage,assessment,contract_review or source_ref/source_refs. Internal source_ref hints name ranges, not model argument aliases. Invalid claims are not normalized into acceptance."
        )
        return result

    def run(runtime):
        complete = runtime.client.complete

        def split(messages):
            tools = getattr(runtime.client, "native_tools", None)
            try:
                if isinstance(tools, list) and tools:
                    runtime.client.native_tools = model_tools(
                        tools, final_phase(runtime)
                    )
                raw = complete(
                    [
                        *messages,
                        {
                            "role": "user",
                            "content": "MODEL_TOOL_FORMAT: ASSESS_CONTRACT uses flat obligation_id,status,source_ranges,evidence,optional findings. source_ranges is ONE array of 1-3 actually read ranges, never source_ref/source_refs. REPORT is final with assessment_ids. Never send stage,assessment,contract_review. Internal stage/reference hints are not model argument aliases.",
                        },
                    ]
                )
            finally:
                runtime.client.native_tools = tools
            mapped = route(raw, allowed)
            if mapped != raw:
                source = json.loads(raw)
                runtime.event(
                    "split_staged_route",
                    {
                        "model_action": source["action"],
                        "argument_fields": sorted(source["arguments"]),
                        "canonical_action": "REPORT",
                        "semantic_acceptance": False,
                    },
                )
            return mapped

        runtime.client.complete = split
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.system_prompt = prompt
    reviewer.ReviewerRuntime.report_template = template
    reviewer.ReviewerRuntime.report_repair = repair
    reviewer.ReviewerRuntime.run = run
    install_dependencies(reviewer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "range_staged_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
