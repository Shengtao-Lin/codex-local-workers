"""Installed offline inspection is authenticating, non-consuming, and not acceptance."""

import json
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from test_installable_bounded import L, S, archive, project


@pytest.fixture
def prepared():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def send_json(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            requests.append(("GET", self.path))
            self.send_json({"data": [{"id": "scripted-reviewer"}]})

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(("POST", payload))
            # Deliberately invalid: this control tests dispatch, never semantic success.
            self.send_json(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "action": "REPORT",
                                        "arguments": {
                                            "obligations": [],
                                            "uncertainties": [],
                                        },
                                    }
                                )
                            },
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
    try:
        with tempfile.TemporaryDirectory(prefix="review-inspection-") as directory:
            root = Path(directory)
            packet, config = project(root, "labels", "review-inspection")
            config.update(
                bounded_compatibility_profile="flat-v1",
                lmstudio_base_url=f"http://127.0.0.1:{server.server_port}/v1",
                reviewer_model="scripted-reviewer",
                single_model_residency=False,
                reviewer_preload_model=False,
                reviewer_native_tools=True,
                max_reviewer_turns=1,
                max_reviewer_protocol_errors=1,
            )
            (root / ".agent/config.json").write_text(
                json.dumps(config), encoding="utf-8"
            )
            S.save(
                root / ".agent/replay.json",
                [{"kind": "replacement", "content": L.TASKS["labels"]["reference"]}],
            )
            result = subprocess.run(
                [
                    str(S.PYTHON),
                    "-B",
                    str(root / ".local-agents/local-bounded-unit.py"),
                    "--mode",
                    "coder",
                    "--packet",
                    ".agent/packet.json",
                    "--config",
                    ".agent/config.json",
                    "--report",
                    ".agent/coder.json",
                    "--replay",
                    ".agent/replay.json",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            coder = S.read(root / ".agent/coder.json")
            assert coder["status"] == "validation_passed_pending_review"
            assert coder["consolidated_harness"]["actual"]["model_requests"] == 0
            request = {
                "schema_version": 1,
                **{k: packet[k] for k in ("task_id", "unit_id", "run_id")},
                "review_id": "inspect-then-review",
                "execution_protocol": coder["execution_protocol"],
            }
            S.save(root / ".agent/review-request.json", request)
            S.save(
                root / ".agent/review-config.json",
                {
                    **config,
                    "reviewer_compact_report": True,
                    "reviewer_evidence_state": True,
                },
            )
            assert requests == []
            yield root, request, requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def invoke(root, report, *, inspect=True, request=".agent/review-request.json"):
    command = [
        str(S.PYTHON),
        "-B",
        str(root / ".local-agents/local-bounded-review.py"),
        "--request",
        request,
        "--config",
        ".agent/review-config.json",
        "--report",
        report,
    ]
    if inspect:
        command.append("--inspect-only")
    return subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )


def task_files(root):
    return {
        p.relative_to(root).as_posix(): S.sha(p)
        for p in (root / ".agent/tasks").rglob("*")
        if p.is_file()
    }


def test_repeated_inspection_preserves_archive_and_live_one_shot(prepared):
    root, request, requests = prepared
    before = task_files(root)
    for name in ("inspection-1.json", "inspection-2.json"):
        result = invoke(root, name)
        assert result.returncode == 0, result.stdout + result.stderr
        report = S.read(root / name)
        assert report["mode"] == "offline-input-inspection"
        assert report["model_calls"] == 0 and report["reviewer_acceptance"] is False
        assert report["reviewer_dispatched"] is False
        assert task_files(root) == before
        assert requests == []
    assert S.read(root / "inspection-1.json") == S.read(root / "inspection-2.json")
    saved_report = S.sha(root / "inspection-1.json")
    assert invoke(root, "inspection-1.json").returncode != 0
    assert S.sha(root / "inspection-1.json") == saved_report
    assert task_files(root) == before and requests == []

    result = invoke(root, "first-review.json", inspect=False)
    assert result.returncode == 2  # Intentional invalid report, not acceptance.
    assert sum(method == "POST" for method, _ in requests) == 1
    dispatch = archive(root) / "host-review-dispatch.json"
    assert S.read(dispatch) == request
    assert S.read(root / "first-review.json")["decision"] == "failed"

    # A new review id or inspection must never reset a consumed dispatch.
    next_request = {**request, "review_id": "another-review-id"}
    S.save(root / ".agent/another-request.json", next_request)
    before = task_files(root)
    result = invoke(
        root, "after-dispatch-inspection.json", request=".agent/another-request.json"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert task_files(root) == before
    result = invoke(
        root, "second-review.json", inspect=False, request=".agent/another-request.json"
    )
    assert result.returncode == 2
    assert "already dispatched" in S.read(root / "second-review.json")["failure_reason"]
    assert sum(method == "POST" for method, _ in requests) == 1
    assert task_files(root) == before


@pytest.mark.parametrize("corrupt", ["source", "policy", "junit", "capture"])
def test_inspection_rejects_stale_or_forged_evidence_without_dispatch(
    prepared, corrupt
):
    root, _request, requests = prepared
    run = archive(root)
    result = invoke(root, "before-change-inspection.json")
    assert result.returncode == 0, result.stdout + result.stderr
    if corrupt == "source":
        path = root / "src/product/code.py"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8"
        )
    elif corrupt == "policy":
        path = root / "acceptance/capture-policy.json"
        policy = S.read(path)
        policy["identity"]["run_id"] = "different-run"
        path.write_text(json.dumps(policy), encoding="utf-8")
    elif corrupt == "junit":
        validation = S.read(run / "validation.json")
        path = root / validation["focused_tests"]["junit"]["path"]
        path.write_text("<testsuite tests='0'/>", encoding="utf-8")
    else:
        path = run / "validation.json"
        validation = S.read(path)
        for check in validation["configured_checks"]:
            if check["id"] == "actual-observations":
                check["stdout"] = "forged observation"
        path.write_text(json.dumps(validation), encoding="utf-8")
    before = task_files(root)
    result = invoke(root, "invalid-inspection.json")
    assert result.returncode != 0
    assert not (root / "invalid-inspection.json").exists()
    assert not (run / "host-review-dispatch.json").exists()
    assert requests == []
    assert task_files(root) == before
    # A previously valid inspection is not a reusable certificate for live input.
    result = invoke(root, "stale-live-review.json", inspect=False)
    assert result.returncode == 2
    assert requests == []
    assert task_files(root) == before
