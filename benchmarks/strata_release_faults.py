"""Installed fault integration, local fake provider only; never real LLM calls."""

import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import bounded_evidence_support as S
import project_caller_trial as J
import strata_release_matrix as M
from strata_native_trial import command

BATCH = M.BATCH.parent / "strata-release-faults-20261023-2"
CASES = ["length-control", "throw-control", "wrong-residency", "changed-residency"]


def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    S.save(
        BATCH / "registration.json",
        {
            "candidate": M.BATCH.name,
            "live_registered": 0,
            "real_llm_calls": 0,
            "cases": CASES,
            "gate": "nonzero/no host handoff/no edits, retained report and clean terminal; no unhandled archive collision",
            "simulation": "last two cells use owned localhost fake status/provider; do not kill/restart user's real model",
        },
    )
    rows = []
    for case in CASES:
        root = BATCH / "cells" / case / "isolated"
        J.copy_project(M.origin("raw") / "templates/raw", root)
        seed = M.BATCH / "cells/raw-1/isolated"
        shutil.copytree(seed / ".local-agents", root / ".local-agents")
        packet, config = (
            S.read(seed / ".agent/packet.json"),
            S.read(seed / ".agent/config.json"),
        )
        packet.update(
            {k: BATCH.name + "-" + case for k in ("task_id", "unit_id", "run_id")}
        )
        counts = {"status": 0, "http": 0}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self, counts=counts):
                assert self.path == "/api/native"
                counts["status"] += 1
                ident = "fake-one" if counts["status"] == 1 else "fake-replacement"
                body = json.dumps(
                    {
                        "instances": [
                            {
                                "id": ident,
                                "model": "iq3_s",
                                "status": "ready",
                                "parallel": 1,
                                "context": 131072,
                            }
                        ]
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self, counts=counts):
                assert self.path == "/v1/messages"
                counts["http"] += 1
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b"data: {}\n\n")

        server = None
        if case in {"wrong-residency", "changed-residency"}:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            config["strata_base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
        for name, value in (
            ("packet", packet),
            ("config", config),
            ("spec", S.read(seed / ".agent/spec.json")),
        ):
            S.save(root / f".agent/{name}.json", value)
        prepared_result = command(
            [
                S.PYTHON,
                "-B",
                root / ".local-agents/local-bounded-prepare.py",
                "--packet",
                ".agent/packet.json",
                "--config",
                ".agent/config.json",
                "--capture-spec",
                ".agent/spec.json",
                "--apply",
            ],
            root,
        )
        assert prepared_result["exit_code"] == 0, prepared_result
        program = {
            "mode": case if case.endswith("control") else "live",
            "instance_id": "wrong" if case == "wrong-residency" else "fake-one",
        }
        S.save(root.parent / "frontend.json", program)
        prepared = root / ".agent/prepared" / packet["run_id"]
        try:
            result = command(
                [
                    S.PYTHON,
                    "-B",
                    root / ".local-agents/strata/strata_native_host_v4.py",
                    "--packet",
                    prepared / "packet.json",
                    "--config",
                    prepared / "config.json",
                    "--program",
                    root.parent / "frontend.json",
                ],
                root,
                timeout=90,
            )
        finally:
            if server:
                server.shutdown()
                server.server_close()
        S.save(root.parent / "process.json", result)
        summary_path = root / ".agent/native-host-summary.json"
        summary = S.read(summary_path) if summary_path.exists() else None
        passed = (
            result["exit_code"] != 0
            and summary is not None
            and summary["host_handoff_verified"] is False
            and summary["actual"]["edits"] == 0
            and "Traceback" not in result["stderr"]
        )
        row = {
            "case": case,
            "pass": passed,
            "fake_http": dict(counts),
            "summary": summary,
            "stderr_tail": result["stderr"][-1500:],
            "real_llm_calls": 0,
        }
        S.save(root.parent / "result.json", row)
        rows.append(row)
        print(case, passed, counts, flush=True)
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_OFFLINE_FAULTS"
            if all(r["pass"] for r in rows)
            else "HOLD_OFFLINE_FAULTS",
            "rows": rows,
            "real_llm_calls": 0,
        },
    )


if __name__ == "__main__":
    main()
