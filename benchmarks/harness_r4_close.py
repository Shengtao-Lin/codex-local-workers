"""Close the frozen R4 batch from explicit Primary adjudications, without models."""

import argparse
import json
from pathlib import Path

import harness_r4_reviewer as H

B = H.B


def wire_metrics(cell):
    calls = []
    for path in sorted((cell / "wire").glob("*-request.json")):
        request = B.read(path)
        response_path = path.with_name(path.name.replace("-request", "-response"))
        response = B.read(response_path) if response_path.exists() else {}
        if not request.get("url", "").endswith("/chat/completions"):
            continue
        try:
            payload = json.loads(response.get("raw", "{}"))
        except json.JSONDecodeError:
            payload = {}
        calls.append(
            {
                "model": request.get("body", {}).get("model"),
                "seconds": response.get("seconds"),
                "usage": payload.get("usage"),
            }
        )
    return calls


def main(used):
    root = H.H.BATCH
    frozen = B.read(root / "live-freeze-approved.json")
    H.R.assert_files(B.KIT, frozen["candidate_and_driver"])
    seal = B.read(H.BATCH / "diagnostic-live-freeze.json")
    assert B.sha(B.KIT / "benchmarks/harness_r4_reviewer.py") == seal["driver"]
    assert B.sha(H.BATCH / "registration.json") == seal["registration"]
    registry = B.read(H.BATCH / "registration.json")
    manual = B.read(H.BATCH / "primary-adjudications.json")
    by_id = {row["id"]: row for row in manual}
    assert len(by_id) == len(manual) == 16
    assert set(by_id) == {row["id"] for row in registry["cells"]}
    controls = []
    for item in registry["cells"]:
        cell = H.BATCH / "cells" / item["id"]
        result, report = B.read(cell / "result.json"), B.read(cell / "reviewer.json")
        H.R.assert_files(Path(item["root"]), item["files"])
        judgment = by_id[item["id"]]
        assert judgment["reason"] and type(judgment["correct"]) is bool
        # Decisions are supplied only after human-level Primary source/report review;
        # matching a report label does not create a substantive adjudication.
        if judgment["correct"]:
            assert result["label_match_not_adjudication"]
            assert not result["protected_drift"] and not result["infra_failure"]
        controls.append(
            {
                **result,
                "primary_adjudication": judgment,
                "report_sha256": B.sha(cell / "reviewer.json"),
                "source_sha256": B.sha(Path(item["root"]) / "src/product/target.py"),
                "tests_sha256": B.sha(Path(item["root"]) / "tests/test_target.py"),
                "protocol_errors": report.get("runtime_facts", {}).get(
                    "protocol_error_count"
                ),
                "chat_completions": wire_metrics(cell),
            }
        )
    correct = sum(row["primary_adjudication"]["correct"] for row in controls)
    B.save(H.BATCH / "grid-results.json", controls)
    B.save(
        H.BATCH / "decision.json",
        {
            "qualification": "PASS" if correct == 16 else "HOLD",
            "registered": 16,
            "executed": 16,
            "substantively_correct": correct,
            "criterion": registry["criterion"],
            "synthetic_controls_not_coder_credit": True,
            "transfer_hold_unchanged": True,
            "usage_end": used,
            "usage_ceiling": 30,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    rows = []
    for name in B.read(root / "registration.json")["order"]:
        cell = root / "cases" / name
        if not (cell / "result.json").exists():
            rows.append({"case": name, "status": "NOT_RUN", "accepted": False})
            continue
        row = B.read(cell / "result.json")
        row["accepted"] = False
        if (cell / "primary-decision.json").exists():
            primary = B.read(cell / "primary-decision.json")
            assert primary == B.read(Path(row["canonical_archive"]) / "review.json")
            row["primary_decision"] = primary
            row["accepted"] = primary["decision"] == "accept"
            assert row["eligible_for_primary"]
        rows.append(row)
    transfer = B.read(root / "transfer-decision.json")
    assert transfer["qualification"] == "HOLD"
    assert sum(row["accepted"] for row in rows if "-candidate-" in row["case"]) == 2
    assert sum(row["accepted"] for row in rows if "-baseline-" in row["case"]) == 2
    B.save(root / "grid-results.json", rows)
    B.save(
        root / "decision.json",
        {
            **transfer,
            "stage": "R4",
            "reviewer_controls_executed": 16,
            "reviewer_controls_correct": correct,
            "reviewer_controls_gate": "PASS" if correct == 16 else "HOLD",
            "reviewer_real_transfer_false_negative": "collect_tools-candidate-1",
            "r5_admitted": False,
            "usage_end": used,
            "usage_ceiling": 30,
            "new_live_requires_separate_registration_and_semantic_scope_decision": True,
            "next_decision": "Contract-boundary coverage and Reviewer causal reasoning; do not retune patch transport or enable product defaults",
        },
    )
    print({"R4": "HOLD", "reviewer_correct": correct, "reviewer_registered": 16})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    main(parser.parse_args().used)
