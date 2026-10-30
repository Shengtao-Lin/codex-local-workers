"""Reuse the frozen recovery runner, now including actual configured failures."""

import argparse
import ast
import json
from pathlib import Path

import checked_research_pair as PAIR

S, T, P = PAIR.S, PAIR.T, PAIR.P
BATCH = P.I.BASE / "checked-static-research-20261022-1"
OLD = P.I.BASE / "usage-completion-transfer-20261022-1"
ORDER = ["usage-1", "usage-2"]
QUESTION = (
    "Which current implementation statement explains the remaining configured-check "
    "failures in src/product/failure.txt? Read the archived executed check facts, the "
    "complete token_usage function and protected helpers in src/product/code.py, and "
    "tests/test_contract.py. Explain the actual check failure and suggest a minimal "
    "in-scope correction preserving the unchanged original contract and passing "
    "behavior. Cite actual source/test/failure lines and state uncertainty. Read-only "
    "research, no edits, no claimed execution, no new requirements or broader audit."
)


def prepare(used):
    assert S.read(OLD / "decision.json")["status"] == "HOLD_STATIC_REPAIR_NO_PROGRESS"
    first = S.read(OLD / "cells.json")[ORDER[0]]
    source = (Path(first["root"]) / "src/product/code.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = tree.body[-1]
    assert isinstance(target, ast.FunctionDef) and target.name == "token_usage"
    P.HEADER = "\n".join(source.splitlines()[: target.lineno - 1]) + "\n"
    P.SYMBOL = target.name
    P.REFERENCE = T.extract(
        OLD / "reference-checks/usage/src/product/code.py", target.name
    )
    original_read, original_save = S.read, S.save

    def read(path):
        value = original_read(path)
        if Path(path).name == "validation.json" and Path(path).is_relative_to(
            OLD / "cells"
        ):
            # Append separately labelled real commands/results. Never alter any
            # archive, test, contract, output string or expected-result oracle.
            checks = [
                {
                    k: c[k]
                    for k in ("id", "argv", "status", "exit_code", "output")
                    if k in c
                }
                for c in value.get("configured_checks", [])
                if c.get("status") == "failed"
            ]
            value["focused_tests"]["output"] += (
                "\nSEPARATELY EXECUTED CONFIGURED CHECK FACTS (not pytest output):\n"
                + json.dumps(checks, ensure_ascii=False, indent=2)
            )
        return value

    def save(path, value):
        if Path(path) == BATCH / "registration.json":
            value.update(
                feature_id="checked-static-local-research",
                question="Can the same one-shot local diagnostic path resolve a static-only repair stall without Primary supplying the correction?",
                exposure="Two already-exposed usage drafts with the same AST and failure, differing in comments. Repeated recovery trials, not distinct tasks or independent mechanisms.",
                candidate="Same checked_research_pair runner/binding/remaining credits. Evidence file additionally carries exact failed configured command/result records, explicitly distinguished from public pytest output.",
                dependencies=[
                    "usage-completion-transfer-20261022-1",
                    "checked-research-transfer-20261022-1",
                ],
                coder_budget="Each parent+child12requests/3edits/3write checks/12preparations/2protocol recovery/900loop seconds;2child edits remain. Two initial checks explicitly, one per invocation.",
                gate="Both trials need source-supported causal research, complete child checks, unchanged original Reviewer and Primary final acceptance. Otherwise HOLD; no additional recovery calls.",
                Primary_cost="No specific repair/type narrowing advice supplied by Primary. Mechanical original check transfer only; preparation and final review remain cloud/active-time costs, unknown quantities.",
            )
            value["pins"][str(Path(__file__))] = S.sha(__file__)
        original_save(path, value)

    S.read, S.save = read, save
    try:
        PAIR.prepare(used)
    finally:
        S.read, S.save = original_read, original_save


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    PAIR.BATCH, PAIR.OLD, PAIR.ORDER, PAIR.QUESTION = BATCH, OLD, ORDER, QUESTION
    prepare(args.weekly_used) if args.mode == "prepare" else PAIR.run(args.weekly_used)
