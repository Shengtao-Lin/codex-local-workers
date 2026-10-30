"""Require actual protected-test reads before associated provisional claims.

This does not certify a claim or overwrite any model finding. The original final,
citation, source-version, execution and review budgets remain authoritative.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_anchored_catalog_adapter import install as install_anchors
from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_dependency_investigation_adapter import install as install_investigation
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe


def citation_navigation(runtime):
    """Describe anchor coverage of already-read handles, never inject citations."""
    runtime._assert_observed_sources_current()
    result = []
    for rule in runtime.config.get("reviewer_dependency_evidence", []):
        options = []
        for entry in runtime.evidence_catalog.entries.values():
            if entry["path"] != rule["path"]:
                continue
            ref = runtime.evidence_catalog.refs(
                [entry["id"]], runtime.read_lines, runtime.observed_read_hashes
            )[0]
            quote = runtime._canonical_contract_ref(ref)["canonical_quote"]
            anchors = [anchor for anchor in rule["anchors"] if anchor in quote]
            if anchors:
                options.append({"id": entry["id"], "covers_anchors": anchors})
        result.append(
            {
                "contract_id": rule["contract_id"],
                "required_anchors": rule["anchors"],
                "actual_read_options": options,
            }
        )
    return result


def install(reviewer):
    original_init = reviewer.ReviewerRuntime.__init__
    original_validate = reviewer.ReviewerRuntime.validate_report
    original_repair = reviewer.ReviewerRuntime.report_repair
    original_run = reviewer.ReviewerRuntime.run

    def init(runtime, *args, **kwargs):
        original_init(runtime, *args, **kwargs)
        rules = runtime.config.get("reviewer_contract_test_reads", [])
        if not isinstance(rules, list):
            raise reviewer.ReviewError("reviewer_contract_test_reads must be a list")
        for rule in rules:
            if (
                not isinstance(rule, dict)
                or set(rule) != {"contract_id", "path"}
                or not isinstance(rule["contract_id"], str)
                or not isinstance(rule["path"], str)
                or rule["contract_id"] not in runtime.packet["owned_contract_ids"]
                or rule["path"] not in runtime.packet["focused_tests"]
                or rule["path"] not in runtime.packet["scope"]["readonly"]
            ):
                raise reviewer.ReviewError(
                    "contract test-read must name an owned contract and protected focused test"
                )
            _, path = runtime._assert_read_allowed(rule["path"])
            if len(path.read_text(encoding="utf-8").splitlines()) > 200:
                raise reviewer.ReviewError(
                    "contract test-read requires a bounded test file (at most 200 lines)"
                )
        runtime.contract_test_reads = rules

    def pending(runtime, obligation=None):
        runtime._assert_observed_sources_current()
        return [
            rule
            for rule in runtime.contract_test_reads
            if (obligation is None or rule["contract_id"] == obligation)
            and not set(
                range(
                    1,
                    len(
                        (runtime.repo_root / rule["path"])
                        .read_text(encoding="utf-8")
                        .splitlines()
                    )
                    + 1,
                )
            )
            <= runtime.read_lines.get(rule["path"], set())
        ]

    def validate(runtime, args):
        runtime._assert_observed_sources_current()
        obligation = None
        if args.get("stage") == "assessment":
            entry = args.get("assessment")
            obligation = entry.get("obligation_id") if isinstance(entry, dict) else None
        remaining = pending(runtime, obligation)
        if remaining:
            raise reviewer.ReviewError(
                "protected contract test read missing: " + remaining[0]["path"]
            )
        return original_validate(runtime, args)

    def repair(runtime, error, args):
        result = original_repair(runtime, error, args)
        if error.startswith("protected contract test read missing:"):
            path = error.split(": ", 1)[1]
            result["suggested_action"] = {
                "action": "READ_FILE",
                "arguments": {"path": path},
            }
        return result

    def run(runtime):
        complete = runtime.client.complete

        def with_tests(messages):
            return complete(
                [
                    *messages,
                    {
                        "role": "user",
                        "content": "CONTRACT_TEST_READ_STATE\n"
                        + json.dumps(
                            {
                                "pending": pending(runtime),
                                "dependency_citation_navigation": citation_navigation(
                                    runtime
                                ),
                                "citation_instruction": "Select dependency evidence IDs whose combined covers_anchors includes every required anchor, plus relevant application evidence, within the existing maximum three IDs. Options are read navigation, not semantic verification; do not assume verified or discard findings.",
                                "instruction": "Before assessing an associated contract, actually read its protected focused test. Reconcile the assertion and actual validation result with the changed implementation. Passing tests do not prove all boundaries and an unchanged line is not automatically correct; explain concrete conflicting evidence rather than ignoring it. Preserve independent findings and uncertain/rework decisions. The runtime does not infer semantic truth or read these tests for you.",
                            }
                        ),
                    },
                ]
            )

        runtime.client.complete = with_tests
        try:
            return original_run(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.__init__ = init
    reviewer.ReviewerRuntime.validate_report = validate
    reviewer.ReviewerRuntime.report_repair = repair
    reviewer.ReviewerRuntime.run = run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "contract_test_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install_range(reviewer)
    install_investigation(reviewer)
    install_catalog(reviewer)
    install_anchors(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
