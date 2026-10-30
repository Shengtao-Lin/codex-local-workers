"""Exposed contract regression: add a protected counterexample, not a repair hint."""

import argparse
import os
from pathlib import Path

import strata_model_trial as MODEL

S, J, P, FIRST = MODEL.S, MODEL.J, MODEL.P, MODEL.FIRST
BATCH = P.I.BASE / "strata-boundary-20261023-2"
ORIGINAL_TASKS = J.TASKS.tasks
BOUNDARY = """
class FalseyInteger(int):
    def __bool__(self) -> bool:
        return False

@pytest.mark.parametrize("value", [FalseyInteger(0), FalseyInteger(7)])
def test_falsey_int_subclass_keeps_legacy_fallback(value):
    payload = {"id": value, "message_id": "fallback"}
    assert stable_message_id("trace", 1, payload) == "fallback"
    assert payload["id"] is value
"""


def tasks():
    specs = ORIGINAL_TASKS()
    specs["message"]["public"] = J.TASKS.join_test_sources(
        specs["message"]["public"], BOUNDARY
    )
    return specs


def save(path, value):
    path = Path(path)
    if path == BATCH / "preparation.json":
        value = {
            **value,
            "authorization": "Autonomous isolated continuation; weekly used stop40%; no production or sibling writes",
            "exposure": "Known falsey-int counterexample added to protected public tests before live. Contract unchanged. Test-assisted exposed regression, not holdout or unassisted new-task credit.",
            "Primary": "One-time test coverage repair from independently confirmed defect; no algorithm supplied or mid-run semantic hints. Preparation cost separate from runtime intervention.",
        }
    if path == BATCH / "registration.json":
        value = {
            **value,
            "registered": 4,
            "exposure": "Same four original project cells and starts; message now includes two protected falsey-int subclass tests. Explicit test assistance; hash repeats are unchanged controls, not new independent tasks.",
            "difference": "Only protected test coverage expands for an already explicit built-in-integer contract. Same Strata thinking-v1 profile, entry, editing/check/review budgets and Primary acceptance.",
            "gate": "4/4 fresh Reviewer plus independent full-project tests/statics and full Primary review, zero protected drift; scoped exposed regression only. Any defect HOLD; retain all remaining cells for diagnosis unless safety/infrastructure/usage stops.",
            "not_claimed": "No general E/C/R release, unknown-boundary Reviewer reliability, causal context improvement or cloud savings; earlier2/4 remains unchanged.",
        }
        value["pins"][str(Path(__file__))] = S.sha(__file__)
    return MODEL.save(path, value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=J.ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    assert args.weekly_used < 40
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    MODEL.BATCH = FIRST.BATCH = BATCH
    FIRST.ENTRY = MODEL.ENTRY
    FIRST.configure()
    FIRST.ORIGINAL_SAVE = save
    J.TASKS.tasks = tasks
    if args.mode == "prepare":
        J.prepare(args.weekly_used)
    else:
        row = S.read(BATCH / "cells.json")[args.cell]
        P.TARGET = row["target"]
        P.run(args.cell, args.weekly_used)
