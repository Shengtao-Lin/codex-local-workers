"""Installed real subprocess/HTTP boundary controls; no LM Studio invocation."""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from test_host_proposal_protocol import KIT, U, W, build


@pytest.fixture
def passed(tmp_path):
    runtime, config, client = build(tmp_path)
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review"
    assert len(client.calls) == 1
    return runtime, config, report


def test_compact_host_report_preserves_explicit_metadata(passed):
    runtime, config, full = passed
    compact = W.compact_handoff(full)
    assert compact["execution_protocol"] == "host-proposal-v1"
    assert "worker_assessment" in compact and compact["worker_assessment"] is None
    assert U.verify_handoff(runtime.repo_root, compact, config=config)


@pytest.mark.parametrize("protocol", [None, "unknown-v99"])
def test_unknown_or_missing_protocol_not_inferred(passed, protocol):
    runtime, config, full = passed
    full = dict(full)
    if protocol is None:
        full.pop("execution_protocol")
    else:
        full["execution_protocol"] = protocol
    compact = W.compact_handoff(full)
    with pytest.raises(ValueError, match="Unknown host"):
        U.verify_handoff(runtime.repo_root, compact, config=config)


def test_serializer_does_not_fabricate_assessment():
    compact = W.compact_handoff({"status": "ready_for_review"})
    assert "execution_protocol" not in compact and "worker_assessment" not in compact
    assert W.compact_handoff({"worker_assessment": {"false_claim": True}})[
        "worker_assessment"
    ] == {"false_claim": True}


def test_fabricated_canonical_assessment_rejected(passed):
    runtime, config, full = passed
    archive = runtime.archive.run_root
    path = archive / "handoff.json"
    handoff = json.loads(path.read_text(encoding="utf-8"))
    handoff["worker_assessment"] = {"confirmed": True}
    path.write_text(json.dumps(handoff), encoding="utf-8")
    with pytest.raises(ValueError, match="fabricated"):
        U.verify_handoff(runtime.repo_root, W.compact_handoff(full), config=config)


def test_installed_default_cli_reaches_unique_real_reviewer(tmp_path):
    # Only HTTP generation is a stub. Installer, both CLIs, default serializer,
    # validators, canonical gate, Reviewer prepare and dispatch are real.
    sys.path.insert(0, str(KIT / "scripts"))
    import install_local_agents as installer

    source = tmp_path.parent / (tmp_path.name + "-install-source")
    source.mkdir()
    shutil.copyfile(KIT / "AGENTS.md", source / "AGENTS.md")
    shutil.copytree(
        KIT / ".local-agents",
        source / ".local-agents",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"),
    )
    installer.install(source, tmp_path, apply=True)
    assert not (tmp_path / ".local-agents/config.json").exists()
    runtime, config, _ = build(tmp_path)
    packet = runtime.packet
    runtime.close()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send_json(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.send_json({"data": [{"id": "stub-coder"}, {"id": "stub-reviewer"}]})

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            content = (
                {"replacement": "def value():\n    return 2"}
                if request["model"] == "stub-coder"
                else {"invalid_test_response": True}
            )
            self.send_json(
                {
                    "choices": [
                        {
                            "message": {"content": json.dumps(content)},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 2,
                    },
                }
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config.update(
        lmstudio_base_url=f"http://127.0.0.1:{server.server_port}/v1",
        coder_model="stub-coder",
        reviewer_model="stub-reviewer",
        reviewer_structured_output=False,
        reviewer_native_tools=False,
        reviewer_preload_model=False,
        single_model_residency=False,
        max_reviewer_turns=1,
        max_reviewer_protocol_errors=1,
    )
    config_path, packet_path = tmp_path / "config.json", tmp_path / "packet.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    coder, reviewer = tmp_path / "coder.json", tmp_path / "reviewer.json"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(tmp_path / ".local-agents/local-unit.py"),
                "--packet",
                str(packet_path),
                "--config",
                str(config_path),
                "--coder-report",
                str(coder),
                "--review-report",
                str(reviewer),
            ],
            cwd=tmp_path,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
            check=False,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    payload = json.loads(result.stdout)
    assert "review_request" in payload, result.stdout + result.stderr
    assert len(payload["review_attempts"]) == 1
    assert payload["reviewer_decision"] != "pass_to_primary"  # No synthetic acceptance.
    compact = json.loads(coder.read_text(encoding="utf-8"))
    assert compact["execution_protocol"] == "host-proposal-v1"
    assert compact["worker_assessment"] is None
    assert len([r for r in requests if r["model"] == "stub-coder"]) == 1
    assert any(r["model"] == "stub-reviewer" for r in requests)
    dispatches = list((tmp_path / ".agent").rglob("host-review-dispatch.json"))
    assert len(dispatches) == 1
    assert len(list((tmp_path / ".agent").rglob("auto-review-request.json"))) == 1
    assert not list((tmp_path / ".agent").rglob("auto-review-retry-request.json"))
