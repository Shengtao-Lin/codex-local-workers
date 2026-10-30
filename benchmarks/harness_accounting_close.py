"""Close the coverage experiment; count false factual explanations as failures."""

import argparse
from pathlib import Path

import harness_observation_accounting as H
import harness_reviewer_stage_close as C


def close(used):
    C.close(
        H,
        {
            "sample-17-candidate": (
                "input_event_presence_misread",
                "Correct source None-guard finding, but observation0 incorrectly says no result part is present. Frozen actual input contains a ToolResultPart(result=None); explicit coverage exists but the factual explanation is wrong. Count complete report as failure, distinguish correct top-level defect finding.",
            ),
            "sample-20-candidate": (
                "implementation_as_normative_reference",
                "False pass. Observation0 explicitly says null leaves requested and calls it consistent because it matches implementation. Frozen contract requires recognized result events to set succeeded. Actual behavior was read, but implementation conformity was substituted for contract conformity.",
            ),
        },
        used,
        "observation-schema",
        "Repair experimental input loss before any more semantic tuning: recover complete typed event input from original sealed request, preserving actual outputs/source/contracts/tests/schema/recovery/budget. One separate fixed input-representation contrast; no expected outcomes or new execution. If omission was not causal, record that rather than declaring model incapacity.",
    )
    B, rows = H.B, []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        root = Path(row["root"])
        paths = list(root.rglob("bounded-request-accounting.json"))
        assert len(paths) == 1
        accounting = B.read(paths[0])
        report = B.read(root.parent / "reviewer.json")
        assert (
            accounting["actual_requests"] <= 16
            and accounting["shared_error_budget_used"] <= 4
        )
        assert len(report["observation_assessments"]) in {3, 4, 6, 7}
        rows.append(
            {
                "id": row["id"],
                **accounting,
                "observation_judgments": report["observation_assessments"],
            }
        )
    B.save(
        H.BATCH / "observation-audit.json",
        {
            "cells": rows,
            "requests": sum(r["actual_requests"] for r in rows),
            "first_request_output_caps": sum(
                r["output_limit_failures"] > 0 for r in rows
            ),
            "report_quality": {"original": "16/16", "real": "2/4"},
            "top_level_judgment_real": "3/4",
            "all_twenty_reports_completed": True,
            "hypothesis_not_proven": "Compact result_input:null may obscure event presence; full typed input contrast needed. Existing shared_setup did state a following result, so input compaction is not yet a proven cause.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
