"""Semantic authority, original report gates, matched inputs and shared budgets."""

import copy
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents/tests"))
import harness_reviewer_semantic as D
import reviewer_semantic_entry as A
import test_reviewer_runtime as H


class Client:
    def __init__(self, module, replies=()):
        self.native_tools = copy.deepcopy(module.REVIEW_NATIVE_TOOLS)
        self.timeout = 180
        self.native_tool_choice = "auto"
        self.last_request_stats = {}
        self.replies = iter(replies)
        self.calls = 0
        self.messages = []

    def preflight(self):
        pass

    def probe_structured_output(self):
        return "native"

    def complete(self, messages):
        self.calls += 1
        self.messages.append(copy.deepcopy(messages))
        return json.dumps(next(self.replies))


def make(tmp_path, replies=(), **config):
    request = H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.E.D.BATCH / "runtime/reviewer-runtime.py", "semantic_control_" + tmp_path.name
    )
    client = Client(module, replies)
    runtime = A.install(module)(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
            **config,
        },
        client,
    )
    return runtime, module, client


def judgment(kind="satisfied"):
    return {
        "obligations": [
            {
                "id": "behavior-1",
                "verdict": kind,
                "evidence_ids": ["E1"],
                "explanation": "Displayed VALUE is two. Concrete inspected source supports this judgment.",
                "line": 1
                if kind in {"implementation_defect", "required_test_gap"}
                else None,
                "fix": "Repair the cited owned behavior."
                if kind in {"implementation_defect", "required_test_gap"}
                else "",
                "severity": "medium",
            }
        ],
        "uncertainties": [],
    }


def test_matched_forty_roots_and_original_budgets_before_live():
    rows = D.B.read(D.BATCH / "registration.json")["cells"]
    assert len(rows) == 40
    for i in range(0, 40, 2):
        pair = rows[i : i + 2]
        assert {r["arm"] for r in pair} == {"candidate", "control"}
        assert pair[0]["case"] == pair[1]["case"]
        hashes = []
        for row in pair:
            root = Path(row["root"])
            D.R.assert_files(root, row["files"])
            D.R.assert_files(Path(row["origin"]), row["origin_files"])
            assert not (root / ".agent/current-task.json").exists()
            assert not (
                root
                / ".agent/tasks"
                / row["identity"]["task_id"]
                / "reviews"
                / row["identity"]["review_id"]
            ).exists()
            hashes.append(
                {
                    p: sha
                    for p, sha in row["files"].items()
                    if p != ".agent/experiment-request.json"
                }
            )
            config = D.B.read(root / ".agent/experiment-config.json")
            assert config["reviewer_max_tokens"] == 4096
            assert config.get("max_reviewer_turns", 16) == 16
            assert config.get("max_reviewer_protocol_errors", 4) == 4
        assert hashes[0] == hashes[1]


def test_all_twenty_task_local_bundles_preserve_complete_obligations_and_display():
    for row in D.B.read(D.BATCH / "registration.json")["cells"]:
        if row["arm"] != "candidate":
            continue
        root = Path(row["root"])
        module = D.R.load(
            root / ".local-agents/reviewer-runtime.py", "semantic_bundle_" + row["id"]
        )
        runtime = A.install(module)(
            root,
            {**row["identity"], "review_id": "offline-" + row["id"]},
            D.B.read(root / ".agent/experiment-config.json"),
            Client(module),
        )
        bundle = runtime.bundle()
        assert bundle["obligations"] == runtime.review_obligations()
        assert runtime.required_reads_complete()
        assert not runtime.coverage_facts()["missing"]
        assert bundle["actual_cumulative_diff"] == runtime.diff
        assert "runtime_validation" not in bundle and "contract_check" not in bundle
        assert "expected_decision" not in json.dumps(bundle)
        assert "primary-adjudication" not in json.dumps(bundle)
        assert "None" not in A.SYSTEM and "collect_tools" not in A.SYSTEM
        D.R.assert_files(root, row["files"])


@pytest.mark.parametrize(
    "kind,decision",
    [
        ("satisfied", "pass_to_primary"),
        ("implementation_defect", "rework"),
        ("required_test_gap", "rework"),
        ("contract_conflict", "escalate"),
        ("uncertain", "escalate"),
    ],
)
def test_explicit_verdict_maps_without_overall_label_or_prose_inference(
    tmp_path, kind, decision
):
    runtime, module, _ = make(tmp_path)
    runtime.bundle()
    args = judgment(kind)
    before = copy.deepcopy(args)
    report = runtime.validate_report(A.assemble(runtime, args, module.ReviewError))
    assert report["decision"] == decision and args == before
    if decision == "rework":
        assert (
            report["findings"][0]["evidence"] == args["obligations"][0]["explanation"]
        )
        assert report["findings"][0]["suggested_fix"] == args["obligations"][0]["fix"]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "unknown_id",
        "unread",
        "bad_line",
        "missing_fix",
        "overall_label",
        "owned_uncertainty",
    ],
)
def test_negative_semantic_shape_and_authority_controls(tmp_path, change):
    runtime, module, _ = make(tmp_path)
    runtime.bundle()
    args = judgment(
        "implementation_defect"
        if change in {"bad_line", "missing_fix"}
        else "satisfied"
    )
    if change == "missing":
        args["obligations"] = []
    elif change == "duplicate":
        args["obligations"] *= 2
    elif change == "unknown_id":
        args["obligations"][0]["id"] = "unowned"
    elif change == "unread":
        args["obligations"][0]["evidence_ids"] = ["E999"]
    elif change == "bad_line":
        args["obligations"][0]["line"] = 999
    elif change == "missing_fix":
        args["obligations"][0]["fix"] = ""
    elif change == "overall_label":
        args["assessment"] = "consistent"
    else:
        args["uncertainties"] = [
            {"contract_id": "behavior-1", "text": "Owned outcome remains unresolved."}
        ]
    with pytest.raises(module.ReviewError):
        A.assemble(runtime, args, module.ReviewError)


