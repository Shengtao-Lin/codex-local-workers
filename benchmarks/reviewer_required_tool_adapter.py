"""Prospective required-native transport only; no report or gate normalization."""

import argparse
import importlib.util
import sys
from pathlib import Path

from reviewer_sampling_probe_adapter import install as install_probe


def install(reviewer):
    original = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete

        def required(messages):
            choice = runtime.client.native_tool_choice
            tools = runtime.client.native_tools
            native = isinstance(tools, list) and bool(tools)
            if native:
                runtime.client.native_tool_choice = "required"
            runtime.event(
                "required_native_probe",
                {"native": native, "choice": runtime.client.native_tool_choice},
            )
            try:
                return complete(messages)
            finally:
                runtime.client.native_tool_choice = choice

        runtime.client.complete = required
        try:
            return original(runtime)
        finally:
            runtime.client.complete = complete

    reviewer.ReviewerRuntime.run = run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    spec = importlib.util.spec_from_file_location(
        "required_native_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    install_probe(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
