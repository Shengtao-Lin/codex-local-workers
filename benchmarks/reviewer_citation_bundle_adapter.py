"""One model-selected read-evidence bundle; unchanged canonical citation gates."""

import argparse
import copy
import importlib.util
import itertools
import json
import sys
from pathlib import Path

from reviewer_anchored_catalog_adapter import install as install_anchors
from reviewer_assembled_request_adapter import install as install_wire
from reviewer_boundary_analogy_adapter import install as install_analogy
from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_contract_test_read_adapter import install as install_test_reads
from reviewer_dependency_investigation_adapter import install as install_dependencies
from reviewer_investigation_phase_adapter import install as install_phase
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def candidates(runtime):
    runtime._assert_observed_sources_current()
    entries = list(runtime.evidence_catalog.entries.values())
    changed = set(runtime.diff_paths())
    source = [item for item in entries if item["path"] in changed]
    windows = [(item["id"],) for item in source]
    for path in sorted(changed):
        chunks = sorted(
            [
                item
                for item in source
                if item["path"] == path and not item.get("anchor_window")
            ],
            key=lambda item: item["start_line"],
        )
        for size in (2, 3):
            for index in range(len(chunks) - size + 1):
                group = chunks[index : index + size]
                if all(
                    a["end_line"] + 1 == b["start_line"]
                    for a, b in itertools.pairwise(group)
                ):
                    windows.append(tuple(item["id"] for item in group))
    result = []
    for obligation in runtime.review_obligations():
        rules = [
            rule
            for rule in runtime.config.get("reviewer_dependency_evidence", [])
            if rule["contract_id"] == obligation["id"]
        ]
        library = [
            item
            for item in entries
            if any(item["path"] == rule["path"] for rule in rules)
        ]
        sets = [()] if not rules else []
        for size in (1, 2):
            for group in itertools.combinations(library, size):
                refs = runtime.evidence_catalog.refs(
                    [item["id"] for item in group],
                    runtime.read_lines,
                    runtime.observed_read_hashes,
                )
                if all(
                    all(
                        anchor
                        in "\n".join(
                            runtime._canonical_contract_ref(ref)["canonical_quote"]
                            for ref in refs
                            if ref["path"] == rule["path"]
                        )
                        for anchor in rule["anchors"]
                    )
                    for rule in rules
                ):
                    sets.append(tuple(item["id"] for item in group))
        for dependency in sets:
            for window in windows:
                ids = list(dict.fromkeys([*window, *dependency]))
                if len(ids) <= 3:
                    runtime.evidence_catalog.refs(
                        ids, runtime.read_lines, runtime.observed_read_hashes
                    )
                    result.append(
                        {"obligation_id": obligation["id"], "source_evidence_ids": ids}
                    )
    return result


def decode(runtime, raw, bundles):
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or envelope.get("action") != "ASSESS_CONTRACT":
        return raw
    args = envelope.get("arguments")
    if not isinstance(args, dict):
        return raw
    if any(
        key in args
        for key in ("source_evidence_ids", "source_refs", "source_ref", "source_ranges")
    ):
        raise ValueError("bundle citation cannot be mixed with other citation fields")
    bundle = bundles.get(args.get("citation_bundle_id"))
    if bundle is None or bundle["obligation_id"] != args.get("obligation_id"):
        raise ValueError("unknown or wrong-contract citation bundle")
    runtime._assert_observed_sources_current()
    runtime.evidence_catalog.refs(
        bundle["source_evidence_ids"], runtime.read_lines, runtime.observed_read_hashes
    )
    args.pop("citation_bundle_id")
    args["source_evidence_ids"] = list(bundle["source_evidence_ids"])
    return json.dumps(envelope, ensure_ascii=False)


def install(reviewer):
    original_run = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete
        bundles = {}
        keys = {}

        def with_bundles(messages):
            for item in candidates(runtime):
                key = (item["obligation_id"], tuple(item["source_evidence_ids"]))
                if key not in keys:
                    identifier = "B" + str(len(bundles) + 1)
                    keys[key] = identifier
                    bundles[identifier] = item
                    reviewer.RUN_STATE.write_json_once(
                        runtime.review_root
                        / ("citation-bundle-" + identifier + ".json"),
                        {"id": identifier, **item, "semantic_acceptance": False},
                    )
            tools = runtime.client.native_tools
            try:
                if isinstance(tools, list) and tools:
                    runtime.client.native_tools = copy.deepcopy(tools)
                    if not bundles:
                        runtime.client.native_tools = [
                            tool
                            for tool in runtime.client.native_tools
                            if tool["function"]["name"] != "ASSESS_CONTRACT"
                        ]
                    for tool in runtime.client.native_tools:
                        if tool["function"]["name"] == "ASSESS_CONTRACT":
                            params = tool["function"]["parameters"]
                            params["properties"].pop("source_evidence_ids", None)
                            params["properties"]["citation_bundle_id"] = {
                                "type": "string",
                                "enum": list(bundles),
                            }
                            params["required"] = [
                                "citation_bundle_id"
                                if key == "source_evidence_ids"
                                else key
                                for key in params["required"]
                            ]
                presented = []
                for message in messages:
                    content = message.get("content", "")
                    if content.startswith("MODEL_CITATION_FORMAT:"):
                        catalog = json.loads(
                            content.split("Current actual-read catalog: ", 1)[1]
                        )
                        compact = [
                            {
                                key: item[key]
                                for key in ("id", "path", "start_line", "end_line")
                            }
                            for item in catalog
                        ]
                        presented.append(
                            {
                                "role": "user",
                                "content": "ACTUAL_READ_HANDLE_CATALOG (navigation, not semantic truth): "
                                + json.dumps(compact),
                            }
                        )
                    else:
                        presented.append(message)
                raw = complete(
                    [
                        *presented,
                        {
                            "role": "user",
                            "content": "CITATION_BUNDLE_FORMAT: ASSESS_CONTRACT uses citation_bundle_id ONLY, not source_evidence_ids/source_ref/source_refs/source_ranges. Select one same-obligation bundle of actual-read source handles. It transports 1-3 valid read ranges, not semantic truth. Preserve status, explanation, findings and all final obligations. Source handle catalog remains navigation. Available bundles: "
                            + json.dumps(
                                {
                                    identifier: item
                                    for identifier, item in bundles.items()
                                }
                            ),
                        },
                    ]
                )
            finally:
                runtime.client.native_tools = tools
            try:
                return decode(runtime, raw, bundles)
            except (ValueError, TypeError):
                return raw  # Original guarded protocol path rejects; never auto-repair.

        runtime.client.complete = with_bundles
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
        "citation_bundle_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install_range(reviewer)
    install_dependencies(reviewer)
    install_catalog(reviewer)
    install_anchors(reviewer)
    install_test_reads(reviewer)
    install_phase(reviewer)
    install_analogy(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    install_wire(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
