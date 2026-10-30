"""Optional host-only pure counting and single-use request/usage binding."""

import json
import subprocess
import time
from pathlib import Path

from general_state import BudgetExhausted, StateError, fingerprint
from strata_artifacts import save


def preflight(host, body):
    profile = host.config.get("strata_token_counter")
    if not profile or body.get("model") != "iq3_s" or body.get("max_tokens") != 12288:
        raise StateError("Unapproved token counter/model route")
    whole_job = bool(host.ledger.state.get("budget_profile"))
    request_cap = host.ledger.current()["limits"]["model_requests"] if whole_job else 16
    if host.ledger.state["used"]["model_requests"] >= request_cap:
        raise BudgetExhausted("model_requests exhausted before token preflight")
    number = host.ledger.state.get("token_preflights", 0) + 1
    # Selected task requests plus the existing2 shared context rebuilds.
    # Legacy/readonly profiles retain their original pure-counting quota.
    if number > (host.ledger.limits["model_requests"] + 2 if whole_job else 18):
        raise BudgetExhausted("Pure token preflight quota exhausted")
    host.ledger.state["token_preflights"] = number
    host.ledger.state["counted_request"] = None
    host.ledger.record("token_preflight_reserved")
    identity = host.identity()
    archive = host.archive.run_root
    save(archive / f"token-preflight-request-{number}.json", {"identity": identity, "body": body})
    start = time.monotonic()
    try:
        result = subprocess.run(
            [
                profile["python"],
                "-I",
                "-B",
                str(Path(__file__).with_name("general_token_counter.py")),
            ],
            input=json.dumps({"profile": profile, "bodies": [body]}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=min(15, max(0.01, host.ledger.remaining_seconds())),
            cwd=host.repo_root,
            check=False,
        )
        if result.returncode:
            raise ValueError("Counter process failed: " + result.stderr[-2000:])
        value = json.loads(result.stdout)["input_tokens"]
        if len(value) != 1 or type(value[0]) is not int or value[0] < 1:
            raise ValueError("Invalid token count")
        count = value[0]
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        save(
            archive / f"token-preflight-result-{number}.json",
            {"error": str(exc), "seconds": time.monotonic() - start},
        )
        raise StateError("Token preflight failed closed: " + str(exc)) from exc
    host.guard()
    receipt = {
        "identity": identity,
        "number": number,
        "body_sha256": fingerprint(body),
        "input_tokens": count,
        "framing_reserve": 4096,
        "output_tokens": 12288,
        "context_limit": 65536,
        "within_bound": count + 4096 + 12288 <= 65536,
        "seconds": time.monotonic() - start,
    }
    save(archive / f"token-preflight-result-{number}.json", receipt)
    host.ledger.state["counted_request"] = receipt
    host.ledger.record("token_preflight_settled")
    return {"kind": "native_context_counted", **receipt}


def consume_receipt(host, body):
    receipt = host.ledger.state.get("counted_request")
    if (
        not receipt
        or receipt["identity"] != host.identity()
        or receipt["body_sha256"] != fingerprint(body)
        or not receipt["within_bound"]
    ):
        raise StateError("Missing/current counted-body context receipt")
    host.ledger.state["counted_request"] = None
    host.ledger.state["pending_input_tokens"] = receipt["input_tokens"]


def verify_provider_usage(host, value):
    expected = host.ledger.state.pop("pending_input_tokens", None)
    if expected is None:
        raise StateError("Missing pending token count")
    if value.get("error") or value.get("status") != 200:
        raise StateError("Provider did not complete counted request")
    try:
        raw = value["body"]
        if raw.lstrip().startswith("{"):
            observed = [json.loads(raw)["usage"]["input_tokens"]]
        else:
            events = [
                json.loads(line[6:]) for line in raw.splitlines() if line.startswith("data: ")
            ]
            observed = [
                e["message"]["usage"]["input_tokens"]
                for e in events
                if e.get("type") == "message_start"
            ]
        if len(observed) != 1 or type(observed[0]) is not int or observed[0] != expected:
            raise ValueError("Actual provider input count differs from preflight")
    except (ValueError, KeyError, TypeError) as exc:
        raise StateError("Provider token attestation failed before tools: " + str(exc)) from exc
    host.ledger.record("provider_token_count_matched", {"input_tokens": expected})
