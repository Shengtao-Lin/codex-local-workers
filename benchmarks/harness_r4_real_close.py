"""Archive the two fixed exposed diagnostics without overwriting prior decisions."""

import argparse
from pathlib import Path

import harness_r4_dto_audit as AUDIT
import harness_r4_real_review as H


def main(used):
    B = H.B
    rows = []
    for item in B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(item["root"])
        H.R.assert_files(root, item["files"])
        for source in item["copied_inputs"].values():
            assert B.sha(Path(source["origin"])) == source["sha256"]
        for old in item["excluded_prior_review_outputs"].values():
            assert B.sha(Path(old["path"])) == old["sha256"]
        result = B.read(root.parent / "result.json")
        report = B.read(root.parent / "reviewer.json")
        judgment = B.read(root.parent / "primary-adjudication.json")
        rows.append(
            {
                **result,
                "primary": judgment,
                "report_sha256": B.sha(root.parent / "reviewer.json"),
            }
        )
        assert not result["protected_drift"] and not result["infra_failure"]
        assert report["evidence_observation_protocol"] == "reviewer-evidence-state-v1"
    for path, sha in B.read(H.BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == sha
    B.save(H.BATCH / "grid-results.json", rows)
    correct = sum(row["primary"]["correct"] for row in rows)
    B.save(
        H.BATCH / "decision.json",
        {
            "qualification": "PASS" if correct == 2 else "HOLD",
            "registered": 2,
            "executed": 2,
            "correct": correct,
            "old_results_unchanged": True,
            "reviewer_sixteen_gate_unchanged": "PASS 16/16",
            "r4_passed": False,
            "no_coder_or_transfer_credit": True,
            "weekly_used": used,
            "usage_ceiling": 45,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "next": "Audit ambiguous contract terminology separately from observation mechanics; no more tuning of frozen candidate on these outputs.",
        },
    )
    B.save(H.BATCH / "metrics.json", AUDIT.metrics(H.BATCH))
    print(
        {"correct": correct, "registered": 2, "all_inputs_and_origins_unchanged": True}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    main(parser.parse_args().used)
