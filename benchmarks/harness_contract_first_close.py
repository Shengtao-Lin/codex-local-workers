"""Qualify only this frozen exposed diagnostic; R4 migration gate remains open."""

import argparse
import json
from pathlib import Path

import harness_contract_first as H
import harness_r4_dto_audit as M
import harness_reviewer_stage_close as C


def close(used):
    C.close(
        H,
        {},
        used,
        "contract-first",
        "Frozen exposed diagnostic passed, not R4. Keep candidate unchanged. Before new three-task/two-repeat/two-arm full-chain matrix, add only offline-proven input transport for actual canonical observation capture: current fixed source-version table is not portable. Prefer a trusted validation-profile capture command, source/epoch binding and actual stdout, no expected outcomes, same material for baseline. Do not change production runtime/handoff or use exposed collect_tools as a new holdout. No new live until transport/install controls and fresh fixtures are frozen.",
    )
    B, rows = H.B, []
    for row in B.read(H.BATCH / "registration.json")["cells"]:
        root, cell = Path(row["root"]), Path(row["root"]).parent
        budget_paths = list(root.rglob("contract-first-budget.json"))
        assert len(budget_paths) == 1
        budget = B.read(budget_paths[0])
        report = B.read(cell / "reviewer.json")
        wire = M.calls(cell)
        assert (
            len(wire)
            == budget["actual_requests"]
            == report["reviewer_model_calls"]
            <= 16
        )
        assert (
            budget["shared_error_budget_used"] <= 4
            and budget["invocation_timeout"] == 600
        )
        assert budget["output_limit_failures"] <= 1
        assert len(report["observation_assessments"]) in {3, 4, 6, 7}
        if row["group"] == "exposed-real":
            normative = B.read(next(root.rglob("normative-input.json")))
            assert set(normative) == {
                "hard_contract",
                "dependency_declarations",
                "approved_acceptance_tests",
                "event_sequences",
            }
            assert "unreviewed_implementation" not in normative
            assert (
                len(report["model_contract_predictions"]) == 6
                and report["normative_model_calls"] == 1
            )
        else:
            assert (
                report["model_contract_predictions"] == []
                and report["normative_model_calls"] == 0
            )
        for profile, call in zip(budget["request_profiles"], wire, strict=True):
            body = B.read(cell / "wire" / call["request"])["body"]
            assert body["temperature"] == 0 and body["max_tokens"] == 4096
            assert body["tool_choice"] == profile["tool_choice"]
            strength = "low" if profile["fallback_active"] else "medium"
            assert (
                "Reasoning strength: " + strength + "."
                in body["messages"][0]["content"]
            )
            assert body["tools"][0]["function"]["name"] == (
                "PREDICT_STATUS"
                if profile["stage"] == "contract_prediction"
                else "REPORT"
            )
        for claim in report["model_contract_predictions"]:
            case = claim["case_index"]
            observation = report["observation_assessments"][case]
            mismatch = (
                claim["model_claimed_required_status"] != claim["observed_status"]
            )
            assert observation["verdict"] == ("violation" if mismatch else "consistent")
        rows.append({"id": row["id"], **budget})
    B.save(
        H.BATCH / "whole-call-budget-audit.json",
        {
            "cells": rows,
            "total_requests": sum(r["actual_requests"] for r in rows),
            "normative_requests": sum(
                p["stage"] == "contract_prediction"
                for r in rows
                for p in r["request_profiles"]
            ),
            "output_caps_retained": sum(r["output_limit_failures"] for r in rows),
            "original_total_limits_unchanged": True,
            "first_source_report_matches_control_except_model_predictions": True,
            "joint_intervention_not_isolated_causal_effect": True,
            "sample17_uncertainty_retained": "Model still questions None wording while explicitly confirming the real defect. Existing confirmed-defect routing retained; no claim of perfectly resolved model confidence or general semantic reliability.",
        },
    )
    current = M.metrics(H.BATCH)
    previous = B.read(H.CONTROL / "metrics.json")
    for metric in (current, previous):
        assert metric["cells"]
    B.save(
        H.BATCH / "observational-cost-comparison.json",
        {
            "previous_real_seconds": sum(
                r["cell_seconds"]
                for r in previous["cells"]
                if int(r["id"].split("-")[1]) >= 17
            ),
            "current_real_seconds": sum(
                r["cell_seconds"]
                for r in current["cells"]
                if int(r["id"].split("-")[1]) >= 17
            ),
            "caveat": "Known exposed snapshots, pinned prior controls, different execution order and extra prediction phase; not randomized concurrent timing evidence or a production saving. Primary active time and cloud tokens unmeasured.",
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print(
        json.dumps(
            {
                "diagnostic": "PASS",
                "r4": "HOLD",
                "requests": sum(r["actual_requests"] for r in rows),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
