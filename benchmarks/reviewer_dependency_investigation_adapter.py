"""Prospective declared dependency investigation before assessment; no truth defaults."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_dependency_evidence_adapter import install as install_dependencies
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def install(reviewer):
    original_validate = reviewer.ReviewerRuntime.validate_report
    original_repair = reviewer.ReviewerRuntime.report_repair
    original_run = reviewer.ReviewerRuntime.run

    def pending(runtime):
        result = []
        for item in runtime.config.get("reviewer_dependency_evidence", []):
            relative, absolute = runtime._assert_read_allowed(item["path"])
            runtime._assert_observed_sources_current()
            lines = absolute.read_text(encoding="utf-8").splitlines()
            displayed = "\n".join(
                line
                for index, line in enumerate(lines, 1)
                if index in runtime.read_lines.get(relative, set())
            )
            if not all(anchor in displayed for anchor in item["anchors"]):
                result.append(
                    {
                        "contract_id": item["contract_id"],
                        "path": relative,
                        "suggested_read": {
                            "path": relative,
                            "start_line": 1,
                            "end_line": min(40, len(lines)),
                        },
                    }
                )
        return result

    def validate(runtime, args):
        remaining = pending(runtime)
        if args.get("stage") == "assessment":
            entry = args.get("assessment")
            remaining = [
                item
                for item in remaining
                if isinstance(entry, dict)
                and item["contract_id"] == entry.get("obligation_id")
            ]
        if remaining:
            raise reviewer.ReviewError(
                "declared dependency investigation incomplete: " + remaining[0]["path"]
            )
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
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                for rule in runtime.config.get("reviewer_dependency_evidence", []):
                    if entry.get("obligation_id") != rule["contract_id"]:
                        continue
                    refs = entry.get("source_refs", [entry.get("source_ref")])
                    quotes = []
                    if isinstance(refs, list):
                        for ref in refs:
                            if (
                                isinstance(ref, dict)
                                and ref.get("path") == rule["path"]
                            ):
                                quotes.append(
                                    runtime._canonical_contract_ref(ref)[
                                        "canonical_quote"
                                    ]
                                )
                    if not all(
                        anchor in "\n".join(quotes) for anchor in rule["anchors"]
                    ):
                        raise reviewer.ReviewError(
                            "dependency assessment citation missing: " + rule["path"]
                        )
        return original_validate(runtime, args)

    def repair(runtime, error, args):
        result = original_repair(runtime, error, args)
        remaining = pending(runtime)
        if (
            error.startswith("declared dependency investigation incomplete:")
            and remaining
        ):
            result["suggested_action"] = {
                "action": "READ_FILE",
                "arguments": remaining[0]["suggested_read"],
            }
        result["dependency_investigation_pending"] = remaining
        if error.startswith("dependency assessment citation missing:"):
            result["instruction"] = (
                "Cite the actually read declared dependency together with application source for this contract, even if uncertain/violated. Reconcile both sources in your explanation; absence of library internals in application code alone is not a library defect. Do not auto-verify."
            )
        return result

    def run(runtime):
        complete = runtime.client.complete

        def with_pending(messages):
            return complete(
                [
                    *messages,
                    {
                        "role": "user",
                        "content": "DEPENDENCY_INVESTIGATION_STATE\n"
                        + json.dumps(
                            {
                                "pending": pending(runtime),
                                "instruction": "Actually read the declared dependency before assessing its contract, including uncertain/violated claims, or submitting any final report. Cite dependency ranges with application source for every listed contract assessment, regardless of status, and reconcile both sources. Missing explicit library internals in changed application code is not evidence that the library lacks them. Reads remain model actions; the runtime does not read on your behalf or infer a verified verdict. After investigation you may remain uncertain, report a real defect, or pass only with all original gates.",
                            }
                        ),
                    },
                ]
            )

        runtime.client.complete = with_pending
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.validate_report = validate
    reviewer.ReviewerRuntime.report_repair = repair
    reviewer.ReviewerRuntime.run = run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--staged", action="store_true")
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "dependency_investigation_reviewer",
        args.snapshot / ".local-agents/reviewer-runtime.py",
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    (install_range if args.staged else install_dependencies)(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
