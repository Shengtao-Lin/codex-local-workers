"""Independent audit of the node-ID repair experiment; never accepts a unit."""

import json
import subprocess
import sys
from pathlib import Path

from capability_fit import KIT, write
from inherited_context_recovery import digest, read
from layer_isolation import check
from quixbugs_repair_prefetch import BASE


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read(BASE / "manifest.json")
    require(
        digest(KIT / "benchmarks/quixbugs_repair_prefetch.py")
        == manifest["driver_sha256"],
        "experiment driver drift",
    )
    rows = []
    inherited_texts = []
    for cell in manifest["cells"]:
        root, snapshot = Path(cell["root"]), Path(cell["runtime"])
        for path, sha in read(snapshot / "freeze.json")["files"].items():
            require(digest(snapshot / path) == sha, "frozen runtime drift")
        require(digest(Path(cell["child"])) == cell["child_sha256"], "packet drift")
        archive = root / ".agent/tasks" / cell["task_id"] / "runs" / cell["run_id"]
        parent = archive.parent / cell["parent_run_id"]
        coder, packet = (
            read(archive / name) for name in ("handoff.json", "packet.json")
        )
        old_packet = read(parent / "packet.json")
        require((archive / "completed.json").exists(), "incomplete Coder")
        require(
            read(parent / "review.json")["decision"] == "takeover",
            "parent decision changed",
        )
        for key in (
            "scope",
            "focused_tests",
            "required_behavior",
            "acceptance_criteria",
            "acceptance_scenarios",
            "validation_profile",
            "owned_contract_ids",
            "required_order",
            "forbidden_orderings",
            "contract_check_required",
        ):
            require(packet[key] == old_packet[key], "inherited hard contract changed")
        expected = dict(cell["inputs"])
        for change in coder["changed_files"]:
            require(
                change["path"] == "src/product/target.py", "unexpected changed path"
            )
            expected[change["path"]] = change["final_sha256"]
        for path, sha in expected.items():
            require(digest(root / path) == sha, "protected/final input drift")
        checks = check(root, "node-prefetch-independent-1")
        write(BASE / f"{cell['arm']}-independent-1.json", checks)
        require(
            checks["tests_executed"] == 7 and checks["static_pass"],
            "missing independent evidence",
        )
        require(
            coder["status"] == "failed" and not checks["semantic_pass"],
            "unexpected successful unit: substantive review needed",
        )
        require(
            not (root / ".agent/node-prefetch-reviewer-a2.json").exists(),
            "unexpected Reviewer",
        )
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(KIT / ".local-agents/record-review.py"),
                "--repo",
                str(root),
                "--task-id",
                cell["task_id"],
                "--run-id",
                cell["run_id"],
                "--decision",
                "takeover",
                "--summary",
                "Independent seven-test check still fails; preserve partial draft and original parent history. No feature acceptance or Coordinator expansion. Remaining exact split expectation needs Primary contract adjudication.",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        require(
            result.returncode == 0,
            "Primary decision recording failed: " + result.stderr,
        )
        validation = read(root / coder["evidence_refs"]["validation_attempts"][-1])
        focused = validation["validation"]["focused_tests"]
        events = [
            json.loads(line)
            for line in (archive / "events.jsonl").read_text().splitlines()
        ]
        inherited_texts.append(
            packet["_inheritance"]["rework_traceback"]["failure_reason"]
        )
        rows.append(
            {
                "arm": cell["arm"],
                "task_id": cell["task_id"],
                "run_id": cell["run_id"],
                "coder_status": coder["status"],
                "last_junit": focused["junit"],
                "failed_test_ids": focused["diagnostic"]["failed_test_ids"],
                "independent_static_pass": checks["static_pass"],
                "independent_semantic_pass": checks["semantic_pass"],
                "reviewer": "not_started_validation_gate",
                "primary_decision": "takeover",
                "validation_attempts": len(
                    coder["evidence_refs"]["validation_attempts"]
                ),
                "local_invocation_seconds": read(
                    BASE / f"{cell['arm']}-invocation.json"
                )["seconds"],
                "prefetch_events": [
                    e["facts"]
                    for e in events
                    if e["event"] == "repair_context_prefetched"
                ],
                "actual_diff_sha256": digest(archive / "cumulative.diff"),
                "protected_inputs_unchanged": True,
            }
        )
    write(
        BASE / "outcomes-1.json",
        {
            "cells": rows,
            "successful_units": 0,
            "coordinator_release_expanded": False,
            "deterministic_bug_fixed": "Focused pytest node IDs failed bare-path membership; bounded test excerpts now retain read-scope checks.",
            "causal_claim": False,
            "limitations": [
                "One live pair, non-deterministic model output, distinct parent identities.",
                "Parent Coder-authored failure_reason wording differs despite equal source/tests/config/hard contracts and explicit Primary feedback; not a perfectly isolated causal experiment.",
                "Prefetch event metadata counts source excerpts only; test excerpt inclusion is established by runtime code/regression tests, not a live test-excerpt event counter.",
                "Remaining exact split assertion is more specific than prose about lossless width-bounded wrapping; needs adjudication, not silent protected-test weakening.",
            ],
            "parent_failure_reason_equal": inherited_texts[0] == inherited_texts[1],
            "remaining_input": {"text": "  abc", "cols": 2},
            "expected": [" ", " a", "bc"],
            "candidate_actual": [" ", " ", "ab", "c"],
            "both_results_nonempty_width_bounded_and_lossless": True,
            "next_step": "Specify or adjudicate split-policy semantics in a fresh versioned fixture before new model calls; then test concrete counterexample feedback without reference implementation.",
            "driver_lint_diagnostic": "Frozen experiment driver has unused KIT import (F401); retained as executed, no effect on model runtime or protected tests.",
            "primary_verification_environment_diagnostic": "System Python has no pytest; independent/full regression uses existing diagnostics venv, no dependency installation.",
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
