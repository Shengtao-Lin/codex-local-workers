"""Opt-in native Agent transport on the unchanged host controller and checks."""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

import strata_bridge_host as BASE


class NativeAgentClient(BASE.NativeReplayClient):
    # Existing host counts dispatch opportunities; real HTTP has separate exact
    # counters. Combined model reservations + host opportunities may not exceed12.
    timeout = 600

    def start(self):
        r = self.runtime
        self.identity = {k: r.packet[k] for k in ("task_id", "unit_id", "run_id")}
        r.ledger.update(native_request_reservations=0, native_http_requests=0)
        self.stderr = (r.archive.run_root / "native-stderr.log").open(
            "x", encoding="utf-8"
        )
        self.process = subprocess.Popen(
            [
                r.config["strata_node_path"],
                str(Path(__file__).with_name("strata_native_agent.mjs")),
                str(self.program),
            ],
            cwd=r.repo_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            encoding="utf-8",
            env={
                **os.environ,
                "KIT_STRATA_HARNESS_ROOT": r.config["strata_harness_root"],
                "KIT_STRATA_BASE_URL": r.config["strata_base_url"],
            },
        )

        def read_frames():
            try:
                for line in self.process.stdout:
                    if len(line) > 4_000_000:
                        break
                    self.frames.put(json.loads(line))
            except (ValueError, OSError):
                pass
            finally:
                self.frames.put(None)

        threading.Thread(target=read_frames, daemon=True).start()

    def complete(self, messages):
        # Drop the old wire-format phase line, retain literal task facts/source.
        self.task_material = messages[1]["content"].partition("\n")[2]
        return super().complete(messages)

    def send(self, value):
        if value.get("kind") == "host_context":
            value["context"].update(task_material=self.task_material)
        return super().send(value)

    def receive(self):
        r = self.runtime
        while True:
            value = super().receive()
            if value.get("kind") == "native_model_permit":
                used = r.ledger["requests"] + r.ledger["native_request_reservations"]
                if used >= getattr(self, "shared_limit", 12) or r.ledger[
                    "native_request_reservations"
                ] >= getattr(self, "model_limit", 12):
                    raise self.worker.WorkerError(
                        "Shared model/tool task budget exhausted"
                    )
                body = value.get("body", {})
                if body.get("model") != "iq3_s" or body.get("max_tokens") != 12288:
                    raise self.worker.PolicyViolation(
                        "Native model/output configuration differs"
                    )
                remaining = r.deadline - time.monotonic()
                if remaining <= 0:
                    raise self.worker.WorkerError("Native task deadline exhausted")
                r.ledger["native_request_reservations"] += 1
                n = r.ledger["native_request_reservations"]
                r.RUN_STATE.write_json_once(
                    r.archive.run_root / f"native-model-request-{n}.json", value
                )
                self.send(
                    {
                        "kind": "native_model_permitted",
                        "remaining_ms": max(1, int(remaining * 1000)),
                    }
                )
            elif value.get("kind") == "native_http_started":
                r.ledger["native_http_requests"] += 1
                r.archive.mark_model_started()
            elif value.get("kind") == "native_model_result":
                n = r.ledger["native_request_reservations"]
                r.RUN_STATE.write_json_once(
                    r.archive.run_root / f"native-model-response-{n}.json", value
                )
            elif value.get("kind") == "driver_done":
                r.RUN_STATE.write_json_once(
                    r.archive.run_root / "native-session-events.json", value
                )
                return value
            else:
                return value


if __name__ == "__main__":
    raise SystemExit(BASE.main(client_type=NativeAgentClient))
