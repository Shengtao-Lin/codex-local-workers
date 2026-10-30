"""Reject incompatible trusted material before loading or calling any model."""

import json
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from test_installable_bounded import F, S, project


def corrupt_material(root, packet, config, defect):
    path = root / F.POLICY_PATH
    policy = S.read(path)
    if defect == "target-symbol":
        policy["target"]["symbol"] = "another_function"
    elif defect == "target-path":
        policy["target"]["path"] = "tests/test_contract.py"
    elif defect == "unprotected-producer":
        packet["scope"]["readonly"].remove(F.PRODUCER)
    elif defect == "interpreter-hash":
        policy["python"]["sha256"] = "0" * 64
    elif defect == "unknown-policy-field":
        policy["unapproved_field"] = "not an allowed policy field"
    path.write_text(json.dumps(policy), encoding="utf-8")
    config["experimental_capture_policy_sha256"] = S.sha(path)
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
    (root / ".agent/packet.json").write_text(json.dumps(packet), encoding="utf-8")


def invoke(root, mode):
    command = [
        str(S.PYTHON),
        "-B",
        str(root / ".local-agents/local-bounded-unit.py"),
        "--mode",
        mode,
        "--packet",
        ".agent/packet.json",
        "--config",
        ".agent/config.json",
        "--report",
        ".agent/preflight-result.json",
    ]
    if mode == "unit":
        command += [
            "--review-report",
            ".agent/reviewer.json",
            "--summary",
            ".agent/summary.json",
        ]
    return subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "target-symbol",
        "target-path",
        "unprotected-producer",
        "interpreter-hash",
        "unknown-policy-field",
    ],
)
def test_installed_preflight_reuses_final_policy_checks(defect):
    with tempfile.TemporaryDirectory(prefix="capture-preflight-") as directory:
        root = Path(directory)
        packet, config = project(root, "labels", "early-capture-check")
        corrupt_material(root, packet, config, defect)
        before = S.sha(root / "src/product/code.py")
        result = invoke(root, "preflight")
        assert result.returncode == (0 if defect is None else 2), (
            result.stdout + result.stderr
        )
        report = S.read(root / ".agent/preflight-result.json")
        assert report["model_calls"] == 0
        if defect is None:
            assert report["preflight"] == "passed"
            assert report["capture_preflight"]["target"]["symbol"] == "merge_labels"
        else:
            assert report["status"] == "blocked"
            assert report["infra_failure"]["reason_code"] == "bounded_capture_preflight"
        assert S.sha(root / "src/product/code.py") == before
        assert not (root / ".agent/tasks").exists()
        assert not (root / ".agent/local-worker-write.lock").exists()


@pytest.mark.parametrize("mode", ["coder", "unit"])
def test_invalid_live_material_never_enters_model_residency(mode):
    requests = []

    class Trap(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            requests.append(self.path)
            body = b'{"models":[]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Trap)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="capture-before-load-") as directory:
            root = Path(directory)
            packet, config = project(root, "labels", "early-capture-live-trap")
            config.update(
                lmstudio_base_url=f"http://127.0.0.1:{server.server_port}/v1",
                single_model_residency=True,
            )
            corrupt_material(root, packet, config, "target-symbol")
            result = invoke(root, mode)
            assert result.returncode == 2, result.stdout + result.stderr
            assert requests == []
            report = S.read(root / ".agent/preflight-result.json")
            assert report["model_calls"] == 0
            assert report["infra_failure"]["reason_code"] == "bounded_capture_preflight"
            assert not (root / ".agent/tasks").exists()
            if mode == "unit":
                assert S.read(root / ".agent/summary.json") == {
                    "coder_status": "blocked",
                    "reviewer_started": False,
                    "reviewer_decision": "NOT_RUN",
                    "automatic_coder_rework": False,
                }
                assert not (root / ".agent/reviewer.json").exists()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
