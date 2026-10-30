"""No-model controls for the exact opt-in direct-Primary CLI composition."""

from pathlib import Path

import strata_subagent_trial as T


def main():
    T.configure()
    batch = T.BATCH
    rows = T.S.read(batch / "cells.json")
    source = Path(rows["hash-1"]["root"])
    cases = {
        "forbidden": [
            {
                "kind": "read",
                "path": ".agent/packet.json",
                "start_line": 1,
                "end_line": 2,
            }
        ],
        "duplicate": [
            {
                "kind": "read",
                "path": "src/evaluation_harness/canonical/fingerprint.py",
                "start_line": 1,
                "end_line": 2,
            }
        ]
        * 3,
    }
    for name, actions in cases.items():
        root = batch / "entry-controls" / name / "isolated"
        T.COPY(source, root)
        replay = root.parent / "replay.json"
        T.S.save(replay, actions)
        result = T.J.T.run(T.P.command(root, replay=replay), root, timeout=180)
        report = T.S.read(root / ".agent/unit-report.json")
        summary = T.S.read(root / ".agent/unit-summary.json")
        actual = report["consolidated_harness"]["actual"]
        assert (
            result["exit_code"] != 0
            and actual["edits"] == actual["post_edit_checks"] == 0
        )
        assert (
            summary["reviewer_started"] is False
            and summary["production_acceptance"] is False
        )
        assert not (root / ".agent/reviewer-report.json").exists()
        assert actual["model_requests"] == 0
        if name == "forbidden":
            assert report["status"] == "policy_violation" and actual["requests"] == 1
        else:
            assert report["status"] == "failed" and actual["evidence_actions"] == 3
        T.S.save(
            root.parent / "result.json",
            {
                "command": result,
                "status": report["status"],
                "ledger": actual,
                "summary": summary,
                "model_calls": 0,
            },
        )
    proof = batch / "replay/hash/isolated"
    report = T.S.read(proof / ".agent/unit-report.json")
    summary = T.S.read(proof / ".agent/unit-summary.json")
    actual = report["consolidated_harness"]["actual"]
    assert actual["evidence_actions"] == 1 and actual["requests"] == 2
    assert actual["edits"] == actual["post_edit_checks"] == 1
    assert actual["model_requests"] == 0 and summary["host_handoff_verified"] is True
    assert (
        summary["reviewer_started"] is False
        and summary["production_acceptance"] is False
    )
    assert not (proof / ".agent/reviewer-report.json").exists()
    for topic in ("message", "hash"):
        selected = [r for r in rows.values() if r["topic"] == topic]
        assert (
            len(selected) == 2
            and selected[0]["start_sha256"] == selected[1]["start_sha256"]
        )
    T.S.save(
        batch / "entry-controls/decision.json",
        {
            "status": "PASS_OFFLINE_ONLY",
            "negative_cases": 2,
            "positive_read_edit_check_verified_handoff": True,
            "provider_calls": 0,
            "paired_start_sha256_equal": True,
            "reviewer_dispatched_in_B": False,
            "production_acceptance": False,
            "script_sha256": T.S.sha(__file__),
        },
    )
    print(
        "Exact CLI controls pass: guarded read+edit+checks+handoff, forbidden path, duplicate stop; zero model calls"
    )


if __name__ == "__main__":
    main()
