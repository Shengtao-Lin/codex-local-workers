"""Read-only evidence audit and exclusive closeout of a completed fixed stage."""

import argparse
import copy
import importlib
import json
from pathlib import Path

import harness_r4_dto_audit as METRICS
from harness_semantic_close import REASONS


def first_body(driver, cell, action=None):
    calls = METRICS.calls(cell)
    assert calls
    for call in calls:
        body = driver.B.read(cell / "wire" / call["request"])["body"]
        if action is None or body["tools"][0]["function"]["name"] == action:
            return body
    raise AssertionError("requested phase has no actual wire request")


def compare_inputs(old, new, axis):
    old, new = copy.deepcopy(old), copy.deepcopy(new)
    if axis == "identical-first-request":
        pass
    elif axis == "temperature":
        assert old.pop("temperature") == 1 and new.pop("temperature") == 0
    elif axis == "canonical-policy":
        assert old["temperature"] == new["temperature"] == 0
        before = json.loads(old["messages"][1]["content"])
        after = json.loads(new["messages"][1]["content"])
        definitions = after.pop("verdict_definitions")
        assert len(definitions) == 5 and before == after
        old["messages"][1]["content"] = new["messages"][1]["content"] = (
            "normalized-identical-task-input"
        )
    elif axis == "observations":
        assert old["temperature"] == new["temperature"] == 0
        before = json.loads(old["messages"][1]["content"])
        after = json.loads(new["messages"][1]["content"])
        observations = after.pop("approved_observations")
        assert isinstance(observations, list) and before == after
        old["messages"][1]["content"] = new["messages"][1]["content"] = (
            "normalized-identical-task-input"
        )
    elif axis == "fixed-observations":
        assert old["temperature"] == new["temperature"] == 0
        before = json.loads(old["messages"][1]["content"])
        after = json.loads(new["messages"][1]["content"])
        assert isinstance(before.pop("approved_observations"), list)
        assert isinstance(after.pop("approved_observations"), list)
        assert before == after
        old["messages"][1]["content"] = new["messages"][1]["content"] = (
            "normalized-identical-task-input"
        )
    elif axis == "observation-schema":
        parameters = new["tools"][0]["function"]["parameters"]
        parameters["required"].remove("observation_assessments")
        assert parameters["properties"].pop("observation_assessments")
    elif axis == "typed-observation-input":
        before = json.loads(old["messages"][1]["content"])
        after = json.loads(new["messages"][1]["content"])
        for prior, changed in zip(
            before["approved_observations"], after["approved_observations"], strict=True
        ):
            if "shared_setup" not in prior:
                continue
            changed["shared_setup"] = prior["shared_setup"]
            for example in changed["examples"]:
                parts = example.pop("input")["parts"]
                assert len(parts) == 2 and parts[1]["type"] == "tool_result"
                example["result_input"] = parts[1]["result"]
        assert before == after
        old["messages"][1]["content"] = new["messages"][1]["content"] = (
            "normalized-identical-task-input"
        )
    elif axis == "contract-first":
        before = json.loads(old["messages"][1]["content"])
        after = json.loads(new["messages"][1]["content"])
        claims = after.pop("model_contract_prediction_review", None)
        if claims is not None:
            assert len(claims["claims"]) == 6
            assert all(
                "model_claimed_required_status" in c and "observed_status" in c
                for c in claims["claims"]
            )
        assert before == after
        old["messages"][1]["content"] = new["messages"][1]["content"] = (
            "normalized-identical-task-input"
        )
    else:
        raise AssertionError("unregistered comparison axis")
    assert old == new


