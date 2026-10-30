"""Close fixed semantic experiment using explicit Primary findings adjudication."""

import argparse
from pathlib import Path

import harness_r4_dto_audit as METRICS
import harness_reviewer_semantic as H

B = H.B
REASONS = {
    1: "dict.get preserves present None/empty and defaults only for absent key; no mutation.",
    2: "Concrete or-fallback defect for present empty/None with actual source and correction.",
    3: "Single fetch, direct return, KeyError-only fallback; optional test coverage does not block.",
    4: "Concrete broad Exception suppression defect; must propagate non-KeyError exceptions.",
    5: "Repeated correct dict.get presence semantics, no invented defect.",
    6: "Repeated correct falsy-preservation defect finding at or-fallback.",
    7: "Repeated correct source-backed single fetch and narrow exception handling.",
    8: "Repeated source-backed broad exception defect, not optional test advice.",
    9: "x+1 source satisfies negatives; absent optional negative test is not required rework.",
    10: "Repeated correct distinction of optional test coverage from hard requirement.",
    11: "Explicit required negative assertion is absent from the complete five-line test.",
    12: "Repeated explicit required-test gap, correct source implementation acknowledged.",
    13: "Correctly identifies simultaneous x+1/x-1 impossibility and escalates.",
    14: "Repeated mathematical contradiction, no piecewise contract rewrite.",
    15: "abs(x)+1 violates x+1 for -2: observed source computes 3 instead of -1.",
    16: "Repeated concrete abs(x)+1 defect and -2 counterexample.",
    17: "Known-call None must update result/status; guard leaves requested. Correct cause, not a false False/0 claim.",
    18: "Reference dict replacement/order and unconditional exact result update satisfy contract, including None.",
    19: "Repeated correct reference acceptance, source model_copy/result/status and stable insertion order.",
    20: "Repeated causal None result/status violation with concrete guard and bounded fix.",
}
SPECIAL = {
    "sample-11-candidate": (
        False,
        "protocol_locator_failure",
        "Every raw report identifies the required missing test. First report selects E1/source and E2/test with line5 valid only in E2; host requires first-ID location. Later reports use null for an absent-test location and remain rejected. No accepted report; do not count raw semantic recognition as success.",
    ),
    "sample-12-candidate": (
        False,
        "protocol_locator_failure",
        "All four raw reports correctly identify required missing negative test, but use null for a missing assertion. Host insists on integer inside first selected ID. Candidate fails despite useful semantic finding.",
    ),
    "sample-16-candidate": (
        False,
        "blocked_route_aggregation",
        "Model explicitly reports implementation_defect with correct -2 counterexample and fix; an owned uncertainty about absent negative test makes host choose insufficient_evidence/escalate. Both routes block acceptance, but required disposition is rework; retain original strict criterion.",
    ),
    "sample-12-control": (
        False,
        "protocol_nonconvergence",
        "Original formal entry exhausts its unchanged protocol error budget; no accepted report, despite same frozen input.",
    ),
    "sample-17-control": (
        False,
        "incorrect_causal_finding",
        "Label rework matches by accident: both findings falsely claim False/falsy values are excluded by is not None, and cite the already passing False test. False is not None is True. Does not articulate the actual known-call None/requested defect; no causal detection credit.",
    ),
    "sample-20-control": (
        False,
        "semantic_false_pass",
        "Marks owned contract verified and passes bad None guard without finding; known-call None remains requested.",
    ),
}


def close(used):
    H.audit()
    grid, judgments = [], []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        root, name = Path(row["root"]), row["id"]
        H.R.assert_files(root, row["files"])
        H.R.assert_files(Path(row["origin"]), row["origin_files"])
        cell = root.parent
        result, report = B.read(cell / "result.json"), B.read(cell / "reviewer.json")
        number = int(name.split("-")[1])
        correct, failure, reason = SPECIAL.get(name, (True, None, REASONS[number]))
        assert not result["protected_drift"] and not result["infra_failure"]
        if correct:
            assert result["observed"] == row["expected_decision"]
        for contract in report.get("contract_review", []):
            for ref in contract.get("source_refs", []):
                source = root / ref["path"]
                lines = source.read_text(encoding="utf-8-sig").splitlines()
                assert (
                    "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
                    == ref["canonical_quote"]
                )
                assert B.sha(source) == ref["source_hash"].removeprefix("sha256:")
        judgment = {
            "id": name,
            "correct": correct,
            "failure_class": failure,
            "reason": reason,
        }
        judgments.append(judgment)
        grid.append(
            {
                **result,
                "primary_adjudication": judgment,
                "report_sha256": B.sha(cell / "reviewer.json"),
            }
        )
    groups = [
        {
            "arm": arm,
            "group": group,
            "correct": sum(
                r["primary_adjudication"]["correct"]
                for r in grid
                if r["arm"] == arm and r["group"] == group
            ),
            "total": sum(r["arm"] == arm and r["group"] == group for r in grid),
        }
        for arm in ("control", "candidate")
        for group in ("original-sixteen", "exposed-real")
    ]
    baseline = B.read(H.BATCH / "baseline.json")
    drift = [
        p
        for p, sha in baseline["files"].items()
        if not (B.KIT / p).is_file() or B.sha(B.KIT / p) != sha
    ]
    assert set(drift) <= {
        "benchmarks/reviewer_semantic_entry.py",
        "tests/test_reviewer_semantic_entry.py",
        "docs/local-model-harness-convergence-plan.md",
    }, drift
    B.save(H.BATCH / "primary-adjudications.json", judgments)
    B.save(H.BATCH / "grid-results.json", grid)
    B.save(H.BATCH / "metrics.json", METRICS.metrics(H.BATCH))
    B.save(
        H.BATCH / "preservation.json",
        {
            "baseline_files": len(baseline["files"]),
            "documented_pre_live_candidate_and_plan_edits": drift,
            "live_pins_unchanged": True,
            "all_forty_input_and_origin_manifests_unchanged": True,
            "old_decisions_unchanged": True,
            "production_runtime_unchanged": True,
            "sibling_writes": False,
        },
    )
    B.save(
        H.BATCH / "decision.json",
        {
            "qualification": "HOLD",
            "registered": 40,
            "executed": 40,
            "not_run": 0,
            "groups": groups,
            "r4_passed": False,
            "production_promoted": False,
            "new_coder_or_holdout_credit": False,
            "weekly_used_start": 44,
            "weekly_used": used,
            "usage_ceiling": 50,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "next": "Separately repair citation-location transport and aggregation of confirmed defect versus attached unresolved notes; first offline replay/negative controls, then one independently frozen repeat with unchanged semantic prompt/model/hard gates. Original batch stays HOLD.",
        },
    )
    print(groups)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
