"""Close the fixed eight-cell diagnostic using explicit Primary adjudications."""

import argparse
from pathlib import Path

import harness_r4_dto_audit as A
import harness_terms_continuation as C


def close(used):
    B, H = C.B, C.H
    registered = C.audit()
    for path, sha in B.read(H.BATCH / "continuation-registration.json")["pins"].items():
        assert B.sha(Path(path)) == sha
    judgments = B.read(H.BATCH / "primary-adjudications.json")
    assert set(judgments) == {r["id"] for r in registered}
    rows = []
    for row in registered:
        cell = Path(row["root"]).parent
        result, report = B.read(cell / "result.json"), B.read(cell / "reviewer.json")
        assert not result["infra_failure"]
        assert not (set(result["protected_drift"]) - C.OUTPUTS)
        assert report["runtime_facts"]["inputs_unchanged"]
        static = B.read(cell / "static-fixture.json")
        assert B.sha(Path(static["source"])) == static["sha256"]
        rows.append(
            {
                **result,
                "wording": row["wording"],
                "implementation": row["implementation"],
                "actual_protected_drift": [],
                "primary": judgments[row["id"]],
                "report_sha256": B.sha(cell / "reviewer.json"),
            }
        )
    matrix = []
    for wording in ("original", "clarified"):
        for implementation in ("draft", "reference"):
            cells = [
                r
                for r in rows
                if r["wording"] == wording and r["implementation"] == implementation
            ]
            matrix.append(
                {
                    "wording": wording,
                    "implementation": implementation,
                    "correct": sum(r["primary"]["correct"] for r in cells),
                    "total": len(cells),
                }
            )
    clarified_ok = sum(r["correct"] for r in matrix if r["wording"] == "clarified") == 4
    B.save(H.BATCH / "grid-results.json", rows)
    B.save(
        H.BATCH / "decision.json",
        {
            "qualification": "PASS" if clarified_ok else "HOLD",
            "criterion": B.read(H.BATCH / "design-registration.json")["criterion"],
            "registered": 8,
            "executed": 8,
            "matrix": matrix,
            "r4_passed": False,
            "new_holdout_or_coder_credit": False,
            "weekly_used": used,
            "usage_ceiling": 45,
            "all_historical_failures_retained": True,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    B.save(H.BATCH / "metrics.json", A.metrics(H.BATCH))
    B.save(
        H.BATCH / "preservation.json",
        {
            "old_pins_and_production_unchanged": True,
            "input_sources_contracts_tests_unchanged": True,
            "actual_protected_drift": [],
            "expected_mutable_outputs": sorted(C.OUTPUTS),
            "first_cell_false_alarm_retained": True,
            "no_resampling": True,
            "no_sibling_writes": True,
        },
    )
    print(matrix)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
