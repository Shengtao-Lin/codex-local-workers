"""Close transport correction without rewriting failures or classifying output caps as HTTP."""

import argparse
from pathlib import Path

import harness_r4_dto_audit as METRICS
import harness_semantic_close as PREVIOUS
import harness_semantic_transport as H

B = H.B


def close(used):
    H.audit()
    grid = []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        root, name = Path(row["root"]), row["id"]
        H.R.assert_files(root, row["files"])
        H.R.assert_files(Path(row["origin"]), row["origin_files"])
        for p, sha in row["same_session_control"].items():
            assert B.sha(Path(p)) == sha
        report = B.read(root.parent / "reviewer.json")
        result = B.read(root.parent / "result.json")
        assert not result["protected_drift"]
        number = int(name.split("-")[1])
        correct, failure, reason = True, None, PREVIOUS.REASONS[number]
        if number == 9:
            correct, failure = False, "invented_required_test"
            reason = "False rework: model acknowledges x+1 source correct but turns behavior for all integers into an explicit test-creation requirement. Exact contract contains no required negative test. Host correctly preserves this incorrect model judgment; do not rescue it from prose."
        elif number == 17:
            correct, failure = False, "model_output_budget_exhausted"
            reason = "Input 4748 tokens, original 4096 completion cap exhausted entirely in reasoning, empty final action; no partial action executed. A model output-limit failure, not HTTP/loading/context overflow. Raw infra_failure field remains unchanged."
            assert result["infra_failure"]["reason_code"] == "output_token_limit"
        else:
            assert not result["infra_failure"]
            assert result["observed"] == row["expected_decision"]
            assert (
                report["semantic_transport_protocol"]
                == "reviewer-semantic-transport-v2"
            )
        if number == 20:
            reason += " Narrative loosely says falsy/None, but explicitly identifies the None guard preventing recognized-call update; no claim that the passing False test fails is credited."
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
        grid.append(
            {
                **result,
                "primary_adjudication": judgment,
                "report_sha256": B.sha(root.parent / "reviewer.json"),
            }
        )
    groups = [
        {
            "group": group,
            "correct": sum(
                r["primary_adjudication"]["correct"]
                for r in grid
                if r["group"] == group
            ),
            "total": sum(r["group"] == group for r in grid),
        }
        for group in ("original-sixteen", "exposed-real")
    ]
    B.save(
        H.BATCH / "primary-adjudications.json",
        [r["primary_adjudication"] for r in grid],
    )
    B.save(H.BATCH / "grid-results.json", grid)
    B.save(H.BATCH / "metrics.json", METRICS.metrics(H.BATCH))
    B.save(
        H.BATCH / "preservation.json",
        {
            "all_twenty_inputs_and_origins_unchanged": True,
            "live_pins_unchanged": True,
            "same_session_controls_unchanged": True,
            "previous_decisions_unchanged": True,
            "production_runtime_unchanged": True,
            "sibling_writes": False,
        },
    )
    B.save(
        H.BATCH / "decision.json",
        {
            "qualification": "HOLD",
            "registered": 20,
            "executed": 20,
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
            "next": "Keep repaired harness fixed. One independently registered temperature 1 to 0 diagnostic, no value sweep, same model/prompt/schema/contract/budget; test whether stochastic issue classification and output exhaustion persist. This is not an already proven remedy.",
        },
    )
    print(groups)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
