"""Diagnostic only: one-shot task-local semantic judgment, never an acceptance gate."""

import argparse
import ast
import json
import time
from pathlib import Path

import harness_terms_continuation as C

H, B = C.H, C.B
BATCH = H.BATCH.parent / "r4-review-semantic-probe-20261016-1"
SYSTEM = "Review whether the supplied implementation satisfies the hard contract. Give concrete source-backed reasoning. Passing tests alone do not prove all inputs. Use REPORT once; no edits or further tools. This is a semantic diagnostic, not final project acceptance.\nReasoning: low"
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "REPORT",
            "description": "Report the semantic judgment of the supplied implementation against its contract.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verdict": {
                        "type": "string",
                        "enum": ["satisfies", "violates", "uncertain"],
                    },
                    "explanation": {"type": "string", "minLength": 1},
                },
                "required": ["verdict", "explanation"],
                "additionalProperties": False,
            },
        },
    }
]


def extract(source, symbol):
    tree = ast.parse(source)
    node = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == symbol
    )
    return ast.get_source_segment(source, node)


def prepare(used):
    assert 0 <= used < 45
    assert B.read(H.BATCH / "decision.json")["qualification"] == "HOLD"
    C.audit()
    BATCH.mkdir(exist_ok=False)
    # All four source instances are already exposed. Counterbalance order, no retry.
    origins = ["cell-02", "cell-04", "cell-05", "cell-07"]
    registration = B.read(H.BATCH / "registration.json")["cells"]
    rows = []
    for i, origin in enumerate(origins, 1):
        prior = next(r for r in registration if r["id"] == origin)
        root = Path(prior["root"])
        cell = BATCH / "cells" / f"probe-{i:02}"
        config = B.read(root / ".agent/experiment-config.json")
        packet = B.read(root / ".agent/packet.json")
        run = root / ".agent/tasks/semantic-terms/runs" / prior["identity"]["run_id"]
        evidence = {
            "hard_contract": packet["required_behavior"],
            "implementation": extract(
                (root / H.TARGET).read_text(encoding="utf-8"), "collect_tools"
            ),
            "dependency_declarations": config["coder_single_function"]["dependencies"],
            "focused_tests": (root / "tests/test_collect_tools.py").read_text(
                encoding="utf-8"
            ),
            "actual_cumulative_diff": (run / "cumulative.diff").read_text(
                encoding="utf-8"
            ),
        }
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
        ]
        B.save(cell / "messages.json", messages)
        rows.append(
            {
                "id": cell.name,
                "origin": origin,
                "origin_root": str(root),
                "implementation": prior["implementation"],
                "expected": "violates"
                if prior["implementation"] == "draft"
                else "satisfies",
                "messages_sha256": B.sha(cell / "messages.json"),
            }
        )
    B.save(
        BATCH / "registration.json",
        {
            "cells": rows,
            "registered": 4,
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "feature_id": "reviewer-task-local-semantic-upper-bound",
            "weekly_used_start": used,
            "usage_ceiling": 45,
            "budget": "one completion per cell, original 4096 output maximum and 180s request timeout; no repair",
            "no_acceptance_or_holdout_credit": True,
            "joint_intervention": "Task-local upfront evidence plus two-field one-shot report replaces navigation/full workflow and assessment taxonomy. Diagnostic cannot isolate these changes or establish a production-ready candidate.",
            "criterion": "All four correct, including causal detection of None update/status loss in both defective sources and no invented defect in either reference. Otherwise HOLD; no resampling.",
            "model_and_sampling": "Unchanged Muse and frozen reviewer sampling; single residency",
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")
    )
    B.save(
        BATCH / "live-freeze.json",
        {
            "pins": {
                str(p): B.sha(p)
                for p in (
                    Path(__file__),
                    B.KIT / "tests/test_reviewer_semantic_probe.py",
                    BATCH / "registration.json",
                    BATCH / "controls.xml",
                )
            }
        },
    )


def run(name, used):
    assert 0 <= used < 45
    C.audit()
    for path, sha in B.read(BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == sha
    rows = B.read(BATCH / "registration.json")["cells"]
    row = next(r for r in rows if r["id"] == name)
    for old in rows[: rows.index(row)]:
        assert not B.read(BATCH / "cells" / old["id"] / "result.json")["infra_failure"]
    cell, root = BATCH / "cells" / name, Path(row["origin_root"])
    assert B.sha(cell / "messages.json") == row["messages_sha256"]
    B.save(
        cell / "started.json",
        {"weekly_used": used, "at": time.time(), "no_retry": True},
    )
    config = B.read(root / ".agent/experiment-config.json")
    worker = H.R.load(root / ".local-agents/worker-runtime.py", "semantic_probe_worker")
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["reviewer_model"],
        config["model_request_timeout_seconds"],
        max_tokens=config["reviewer_max_tokens"],
        temperature=config["reviewer_temperature"],
        top_p=config["reviewer_top_p"],
        top_k=config["reviewer_top_k"],
        min_p=config["reviewer_min_p"],
        repeat_penalty=config["reviewer_repeat_penalty"],
        structured_output=False,
        native_tools=TOOLS,
        context_length=config["reviewer_context_length"],
        context_safety_margin=config["model_context_safety_margin"],
    )
    start = time.monotonic()
    raw, parsed, error, infra = None, None, None, False
    try:
        with worker.MODEL_RESIDENCY.role_model_lease(client, config):
            raw = client.complete(B.read(cell / "messages.json"))
        parsed = worker.parse_action(raw)
        assert parsed["action"] == "REPORT"
        assert set(parsed["arguments"]) == {"verdict", "explanation"}
        assert parsed["arguments"]["verdict"] in {"satisfies", "violates", "uncertain"}
        assert (
            isinstance(parsed["arguments"]["explanation"], str)
            and parsed["arguments"]["explanation"].strip()
        )
    except (
        worker.WorkerError,
        AssertionError,
        KeyError,
        TypeError,
        ValueError,
        OSError,
    ) as exc:
        error = repr(exc)
        infra = raw is None
    B.save(
        cell / "result.json",
        {
            "id": name,
            "raw": raw,
            "parsed": parsed,
            "error": error,
            "infra_failure": infra,
            "seconds": time.monotonic() - start,
            "request_stats": client.last_request_stats,
            "primary_adjudication": "pending",
        },
    )
    print(
        {"id": name, "parsed": parsed, "error": error, "infra_failure": infra},
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "freeze", "run"])
    p.add_argument("--case")
    p.add_argument("--used", type=int)
    args = p.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "freeze":
        freeze()
    else:
        run(args.case, args.used)
