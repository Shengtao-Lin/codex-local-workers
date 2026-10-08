"""Bounded paired Reviewer context-recovery development comparison."""

import hashlib
import json
import subprocess
import sys
import time

from capability_fit import WORK, write


def main():
    base = WORK / "roleq-context-comparison-1"
    base.mkdir(exist_ok=False)
    snapshot = WORK / "roleq-context-candidate-1"
    frozen = json.loads((snapshot / "freeze.json").read_text(encoding="utf-8"))
    # Use the same candidate binary for both arms; only the opt-in flag differs.
    for relative, digest in frozen["files"].items():
        if hashlib.sha256((snapshot / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("snapshot drift: " + relative)
    cells = [("hidden", False), ("hidden", True), ("clean", True), ("clean", False)]
    write(
        base / "plan.json",
        {
            "feature_id": "reviewer-visible-context-recovery",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "contracts": [
                "citation-authority-unchanged",
                "bounded-source-restoration",
                "qualification-before-coordinator",
            ],
            "risk_rationale": "Changes reviewer loop continuation; citation, scope and acceptance gates must remain intact.",
            "snapshot": str(snapshot),
            "cells": cells,
            "classification": "Known-family development comparison; four fresh review contexts, not qualification",
            "single_axis": "reviewer_context_recovery false/true",
            "criterion": "Inspect causal findings, clean false positives, and actual recovery events. No activation means no efficacy claim.",
            "models_sampling_prompts_unchanged": True,
            "coordinator_started": False,
            "weekly_ceiling": 40,
        },
    )
    for variant, enabled in cells:
        root = (
            WORK / "roleq-six-1/reviewer-controls" / f"window-groups-{variant}-r1-low"
        )
        label = f"{variant}-{'on' if enabled else 'off'}"
        config = json.loads((root / ".agent/config.json").read_text(encoding="utf-8"))
        config["reviewer_context_recovery"] = enabled
        request = json.loads((root / ".agent/request.json").read_text(encoding="utf-8"))
        request["review_id"] = "context-comparison-1-" + label
        config_path, request_path = (
            base / f"{label}-config.json",
            base / f"{label}-request.json",
        )
        write(config_path, config)
        write(request_path, request)
        started = time.monotonic()
        result = subprocess.run(
            [
                sys.executable,
                str(snapshot / ".local-agents/local-review.py"),
                "--request",
                str(request_path),
                "--config",
                str(config_path),
                "--report",
                str(base / f"{label}-report.json"),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
        events_path = (
            root
            / ".agent/tasks"
            / request["task_id"]
            / "reviews"
            / request["review_id"]
            / "events.jsonl"
        )
        events = (
            [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            if events_path.exists()
            else []
        )
        record = {
            "label": label,
            "exit_code": result.returncode,
            "seconds": round(time.monotonic() - started, 2),
            "context_restorations": sum(
                e["event"] == "read_context_restored" for e in events
            ),
            "events_path": str(events_path),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "primary_accepted": False,
            "coder_calls": 0,
        }
        write(base / f"{label}-result.json", record)
        print(
            json.dumps(
                {k: v for k, v in record.items() if k not in {"stdout", "stderr"}}
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
