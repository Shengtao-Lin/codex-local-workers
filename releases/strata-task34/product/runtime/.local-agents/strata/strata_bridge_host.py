"""Offline native tools -> unchanged installed host loop -> real checks/archive.

No new execution controller: client.complete yields one native action to the
existing Consolidated.run. Its next context/final report is the tool feedback.
No LLM or native fs/shell/SDK provider; existing capture profile stays mandatory.
"""

import argparse
import contextlib
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import strata_artifacts as S
from strata_subagent_rules import select


class NativeReplayClient:
    offline = True
    structured_output = True
    native_tools = None
    typed_action_arguments = False
    timeout = 180
    last_request_stats = None

    def __init__(self, program, worker):
        self.program = program
        self.worker = worker
        self.process = None
        self.frames = queue.Queue()
        self.done = False
        self.stderr = None

    def receive(self):
        try:
            remaining = max(1, self.runtime.deadline - time.monotonic() + 5)
            value = self.frames.get(timeout=min(self.timeout, remaining))
        except queue.Empty as exc:
            raise self.worker.WorkerError("Native frontend response timeout") from exc
        if not isinstance(value, dict):
            raise self.worker.WorkerError("Native frontend closed or malformed frame")
        if value.get("identity") != self.identity:
            raise self.worker.PolicyViolation("Native frontend identity differs")
        return value

    def send(self, value):
        try:
            self.process.stdin.write(
                json.dumps({**value, "identity": self.identity}) + "\n"
            )
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise self.worker.WorkerError("Native frontend exited early") from exc

    def start(self):
        r = self.runtime
        self.identity = {k: r.packet[k] for k in ("task_id", "unit_id", "run_id")}
        self.stderr = (r.archive.run_root / "native-stderr.log").open(
            "x", encoding="utf-8"
        )
        self.process = subprocess.Popen(
            [
                "F:/Strata/node/node.exe",
                str(Path(__file__).with_name("strata_native_replay.mjs")),
                str(self.program),
            ],
            cwd=r.repo_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            encoding="utf-8",
        )

        def read_frames():
            try:
                for line in self.process.stdout:
                    if len(line) > 2_000_000:
                        break
                    self.frames.put(json.loads(line))
            except (ValueError, OSError):
                pass
            finally:
                self.frames.put(None)

        threading.Thread(target=read_frames, daemon=True).start()

    def complete(self, _messages):
        r = self.runtime
        if self.process is None:
            self.start()
        context = {
            "source_sha256": r.editor.read_bytes(r.single_function["path"])[1],
            "resource_ledger": dict(r.ledger),
            "validation_status": r.validation.status,
            **r.evidence_window.state(),
        }
        self.send({"kind": "host_context", "context": context})
        value = self.receive()
        if value.get("kind") == "driver_done":
            self.done = True
            raise self.worker.WorkerError(
                "Native frontend ended before host completion"
            )
        if (
            set(value) != {"kind", "identity", "action", "arguments", "call_id"}
            or value["kind"] != "host_action"
        ):
            raise self.worker.PolicyViolation("Invalid native action envelope")
        r.RUN_STATE.write_json_once(
            r.archive.run_root / f"native-action-{r.ledger['requests']}.json", value
        )
        action, args = value["action"], value["arguments"]
        if not isinstance(args, dict):
            raise self.worker.PolicyViolation("Native arguments must be an object")
        if action in {"read", "search"}:
            expected = (
                {"path", "start_line", "end_line"}
                if action == "read"
                else {"path", "query"}
            )
            if set(args) != expected:
                raise self.worker.PolicyViolation("Exact evidence fields required")
            result = {"kind": action, **args}
        elif action == "propose":
            if set(args) != {"path", "expected_sha256", "content"}:
                raise self.worker.PolicyViolation("Exact proposal fields required")
            if args["path"] != r.single_function["path"]:
                raise self.worker.PolicyViolation(
                    "Native proposal outside approved target"
                )
            if args["expected_sha256"] != r.editor.read_bytes(args["path"])[1]:
                raise self.worker.PolicyViolation(
                    "Native proposal source version stale"
                )
            result = {"kind": "replacement", "content": args["content"]}
        elif action == "blocked" and set(args) == {"reason"}:
            result = {"kind": "blocked", "content": args["reason"]}
        else:
            raise self.worker.PolicyViolation("Unknown native action")
        return json.dumps(result)

    def finish(self, report, verified):
        if self.process is None:
            return
        if report["status"] == "interrupted":
            self.close()
            return
        try:
            if not self.done:
                self.send(
                    {
                        "kind": "host_terminal",
                        "status": report["status"],
                        "host_handoff_verified": verified,
                    }
                )
                value = self.receive()
                if value.get("kind") != "driver_done":
                    raise self.worker.WorkerError("Native frontend did not settle")
                self.runtime.RUN_STATE.write_json_once(
                    self.runtime.archive.run_root / "native-outcome.json", value
                )
            self.process.wait(timeout=10)
            if self.process.returncode != 0:
                raise self.worker.WorkerError("Native frontend exit failure")
        finally:
            self.close()

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()  # Only this entry's owned offline child.
                self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout):
                with contextlib.suppress(OSError, ValueError):
                    stream.close()
            self.process = None
        if self.stderr is not None:
            self.stderr.close()
            self.stderr = None


