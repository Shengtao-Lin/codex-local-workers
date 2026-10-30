"""A genuine Coder archive from scripted actions; zero model capability credit."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / ".local-agents"))
from reviewer_capture_envelope import parse_command_capture, source_manifest


def test_scripted_canonical_validation_capture(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "capture_replay_helpers", ROOT / ".local-agents/tests/test_worker_runtime.py"
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    helpers.WorkerRuntimeTests().make_tree(tmp_path)
    (tmp_path / "tests/test_example.py").write_text(
        "from src.example import VALUE\n\ndef test_value():\n    assert VALUE == 2\n",
        encoding="utf-8",
    )
    (tmp_path / "profile.json").write_text(
        '{"profile":"offline-value-only"}', encoding="utf-8"
    )
    producer = """import hashlib, json
from pathlib import Path
from src.example import VALUE
paths = ["src/example.py", "capture.py", "profile.json"]
hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
print(json.dumps({"schema_version": 1, "bindings": {
    "task_id": "test-1", "run_id": "test-1-a1",
    "producer_sha256": hashes["capture.py"], "profile_sha256": hashes["profile.json"],
    "source_manifest_sha256": digest},
    "observations": [{"input": None, "outcome": {"kind": "returned", "value": VALUE}}]}))
"""
    (tmp_path / "capture.py").write_text(producer, encoding="utf-8")
    packet = helpers.packet()
    packet["scope"]["read"] = ["src", "tests", "capture.py", "profile.json"]
    packet["scope"]["readonly"] = [
        "capture.py",
        "profile.json",
        "tests/test_example.py",
    ]

    class ScriptedClient:
        def __init__(self):
            self.reads = iter(["capture.py", "profile.json"])
            self.remaining = helpers.AdaptiveSuccessClient()

        def complete(self, messages):
            path = next(self.reads, None)
            if path is not None:
                return json.dumps({"action": "READ_FILE", "arguments": {"path": path}})
            return self.remaining.complete(messages)

    config = {
        "validation_profiles": {
            "python-focused": {
                "python": sys.executable,
                "compile": True,
                "pytest_argv": ["-B", "-m", "pytest", "-q"],
                "commands": [
                    {"id": "capture", "argv": ["{python}", "-B", "{repo}/capture.py"]}
                ],
            }
        },
    }
    report = helpers.RUNTIME.WorkerRuntime(
        tmp_path, packet, config, ScriptedClient()
    ).run()
    assert report["status"] == "ready_for_review"
    archive = tmp_path / ".agent/tasks/test-1/runs/test-1-a1"
    assert (archive / "completed.json").is_file()
    validation = json.loads((archive / "validation.json").read_text(encoding="utf-8"))
    post = json.loads((archive / "post-state.json").read_text(encoding="utf-8"))
    for path in ["capture.py", "profile.json", "src/example.py"]:
        assert path in post["validation_inputs"]
    paths = ["src/example.py", "capture.py", "profile.json"]
    manifest = source_manifest(tmp_path, paths, approved_paths=paths)
    bindings = {
        "task_id": "test-1",
        "run_id": "test-1-a1",
        "producer_sha256": hashlib.sha256(
            (tmp_path / "capture.py").read_bytes()
        ).hexdigest(),
        "profile_sha256": hashlib.sha256(
            (tmp_path / "profile.json").read_bytes()
        ).hexdigest(),
        "source_manifest_sha256": manifest["sha256"],
    }
    actual = parse_command_capture(
        validation["configured_checks"],
        check_id="capture",
        argv=[sys.executable, "-B", str(tmp_path) + "/capture.py"],
        bindings=bindings,
    )
    assert actual == [{"input": None, "outcome": {"kind": "returned", "value": 2}}]
    assert validation["status"] == "passed"
