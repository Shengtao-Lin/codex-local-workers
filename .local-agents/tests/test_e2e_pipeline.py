"""HTTP-to-archive integration test with a scripted local model endpoint.

This deliberately runs the real Explorer, Coder, Reviewer CLIs and real pytest.
It does not claim to validate the quality of a live LM Studio model.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

AGENTS_DIR = Path(__file__).resolve().parents[1]
ORIGINAL = "def safe_divide(numerator, denominator):\n    return numerator / denominator\n"
INCOMPLETE = (
    "def safe_divide(numerator, denominator):\n"
    "    if denominator == 0:\n"
    "        return 0\n"
    "    return numerator / denominator\n"
)
CORRECT = (
    "def safe_divide(numerator, denominator):\n"
    "    if isinstance(numerator, bool) or isinstance(denominator, bool):\n"
    "        raise TypeError('boolean inputs are not supported')\n"
    "    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):\n"
    "        raise TypeError('numeric inputs are required')\n"
    "    if denominator == 0:\n"
    "        raise ValueError('denominator must not be zero')\n"
    "    return numerator / denominator\n"
)


class ScriptedModel:
    def __init__(self) -> None:
        self.turns: dict[str, int] = {}

    def action(self, request: dict) -> dict:
        messages = request["messages"]
        model = request["model"]
        if model == "explorer-fixture":
            identity = "explorer"
        elif model == "reviewer-fixture":
            identity = "reviewer"
        else:
            packet_text = next(
                message["content"].split("\n", 1)[1]
                for message in messages
                if message["role"] == "user"
                and message["content"].startswith("IMPLEMENTATION_PACKET\n")
            )
            identity = json.loads(packet_text)["run_id"]
        turn = self.turns.get(identity, 0) + 1
        self.turns[identity] = turn
        if identity == "explorer":
            actions = [
                {"action": "SEARCH", "query": "safe_divide(", "path": "src"},
                {"action": "READ_FILE", "path": "src/division.py", "start_line": 1},
                {
                    "action": "READ_FILE",
                    "path": "tests/test_division.py",
                    "start_line": 1,
                },
                {
                    "action": "FINISH_SUCCESS",
                    "relevant_files": ["src/division.py", "tests/test_division.py"],
                    "call_flow": ["Tests import safe_divide from division."],
                    "findings": ["Division lacks input validation."],
                    "relevant_tests": ["tests/test_division.py"],
                    "uncertainties": [],
                },
            ]
            return actions[turn - 1]
        if identity == "reviewer":
            if turn == 1:
                return {"action": "READ_FILE", "arguments": {"path": "src/division.py"}}
            if turn == 2:
                return {"action": "READ_FILE", "arguments": {"path": "tests/test_division.py"}}
            review_input = next(
                json.loads(message["content"].split("\n", 1)[1])
                for message in messages
                if message["role"] == "user"
                and message["content"].startswith("LOCAL_REVIEW_INPUT\n")
            )
            report = review_input["report_template_replace_evidence_before_use"]
            # A real reviewer must choose a decision; the neutral shape is not
            # itself a pass report. This scripted endpoint reviews CORRECT.
            report["arguments"]["decision"] = "pass_to_primary"
            report["arguments"]["verified_contract_ids"] = ["guard"]
            if report["arguments"]["contract_review"]:
                report["arguments"]["contract_review"][0].update(
                    {
                        "status": "verified",
                        "source_ref": {
                            "path": "src/division.py",
                            "start_line": 5,
                            "end_line": 5,
                        },
                        "evidence": "The guarded implementation rejects invalid numeric inputs.",
                    }
                )
            return report
        if turn == 1:
            return {"action": "READ_FILE", "arguments": {"path": "src/division.py"}}
        if turn == 2:
            observation = json.loads(messages[-1]["content"].split("\n", 1)[1])
            before, after = (
                (ORIGINAL, INCOMPLETE) if identity == "run-a1" else (INCOMPLETE, CORRECT)
            )
            return {
                "action": "SAFE_REPLACE",
                "arguments": {
                    "path": "src/division.py",
                    "expected_sha256": observation["sha256"],
                    "find": before,
                    "replace": after,
                },
            }
        if turn == 3:
            return {"action": "VALIDATE", "arguments": {}}
        if identity == "run-a1":
            return {
                "action": "FINISH_FAILED",
                "arguments": {
                    "summary": ["Focused error-path test still fails."],
                    "reason": "Zero denominator still returns a value.",
                    "remaining_uncertainty": [],
                },
            }
        return {
            "action": "FINISH_SUCCESS",
            "arguments": {
                "summary": ["All focused scenarios passed."],
                "remaining_uncertainty": [],
            },
        }


class ModelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps(
            {
                "data": [
                    {"id": "explorer-fixture"},
                    {"id": "coder-fixture"},
                    {"id": "reviewer-fixture"},
                ]
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        action = self.server.model.action(request)  # type: ignore[attr-defined]
        body = json.dumps({"choices": [{"message": {"content": json.dumps(action)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        pass


@unittest.skipUnless(importlib.util.find_spec("pytest"), "real pytest is required for E2E")
class PipelineE2ETests(unittest.TestCase):
    def run_cli(self, root: Path, script: str, *args: str, exit_code: int = 0) -> dict:
        report_path = root / f"{script}.report.json"
        result = subprocess.run(
            [
                sys.executable,
                str(AGENTS_DIR / script),
                *args,
                "--report",
                str(report_path),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
        return json.loads(report_path.read_text(encoding="utf-8"))

    def test_explore_failed_coder_inherited_rework_and_review(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / ".agent").mkdir()
            (root / "src" / "division.py").write_text(ORIGINAL, encoding="utf-8")
            (root / "tests" / "test_division.py").write_text(
                "from src.division import safe_divide\n"
                "import pytest\n\n"
                "def test_normal():\n    assert safe_divide(8, 2) == 4\n\n"
                "def test_negative():\n    assert safe_divide(-8, 2) == -4\n\n"
                "def test_fraction():\n    assert safe_divide(1, 4) == 0.25\n\n"
                "def test_zero():\n"
                "    with pytest.raises(ValueError):\n        safe_divide(1, 0)\n\n"
                "def test_bool():\n"
                "    with pytest.raises(TypeError):\n        safe_divide(True, 2)\n\n"
                "def test_text():\n"
                "    with pytest.raises(TypeError):\n        safe_divide('8', 2)\n",
                encoding="utf-8",
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
            server.model = ScriptedModel()  # type: ignore[attr-defined]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                config = {
                    "lmstudio_base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "explorer_model": "explorer-fixture",
                    "coder_model": "coder-fixture",
                    "reviewer_model": "reviewer-fixture",
                    "python": sys.executable,
                    "validation_profiles": {
                        "python-focused": {
                            "python": sys.executable,
                            "pytest_argv": ["-B", "-m", "pytest"],
                            "compile": True,
                        }
                    },
                    "require_edit_targets": True,
                    "reviewer_require_source_and_test_reads": True,
                    "max_model_turns": 12,
                }
                config_path = root / "config.json"
                config_path.write_text(json.dumps(config), encoding="utf-8")
                explored = self.run_cli(
                    root,
                    "local-explore.py",
                    "--task",
                    "Locate safe_divide and tests.",
                    "--config",
                    str(config_path),
                )
                self.assertEqual(explored["status"], "success")
                packet = {
                    "schema_version": 2,
                    "task_id": "division-feature",
                    "feature_id": "division-feature",
                    "unit_id": "division-guard",
                    "run_id": "run-a1",
                    "attempt": 1,
                    "plan_revision": 1,
                    "packet_revision": 1,
                    "goal": "Validate division inputs.",
                    "risk": {
                        "feature": "high",
                        "unit": "high",
                        "integration": "high",
                        "reasons": [],
                    },
                    "scope": {
                        "read": ["src", "tests"],
                        "readonly": ["tests/test_division.py"],
                        "modify": ["src/division.py"],
                        "create": [],
                        "forbidden": [],
                    },
                    "edit_targets": [
                        {
                            "path": "src/division.py",
                            "anchor": "def safe_divide",
                            "line_hint": 1,
                        }
                    ],
                    "required_behavior": [{"id": "guard", "text": "Reject invalid division."}],
                    "owned_contract_ids": ["guard"],
                    "acceptance_criteria": [{"id": "tests", "text": "Focused tests pass."}],
                    "acceptance_scenarios": [
                        {"id": "normal", "text": "Valid numeric division."},
                        {"id": "error", "text": "Zero and invalid types reject."},
                        {"id": "boundary", "text": "Negative and fractional inputs."},
                    ],
                    "validation_profile": "python-focused",
                    "focused_tests": ["tests/test_division.py"],
                }
                packet_path = root / "packet-a1.json"
                packet_path.write_text(json.dumps(packet), encoding="utf-8")
                first = self.run_cli(
                    root,
                    "local-code.py",
                    "--packet",
                    str(packet_path),
                    "--config",
                    str(config_path),
                    exit_code=1,
                )
                self.assertEqual(first["status"], "failed")
                parent_root = root / ".agent" / "tasks" / "division-feature" / "runs" / "run-a1"
                self.assertTrue((parent_root / "validation-attempt-1.json").is_file())
                self.assertTrue((parent_root / "reverse.diff").is_file())
                failed_validation = json.loads(
                    (parent_root / "validation-attempt-1.json").read_text(encoding="utf-8")
                )["validation"]
                self.assertEqual(failed_validation["focused_tests"]["junit"]["tests"], 6)
                self.assertGreaterEqual(failed_validation["focused_tests"]["junit"]["failures"], 2)
                child = {
                    "schema_version": 2,
                    "task_id": "division-feature",
                    "unit_id": "division-guard",
                    "run_id": "run-a2",
                    "attempt": 2,
                    "plan_revision": 1,
                    "packet_revision": 2,
                    "parent_run_id": "run-a1",
                    "preserve_contract": True,
                    "review_feedback": [
                        {
                            "finding_id": "zero-path",
                            "text": "Raise ValueError for zero denominator.",
                        }
                    ],
                }
                child_path = root / "packet-a2.json"
                child_path.write_text(json.dumps(child), encoding="utf-8")
                second_process = subprocess.run(
                    [
                        sys.executable,
                        str(AGENTS_DIR / "local-unit.py"),
                        "--packet",
                        str(child_path),
                        "--config",
                        str(config_path),
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                self.assertEqual(
                    second_process.returncode, 0, second_process.stdout + second_process.stderr
                )
                second = json.loads(second_process.stdout)
                self.assertEqual(second["status"], "ready_for_review")
                self.assertEqual(second["reviewer_decision"], "pass_to_primary")
                self.assertEqual(
                    (root / "src" / "division.py").read_text(encoding="utf-8"), CORRECT
                )
                child_root = root / ".agent" / "tasks" / "division-feature" / "runs" / "run-a2"
                passed_validation = json.loads(
                    (child_root / "validation.json").read_text(encoding="utf-8")
                )
                self.assertEqual(passed_validation["focused_tests"]["junit"]["executed"], 6)
                inherited = json.loads((child_root / "packet.json").read_text(encoding="utf-8"))
                self.assertTrue(inherited["_inheritance"]["rework_traceback"]["failed_test_ids"])
                reviewed = json.loads(Path(second["review_report"]).read_text(encoding="utf-8"))
                self.assertEqual(reviewed["decision"], "pass_to_primary")
                self.assertEqual(reviewed["contract_review"][0]["obligation_id"], "guard")
                self.assertEqual(
                    reviewed["runtime_facts"]["read_paths"],
                    ["src/division.py", "tests/test_division.py"],
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
