"""Aggregate the frozen direct-entry diagnostics; never invoke a Worker."""

import argparse
import ast
from pathlib import Path

import bounded_evidence_live_close as COST
import bounded_evidence_support as S
from consolidated_trial import BATCH, STARTS


def main(used):
    registration, cells = (
        S.read(BATCH / "registration.json"),
        S.read(BATCH / "cells.json"),
    )
    assert all(S.sha(p) == sha for p, sha in registration["pins"].items())
    originals = S.read(STARTS / "cells.json")
    rows = []
    for cell in registration["order"]:
        row = cells[cell]
        root = Path(row["root"])
        identity = row["identity"]
        archive = (
            root / ".agent/tasks" / identity["task_id"] / "runs" / identity["run_id"]
        )
        result = S.read(BATCH / "live-results" / cell / "result.json")
        report = S.read(archive / "handoff.json")
        counts = report["consolidated_harness"]["actual"]
        assert counts["edits"] == counts["post_edit_checks"]
        assert counts["model_requests"] == counts["requests"]
        source = root / "src/product/code.py"
        initial = Path(originals[row["topic"] + "-A1"]["root"]) / "src/product/code.py"
        prepared = sorted(archive.glob("preparation-*.json"))
        attempts = sorted(archive.glob("validation-attempt-*.json"))
        assert len(prepared) == counts["format_preparations"]
        assert len(attempts) == counts["initial_checks"] + counts["post_edit_checks"]
        rows.append(
            {
                "cell": cell,
                "identity": identity,
                "ledger": counts,
                "failure_reason": report.get("failure_reason"),
                "source_ast_changed": ast.dump(
                    ast.parse(initial.read_text(encoding="utf-8"))
                )
                != ast.dump(ast.parse(source.read_text(encoding="utf-8"))),
                "independent_checks": result["independent_checks"],
                "independent_all_checks_passed": result[
                    "independent_all_checks_passed"
                ],
                "reviewer_started": result["summary"]["reviewer_started"],
                "seconds": result["seconds"],
                "usage": COST.usage(
                    sorted(archive.glob("proposal-response-*.json")), "stats"
                ),
                "preparation_seconds": sum(S.read(p)["seconds"] for p in prepared),
                "final_source_sha256": result["final_source_sha256"],
                "protected_drift": result["protected_drift"],
                "Primary_decision": S.read(archive / "review.json")["decision"],
                "assisted": result["assisted"],
                "Primary_takeover": result["Primary_takeover"],
            }
        )
    totals = {key: sum(r["ledger"][key] for r in rows) for key in rows[0]["ledger"]}
    S.save(
        BATCH / "metrics.json",
        {
            "registered": 4,
            "executed": len(rows),
            "not_run": 0,
            "accepted": 0,
            "totals": totals,
            "cells": rows,
            "weekly_used": used,
            "weekly_stop": 20,
            "qualification": "HOLD, exposed diagnostic only",
            "Primary_active_seconds": None,
            "Primary_cloud_tokens": None,
            "model_loading_seconds_separate": None,
        },
    )
    print(totals)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    main(p.parse_args().weekly_used)
