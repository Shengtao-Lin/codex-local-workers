"""Frozen exposed Reviewer semantic controls; diagnostic, not acceptance."""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import bounded_evidence_support as S
from strata_probe import environment

BASE = S.KIT / "benchmarks/work/harness-convergence"
BATCH = BASE / "strata-review-diagnostic-20261023-1"
OLD = BASE / "r4-review-semantic-probe-20261016-1"
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["satisfies", "violates", "uncertain"]},
        "explanation": {"type": "string"},
    },
    "required": ["verdict", "explanation"],
    "additionalProperties": False,
}


def register(used):
    assert used < 40 and not BATCH.exists()
    old = S.read(OLD / "registration.json")
    rows = []
    for row in old["cells"]:
        path = OLD / "cells" / row["id"] / "messages.json"
        assert S.sha(path) == row["messages_sha256"]
        messages = S.read(path)
        messages[0]["content"] = (
            "Review whether the supplied implementation satisfies the hard contract. "
            "Give concrete source-backed reasoning. Passing tests alone do not prove all inputs. "
            "Return JSON with verdict (satisfies, violates, uncertain) and explanation. "
            "No edits or further tools. This is a semantic diagnostic, not final project acceptance."
        )
        target = BATCH / row["id"] / "messages.json"
        S.save(target, messages)
        rows.append(
            {
                "id": row["id"],
                "expected": row["expected"],
                "messages_sha256": S.sha(target),
            }
        )
    S.save(
        BATCH / "registration.json",
        {
            "order": [r["id"] for r in rows],
            "rows": rows,
            "registered": 4,
            "purpose": "Two already-exposed correct/defective collect_tools implementations, two repeats each; no holdout credit",
            "source": str(OLD),
            "model": "Same resident IQ3_S, medium reasoning, temperature1/top_p.95/top_k20",
            "budget": "Exactly one request per cell, max12288 total output/4096 thinking/600s; no resampling",
            "gate": "4/4 right verdicts; defective explanation must identify ignored None result/status loss; correct implementations no invented defect. Primary manually scores explanation.",
            "continue": "Ordinary judgment errors finish fixed batch; infrastructure/residency/safety/budget halts. No code/acceptance rights.",
            "limits": "Upfront complete source diagnostic, not the installed Reviewer protocol, not independent full-chain qualification or cloud savings",
            "weekly_used": used,
            "weekly_stop": 40,
            "pins": {str(Path(__file__)): S.sha(__file__)},
        },
    )
    print("Four semantic control requests registered; zero live")


def run(cell, used):
    assert used < 40
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    row = next(r for r in reg["rows"] if r["id"] == cell)
    for previous in reg["order"][: reg["order"].index(cell)]:
        assert "error" not in S.read(BATCH / previous / "result.json")
    messages = BATCH / cell / "messages.json"
    assert S.sha(messages) == row["messages_sha256"]
    S.save(BATCH / cell / "environment.json", environment())
    body = {
        "model": "iq3_s",
        "messages": S.read(messages),
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "repeat_penalty": 1.0,
        "reasoning_effort": "medium",
        "reasoning_budget_tokens": 4096,
        "max_tokens": 12288,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "semantic_diagnostic",
                "strict": True,
                "schema": SCHEMA,
            },
        },
    }
    S.save(BATCH / cell / "request.json", body)
    start = time.monotonic()
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:47831/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            response = json.load(r)
        S.save(BATCH / cell / "response.json", response)
        answer = json.loads(response["choices"][0]["message"]["content"])
        result = {
            "answer": answer,
            "verdict_matches": answer.get("verdict") == row["expected"],
            "finish_reason": response["choices"][0].get("finish_reason"),
            "usage": response.get("usage"),
            "seconds": time.monotonic() - start,
            "Primary_explanation_review": "PENDING",
        }
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        result = {"error": str(exc), "seconds": time.monotonic() - start}
        if isinstance(exc, urllib.error.HTTPError):
            result["body"] = exc.read().decode(errors="replace")
    S.save(BATCH / cell / "result.json", result)
    print(json.dumps({"cell": cell, **result}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["register", "run"])
    parser.add_argument(
        "--cell", choices=["probe-01", "probe-02", "probe-03", "probe-04"]
    )
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "register":
        register(args.weekly_used)
    else:
        run(args.cell, args.weekly_used)
