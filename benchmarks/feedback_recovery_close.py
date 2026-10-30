"""Immutable facts only; decisions remain Primary-authored."""

import argparse
import json
from pathlib import Path

import bounded_evidence_live_close as COST
import bounded_evidence_support as S
from feedback_recovery_trial_v2 import BATCH


def main(used):
    registration = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == sha for p, sha in registration["pins"].items())
    cells = S.read(BATCH / "cells-receipt.json")
    rows = []
    totals = {
        a: {"executed": 0, "accepted": 0, "requests": 0, "edits": 0, "noops": 0}
        for a in ("A", "B")
    }
    for cell in registration["order"]:
        prepared = cells[cell]
        root = Path(prepared["root"])
        packet = S.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        result = S.read(BATCH / "live-results" / cell / "result.json")
        review = S.read(archive / "review.json")
        handoff = S.read(archive / "handoff.json")
        actual = handoff["bounded_evidence"]["actual"]
        assert actual["effective_edits"] == actual["post_edit_checks"]
        drift = [
            p
            for p, sha in prepared["files"].items()
            if p != "src/product/code.py" and S.sha(root / p) != sha
        ]
        assert not drift
        unchanged = (
            S.sha(root / "src/product/code.py")
            == prepared["files"]["src/product/code.py"]
        )
        requests = [S.read(p) for p in sorted(archive.glob("proposal-request-*.json"))]
        facts = [
            json.JSONDecoder().raw_decode(r["messages"][1]["content"])[0]
            for r in requests
        ]
        receipt = any(
            any(x.get("status") == "no_op" for x in f["host_receipt"]["recent"])
            for f in facts
        )
        arm = prepared["arm"]
        assert receipt == (arm == "B"), "Treatment not exercised"
        row = {
            "cell": cell,
            "arm": arm,
            "task": prepared["task"],
            "ledger": actual,
            "explicit_receipt_observed": receipt,
            "source_unchanged": unchanged,
            "final_source_sha256": result["final_source_sha256"],
            "protected_drift": drift,
            "reviewer_started": result["summary"]["reviewer_started"],
            "independent_all_checks_passed": result["independent_all_checks_passed"],
            "primary_decision": review["decision"],
            "assisted": False,
            "unit_seconds": result["unit_seconds"],
            "coder_usage": COST.usage(
                sorted(archive.glob("proposal-response-*.json")), "stats"
            ),
            "source_checks": [
                {"exit_code": c["exit_code"], "stdout": c["stdout"]}
                for c in result["independent_checks"]
            ],
        }
        rows.append(row)
        count = totals[arm]
        count["executed"] += 1
        count["accepted"] += review["decision"] == "accept"
        count["requests"] += actual["requests"]
        count["edits"] += actual["effective_edits"]
        count["noops"] += actual["noops"]
    S.save(
        BATCH / "metrics.json",
        {
            "totals": totals,
            "cells": rows,
            "registered": 8,
            "not_run": 0,
            "weekly_used": used,
            "weekly_stop": 20,
            "Primary_cloud_tokens": None,
            "Primary_active_seconds": None,
            "load_seconds_separate": None,
            "Primary_source_takeovers": 0,
            "Primary_new_semantic_hints": 0,
            "preparation_cost": "One-time adapter/fixtures/runners plus documented infrastructure corrections; not task savings",
            "invalid_v1": "Three executed invalid-treatment cells and fiveNOT_RUN preserved separately; not added to valid denominator",
        },
    )
    print(totals)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    main(p.parse_args().weekly_used)