def close(driver, errors, used, axis, next_action):
    driver.audit()
    B, grid, paired = driver.B, [], []
    for row in B.read(driver.BATCH / "registration.json")["cells"]:
        root, name = Path(row["root"]), row["id"]
        driver.R.assert_files(root, row["files"])
        driver.R.assert_files(Path(row["origin"]), row["origin_files"])
        for p, sha in row["same_session_control"].items():
            assert B.sha(Path(p)) == sha
        cell = root.parent
        report, result = B.read(cell / "reviewer.json"), B.read(cell / "result.json")
        assert not result["protected_drift"]
        correct = name not in errors
        failure, reason = errors.get(name, (None, REASONS[int(name.split("-")[1])]))
        if correct:
            assert result["observed"] == row["expected_decision"]
            assert not result["infra_failure"]
            assert report["runtime_facts"]["inputs_unchanged"]
        for contract in report.get("contract_review", []):
            for ref in contract.get("source_refs", []):
                source = root / ref["path"]
                lines = source.read_text(encoding="utf-8-sig").splitlines()
                assert (
                    "\n".join(lines[ref["start_line"] - 1 : ref["end_line"]])
                    == ref["canonical_quote"]
                )
                assert B.sha(source) == ref["source_hash"].removeprefix("sha256:")
        control = Path(next(iter(row["same_session_control"]))).parent
        compare_inputs(
            first_body(driver, control),
            first_body(driver, cell, "REPORT" if axis == "contract-first" else None),
            axis,
        )
        paired.append(
            {"id": name, "axis": axis, "other_first_wire_fields_identical": True}
        )
        grid.append(
            {
                **result,
                "report_sha256": B.sha(cell / "reviewer.json"),
                "primary_adjudication": {
                    "id": name,
                    "correct": correct,
                    "failure_class": failure,
                    "reason": reason,
                },
            }
        )
    groups = [
        {
            "group": g,
            "correct": sum(
                r["primary_adjudication"]["correct"] for r in grid if r["group"] == g
            ),
            "total": sum(r["group"] == g for r in grid),
        }
        for g in ("original-sixteen", "exposed-real")
    ]
    state = "PASS" if all(g["correct"] == g["total"] for g in groups) else "HOLD"
    B.save(
        driver.BATCH / "primary-adjudications.json",
        [r["primary_adjudication"] for r in grid],
    )
    B.save(driver.BATCH / "grid-results.json", grid)
    B.save(driver.BATCH / "matched-wire-audit.json", paired)
    B.save(driver.BATCH / "metrics.json", METRICS.metrics(driver.BATCH))
    B.save(
        driver.BATCH / "preservation.json",
        {
            "all_inputs_origins_and_controls_unchanged": True,
            "live_pins_unchanged": True,
            "original_runtime_and_old_decisions_unchanged": True,
            "sibling_writes": False,
        },
    )
    B.save(
        driver.BATCH / "decision.json",
        {
            "qualification": state,
            "registered": len(grid),
            "executed": len(grid),
            "not_run": 0,
            "groups": groups,
            "r4_passed": False,
            "production_promoted": False,
            "new_coder_or_holdout_credit": False,
            "weekly_used_start": B.read(driver.BATCH / "registration.json")[
                "weekly_used_start"
            ],
            "weekly_used": used,
            "usage_ceiling": 50,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "next": next_action,
        },
    )
    print(
        {"qualification": state, "groups": groups, "matched_first_inputs": len(paired)}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    args = parser.parse_args()
    close(
        importlib.import_module("harness_semantic_greedy"),
        {
            "sample-01-candidate": (
                "invented_required_test",
                "Correct dict.get implementation acknowledged; model invents mandatory empty/None/mutation tests from behavior scenarios. No explicit test-creation obligation; false rework.",
            ),
            "sample-09-candidate": (
                "invented_required_test",
                "Correct x+1 implementation acknowledged; model confuses negative behavior requirement with mandatory negative test. False rework, not a source defect.",
            ),
        },
        args.used,
        "temperature",
        "Close this sole decoding profile HOLD; restore the original formal category definitions lost in task-local rendering, first prove exact provenance and unchanged task facts offline, then one separate fixed policy candidate. No more sampling values.",
    )
