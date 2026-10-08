"""One paired hidden/clean development comparison of native Reviewer history."""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

from capability_fit import WORK, write
from inherited_context_recovery import digest, read
from native_history_adapter import paired_history

BASE = WORK / "roleq-reviewer-native-history-1"
SNAPSHOT = WORK / "roleq-native-wire-candidate-1"
ORDER = ("hidden-off", "hidden-on", "clean-on", "clean-off")


def install(worker):
    original = worker.LMStudioClient.complete

    def complete(client, messages):
        issued = getattr(client, "_paired_native_actions", set())
        adapted = (
            paired_history(messages, issued)
            if client.native_tools is not None
            else messages
        )
        raw = original(client, adapted)
        client.last_request_stats["paired_native_tool_results"] = sum(
            m.get("role") == "tool" for m in adapted
        )
        if client.last_request_stats.get("native_tool_call"):
            action = json.loads(raw)
            if action.get("action") == client.last_request_stats["native_tool_call"]:
                issued.add(raw)
                client._paired_native_actions = issued
        return raw

    worker.LMStudioClient.complete = complete


def prepare():
    BASE.mkdir(exist_ok=False)
    cells = []
    for label in ORDER:
        variant, _arm = label.split("-")
        root = (
            WORK / "roleq-six-1/reviewer-controls" / f"window-groups-{variant}-r1-low"
        )
        request = read(root / ".agent/request.json")
        request["review_id"] = "paired-history-1-" + label
        config = read(root / ".agent/config.json")
        config.update(
            reviewer_context_retention="budgeted", reviewer_context_recovery=False
        )
        write(BASE / (label + "-request.json"), request)
        write(BASE / (label + "-config.json"), config)
        cells.append(
            {
                "label": label,
                "root": str(root),
                "hashes": {
                    str(p.relative_to(root)): digest(p)
                    for p in (root / "src").rglob("*.py")
                },
                "request_sha256": digest(BASE / (label + "-request.json")),
                "config_sha256": digest(BASE / (label + "-config.json")),
            }
        )
    write(
        BASE / "manifest.json",
        {
            "feature_id": "native-review-history",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Read-only transport changes must preserve authority, source citations, actual validation and independent judgment",
            "contracts": ["read-only", "citation-authority", "no-automatic-acceptance"],
            "cells": cells,
            "order": ORDER,
            "reviewer_calls_max": 4,
            "retries": 0,
            "classification": "Known-family development comparison, not new qualification; adjudicate causal defect and compatible suggested fix, not report validity alone",
            "axis": "Native assistant/tool history only; same source/packet/prompts/model/sampling/context and native tool schema",
            "coordinator_started": False,
            "weekly_used_ceiling": 60,
            "drivers": {
                str(p): digest(p)
                for p in [
                    Path(__file__),
                    Path(__file__).with_name("native_history_adapter.py"),
                ]
            },
        },
    )


def run(label):
    manifest = read(BASE / "manifest.json")
    for p, sha in manifest["drivers"].items():
        if digest(Path(p)) != sha:
            raise ValueError("driver drift")
    for p, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / p) != sha:
            raise ValueError("snapshot drift")
    cell = next(c for c in manifest["cells"] if c["label"] == label)
    root = Path(cell["root"])
    for p, sha in cell["hashes"].items():
        if digest(root / p) != sha:
            raise ValueError("source drift")
    for suffix in ("request", "config"):
        if digest(BASE / f"{label}-{suffix}.json") != cell[suffix + "_sha256"]:
            raise ValueError("request/config drift")
    write(BASE / (label + "-started.json"), {"at": time.time()})
    spec = importlib.util.spec_from_file_location(
        "paired_reviewer", SNAPSHOT / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    if label.endswith("-on"):
        install(reviewer.WORKER)
    sys.argv = [
        "local-review.py",
        "--request",
        str(BASE / (label + "-request.json")),
        "--config",
        str(BASE / (label + "-config.json")),
        "--report",
        str(BASE / (label + "-report.json")),
    ]
    import os

    os.chdir(root)
    started = time.monotonic()
    exit_code = reviewer.main()
    write(
        BASE / (label + "-result.json"),
        {
            "exit_code": exit_code,
            "seconds": time.monotonic() - started,
            "primary_accepted": False,
        },
    )
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", *ORDER))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        raise SystemExit(run(args.action))
