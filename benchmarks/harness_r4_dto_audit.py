"""Post-live observational audit only; never edits a frozen candidate or result."""

import json

import harness_r4_dto as D

B = D.B


def calls(cell):
    result = []
    for path in sorted((cell / "wire").glob("*-request.json")):
        request = B.read(path)
        if not request.get("url", "").endswith("/chat/completions"):
            continue
        response = B.read(path.with_name(path.name.replace("-request", "-response")))
        payload = json.loads(response["raw"])
        message = payload["choices"][0]["message"]
        actions = []
        for tool in message.get("tool_calls", []):
            function = tool["function"]
            actions.append(
                {
                    "action": function["name"],
                    "arguments": json.loads(function["arguments"]),
                }
            )
        if not actions:
            try:
                action = json.loads(message.get("content", ""))
                actions.append(
                    action if isinstance(action, dict) else {"action": "non_object"}
                )
            except json.JSONDecodeError:
                actions.append({"action": "non_json"})
        result.append(
            {
                "request": path.name,
                "request_sha256": B.sha(path),
                "actions": actions,
                "usage": payload.get("usage", {}),
                "finish_reason": payload["choices"][0]["finish_reason"],
                "seconds": response["seconds"],
            }
        )
    return result


def metrics(batch):
    rows = []
    for row in B.read(batch / "registration.json")["cells"]:
        cell = batch / "cells" / row["id"]
        if not (cell / "result.json").exists():
            continue
        wire = calls(cell)
        result, report = B.read(cell / "result.json"), B.read(cell / "reviewer.json")
        rows.append(
            {
                "id": row["id"],
                "decision": report.get("decision"),
                "chat_completions": len(wire),
                "cell_seconds": result["seconds"],
                "prompt_tokens": sum(c["usage"].get("prompt_tokens", 0) for c in wire),
                "completion_tokens": sum(
                    c["usage"].get("completion_tokens", 0) for c in wire
                ),
                "maximum_prompt_tokens": max(
                    c["usage"].get("prompt_tokens", 0) for c in wire
                ),
                "protocol_errors_if_reported": report.get("runtime_facts", {}).get(
                    "protocol_error_count"
                ),
            }
        )
    return {
        "cells": rows,
        "totals": {
            key: sum(row[key] for row in rows)
            for key in (
                "chat_completions",
                "cell_seconds",
                "prompt_tokens",
                "completion_tokens",
            )
        },
        "maximum_prompt_tokens": max(row["maximum_prompt_tokens"] for row in rows),
    }


def main():
    cell = D.BATCH / "cells/required-coverage-r1"
    wire = calls(cell)
    last = B.read(cell / "wire" / wire[-1]["request"])
    observations = [
        json.loads(message["content"].split("\n", 1)[1])
        for message in last["body"]["messages"]
        if message["role"] == "user" and message["content"].startswith("OBSERVATION\n")
    ]
    test = cell / "isolated/tests/test_target.py"
    raw = test.read_bytes()
    trace = {
        "case": "required-coverage-r1",
        "actions": wire,
        "observations_before_last_action": observations,
        "test": {
            "bytes": len(raw),
            "lines": len(raw.decode().splitlines()),
            "sha256": B.sha(test),
        },
        "report_attempts": sum(
            a.get("action") == "REPORT" for c in wire for a in c["actions"]
        ),
        "total_lines_exposed_by_read": any("total_lines" in o for o in observations),
        "eof_exposed_by_read": any("eof" in o or "at_eof" in o for o in observations),
        "interpretation": "Observed navigation/noncompletion failure, not an invalid REPORT rejection. Missing explicit EOF/total-lines metadata is a testable interface hypothesis, not proven root cause or permission to auto-pass.",
        "counterfactual_live_success": "not_tested",
    }
    assert trace["test"]["lines"] == 5 and trace["report_attempts"] == 0
    assert all(c["finish_reason"] != "length" for c in wire)
    B.save(D.BATCH / "failure-observation-audit.json", trace)
    comparison = {"old": metrics(D.OLD.BATCH), "candidate": metrics(D.BATCH)}
    comparison["caveat"] = (
        "Sequential fixed controls, not randomized same-time causal proof. Local LM token usage is not Codex usage or Primary active time. Include every failure."
    )
    B.save(D.BATCH / "protocol-cost-comparison.json", comparison)
    print(
        {
            key: value["totals"]
            for key, value in comparison.items()
            if isinstance(value, dict)
        }
    )


if __name__ == "__main__":
    main()
