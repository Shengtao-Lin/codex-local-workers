"""Audit conditional recovery without converting completed false passes to success."""

import argparse
import copy
from pathlib import Path

import harness_conditional_recovery as H
import harness_r4_dto_audit as M
import harness_reviewer_stage_close as C


def close(used):
    C.close(
        H,
        {
            "sample-17-candidate": (
                "semantic_false_pass_after_recovery",
                "Known-call None result remains requested, while frozen contract requires exact result and succeeded. The low recovery passes after listing False/0/empty containers but omits the supplied None case. Valid REPORT and source quotes do not establish semantic correctness.",
            )
        },
        used,
        "identical-first-request",
        "Keep conditional recovery unpromoted. A separate observation-accounting candidate may require explicit model judgments for every actual observation and reject omitted or self-contradictory reports, without host-inferred expected values, prompt additions, new execution authority or budget increases. No new holdouts/R5 yet.",
    )
    B, rows = H.B, []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        cell = root.parent
        accounting = list(root.rglob("bounded-request-accounting.json"))
        assert len(accounting) == 1
        facts = B.read(accounting[0])
        calls = M.calls(cell)
        assert len(calls) == facts["actual_requests"] <= 16
        assert facts["shared_error_budget_used"] <= 4
        if facts["output_limit_failures"]:
            assert facts["output_limit_failures"] == 1 and len(calls) == 2
            first, recovery = [
                B.read(cell / "wire" / c["request"])["body"] for c in calls
            ]
            changed = copy.deepcopy(recovery)
            assert changed["tool_choice"] == "required"
            changed["tool_choice"] = first["tool_choice"]
            assert "Reasoning strength: low." in changed["messages"][0]["content"]
            changed["messages"][0]["content"] = changed["messages"][0][
                "content"
            ].replace("strength: low.", "strength: medium.")
            from reviewer_bounded_recovery import NUDGE

            assert changed["messages"][-1]["content"].endswith(NUDGE)
            changed["messages"][-1]["content"] = changed["messages"][-1]["content"][
                : -len(NUDGE)
            ]
            assert changed == first
        rows.append({"id": row["id"], **facts})
    B.save(
        H.BATCH / "recovery-audit.json",
        {
            "cells": rows,
            "requests": sum(r["actual_requests"] for r in rows),
            "first_request_completed": 18,
            "recovery_attempted": 2,
            "recovery_reports_completed": 2,
            "recovery_reports_semantically_correct": 1,
            "recovery_false_passes": 1,
            "uncapped_sample02_advice_now_correct": True,
            "causality_caveat": "Uncapped first request unchanged, so its advice variation is not attributable to low recovery.",
            "sample20_quality_note": "Core None/update finding and bounded fix correct. Its extra claim about preserve-input/fresh-result semantics is overbroad: the None guard alone does not violate those properties; do not adopt that rationale.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
