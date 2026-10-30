"""Read-backed opaque handles over existing staged/monolithic citation gates."""

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_dependency_evidence_adapter import install as install_dependencies
from reviewer_dependency_investigation_adapter import install as install_investigation
from reviewer_evidence_catalog_adapter_v2 import EvidenceCatalog
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def model_tools(tools):
    result = copy.deepcopy(tools)
    for tool in result:
        name = tool["function"]["name"]
        params = tool["function"]["parameters"]
        entries = [params] if name == "ASSESS_CONTRACT" else []
        if name == "REPORT" and "contract_review" in params["properties"]:
            entries.append(params["properties"]["contract_review"]["items"])
        for entry in entries:
            props = entry["properties"]
            for alias in ("source_ranges", "source_ref", "source_refs"):
                props.pop(alias, None)
            props["source_evidence_ids"] = {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "uniqueItems": True,
                "items": {"type": "string"},
            }
            entry["required"] = [
                "obligation_id",
                "status",
                "source_evidence_ids",
                "evidence",
            ]
    return result


def decode(runtime, raw):
    try:
        envelope = json.loads(raw)
    except (ValueError, TypeError):
        return raw
    if not isinstance(envelope, dict) or not isinstance(
        envelope.get("arguments"), dict
    ):
        return raw
    args = envelope["arguments"]
    staged = envelope.get("action") == "ASSESS_CONTRACT"
    entries = (
        [args]
        if staged
        else args.get("contract_review", [])
        if envelope.get("action") == "REPORT"
        else []
    )
    if not isinstance(entries, list):
        return raw
    runtime._assert_observed_sources_current()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "source_evidence_ids" not in entry or any(
            alias in entry for alias in ("source_ref", "source_refs", "source_ranges")
        ):
            return json.dumps(
                {
                    "action": "INVALID_MODEL_CATALOG_FIELDS",
                    "arguments": json.loads(raw)["arguments"],
                }
            )
        refs = runtime.evidence_catalog.refs(
            entry["source_evidence_ids"],
            runtime.read_lines,
            runtime.observed_read_hashes,
        )
        entry.pop("source_evidence_ids")
        entry["source_ranges" if staged else "source_refs"] = refs
    return json.dumps(envelope, ensure_ascii=False)


def install(reviewer):
    original_init = reviewer.ReviewerRuntime.__init__
    original_read = reviewer.ReviewerRuntime.read_file
    original_run = reviewer.ReviewerRuntime.run

    def init(runtime, *args, **kwargs):
        original_init(runtime, *args, **kwargs)
        runtime.evidence_catalog = EvidenceCatalog()

    def read(runtime, args):
        observation = original_read(runtime, args)
        runtime._assert_observed_sources_current()
        observation["new_source_evidence"] = runtime.evidence_catalog.observe(
            runtime.read_lines, runtime.observed_read_hashes
        )
        observation["model_citation_instruction"] = (
            "Choose 1-3 actually read source_evidence_ids for each contract assessment, not line ranges. IDs only transport citations, never certify semantics."
        )
        return observation

    def run(runtime):
        complete = runtime.client.complete

        def with_catalog(messages):
            tools = runtime.client.native_tools
            try:
                if isinstance(tools, list) and tools:
                    runtime.client.native_tools = model_tools(tools)
                raw = complete(
                    [
                        *messages,
                        {
                            "role": "user",
                            "content": "MODEL_CITATION_FORMAT: For ASSESS_CONTRACT or REPORT.contract_review use source_evidence_ids ONLY from successful READ_FILE new_source_evidence. Never submit source_ref/source_refs/source_ranges; internal range advice names catalog entries, not model fields. Preserve status, explanation, findings, ordering and all final obligations. Current actual-read catalog: "
                            + json.dumps(
                                list(runtime.evidence_catalog.entries.values())
                            ),
                        },
                    ]
                )
            finally:
                runtime.client.native_tools = tools
            try:
                return decode(runtime, raw)
            except ValueError:
                # Route the invalid original fields to the ordinary bounded protocol
                # error path. No invented citation or normalized successful report.
                return raw

        runtime.client.complete = with_catalog
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.__init__ = init
    reviewer.ReviewerRuntime.read_file = read
    reviewer.ReviewerRuntime.run = run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--staged", action="store_true")
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "catalog_staged_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    (install_range if args.staged else install_dependencies)(reviewer)
    install_investigation(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
