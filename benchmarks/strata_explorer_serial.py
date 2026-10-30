"""Serialize bounded read-only native batches through the existing executor."""

import io
import json
import os
from collections import deque
from pathlib import Path

import strata_explorer_trial as E
import strata_model_entry as MODEL
from strata_entry import guard

ORIGINAL_PATCH = MODEL.patch


def read_batch(calls):
    if not isinstance(calls, list) or not 2 <= len(calls) <= 4:
        raise ValueError("Expected two to four read-only tool calls")
    actions = []
    for call in calls:
        function = call.get("function", {})
        name = function.get("name")
        if name not in {"READ_FILE", "SEARCH", "LIST_FILES"}:
            raise ValueError("Only read-only tools can be serialized")
        raw = function.get("arguments")
        arguments = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be an object")
        actions.append({"action": name, "arguments": arguments})
    return actions


def patch(module, config):
    ORIGINAL_PATCH(module, config)
    pending = deque()
    original_open = module.urllib.request.urlopen
    request_class = module.urllib.request.Request
    base = module.LMStudioClient
    batches = 0

    def urlopen(req, *args, **kwargs):
        nonlocal batches
        if not isinstance(req, request_class) or not req.full_url.endswith(
            "/chat/completions"
        ):
            return original_open(req, *args, **kwargs)
        body = json.loads(req.data)
        body["parallel_tool_calls"] = False
        adjusted = request_class(
            req.full_url,
            data=json.dumps(body).encode(),
            headers=dict(req.header_items()),
            method=req.get_method(),
        )
        with original_open(adjusted, *args, **kwargs) as r:
            raw = r.read()
        response = json.loads(raw)
        message = response["choices"][0]["message"]
        calls = message.get("tool_calls", [])
        if len(calls) > 1:
            actions = read_batch(
                calls
            )  # validate whole batch before dispatching even the first
            pending.extend(actions[1:])
            batches += 1
            from bounded import capture_fixture_support as F

            state = F.load(
                Path.cwd() / ".local-agents/run-state.py", "strata_batch_state"
            )
            state.write_json_once(
                Path.cwd()
                / ".agent/strata-wire"
                / f"{os.getpid()}-batch-{batches}.json",
                {
                    "calls": calls,
                    "actions": actions,
                    "order": "original order, sequential original executor",
                    "permission_granted": False,
                    "report_batch_allowed": False,
                },
            )
            message["tool_calls"] = calls[:1]
            message["content"] = None
        return io.BytesIO(json.dumps(response).encode())

    module.urllib.request.urlopen = urlopen

    class SerialReadClient(base):
        def complete(self, messages):
            if pending:
                guard(
                    self.model,
                    self.context_length,
                    config["experimental_strata_instance_id"],
                )
                action = pending.popleft()
                self.last_request_stats = {
                    "model": self.model,
                    "strata_queued_read": True,
                    "provider_requests": 0,
                    "pending_read_actions": len(pending),
                }
                return json.dumps(action)
            result = super().complete(messages)
            self.last_request_stats["provider_requests"] = 1
            self.last_request_stats["pending_read_actions"] = len(pending)
            return result

    module.LMStudioClient = SerialReadClient


if __name__ == "__main__":
    E.BATCH = E.S.KIT / "benchmarks/work/harness-convergence/strata-explorer-20261023-2"
    E.ENTRY = Path(__file__).resolve()
    a = E.argparse.ArgumentParser()
    a.add_argument("mode", choices=["prepare", "run", "worker"])
    a.add_argument("--cell", choices=E.TASKS)
    a.add_argument("--weekly-used", type=int, required=True)
    args = a.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if args.mode == "prepare":
        E.prepare(args.weekly_used)
        E.S.save(
            E.BATCH / "protocol-amendment.json",
            {
                "candidate": "Max4 read-only tool calls serialized in original order through unchanged Explorer executor; send parallel_tool_calls=false",
                "budget": "Every queued action still consumes an original Explorer turn/read/search credit; actual provider requests counted separately in wire logs. No new role or permission.",
                "gate": "Same two frozen questions and evidence gate; prior0/2 retained. Invalid or mixed read/report/write batches rejected before dispatch.",
                "pins": {
                    str(Path(E.__file__)): E.S.sha(E.__file__),
                    str(
                        Path(__file__).parents[1] / "tests/test_strata_read_batch.py"
                    ): E.S.sha(
                        Path(__file__).parents[1] / "tests/test_strata_read_batch.py"
                    ),
                },
            },
        )
    elif args.mode == "worker":
        MODEL.patch = patch
        raise SystemExit(E.worker(args))
    else:
        amendment = E.S.read(E.BATCH / "protocol-amendment.json")
        assert all(E.S.sha(p) == h for p, h in amendment["pins"].items())
        E.run(args.cell, args.weekly_used)
