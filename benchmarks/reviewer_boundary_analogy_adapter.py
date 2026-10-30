"""Frozen, executed generic protocol analogy; no target-specific answer injection."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from reviewer_anchored_catalog_adapter import install as install_anchors
from reviewer_catalog_staged_adapter import install as install_catalog
from reviewer_contract_test_read_adapter import install as install_test_reads
from reviewer_dependency_investigation_adapter import install as install_dependencies
from reviewer_investigation_phase_adapter import install as install_phase
from reviewer_range_staged_adapter import install as install_range
from reviewer_required_tool_adapter import install as install_required
from reviewer_sampling_probe_adapter import install as install_probe
from reviewer_wire_budget_adapter import install as install_wire

EXAMPLE = Path(__file__).resolve().parent / "fixtures/reviewer-protocol-analogy-v1.json"


def install(reviewer):
    original_run = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete
        analogy = json.loads(EXAMPLE.read_text(encoding="utf-8"))

        def with_analogy(messages):
            return complete(
                [
                    *messages,
                    {
                        "role": "user",
                        "content": "GENERIC_PROTOCOL_REASONING_ANALOGY\n"
                        + json.dumps(analogy),
                    },
                ]
            )

        runtime.client.complete = with_analogy
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
        "boundary_analogy_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install_wire(reviewer)
    install_range(reviewer)
    install_dependencies(reviewer)
    install_catalog(reviewer)
    install_anchors(reviewer)
    install_test_reads(reviewer)
    install_phase(reviewer)
    install(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
