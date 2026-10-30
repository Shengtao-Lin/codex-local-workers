"""Explicit IQ3_S thinking profile around the unmodified installed harness."""

import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

import strata_entry as ENTRY

PATCH = ENTRY.patch_worker


def request_body(body, thinking_budget):
    if (
        type(thinking_budget) is not int
        or not 1 <= thinking_budget < body["max_tokens"]
    ):
        raise ValueError("Thinking budget must leave positive final-output capacity")
    return {**body, "reasoning_budget_tokens": thinking_budget}


def patch(worker, config):
    PATCH(worker, config)
    if getattr(worker, "_strata_thinking_profile", False):
        return
    if config.get("experimental_strata_model_profile") != "thinking-v1":
        raise ValueError("Explicit thinking-v1 profile required")
    original = worker.urllib.request
    sequence = 0

    def urlopen(req, *args, **kwargs):
        nonlocal sequence
        if (
            not isinstance(req, original.Request)
            or req.full_url != ENTRY.BASE + "/chat/completions"
        ):
            return original.urlopen(req, *args, **kwargs)
        body = request_body(
            json.loads(req.data), config["experimental_strata_thinking_tokens"]
        )
        sequence += 1
        archive = Path.cwd() / ".agent/strata-wire" / f"{os.getpid()}-{sequence}"
        from bounded import capture_fixture_support as F

        state = F.load(Path.cwd() / ".local-agents/run-state.py", "strata_wire_state")
        state.write_json_once(archive.with_suffix(".request.json"), body)
        adjusted = original.Request(
            req.full_url,
            data=json.dumps(body).encode(),
            headers=dict(req.header_items()),
            method=req.get_method(),
        )
        with original.urlopen(adjusted, *args, **kwargs) as response:
            data = response.read()
        state.write_json_once(archive.with_suffix(".response.json"), json.loads(data))
        return io.BytesIO(data)

    # Only this worker module sees the wrapper; global urllib is untouched.
    worker.urllib = SimpleNamespace(**vars(worker.urllib))
    worker.urllib.request = SimpleNamespace(**vars(original))
    worker.urllib.request.urlopen = urlopen
    base = worker.LMStudioClient

    class ModelClient(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reasoning_effort = "medium"

        def complete(self, messages):
            result = super().complete(messages)
            self.last_request_stats["strata_thinking_budget"] = config[
                "experimental_strata_thinking_tokens"
            ]
            self.last_request_stats["wire_budget_injected"] = True
            return result

    worker.LMStudioClient = ModelClient
    worker._strata_thinking_profile = True


if __name__ == "__main__":
    ENTRY.patch_worker = patch
    ENTRY.__file__ = __file__  # Reviewer subprocess selects the same explicit adapter.
    raise SystemExit(ENTRY.main())
