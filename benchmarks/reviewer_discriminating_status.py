"""Add negative state controls and unchanged visible tests to the matched probe."""

import argparse
import ast
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import reviewer_contract_status_probe as P
import reviewer_observation_probe as OBS

B = P.B
CONTROL = P.BATCH
BATCH = CONTROL.parent / "r4-discriminating-status-20261017-2"
TOOLS = copy.deepcopy(P.TOOLS)
ARRAY = TOOLS[0]["function"]["parameters"]["properties"]["predictions"]
ARRAY["minItems"] = ARRAY["maxItems"] = 8
ARRAY["items"]["properties"]["case_index"]["maximum"] = 7
TOOLS[0]["function"]["description"] = (
    "Predict contractual terminal status of target_call_id for each provided sequence, not current implementation behavior."
)


def negative_cases(tests):
    test = next(
        n
        for n in ast.parse(tests).body
        if isinstance(n, ast.FunctionDef)
        and n.name == "test_repeated_request_replaces_value_without_reordering"
    )
    assignment = next(
        n
        for n in test.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "messages" for t in n.targets)
    )
    message = assignment.value.elts[0]
    if (
        not isinstance(message, ast.Call)
        or not isinstance(message.func, ast.Name)
        or message.func.id != "message"
    ):
        raise ValueError("unexpected approved test fixture")
    kinds, parts = {"ToolCallPart": "tool_call", "ToolResultPart": "tool_result"}, []
    for expr in message.args:
        if (
            not isinstance(expr, ast.Call)
            or not isinstance(expr.func, ast.Name)
            or expr.func.id not in kinds
            or expr.args
            or any(k.arg is None for k in expr.keywords)
        ):
            raise ValueError(
                "approved fixture must use fixed keyword-only data constructors"
            )
        parts.append(
            {
                "type": kinds[expr.func.id],
                **{kw.arg: ast.literal_eval(kw.value) for kw in expr.keywords},
            }
        )
    request = {
        "cases": [
            {"parts": parts},
            {
                "parts": copy.deepcopy(parts)
                + [{"type": "tool_result", "call_id": "unrecognized", "result": None}]
            },
        ]
    }
    OBS.validate_request(request)
    assert (
        parts[0]["call_id"] == "a"
        and parts[-1]["type"] == "tool_call"
        and parts[-1]["call_id"] == "a"
    )
    return request


def validate(raw):
    action = json.loads(raw)
    if (
        not isinstance(action, dict)
        or set(action) != {"action", "arguments"}
        or action["action"] != "PREDICT_STATUS"
    ):
        raise ValueError("requires PREDICT_STATUS")
    args = action["arguments"]
    if (
        not isinstance(args, dict)
        or set(args) != {"predictions"}
        or not isinstance(args["predictions"], list)
        or len(args["predictions"]) != 8
    ):
        raise ValueError("requires exactly eight predictions")
    for i, row in enumerate(args["predictions"]):
        if (
            not isinstance(row, dict)
            or set(row) != {"case_index", "status", "reason"}
            or type(row["case_index"]) is not int
            or row["case_index"] != i
            or row["status"] not in {"requested", "succeeded", "failed", "unknown"}
            or not isinstance(row["reason"], str)
            or not row["reason"].strip()
            or len(row["reason"]) > 400
        ):
            raise ValueError("invalid prediction shape")
    return action


def prepare(used):
    assert 0 <= used < 50
    P.audit()
    assert B.read(CONTROL / "decision.json")["qualification"] == "PASS_NARROW"
    BATCH.mkdir(exist_ok=False)
    prior = B.read(CONTROL / "registration.json")
    root = Path(prior["origin_root"])
    tests_path = root / "tests/test_collect_tools.py"
    tests = tests_path.read_text(encoding="utf-8-sig")
    negative_request = negative_cases(tests)
    negatives = negative_request["cases"]
    # Execute only fixed Primary data through the existing approved reference snapshot.
    # These actual outcomes and the judge are never put in a model prompt.
    with patch.object(OBS, "BATCH", BATCH):
        observed = OBS.execute(
            "sample-18-candidate",
            negative_request,
            BATCH / "offline-negative-observations",
        )
    assert all(
        o["outcome"]["value"][0]["call_id"] == "a" for o in observed["observations"]
    )
    negative_statuses = [
        o["outcome"]["value"][0]["status"] for o in observed["observations"]
    ]
    assert negative_statuses == ["requested", "requested"]
    rows = []
    for old in prior["cells"]:
        messages = B.read(CONTROL / "cells" / old["id"] / "messages.json")
        content = json.loads(messages[1]["content"])
        content["approved_acceptance_tests"] = tests
        content["event_sequences"].extend(
            {"case_index": 6 + i, "input": case} for i, case in enumerate(negatives)
        )
        for sequence in content["event_sequences"]:
            sequence["target_call_id"] = "a"
        messages[1]["content"] = json.dumps(content, ensure_ascii=False)
        cell = BATCH / "cells" / old["id"]
        B.save(cell / "messages.json", messages)
        rows.append({**old, "messages_sha256": B.sha(cell / "messages.json")})
    B.save(
        BATCH / "judge.json",
        {
            "statuses": ["succeeded"] * 6 + negative_statuses,
            "basis": "Recognized results including None succeed. Exact repeated-request fixture explicitly asserts requested; an unrecognized result cannot change it. Negatives come from that approved test, not guessed initial-state behavior. Reference observations confirm. Not model input.",
        },
    )
    B.save(
        BATCH / "registration.json",
        {
            **prior,
            "feature_id": "discriminating-contract-status-probe",
            "weekly_used_start": used,
            "cells": rows,
            "visible_test_source": str(tests_path),
            "visible_test_sha256": B.sha(tests_path),
            "criterion": "Each arm separately4/4, every call all8 statuses correct with consistent reasons. Source absence/presence is the only within-batch axis. Constant succeeded predictor must fail. No full Reviewer/R4/holdout credit.",
            "enhancement_from_prior": "Negatives are extracted from the existing visible repeated-request test (explicit requested assertion). Verbatim visible tests and target_call_id query supplied to both arms. Avoid under-specified initial-state expectations. No causal comparison of old versus new accuracy.",
            "dependencies": [str(CONTROL / "decision.json")],
            "next_if_pass": "Only then consider a contract-first staged Reviewer candidate, sharing original16 requests/4 errors/600-second total; do not auto-adopt this predictor as truth or acceptance.",
        },
    )


def freeze():
    tree = ET.parse(BATCH / "controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("failure", "error", "skipped")
    )
    paths = [
        Path(__file__),
        B.KIT / "tests/test_reviewer_discriminating_status.py",
        BATCH / "registration.json",
        BATCH / "judge.json",
        BATCH / "controls.xml",
        CONTROL / "decision.json",
    ]
    paths.extend((BATCH / "cells").rglob("messages.json"))
    paths.extend((BATCH / "offline-negative-observations").glob("*.json"))
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(CONTROL / "live-freeze.json")["pins"],
                **{str(p): B.sha(p) for p in paths},
            }
        },
    )


def run(name, used):
    P.audit()
    with (
        patch.object(P, "BATCH", BATCH),
        patch.object(P, "TOOLS", TOOLS),
        patch.object(P, "validate", validate),
    ):
        P.run(name, used)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "run"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
