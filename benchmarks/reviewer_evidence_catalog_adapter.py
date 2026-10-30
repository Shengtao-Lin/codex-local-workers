"""Experimental read-ledger evidence handles; unchanged canonical semantic gates."""

import argparse
import copy
import importlib.util
import sys
from pathlib import Path


class EvidenceCatalog:
    def __init__(self):
        self.entries = {}
        self.keys = {}

    def observe(self, read_lines, hashes):
        # Partition only contiguous actually displayed lines; never bridge gaps.
        added = []
        for path, numbers in sorted(read_lines.items()):
            runs = []
            for number in sorted(numbers):
                if type(number) is not int or number < 1:
                    raise ValueError("invalid read ledger")
                if not runs or number != runs[-1][-1] + 1 or len(runs[-1]) == 20:
                    runs.append([number])
                else:
                    runs[-1].append(number)
            for run in runs:
                key = (path, hashes[path], run[0], run[-1])
                if key in self.keys:
                    continue
                evidence_id = "E" + str(len(self.entries) + 1)
                self.keys[key] = evidence_id
                entry = {
                    "id": evidence_id,
                    "path": path,
                    "start_line": run[0],
                    "end_line": run[-1],
                    "source_hash": hashes[path],
                }
                self.entries[evidence_id] = entry
                added.append(copy.deepcopy(entry))
        return added

    def refs(self, ids, read_lines, hashes):
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 3
            or any(not isinstance(item, str) for item in ids)
            or len(set(ids)) != len(ids)
        ):
            raise ValueError(
                "source_evidence_ids requires one to three distinct actually read evidence IDs"
            )
        result = []
        for evidence_id in ids:
            entry = self.entries.get(evidence_id)
            if entry is None:
                raise ValueError("unknown source_evidence_id: " + evidence_id)
            path = entry["path"]
            if hashes.get(path) != entry["source_hash"] or not set(
                range(entry["start_line"], entry["end_line"] + 1)
            ) <= read_lines.get(path, set()):
                raise ValueError("stale or unread source_evidence_id: " + evidence_id)
            result.append(
                {key: entry[key] for key in ("path", "start_line", "end_line")}
            )
        return result


def install(reviewer):
    original_init = reviewer.ReviewerRuntime.__init__
    original_read = reviewer.ReviewerRuntime.read_file
    original_validate = reviewer.ReviewerRuntime.validate_report
    original_prompt = reviewer.ReviewerRuntime.system_prompt
    original_template = reviewer.ReviewerRuntime.report_template
    original_repair = reviewer.ReviewerRuntime.report_repair
    tools = copy.deepcopy(reviewer.REVIEW_NATIVE_TOOLS)
    for tool in tools:
        if tool["function"]["name"] == "REPORT":
            tool["function"]["parameters"]["properties"]["contract_review"]["items"] = {
                "type": "object",
                "properties": {
                    "obligation_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["verified", "violated", "uncertain"],
                    },
                    "source_evidence_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    },
                    "evidence": {"type": "string"},
                },
                "required": [
                    "obligation_id",
                    "status",
                    "source_evidence_ids",
                    "evidence",
                ],
                "additionalProperties": False,
            }
    reviewer.REVIEW_NATIVE_TOOLS = tools

    def init(runtime, *args, **kwargs):
        original_init(runtime, *args, **kwargs)
        runtime.evidence_catalog = EvidenceCatalog()

    def hashes(runtime):
        runtime._assert_inputs_current()
        return {
            path: runtime.expected_inputs[path]["sha256"] for path in runtime.read_lines
        }

    def read(runtime, args):
        observation = original_read(runtime, args)
        current_hashes = hashes(runtime)
        added = runtime.evidence_catalog.observe(runtime.read_lines, current_hashes)
        result = copy.deepcopy(observation)
        result["new_source_evidence"] = added
        result["evidence_instruction"] = (
            "For contract_review choose 1-3 actually read source_evidence_ids supporting the entire obligation. IDs are citation mechanics, not proof. Ordering review still uses flat path/line."
        )
        return result

    def validate(runtime, args):
        canonical = copy.deepcopy(args)
        entries = canonical.get("contract_review", [])
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) - {
                    "obligation_id",
                    "status",
                    "source_evidence_ids",
                    "evidence",
                }:
                    raise reviewer.ReviewError(
                        "Evidence catalog contract_review accepts only obligation_id, status, source_evidence_ids, evidence; mixed legacy citations are rejected"
                    )
                try:
                    entry["source_refs"] = runtime.evidence_catalog.refs(
                        entry.pop("source_evidence_ids", None),
                        runtime.read_lines,
                        hashes(runtime),
                    )
                except ValueError as exc:
                    raise reviewer.ReviewError(str(exc)) from exc
        # Status, claims, finding IDs and constraint IDs are unchanged. The original
        # gate still validates scope/read/hash, anchors, contradiction and semantics.
        return original_validate(runtime, canonical)

    def prompt(runtime):
        return (
            original_prompt(runtime)
            + "\nEVIDENCE_CATALOG transport: For contract_review use source_evidence_ids ONLY, chosen from new_source_evidence returned by successful actual reads. Do not submit source_ref/source_refs or invented quotes there. The runtime translates chosen IDs to canonical ranges and applies all original gates. IDs never establish semantic truth; trace the whole obligation and use rework/escalate for defects/uncertainty. Ordering review and findings keep their existing flat citation fields."
        )

    def template(runtime):
        result = original_template(runtime)
        for entry in result["arguments"]["contract_review"]:
            for key in ("source_ref", "source_refs", "path", "line", "source_quote"):
                entry.pop(key, None)
            entry["source_evidence_ids"] = ["CHOOSE_ACTUALLY_READ_ID"]
        return result

    def repair(runtime, error, args):
        result = original_repair(runtime, error, args)
        result["source_evidence_catalog"] = list(
            runtime.evidence_catalog.entries.values()
        )
        anchor = result.get("anchor_source_ref")
        if isinstance(anchor, dict):
            result["required_anchor_evidence_ids"] = [
                entry["id"]
                for entry in runtime.evidence_catalog.entries.values()
                if entry["path"] == anchor["path"]
                and entry["start_line"] <= anchor["start_line"] <= entry["end_line"]
            ]
        result["catalog_transport_instruction"] = (
            "Keep all substantive repair obligations. For contract_review translate any "
            "range advice into source_evidence_ids from this actually read catalog; do not "
            "send legacy source_ref/source_refs or quotes. If the needed source is unread, "
            "execute suggested_action first. An ID identifies read text, never verification. "
            "Ordering review still uses its original flat path/line fields."
        )
        return result

    reviewer.ReviewerRuntime.__init__ = init
    reviewer.ReviewerRuntime.read_file = read
    reviewer.ReviewerRuntime.validate_report = validate
    reviewer.ReviewerRuntime.system_prompt = prompt
    reviewer.ReviewerRuntime.report_template = template
    reviewer.ReviewerRuntime.report_repair = repair


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "catalog_review_diagnostic", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
