"""Close the immutable readiness batch after independently recorded Primary reviews."""

import argparse
from pathlib import Path

import harness_r3_readiness as S

B = S.B


def main(used):
    frozen = B.read(S.BATCH / "live-freeze-approved.json")
    S.R.assert_files(B.KIT, frozen["candidate_and_driver"])
    binding = S.R.load(B.KIT / ".local-agents/citation-binding.py", "close_binding")
    rows = []
    for name in S.P.ORDER:
        case = S.BATCH / "cases" / name
        if not (case / "result.json").exists():
            rows.append({"case": name, "status": "NOT_RUN", "accepted": False})
            continue
        row = B.read(case / "result.json")
        row["accepted"] = False
        if (case / "primary-decision.json").exists():
            primary = B.read(case / "primary-decision.json")
            canonical = B.read(Path(row["canonical_archive"]) / "review.json")
            assert primary == canonical
            assert row["eligible_for_primary"] and primary["decision"] == "accept"
            report = B.read(case / "reviewer.json")
            packet = B.read(case / "isolated/.agent/packet.json")
            entries = {
                item["obligation_id"]: item for item in report["contract_review"]
            }
            for behavior in packet["required_behavior"]:
                ref = behavior["implementation_ref"]
                source = (case / "isolated" / ref["path"]).read_text(encoding="utf-8")
                assert binding.covers(
                    ref, source, entries[behavior["id"]]["source_refs"]
                )
            row["accepted"] = True
        rows.append(row)
    candidate = [row for row in rows if "-candidate-" in row["case"]]
    baseline = [row for row in rows if "-baseline-" in row["case"]]
    passed = sum(row["accepted"] for row in candidate) == 6
    assert (
        passed
        or any(row.get("eligible_for_primary") is False for row in candidate)
        or used >= 30
    )
    B.save(S.BATCH / "grid-results.json", rows)
    B.save(
        S.BATCH / "decision.json",
        {
            "stage": "R3",
            "qualification": "PASS" if passed else "HOLD",
            "candidate_hashes": frozen["candidate_and_driver"],
            "registered": 12,
            "executed": sum(row.get("status") != "NOT_RUN" for row in rows),
            "not_run": sum(row.get("status") == "NOT_RUN" for row in rows),
            "candidate_accepted": sum(row["accepted"] for row in candidate),
            "baseline_accepted": sum(row["accepted"] for row in baseline),
            "candidate_denominator": 6,
            "r4_admitted": passed,
            "usage_end": used,
            "usage_ceiling": 30,
            "primary_semantic_takeover": False,
            "scope": "two exposed single-function development tasks; not general model qualification",
            "next_action": "Frozen R4 transfer and original sixteen Reviewer controls"
            if passed
            else "Classify the preserved failure before any new candidate",
        },
    )
    print(
        {
            "qualification": "PASS" if passed else "HOLD",
            "candidate_accepted": sum(row["accepted"] for row in candidate),
            "baseline_accepted": sum(row["accepted"] for row in baseline),
        },
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    main(parser.parse_args().used)
