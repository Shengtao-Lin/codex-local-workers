"""Budget the actual assembled request without changing evidence authority."""

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


def trim_wire(messages, tools, context, output, margin):
    """Retain contract, current controller state and the latest five exchanges."""
    available = max(0, context - output - margin)
    target = int(available * 0.9)
    kept = list(messages)
    removed = 0
    while True:
        estimate = (
            sum(len(item.get("content", "")) for item in kept)
            + len(json.dumps(tools, ensure_ascii=False))
            + 3
        ) // 4
        if estimate <= target:
            return kept, removed
        dialogue = [
            index
            for index, item in enumerate(kept)
            if index >= 2
            and (
                item.get("role") == "assistant"
                or item.get("content", "").startswith("OBSERVATION\n")
            )
        ]
        if len(dialogue) <= 10:
            return kept, removed  # Original client preflight remains fail-closed.
        # Delete only an old action/observation pair, never current state, contract
        # or the recent evidence window. Canonical archives and read hashes persist.
        take = dialogue[: min(2, len(dialogue) - 10)]
        for index in reversed(take):
            del kept[index]
        removed += len(take)


def install(reviewer):
    original_run = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete

        def budgeted(messages):
            context = runtime.client.context_length
            if type(context) is not int or context <= 0:
                raise reviewer.ReviewError(
                    "wire budget requires configured context length"
                )
            kept, removed = trim_wire(
                messages,
                runtime.client.native_tools,
                context,
                runtime.client.max_tokens,
                runtime.client.context_safety_margin,
            )
            if removed:
                runtime.event(
                    "assembled_wire_context_trim",
                    {
                        "removed_old_messages": removed,
                        "canonical_evidence_unchanged": True,
                        "automatic_acceptance": False,
                    },
                )
            if runtime.context_recovery:
                runtime._update_active_read_context(kept)
            return complete(kept)

        runtime.client.complete = budgeted
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
        "wire_budget_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    # Install first: its client wrapper executes last, after every prompt/schema
    # adapter has assembled the actual request, unlike core history-only trimming.
    install(reviewer)
    install_range(reviewer)
    install_dependencies(reviewer)
    install_catalog(reviewer)
    install_anchors(reviewer)
    install_test_reads(reviewer)
    install_phase(reviewer)
    install_required(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
