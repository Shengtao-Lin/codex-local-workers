"""Observe effective sampling without changing prompts, schemas or review gates."""

import argparse
import importlib.util
import sys
from pathlib import Path


def install(reviewer):
    original = reviewer.ReviewerRuntime.run

    def run(runtime):
        complete = runtime.client.complete

        def observed(messages):
            runtime.event(
                "sampling_probe",
                {
                    key: getattr(runtime.client, key, None)
                    for key in (
                        "model",
                        "temperature",
                        "top_p",
                        "top_k",
                        "min_p",
                        "repeat_penalty",
                        "max_tokens",
                        "native_tool_choice",
                    )
                },
            )
            return complete(messages)

        runtime.client.complete = observed
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
        "sampling_probe_reviewer", args.snapshot / ".local-agents/reviewer-runtime.py"
    )
    reviewer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reviewer
    spec.loader.exec_module(reviewer)
    install(reviewer)
    sys.argv = ["reviewer-runtime.py", *remaining]
    raise SystemExit(reviewer.main())
