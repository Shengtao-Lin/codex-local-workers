"""Compact transport never repairs a semantic decision or bypasses old gates."""

import copy
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents/tests"))
import harness_r4_dto as D
import reviewer_compact_dto as A
import test_reviewer_runtime as H


@pytest.fixture
def runtime(tmp_path):
    request = H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    module = D.R.load(
        D.BATCH / "runtime/reviewer-runtime.py", "dto_control_" + tmp_path.name
    )
    cls = A.install(module)
    instance = cls(
        tmp_path,
        request,
        {
            "reviewer_compact_report": True,
            "reviewer_assessment_protocol": True,
            "reviewer_evidence_ids": True,
            "reviewer_require_source_and_test_reads": True,
        },
        H.FakeClient([]),
    )
    instance.read_file({"path": "src/example.py"})
    instance.read_file({"path": "tests/test_example.py"})
    return instance, module


def report():
    return {
        "assessment": "consistent",
        "findings": [],
        "ordering_review": [],
        "unverified_claims": [],
        "contract_review": [
            {
                "obligation_id": "behavior-1",
                "status": "verified",
                "evidence_ids": ["E1"],
                "evidence": "Displayed VALUE equals two.",
            }
        ],
    }


def finding():
    return {
        "id": "F1",
        "severity": "high",
        "category": "test_gap",
        "path": "tests/test_example.py",
        "line": 1,
        "contract_id": "behavior-1",
        "evidence": "Explicit test obligation is absent in the displayed suite.",
        "suggested_fix": "Add the required assertion after Primary adjudication.",
    }


def test_registered_screen_has_exact_inputs_models_and_original_budgets():
    original = {
        row["id"]: row for row in D.B.read(D.OLD.BATCH / "registration.json")["cells"]
    }
    registry = D.B.read(D.BATCH / "registration.json")
    assert [row["id"] for row in registry["cells"]] == list(original)
    assert len(registry["cells"]) == 16
    for row in registry["cells"]:
        root = Path(row["root"])
        before = original[row["id"]]
        D.R.assert_files(root, before["files"])
        after_config = D.B.read(root / ".agent/dto-config.json")
        assert after_config.pop("reviewer_compact_report") is True
        assert after_config == D.B.read(Path(before["root"]) / ".agent/config.json")
        assert row["expected_decision"] == before["expected_decision"]
        assert not (root / ".agent/current-task.json").exists()
        assert not (root / "registration.json").exists()
        assert not (root / ".agent/primary-control-adjudication.json").exists()


def test_explicit_status_only_and_truthful_host_check_provenance(runtime):
    r, _ = runtime
    r.validation["configured_checks"] = [{"id": "lint", "status": "passed"}]
    args = report()
    original = copy.deepcopy(args)
    result = r.validate_report(args)
    assert args == original
    assert result["verified_contract_ids"] == ["behavior-1"]
    assert result["verified_check_ids"] == ["lint"]
    assert result["review_protocol"] == A.PROTOCOL
    assert (
        "not model acknowledgement"
        in result["derived_field_provenance"]["verified_check_ids"]
    )


@pytest.mark.parametrize(
    "change",
    [
        "uncertain",
        "missing",
        "unknown",
        "duplicate",
        "unread",
        "drift",
        "failed_check",
        "observed_failure",
        "contradiction",
        "missing_finding",
        "injected_index",
    ],
)
def test_fail_closed(runtime, change):
    r, module = runtime
    args = report()
    entry = args["contract_review"][0]
    if change == "uncertain":
        entry["status"] = "uncertain"
    elif change == "missing":
        args["contract_review"] = []
    elif change == "unknown":
        entry["obligation_id"] = "invented"
    elif change == "duplicate":
        args["contract_review"].append(copy.deepcopy(entry))
    elif change == "unread":
        entry["evidence_ids"] = ["E999"]
    elif change == "drift":
        (r.repo_root / "src/example.py").write_text("VALUE = 3\n", encoding="utf-8")
    elif change == "failed_check":
        r.validation["configured_checks"] = [{"id": "lint", "status": "failed"}]
    elif change == "observed_failure":
        r.approved_execution.append(
            {"kind": "test", "id": "focused-tests", "status": "failed"}
        )
    elif change == "contradiction":
        args.update(assessment="required_test_gap", findings=[finding()])
    elif change == "missing_finding":
        args["assessment"] = "required_test_gap"
        entry["status"] = "violated"
    else:
        args["verified_contract_ids"] = ["behavior-1"]
    with pytest.raises(module.ReviewError):
        r.validate_report(args)


