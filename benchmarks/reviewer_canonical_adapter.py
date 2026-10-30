"""Diagnostic one citation shape from startup; unchanged read and acceptance gates."""

import argparse
import importlib.util
import sys
from pathlib import Path


def install(reviewer):
    reviewer.REVIEW_NATIVE_TOOLS = reviewer.canonical_citation_tools(
        reviewer.REVIEW_NATIVE_TOOLS
    )
    original_template = reviewer.ReviewerRuntime.report_template
    original_validate = reviewer.ReviewerRuntime.validate_report
    original_prompt = reviewer.ReviewerRuntime.system_prompt

    def template(runtime):
        result = original_template(runtime)
        for entry in result["arguments"]["contract_review"]:
            entry["source_refs"] = [entry.pop("source_ref")]
        return result

    def prompt(runtime):
        return original_prompt(runtime) + (
            "\nFor contract_review use only source_refs, an array of one to three actually read ranges, each at most 20 lines. Do not use source_ref or legacy path/line/source_quote fields there. Ordering review still uses flat path and line beside constraint_id, not nested refs. The runtime materializes exact read quotes, not semantic conclusions."
        )

    def validate(runtime, args):
        entries = args.get("contract_review", [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and (
                    "source_refs" not in entry
                    or set(entry)
                    - {"obligation_id", "status", "source_refs", "evidence"}
                ):
                    raise reviewer.ReviewError(
                        "Canonical citation candidate requires only obligation_id, status, source_refs and evidence per contract_review entry; actual source/read/anchor gates still apply"
                    )
        return original_validate(runtime, args)

    reviewer.ReviewerRuntime.report_template = template
    reviewer.ReviewerRuntime.system_prompt = prompt
    reviewer.ReviewerRuntime.validate_report = validate


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "canonical_review_diagnostic",
        args.snapshot / ".local-agents/reviewer-runtime.py",
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    return reviewer.main()


if __name__ == "__main__":
    raise SystemExit(main())
