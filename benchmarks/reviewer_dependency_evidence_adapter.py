"""Optional Primary-declared dependency citations; stricter evidence, never truth proof."""

import argparse
import importlib.util
import sys
from pathlib import Path

from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def install(reviewer):
    original_validate = reviewer.ReviewerRuntime.validate_report
    original_prompt = reviewer.ReviewerRuntime.system_prompt
    original_repair = reviewer.ReviewerRuntime.report_repair

    def rules(runtime):
        values = runtime.config.get("reviewer_dependency_evidence", [])
        if not isinstance(values, list):
            raise reviewer.ReviewError("dependency evidence rules must be an array")
        checked = []
        for item in values:
            if (
                not isinstance(item, dict)
                or item.get("contract_id") not in runtime.packet["owned_contract_ids"]
            ):
                raise reviewer.ReviewError(
                    "dependency evidence requires an owned contract"
                )
            path, _ = runtime._assert_read_allowed(item.get("path"))
            anchors = item.get("anchors")
            if (
                not isinstance(anchors, list)
                or not anchors
                or any(
                    not isinstance(anchor, str) or not anchor.strip()
                    for anchor in anchors
                )
            ):
                raise reviewer.ReviewError(
                    "dependency evidence anchors must be nonempty strings"
                )
            checked.append(
                {"contract_id": item["contract_id"], "path": path, "anchors": anchors}
            )
        return checked

    def validate(runtime, args):
        entries = (
            [args.get("assessment")]
            if args.get("stage") == "assessment"
            else args.get("contract_review", [])
        )
        if args.get("stage") == "final":
            ids = args.get("assessment_ids")
            stored = getattr(runtime, "staged_assessments", {})
            if isinstance(ids, list) and all(
                isinstance(key, str) and key in stored for key in ids
            ):
                entries = [stored[key]["entry"] for key in ids]
        requirements = rules(runtime)
        if args.get("decision") == "pass_to_primary":
            for item in requirements:
                if not isinstance(entries, list) or not any(
                    isinstance(entry, dict)
                    and entry.get("obligation_id") == item["contract_id"]
                    and entry.get("status") == "verified"
                    for entry in entries
                ):
                    raise reviewer.ReviewError(
                        "dependency evidence missing for "
                        + item["contract_id"]
                        + ": "
                        + item["path"]
                    )
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("status") != "verified":
                    continue
                for item in requirements:
                    if entry.get("obligation_id") != item["contract_id"]:
                        continue
                    refs = entry.get("source_refs")
                    if refs is None:
                        refs = [entry.get("source_ref")]
                    quotes = []
                    if isinstance(refs, list):
                        for ref in refs:
                            if (
                                isinstance(ref, dict)
                                and ref.get("path") == item["path"]
                            ):
                                canonical = runtime._canonical_contract_ref(ref)
                                quotes.append(canonical["canonical_quote"])
                    quoted = "\n".join(quotes)
                    if not all(anchor in quoted for anchor in item["anchors"]):
                        raise reviewer.ReviewError(
                            "dependency evidence missing for "
                            + item["contract_id"]
                            + ": "
                            + item["path"]
                        )
        return original_validate(runtime, args)

    def prompt(runtime):
        text = original_prompt(runtime)
        requirements = rules(runtime)
        if requirements:
            text += (
                "\nDEPENDENCY_EVIDENCE: For a verified listed contract, actually read and cite the declared dependency source in addition to relevant changed implementation. A familiar API name is not evidence for its implementation guarantees. Source-backed explanation must cover the whole original contract; citations do not automatically certify semantics. Missing evidence may remain uncertain/escalate, never auto-verified. Requirements: "
                + str(requirements)
            )
        return text

    def repair(runtime, error, args):
        result = original_repair(runtime, error, args)
        result["dependency_evidence_requirements"] = rules(runtime)
        if error.startswith("dependency evidence missing for "):
            matching = [item for item in rules(runtime) if item["path"] in error]
            if matching:
                result["suggested_action"] = {
                    "action": "READ_FILE",
                    "arguments": {
                        "path": matching[0]["path"],
                        "start_line": 1,
                        "end_line": 40,
                    },
                }
            result["instruction"] = (
                "Read declared dependency source, then cite actually displayed supporting ranges and explain its real guarantees. Do not invent API behavior or normalize claims into verification."
            )
        return result

    reviewer.ReviewerRuntime.validate_report = validate
    reviewer.ReviewerRuntime.system_prompt = prompt
    reviewer.ReviewerRuntime.report_repair = repair


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "dependency_evidence_reviewer",
        args.snapshot / ".local-agents/reviewer-runtime.py",
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