def test_defect_and_conflict_preserve_explicit_model_judgments(runtime):
    r, _ = runtime
    args = report()
    args.update(assessment="required_test_gap", findings=[finding()])
    args["contract_review"][0]["status"] = "violated"
    result = r.validate_report(args)
    assert result["decision"] == "rework" and result["findings"] == args["findings"]
    assert result["verified_contract_ids"] == []
    args.update(assessment="contract_conflict", findings=[])
    args["contract_review"][0]["status"] = "uncertain"
    assert r.validate_report(args)["decision"] == "escalate"


def test_schema_template_and_citation_repair_are_consistent(runtime):
    r, module = runtime
    before = copy.deepcopy(module.REVIEW_NATIVE_TOOLS)
    tools = A.compact_tools(module.assessment_tools(module.evidence_id_tools(before)))
    assert before == module.REVIEW_NATIVE_TOOLS
    repaired = module.canonical_citation_tools(tools)
    params = next(
        t["function"]["parameters"]
        for t in repaired
        if t["function"]["name"] == "REPORT"
    )
    assert set(params["required"]) == set(params["properties"]) == A.FIELDS
    item = params["properties"]["findings"]["items"]
    assert set(item["required"]) == set(finding())
    assert set(r.report_template()["arguments"]) == A.FIELDS
    assert r.report_template()["arguments"]["contract_review"][0]["status"].startswith(
        "CHOOSE"
    )
    assert (
        "REPORT arguments: assessment, findings, verified_contract_ids"
        not in r.system_prompt()
    )


def test_archived_invalid_reports_replay_without_semantic_rewrite():
    row = next(
        x
        for x in D.B.read(D.BATCH / "registration.json")["cells"]
        if x["id"] == "required-coverage-r1"
    )
    root = Path(row["root"])
    module = D.R.load(root / ".local-agents/reviewer-runtime.py", "dto_archived_replay")
    r = A.install(module)(
        root,
        row["identity"],
        D.B.read(root / ".agent/dto-config.json"),
        H.FakeClient([]),
    )
    r.read_file({"path": "tests/test_target.py"})
    r.read_file({"path": "src/product/target.py"})
    wire = D.OLD.BATCH / "cells/required-coverage-r1/wire"
    reports = []
    for path in sorted(wire.glob("*-response.json")):
        payload = json.loads(D.B.read(path)["raw"])
        for call in payload["choices"][0]["message"].get("tool_calls", []):
            if call["function"]["name"] == "REPORT":
                reports.append(json.loads(call["function"]["arguments"]))
    assert len(reports) == 3
    for index, raw in enumerate(reports):
        args = {key: value for key, value in raw.items() if key in A.FIELDS}
        original = copy.deepcopy(args)
        if index == 1:
            result = r.validate_report(args)
            assert result["decision"] == "rework"
            assert result["findings"] == raw["findings"]
            assert result["contract_review"][0]["status"] == "violated"
        else:
            with pytest.raises(module.ReviewError, match="at least one finding"):
                r.validate_report(args)
        assert args == original


def test_actual_cli_serializes_provenance_with_http_stub(tmp_path):
    request = H.ReviewerRuntimeTests().make_run(tmp_path, risk="high")
    shutil.copytree(D.BATCH / "runtime", tmp_path / ".local-agents")
    actions = [
        {"action": "READ_FILE", "arguments": {"path": "src/example.py"}},
        {"action": "READ_FILE", "arguments": {"path": "tests/test_example.py"}},
        {"action": "REPORT", "arguments": report()},
    ]
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send_json(self, value):
            data = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.send_json({"data": [{"id": "stub-reviewer"}]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(body)
            action = (
                actions.pop(0)
                if actions
                else {"action": "REPORT", "arguments": report()}
            )
            self.send_json(
                {
                    "choices": [
                        {
                            "message": {"content": json.dumps(action)},
                            "finish_reason": "stop",
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
        "reviewer_assessment_protocol": True,
        "reviewer_evidence_ids": True,
        "reviewer_require_source_and_test_reads": True,
    }
    D.B.save(tmp_path / "request.json", request)
    D.B.save(tmp_path / "config.json", config)
    try:
        process = subprocess.run(
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
            encoding="utf-8",
            timeout=45,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    result = D.B.read(tmp_path / "result.json")
    assert process.returncode == 0, process.stdout + process.stderr
    assert (
        result["decision"] == "pass_to_primary"
        and result["review_protocol"] == A.PROTOCOL
    )
    assert len(received) == 3 and not actions
    schemas = [
        next(
            t["function"]["parameters"]
            for t in call["tools"]
            if t["function"]["name"] == "REPORT"
        )
        for call in received
    ]
    assert all(set(schema["properties"]) == A.FIELDS for schema in schemas)