def test_optional_advice_and_keyword_prose_do_not_create_host_semantic_findings(
    tmp_path,
):
    runtime, module, _ = make(tmp_path)
    runtime.bundle()
    args = judgment()
    args["uncertainties"] = [
        {"contract_id": None, "text": "Optional extra None boundary test."}
    ]
    report = runtime.validate_report(A.assemble(runtime, args, module.ReviewError))
    assert report["decision"] == "pass_to_primary" and report["findings"] == []
    assert report["unverified_claims"] == [args["uncertainties"][0]["text"]]


@pytest.mark.parametrize(
    "change", ["source_drift", "missing_test_read", "failed_check", "ordering"]
)
def test_original_runtime_gates_remain_effective(tmp_path, change):
    runtime, module, _ = make(tmp_path)
    if change == "ordering":
        runtime.config["reviewer_require_search"] = True
        with pytest.raises(module.ReviewError, match="does not support"):
            runtime.bundle()
        return
    runtime.bundle()
    if change == "source_drift":
        (tmp_path / "src/example.py").write_text("VALUE = 99\n", encoding="utf-8")
    elif change == "missing_test_read":
        runtime.read_lines.pop("tests/test_example.py")
    else:
        runtime.validation["configured_checks"] = [{"id": "lint", "status": "failed"}]
    with pytest.raises(module.ReviewError):
        runtime.validate_report(A.assemble(runtime, judgment(), module.ReviewError))


def test_full_run_retains_canonical_report_and_single_call(tmp_path):
    runtime, _, client = make(tmp_path, [{"action": "REPORT", "arguments": judgment()}])
    report = runtime.run()
    assert report["decision"] == "pass_to_primary" and client.calls == 1
    assert report["semantic_review_protocol"] == A.PROTOCOL
    assert (runtime.review_root / "completed.json").is_file()
    assert (runtime.review_root / "runtime-validation.json").is_file()


@pytest.mark.parametrize("limit,expected", [("turn", 2), ("protocol", 2)])
def test_judgment_and_report_assembly_share_call_and_error_budget(
    tmp_path, limit, expected
):
    cfg = {
        "max_reviewer_turns": 2 if limit == "turn" else 16,
        "max_reviewer_protocol_errors": 4 if limit == "turn" else 2,
    }
    runtime, module, client = make(
        tmp_path, [{"action": "REPORT", "arguments": {}}] * 5, **cfg
    )
    with pytest.raises(module.ReviewError, match="budget exhausted"):
        runtime.run()
    assert client.calls == expected
    assert not (runtime.review_root / "completed.json").exists()
    assert all(len(m) == 2 for m in client.messages)


def test_shared_deadline_expires_before_any_extra_model_call(tmp_path):
    runtime, module, client = make(tmp_path)
    with (
        patch.object(A.time, "monotonic", side_effect=[0, 601]),
        pytest.raises(module.ReviewError, match="deadline exhausted"),
    ):
        runtime.run()
    assert client.calls == 0


@pytest.mark.parametrize(
    "kind,decision",
    [("satisfied", "pass_to_primary"), ("implementation_defect", "rework")],
)
def test_actual_native_http_cli_roundtrip_retains_semantic_disposition(
    tmp_path, kind, decision
):
    request = H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    shutil.copytree(D.E.D.BATCH / "runtime", tmp_path / ".local-agents")
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send_json(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.send_json({"data": [{"id": "stub-reviewer"}]})

        def do_POST(self):
            received.append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            self.send_json(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "REPORT",
                                            "arguments": json.dumps(judgment(kind)),
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                }
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = {
        "lmstudio_base_url": f"http://127.0.0.1:{server.server_port}/v1",
        "reviewer_model": "stub-reviewer",
        "reviewer_native_tools": True,
        "reviewer_preload_model": False,
        "single_model_residency": False,
        "reviewer_compact_report": True,
        "reviewer_evidence_state": True,
        "reviewer_assessment_protocol": True,
        "reviewer_evidence_ids": True,
        "reviewer_require_source_and_test_reads": True,
    }
    D.B.save(tmp_path / "request.json", request)
    D.B.save(tmp_path / "config.json", config)
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(D.ADAPTER),
                "--runtime-dir",
                str(tmp_path / ".local-agents"),
                "--request",
                "request.json",
                "--config",
                "config.json",
                "--report",
                "result.json",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    report = D.B.read(tmp_path / "result.json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (
        report["decision"] == decision
        and report["semantic_review_protocol"] == A.PROTOCOL
    )
    assert report["semantic_verdicts"] == judgment(kind)
    assert len(received) == report["reviewer_model_calls"] == 1
    assert (
        set(received[0]["tools"][0]["function"]["parameters"]["properties"]) == A.FIELDS
    )
