"""Real subprocess command-layer replay, explicitly not canonical qualification."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / ".local-agents"))
from reviewer_capture_envelope import CaptureRejected, parse_command_capture


@pytest.fixture(scope="module")
def runtime_module():
    spec = importlib.util.spec_from_file_location(
        "capture_boundary_worker", ROOT / ".local-agents/worker-runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode", ["clean", "stderr", "truncated", "nonzero"])
def test_real_subprocess_output_boundary(runtime_module, tmp_path, mode):
    bindings = {
        "task_id": "offline",
        "run_id": "command-layer-only",
        "producer_sha256": "a" * 64,
        "profile_sha256": "b" * 64,
        "source_manifest_sha256": "c" * 64,
    }
    envelope = json.dumps(
        {
            "schema_version": 1,
            "bindings": bindings,
            "observations": [
                {"input": None, "outcome": {"kind": "returned", "value": 0}}
            ],
        }
    )
    script = "import sys; print(" + repr(envelope) + ")"
    if mode == "stderr":
        script += "; print('warning', file=sys.stderr)"
    elif mode == "nonzero":
        script += "; sys.exit(2)"
    argv = [sys.executable, "-B", "-c", script]
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        command_timeout=10,
        max_output=16 if mode == "truncated" else 16000,
        _remaining_seconds=lambda phase: 30,
    )
    record = runtime_module.WorkerRuntime._run_command(runtime, argv)
    if mode == "clean":
        assert (
            parse_command_capture(
                [{"id": "capture", **record}],
                check_id="capture",
                argv=argv,
                bindings=bindings,
            )[0]["outcome"]["value"]
            == 0
        )
    else:
        with pytest.raises(CaptureRejected):
            parse_command_capture(
                [{"id": "capture", **record}],
                check_id="capture",
                argv=argv,
                bindings=bindings,
            )


def test_readonly_alone_does_not_bind_validation_epoch(runtime_module):
    runtime = SimpleNamespace(
        packet={
            "scope": {"modify": ["src.py"], "create": [], "readonly": ["capture.py"]},
            "focused_tests": ["test_unit.py::test_one"],
        },
        observed_hashes={},
    )
    paths = runtime_module.WorkerRuntime._validation_paths(runtime)
    assert "capture.py" not in paths
    runtime.observed_hashes["capture.py"] = "a" * 64
    assert "capture.py" in runtime_module.WorkerRuntime._validation_paths(runtime)
