"""Two fixed calibration calls on the failed frozen input; no code application."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import bounded_evidence_support as S
from strata_probe import environment

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-output-20261023-1"
ORIGIN = (
    S.KIT
    / "benchmarks/work/harness-convergence/strata-project-20261023-1/cells/message-1/isolated/.agent/tasks/strata-project-20261023-1-message-1/runs/strata-project-20261023-1-message-1/proposal-request-1.json"
)
ORDER = ["raw-low", "schema-capped"]


def run(mode, cell, used):
    assert used < 40
    if mode == "register":
        assert not BATCH.exists()
        S.save(
            BATCH / "registration.json",
            {
                "order": ORDER,
                "registered": 2,
                "purpose": "Output allocation/transport only, no implementation acceptance",
                "origin": str(ORIGIN),
                "origin_sha256": S.sha(ORIGIN),
                "pins": {str(Path(__file__)): S.sha(__file__)},
                "model": "same loaded IQ3_S, low thinking, existing Coder sampling, max_tokens4096",
                "differences": {
                    "raw-low": "omit response_format to retain raw reasoning/final content",
                    "schema-capped": "original strict schema with reasoning_budget_tokens1024",
                },
                "budget": "2 requests total, each4096 output/180s; no implicit retries or code writes",
                "weekly_used": used,
                "weekly_stop": 40,
            },
        )
        print("Registered two output calibration requests")
        return
    reg = S.read(BATCH / "registration.json")
    assert S.sha(ORIGIN) == reg["origin_sha256"]
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    if cell == ORDER[1]:
        assert (BATCH / ORDER[0] / "result.json").exists()
    sys.path.insert(0, str(S.KIT / ".local-agents"))
    from bounded import tagged_wire as wire

    request = {
        "model": "iq3_s",
        "messages": S.read(ORIGIN)["messages"],
        "temperature": 0.1,
        "top_p": 0.9,
        "top_k": 40,
        "min_p": 0.0,
        "repeat_penalty": 1.0,
        "reasoning_effort": "low",
        "max_tokens": 4096,
        "stream": False,
    }
    if cell == "schema-capped":
        request["reasoning_budget_tokens"] = 1024
        request["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "consolidated_proposal_v1",
                "strict": True,
                "schema": wire.SCHEMA,
            },
        }
    S.save(BATCH / cell / "environment.json", environment())
    S.save(BATCH / cell / "request.json", request)
    started = time.monotonic()
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:47831/v1/chat/completions",
            data=json.dumps(request).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as r:
            response = json.load(r)
        S.save(BATCH / cell / "response.json", response)
        choice = response["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""
        try:
            proposal = wire.decode(content)
            parsed = True
            kind = "replacement" if "replacement" in proposal else "blocked"
        except (ValueError, TypeError, KeyError):
            parsed, kind = False, None
        result = {
            "finish_reason": choice.get("finish_reason"),
            "parsed": parsed,
            "proposal_kind": kind,
            "content_chars": len(content),
            "reasoning_chars": len(
                message.get("reasoning_content") or message.get("reasoning") or ""
            ),
            "usage": response.get("usage"),
            "seconds": time.monotonic() - started,
        }
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        body = (
            exc.read().decode(errors="replace")
            if isinstance(exc, urllib.error.HTTPError)
            else None
        )
        result = {
            "error": str(exc),
            "body": body,
            "seconds": time.monotonic() - started,
        }
    S.save(BATCH / cell / "result.json", result)
    print(json.dumps({"cell": cell, **result}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["register", "run"])
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    a = p.parse_args()
    run(a.mode, a.cell, a.weekly_used)
