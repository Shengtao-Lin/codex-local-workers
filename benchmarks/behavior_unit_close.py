"""Read-only evidence aggregation; no Worker calls, score rewriting or patch replay."""

import argparse
import ast
import json
from pathlib import Path

import bounded_evidence_live_close as COST
import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/behavior-unit-20261018-3"


def structure(source):
    return ast.dump(ast.parse(source))


def imports(source):
    return [
        ast.dump(n)
        for n in ast.parse(source).body
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]


def main(used):
    registration, cells = (
        S.read(BATCH / "registration.json"),
        S.read(BATCH / "cells.json"),
    )
    assert all(S.sha(p) == sha for p, sha in registration["pins"].items())
    rows = []
    for cell in registration["order"]:
        row = cells[cell]
        root = Path(row["root"])
        packet = S.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        result, handoff = (
            S.read(BATCH / "live-results" / cell / "result.json"),
            S.read(archive / "handoff.json"),
        )
        original = (
            BATCH / "templates" / row["task"] / "src/product/code.py"
        ).read_text(encoding="utf-8")
        current = (root / "src/product/code.py").read_text(encoding="utf-8")
        actual = handoff["bounded_evidence"]["actual"]
        assert actual["effective_edits"] == actual["post_edit_checks"]
        drift = [
            p
            for p, sha in row["files"].items()
            if p != "src/product/code.py" and S.sha(root / p) != sha
        ]
        assert not drift
        responses = sorted(archive.glob("proposal-response-*.json"))
        proposals = []
        for response in responses:
            value = S.read(response)
            try:
                decoded = json.loads(value["raw"])
                keys = sorted(decoded)
                one_with_inactive_null = (
                    set(decoded) == {"replacement", "blocked_reason"}
                    and isinstance(decoded["replacement"], str)
                    and decoded["blocked_reason"] is None
                )
                request = S.read(archive / response.name.replace("response", "request"))
                changed = None
                if isinstance(decoded.get("replacement"), str):
                    try:
                        changed = structure(decoded["replacement"]) != structure(
                            request["binding"]["source"]
                        )
                    except (ValueError, SyntaxError):
                        pass
                proposals.append(
                    {
                        "file": response.name,
                        "keys": keys,
                        "inactive_null": one_with_inactive_null,
                        "replacement_ast_changed_from_request": changed,
                    }
                )
            except (ValueError, KeyError, TypeError):
                proposals.append(
                    {
                        "file": response.name,
                        "classification": "UNPARSEABLE_OR_REQUEST_ERROR",
                    }
                )
        extra = [S.read(p) for p in sorted(archive.glob("complete-diagnostics-*.json"))]
        validation = [S.read(p) for p in archive.glob("validation-attempt-*.json")]
        rows.append(
            {
                "cell": cell,
                "arm": row["arm"],
                "task": row["task"],
                "ledger": actual,
                "failure_reason": handoff.get("failure_reason"),
                "source_ast_changed": structure(current) != structure(original),
                "top_level_imports_changed": imports(current) != imports(original),
                "independent_all_checks_passed": result[
                    "independent_all_checks_passed"
                ],
                "independent_checks": result["independent_checks"],
                "reviewer_started": result["summary"]["reviewer_started"],
                "unit_seconds": result["unit_seconds"],
                "usage": COST.usage(responses, "stats"),
                "protected_drift": drift,
                "proposals": proposals,
                "supplemental_command_count": sum(
                    len(x["additional_checks"]) for x in extra
                ),
                "validation_attempt_count": len(validation),
                "final_source_sha256": S.sha(root / "src/product/code.py"),
                "assisted": False,
                "Primary_takeover": False,
            }
        )
    totals = {}
    for arm in ("A", "B"):
        selected = [r for r in rows if r["arm"] == arm]
        totals[arm] = {
            "executed": len(selected),
            "accepted": 0,
            "requests": sum(r["ledger"]["requests"] for r in selected),
            "text_edits": sum(r["ledger"]["effective_edits"] for r in selected),
            "post_edit_checks": sum(r["ledger"]["post_edit_checks"] for r in selected),
            "noops": sum(r["ledger"]["noops"] for r in selected),
            "protocol_recoveries": sum(
                r["ledger"]["protocol_recoveries"] for r in selected
            ),
            "changed_ast_cells": sum(r["source_ast_changed"] for r in selected),
            "changed_import_cells": sum(
                r["top_level_imports_changed"] for r in selected
            ),
        }
    S.save(
        BATCH / "metrics.json",
        {
            "cells": rows,
            "totals": totals,
            "not_run": 0,
            "weekly_used": used,
            "stop_used": 20,
            "note": "text edits are not semantic repair count; no import authority used in final drafts. Both arms have no all-check pass or Reviewer dispatch.",
            "Primary_active_seconds": None,
            "Primary_cloud_tokens": None,
        },
    )
    print(totals)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    main(p.parse_args().weekly_used)
