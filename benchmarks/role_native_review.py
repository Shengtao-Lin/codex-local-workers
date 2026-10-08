"""Exercise experimental native client through unchanged trusted Reviewer gates."""

import argparse
import importlib.util
import json
import sys

from capability_fit import WORK, write
from native_reasoning_client import build_client


def run(error_probe=False):
    base = WORK / (
        "roleq-native-error-probe-1" if error_probe else "roleq-native-review-1"
    )
    base.mkdir(exist_ok=False)
    snapshot = WORK / "roleq-six-runtime-1"
    spec = importlib.util.spec_from_file_location(
        "native_review_candidate", snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    write(
        base / "plan.json",
        {
            "classification": "Experimental transport/real reasoning compatibility, known cases not qualification",
            "model": "meta/muse-glimmer",
            "reasoning": "high",
            "cells": "hidden/clean each two fresh contexts, 4 maximum",
            "runtime_snapshot": str(snapshot),
            "unchanged_gates": True,
            "coordinator_started": False,
            "single_model_residency": True,
            "changes": [
                "native transport",
                "serialized role transcript",
                "plain JSON compatibility probe",
                "real reasoning request",
            ],
            "criterion": "Independent causal review plus compatible fixes and no clean false defects; do not attribute improvement to reasoning alone",
            "weekly_ceiling": 40,
        },
    )
    for repetition in (1,) if error_probe else (1, 2):
        for variant in ("hidden",) if error_probe else ("hidden", "clean"):
            root = (
                WORK
                / "roleq-six-1/reviewer-controls"
                / f"window-groups-{variant}-r{repetition}-low"
            )
            config = json.loads(
                (root / ".agent/config.json").read_text(encoding="utf-8")
            )
            config.update(
                reviewer_native_tools=False,
                reviewer_structured_output=False,
                reviewer_reasoning_strength="high",
            )
            request = json.loads(
                (root / ".agent/request.json").read_text(encoding="utf-8")
            )
            request["review_id"] = (
                "native-error-probe-1" if error_probe else "native-candidate-1"
            )
            write(
                root
                / (
                    ".agent/native-error-request-1.json"
                    if error_probe
                    else ".agent/native-request-1.json"
                ),
                request,
            )
            client = build_client(
                reviewer.WORKER,
                config["lmstudio_base_url"],
                config["reviewer_model"],
                reasoning="high",
                max_tokens=config["reviewer_max_tokens"],
                temperature=config["reviewer_temperature"],
                top_p=config["reviewer_top_p"],
                top_k=config["reviewer_top_k"],
                min_p=config["reviewer_min_p"],
                repeat_penalty=config["reviewer_repeat_penalty"],
                context_length=config["reviewer_context_length"],
            )
            try:
                with reviewer.WORKER.MODEL_RESIDENCY.role_model_lease(client, config):
                    runtime = reviewer.ReviewerRuntime(root, request, config, client)
                    report = runtime.run()
                record = {
                    "variant": variant,
                    "repetition": repetition,
                    "report": report,
                    "last_request_stats": client.last_request_stats,
                    "primary_accepted": False,
                }
            except reviewer.WORKER.WorkerError as error:
                record = {
                    "variant": variant,
                    "repetition": repetition,
                    "error": str(error),
                    "last_request_stats": client.last_request_stats,
                    "primary_accepted": False,
                }
            except reviewer.ReviewError as error:
                record = {
                    "variant": variant,
                    "repetition": repetition,
                    "error": str(error),
                    "last_request_stats": client.last_request_stats,
                    "primary_accepted": False,
                }
            write(base / f"{variant}-r{repetition}.json", record)
            print(json.dumps(record), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--error-probe", action="store_true")
    run(parser.parse_args().error_probe)
