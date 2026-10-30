"""Matched normative-status probe, not a Reviewer acceptance path."""

import argparse
import ast
import copy
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_typed_observations as H
import reviewer_observed_facts as REAL

B, R = H.B, H.R
BATCH = H.BATCH.parent / "r4-contract-status-20261017-1"
SYSTEM = "Predict the terminal status REQUIRED BY THE HARD CONTRACT for each supplied event sequence. Use PREDICT_STATUS. Unreviewed implementation, when present, is context, not the specification. Explain each prediction briefly. Reasoning strength: medium."
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "PREDICT_STATUS",
            "description": "Predict contractual terminal status, not current implementation behavior.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["predictions"],
                "properties": {
                    "predictions": {
                        "type": "array",
                        "minItems": 6,
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["case_index", "status", "reason"],
                            "properties": {
                                "case_index": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 5,
                                },
                                "status": {
                                    "type": "string",
                                    "enum": [
                                        "requested",
                                        "succeeded",
                                        "failed",
                                        "unknown",
                                    ],
                                },
                                "reason": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 400,
                                },
                            },
                        },
                    }
                },
            },
        },
    }
]
ORDER = ["blind", "source", "source", "blind", "blind", "source", "source", "blind"]


def validate(raw):
    action = json.loads(raw)
    if (
        not isinstance(action, dict)
        or set(action) != {"action", "arguments"}
        or action["action"] != "PREDICT_STATUS"
    ):
        raise ValueError("requires PREDICT_STATUS action")
    args = action["arguments"]
    if (
        not isinstance(args, dict)
        or set(args) != {"predictions"}
        or not isinstance(args["predictions"], list)
        or len(args["predictions"]) != 6
    ):
        raise ValueError("requires exactly six predictions")
    for i, row in enumerate(args["predictions"]):
        if (
            not isinstance(row, dict)
            or set(row) != {"case_index", "status", "reason"}
            or type(row["case_index"]) is not int
            or row["case_index"] != i
            or row["status"] not in {"requested", "succeeded", "failed", "unknown"}
            or not isinstance(row["reason"], str)
            or not row["reason"].strip()
            or not 1 <= len(row["reason"]) <= 400
        ):
            raise ValueError("invalid prediction identity/status/reason")
    return action


def prepare(used):
    assert 0 <= used < 50
    H.audit()
    assert B.read(H.BATCH / "decision.json")["qualification"] == "HOLD"
    row = B.read(H.BATCH / "registration.json")["cells"][16]
    root = Path(row["root"])
    R.assert_files(root, row["files"])
    config = B.read(root / ".agent/experiment-config.json")
    binding = config["coder_single_function"]
    source = (root / binding["path"]).read_text(encoding="utf-8-sig")
    node = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == binding["symbol"]
    )
    code = ast.get_source_segment(source, node)
    seal = B.read(REAL.SEAL)
    old = next(
        s
        for s in seal["sources"]
        if s["source_manifest"][REAL.OBS.TARGET] == B.sha(root / binding["path"])
    )
    request = B.read(Path(old["request"]))
    REAL.OBS.validate_request(request)
    packet_path = next((root / ".agent/tasks").rglob("packet.json"))
    packet = B.read(packet_path)
    evidence = {
        "hard_contract": packet["required_behavior"],
        "dependency_declarations": binding["dependencies"],
        "event_sequences": [
            {"case_index": i, "input": case} for i, case in enumerate(request["cases"])
        ],
    }
    BATCH.mkdir(exist_ok=False)
    rows = []
    for i, arm in enumerate(ORDER, 1):
        content = copy.deepcopy(evidence)
        if arm == "source":
            content["unreviewed_implementation"] = code
        cell = BATCH / "cells" / f"cell-{i:02}"
        B.save(
            cell / "messages.json",
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ],
        )
        rows.append(
            {
                "id": cell.name,
                "arm": arm,
                "messages_sha256": B.sha(cell / "messages.json"),
            }
        )
    B.save(
        BATCH / "judge.json",
        {
            "statuses": ["succeeded"] * 6,
            "basis": "Owned contract requires every recognized ToolResultPart to set succeeded, regardless of exact result. All six frozen inputs contain a recognized result event. This file is never supplied to the model.",
        },
    )
    B.save(
        BATCH / "registration.json",
        {
            "feature_id": "contract-interpretation-source-anchoring-diagnostic",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "owned_contract_ids": [
                "matched-normative-question",
                "no-oracle-input",
                "no-execution-or-acceptance",
                "fixed-budget",
            ],
            "weekly_used_start": used,
            "usage_ceiling": 50,
            "cells": rows,
            "registered": 8,
            "origin_root": str(root),
            "origin_files": row["files"],
            "source_sha256": B.sha(root / binding["path"]),
            "budget": {
                "requests_per_cell": 1,
                "max_tokens": 4096,
                "timeout_seconds": 180,
                "repair": 0,
            },
            "sampling": {
                "model": config["reviewer_model"],
                "temperature": 0,
                "top_p": config["reviewer_top_p"],
                "top_k": config["reviewer_top_k"],
                "min_p": config["reviewer_min_p"],
                "repeat_penalty": config["reviewer_repeat_penalty"],
                "tool_choice": "auto",
                "context_length": 24576,
            },
            "axis": "Only unreviewed_implementation field present/absent. Same contract, typed input, system, native schema, sampling and one-call budget. Counterbalanced paired order.",
            "criterion": "Assess arms separately, four of four complete correct six-case predictions required for capability evidence. Never R4/Reviewer acceptance or new holdout credit. Do not combine denominators with old reports.",
            "decision_table": {
                "blind4_source_less4": "Evidence consistent with implementation anchoring in this matched task; consider contract-first staged harness.",
                "both4": "Contract status capability exists in narrow prediction task; broader review task framing/aggregation remains suspect. No causal source penalty observed.",
                "blind_less4": "Normative interpretation/completion not reliable in this profile; do not assume a contract-first harness will work.",
            },
            "production_or_handoff_modified": False,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )


def freeze():
    tree = ET.parse(BATCH / "controls-final.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("failure", "error", "skipped")
    )
    paths = [
        Path(__file__),
        B.KIT / "tests/test_reviewer_contract_status_probe.py",
        BATCH / "registration.json",
        BATCH / "judge.json",
        BATCH / "controls.xml",
        BATCH / "controls-final.xml",
        H.BATCH / "decision.json",
    ]
    paths.extend((BATCH / "cells").rglob("messages.json"))
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                **B.read(H.BATCH / "live-freeze.json")["pins"],
                **{str(p): B.sha(p) for p in paths},
            }
        },
    )


