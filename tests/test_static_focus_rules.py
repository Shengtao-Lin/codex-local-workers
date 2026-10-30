import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import static_focus_rules as R

W = F.load(F.KIT / ".local-agents/worker-runtime.py", "static_focus_parser_controls")


def runtime_and_binding(tmp_path):
    relative = "src/product/code.py"
    output = f'{tmp_path / relative}:1:7 - error: Type annotation is missing for parameter "x" (reportMissingParameterType)\n'
    validation = SimpleNamespace(
        configured_checks=[{"id": "pyright", "status": "failed", "output": output}],
        focused_tests={
            "input_facts": {relative: {"sha256": "same"}},
            "inputs_unchanged": True,
        },
    )
    runtime = SimpleNamespace(
        repo_root=tmp_path,
        validation=validation,
        packet={"scope": {"modify": [relative]}},
        _configured_check_repair_hint=W.WorkerRuntime._configured_check_repair_hint,
    )
    binding = {
        "path": relative,
        "sha256": "same",
        "source": "def f(x):\n    return x\n",
    }
    return runtime, binding


def test_reuses_real_parser_with_current_source_binding_and_no_old_actions(tmp_path):
    runtime, binding = runtime_and_binding(tmp_path)
    focus = R.diagnostics(runtime, binding)
    assert len(focus) == 1
    assert focus[0]["rule"] == "reportMissingParameterType"
    assert focus[0]["path"] == binding["path"]
    assert focus[0]["current_line"] == "def f(x):"
    assert focus[0]["source_sha256"] == binding["sha256"]
    assert "instruction" not in focus[0] and "required_next_action" not in focus[0]


@pytest.mark.parametrize("failure", ["stale", "readonly", "outside", "changed", "line"])
def test_rejects_unbound_or_unauthorized_location(tmp_path, failure):
    runtime, binding = runtime_and_binding(tmp_path)
    if failure == "stale":
        binding["sha256"] = "new"
    elif failure == "readonly":
        runtime.packet["scope"]["modify"] = []
    elif failure == "outside":
        runtime.repo_root = tmp_path / "other-root"
    elif failure == "changed":
        runtime.validation.focused_tests["inputs_unchanged"] = False
    else:
        binding["source"] = ""
    assert R.diagnostics(runtime, binding) == []
