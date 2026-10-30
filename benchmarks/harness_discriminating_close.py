"""Close matched negative-control diagnostic, with no Reviewer/R4 credit."""

import argparse
import copy
import json

import harness_r4_dto_audit as M
import reviewer_discriminating_status as D


def close(used):
    D.P.audit()
    B, rows, payloads = D.B, [], {}
    reg = B.read(D.BATCH / "registration.json")
    for path, sha in B.read(D.BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(__import__("pathlib").Path(path)) == sha
    expected = B.read(D.BATCH / "judge.json")["statuses"]
    for row in reg["cells"]:
        cell = D.BATCH / "cells" / row["id"]
        result = B.read(cell / "result.json")
        calls = M.calls(cell)
        assert len(calls) == 1
        body = B.read(cell / "wire" / calls[0]["request"])["body"]
        assert (
            body["messages"] == B.read(cell / "messages.json")
            and body["tools"] == D.TOOLS
        )
        statuses = (
            [r["status"] for r in result["parsed"]["arguments"]["predictions"]]
            if result["parsed"]
            else None
        )
        rows.append(
            {
                **result,
                "wire": calls,
                "primary_adjudication": {
                    "correct": statuses == expected,
                    "basis": "None result is a recognized completion, repeated request resets to explicitly tested requested state, unknown id does not alter a. Inspected None/reset/unknown reasons for all cells.",
                },
            }
        )
        payloads.setdefault(row["arm"], []).append(body)
    for values in payloads.values():
        assert all(value == values[0] for value in values)
    blind, source = (
        copy.deepcopy(payloads["blind"][0]),
        copy.deepcopy(payloads["source"][0]),
    )
    before, after = [
        json.loads(body["messages"][1]["content"]) for body in (blind, source)
    ]
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
    B.save(D.BATCH / "grid-results.json", rows)
    B.save(
        D.BATCH / "matched-wire-audit.json",
        {
            "only_source_field_differs": True,
            "one_rpc_per_cell": True,
            "constant_predictor_negative_control": True,
        },
    )
    B.save(
        D.BATCH / "decision.json",
        {
            "qualification": "PASS_COMPONENT"
            if all(g["correct"] == 4 for g in groups)
            else "HOLD",
            "groups": groups,
            "registered": 8,
            "executed": len(rows),
            "not_run": 0,
            "r4_passed": False,
            "reviewer_passed": False,
            "production_promoted": False,
            "new_holdout_credit": False,
            "weekly_used": used,
            "usage_ceiling": 50,
            "conclusion": "This Muse profile can derive these contractual states in a narrow prediction task, including discriminating negative cases, with or without unreviewed source. No causal source-presence penalty observed. Broader REPORT failure does not prove absent raw semantic capability; task framing/composition remains an implementation hypothesis.",
            "next": "One frozen contract-first Reviewer candidate, no oracle: archive untrusted source-blind model predictions, compare its explicit claims mechanically with actual facts, keep final source-backed REPORT mandatory. Shared original16/4/600 budget, same model, no production/handoff change. Original16/16 and exposed4/4 must pass before new R4 transfers.",
        },
    )
    print(groups)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