def audit():
    H.audit()
    for p, sha in B.read(BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(p)) == sha, p
    registration = B.read(BATCH / "registration.json")
    R.assert_files(Path(registration["origin_root"]), registration["origin_files"])


def run(name, used):
    assert 0 <= used < 50
    audit()
    registration = B.read(BATCH / "registration.json")
    row = next(r for r in registration["cells"] if r["id"] == name)
    for previous in registration["cells"][: registration["cells"].index(row)]:
        assert not B.read(BATCH / "cells" / previous["id"] / "result.json")[
            "infra_failure"
        ]
    cell, root = BATCH / "cells" / name, Path(registration["origin_root"])
    B.save(
        cell / "started.json",
        {"at": time.time(), "weekly_used": used, "no_retry": True},
    )
    config = B.read(root / ".agent/experiment-config.json")
    worker = R.load(root / ".local-agents/worker-runtime.py", "contract_status_worker")
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["reviewer_model"],
        timeout=180,
        max_tokens=4096,
        temperature=0,
        top_p=config["reviewer_top_p"],
        top_k=config["reviewer_top_k"],
        min_p=config["reviewer_min_p"],
        repeat_penalty=config["reviewer_repeat_penalty"],
        structured_output=False,
        native_tools=TOOLS,
        context_length=24576,
        context_safety_margin=1024,
    )
    start = time.monotonic()
    raw, parsed, error, infra = None, None, None, False
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            raw = client.complete(B.read(cell / "messages.json"))
        parsed = validate(raw)
    except (worker.WorkerError, ValueError, TypeError, KeyError, OSError) as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "reason_code": getattr(exc, "reason_code", None),
        }
        infra = (
            raw is None
            and error["reason_code"] != "output_token_limit"
            and "finish_reason" not in client.last_request_stats
        )
    audit()
    B.save(
        cell / "result.json",
        {
            "id": name,
            "arm": row["arm"],
            "raw": raw,
            "parsed": parsed,
            "error": error,
            "infra_failure": infra,
            "request_stats": client.last_request_stats,
            "seconds": time.monotonic() - start,
            "primary_adjudication": "pending",
        },
    )
    print(
        {
            "id": name,
            "arm": row["arm"],
            "statuses": [r["status"] for r in parsed["arguments"]["predictions"]]
            if parsed
            else None,
            "error": error,
            "infra_failure": infra,
        },
        flush=True,
    )


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
