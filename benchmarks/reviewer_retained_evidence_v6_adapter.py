"""Keep bounded real source evidence visible in the canonical initial context."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_anchored_catalog_adapter import install as install_anchors
from reviewer_boundary_analogy_adapter import install as install_analogy
from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_citation_bundle_adapter import install as install_bundles
from reviewer_contract_test_read_adapter import install as install_test_reads
from reviewer_dependency_investigation_adapter import install as install_dependencies
from reviewer_execution_phase_adapter import install as install_execution
from reviewer_investigation_phase_adapter import install as install_phase
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_retained_wire_v2_adapter import install as install_wire
from reviewer_sampling_probe_adapter import install as install_probe
from reviewer_visible_quote_compaction import install as install_quotes


def install(reviewer):
    original_payload = reviewer.ReviewerRuntime.initial_payload
    original_active = reviewer.ReviewerRuntime._update_active_read_context

    def payload(runtime):
        result = original_payload(runtime)
        requests = runtime.config.get("reviewer_provided_read_evidence", [])
        if not isinstance(requests, list) or len(requests) > 6:
            raise reviewer.ReviewError(
                "provided read evidence must be at most six bounded requests"
            )
        if not requests:
            return result
        # Validate every requested scope/range before populating the read ledger.
        # Any later read or size failure aborts startup, before a model turn or
        # REPORT can credit this evidence as displayed.
        for request in requests:
            if not isinstance(request, dict) or set(request) != {
                "path",
                "start_line",
                "end_line",
            }:
                raise reviewer.ReviewError(
                    "provided read request requires exact path/start_line/end_line"
                )
            if (
                type(request["start_line"]) is not int
                or type(request["end_line"]) is not int
                or not 1 <= request["start_line"] <= request["end_line"]
                or request["end_line"] - request["start_line"] >= 160
            ):
                raise reviewer.ReviewError(
                    "provided read range must be one to 160 source lines"
                )
            runtime._assert_read_allowed(request["path"])
        if not hasattr(runtime, "provided_read_evidence"):
            observations = []
            for request in requests:
                observed = runtime.read_file(request)
                if observed.get("status") != "ok" or observed.get("truncated"):
                    raise reviewer.ReviewError(
                        "provided source evidence must be fully displayed"
                    )
                observations.append(
                    {
                        key: observed[key]
                        for key in (
                            "path",
                            "start_line",
                            "end_line",
                            "content",
                            "truncated",
                        )
                    }
                )
            if len(json.dumps(observations, ensure_ascii=False)) > runtime.max_output:
                raise reviewer.ReviewError(
                    "aggregate provided source exceeds original tool-output bound"
                )
            runtime.provided_read_evidence = observations
            reviewer.RUN_STATE.write_json_once(
                runtime.review_root / "provided-read-evidence.json",
                {
                    "actual_read_evidence": observations,
                    "model_selected_navigation": False,
                    "semantic_acceptance": False,
                },
            )
            runtime.event(
                "bounded_read_evidence_provided",
                {
                    "paths": [item["path"] for item in observations],
                    "semantic_acceptance": False,
                    "not_model_read_actions": True,
                },
            )
        runtime._assert_observed_sources_current()
        result["provided_read_evidence"] = runtime.provided_read_evidence
        result["provided_evidence_notice"] = (
            "Framework supplied these bounded actual source reads inside your scope. They remain visible here across history trimming. They are evidence, not a verdict or code recipe; independently reconcile the whole contract, implementation, tests and dependency, and use READ_FILE/SEARCH for additional unanswered questions."
        )
        return result

    def active(runtime, messages):
        mirrors = []
        for message in messages:
            content = message.get("content", "")
            if content.startswith("LOCAL_REVIEW_INPUT\n"):
                value = json.loads(content.split("\n", 1)[1])
                if "provided_read_evidence" in value:
                    mirrors.append(
                        {
                            "role": "user",
                            "content": "OBSERVATION\n"
                            + json.dumps(
                                {
                                    "provided_read_evidence": value[
                                        "provided_read_evidence"
                                    ]
                                }
                            ),
                        }
                    )
        # Only visibility indexing uses these mirrors; they are not extra model
        # messages, reads, source authority or ledger entries.
        original_active(runtime, [*messages, *mirrors])

    reviewer.ReviewerRuntime.initial_payload = payload
    reviewer.ReviewerRuntime._update_active_read_context = active


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "retained_evidence_reviewer",
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
    install_phase(reviewer)
    install_analogy(reviewer)
    install_bundles(reviewer)
    install(reviewer)
    install_quotes(reviewer)
    install_execution(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    install_wire(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
