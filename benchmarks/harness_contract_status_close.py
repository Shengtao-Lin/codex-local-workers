"""Close a narrow diagnostic, never silently grant it full Reviewer qualification."""

import argparse
import copy
import json

import harness_r4_dto_audit as M
import reviewer_contract_status_probe as P


def close(used):
    P.audit()
    B, rows, payloads = P.B, [], {}
    expected = B.read(P.BATCH / "judge.json")["statuses"]
    for row in B.read(P.BATCH / "registration.json")["cells"]:
        cell = P.BATCH / "cells" / row["id"]
        result = B.read(cell / "result.json")
        calls = M.calls(cell)
        assert len(calls) == 1
        body = B.read(cell / "wire" / calls[0]["request"])["body"]
        assert body["messages"] == B.read(cell / "messages.json")
        assert body["tools"] == P.TOOLS and body["max_tokens"] == 4096
        statuses = (
            [r["status"] for r in result["parsed"]["arguments"]["predictions"]]
            if result["parsed"]
            else None
        )
        correct = statuses == expected
        rows.append(
            {
                **result,
                "primary_adjudication": {
                    "correct": correct,
                    "basis": "All recognized result events must set succeeded; reasons inspected against exact frozen contract. No current-implementation exception for None.",
                },
                "wire": calls,
            }
        )
        payloads.setdefault(row["arm"], []).append(body)
    for values in payloads.values():
        assert all(p == values[0] for p in values)
    blind, source = (
        copy.deepcopy(payloads["blind"][0]),
        copy.deepcopy(payloads["source"][0]),
    )
    before, after = [json.loads(b["messages"][1]["content"]) for b in (blind, source)]
    assert after.pop("unreviewed_implementation") and before == after
    blind["messages"][1]["content"] = source["messages"][1]["content"] = "matched"
    assert blind == source
    groups = [
        {
            "arm": arm,
            "correct": sum(
                r["primary_adjudication"]["correct"] for r in rows if r["arm"] == arm
            ),
            "total": 4,
        }
        for arm in ("blind", "source")
    ]
    B.save(P.BATCH / "grid-results.json", rows)
    B.save(
        P.BATCH / "matched-wire-audit.json",
        {
            "only_source_field_differs": True,
            "one_rpc_each": True,
            "same_schema_sampling_and_limits": True,
        },
    )
    B.save(
        P.BATCH / "decision.json",
        {
            "qualification": "PASS_NARROW"
            if all(g["correct"] == 4 for g in groups)
            else "HOLD",
            "groups": groups,
            "registered": 8,
            "executed": len(rows),
            "r4_passed": False,
            "production_promoted": False,
            "new_holdout_credit": False,
            "weekly_used": used,
            "usage_ceiling": 50,
            "limitation": "Six positive inputs all require succeeded. Correct nontrivial reasons support narrow contract interpretation, but a constant succeeded predictor is not ruled out. Add absence/unknown-id controls grounded in existing visible tests before integration. No causal source penalty observed in this task; cannot infer why the broader REPORT task fails.",
            "next": "One separate discriminating matched diagnostic, no production/handoff changes, no new prompt or sampling sweep.",
        },
    )
    print(groups)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