def main(*, client_type=NativeReplayClient, rules_selector=select):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--program", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F
    from bounded import compatibility_profile as COMPAT
    from bounded import consolidated_harness as H
    from bounded import static_focus_rules as RULES

    worker = F.load(root / ".local-agents/worker-runtime.py", "native_bridge_worker")

    def deny_network(*_args, **_kwargs):
        raise AssertionError("No network in offline native bridge")

    worker.urllib.request.urlopen = deny_network
    config = worker.load_json(args.config)
    if config.get("experimental_strata_subagent") is not True:
        raise ValueError("Explicit experimental subagent required")
    packet = worker.resolve_inherited_packet(root, worker.load_json(args.packet))
    rules = rules_selector(COMPAT.proposal_rules(config, RULES))
    client = client_type(args.program.resolve(), worker)
    client.action_schema = rules.SCHEMA
    runtime = H.make_runtime(worker, proposal_rules=rules)(root, packet, config, client)
    client.runtime = runtime
    try:
        F.preflight_material(runtime)
        runtime.preflight()
        report = runtime.run()
        verified = False
        if report["status"] == "validation_passed_pending_review":
            gate = F.load(root / ".local-agents/local-unit.py", "native_bridge_gate")
            gate.verify_handoff(root, report, config=config)
            verified = True
        S.save(root / ".agent/native-host-report.json", report)
        provider_calls = (
            report.get("consolidated_harness", {})
            .get("actual", {})
            .get("native_http_requests", 0)
        )
        S.save(
            root / ".agent/native-host-summary.json",
            {
                "status": report["status"],
                "host_handoff_verified": verified,
                "provider_calls": provider_calls,
                "reviewer_started": False,
                "production_acceptance": False,
                "primary_acceptance": "PENDING",
                "actual": report.get("consolidated_harness", {}).get("actual"),
            },
        )
        try:
            client.finish(report, verified)
        except (worker.WorkerError, OSError, subprocess.TimeoutExpired) as exc:
            S.save(runtime.archive.run_root / "native-settlement.json", {
                "settled": False, "error": str(exc), "acceptance": False,
                "host_checks_passed": verified,
            })
            print(json.dumps({"status": "frontend_settlement_failed", "host_handoff_verified": False,
                              "provider_calls": provider_calls, "acceptance": False}))
            return 2
        S.save(runtime.archive.run_root / "native-settlement.json", {"settled": True, "acceptance": False})
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "host_handoff_verified": verified,
                    "provider_calls": provider_calls,
                }
            )
        )
        return 0 if verified else 2
    finally:
        runtime.close()
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
