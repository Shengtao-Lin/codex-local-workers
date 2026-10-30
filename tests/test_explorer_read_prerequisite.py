import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_support as S
import capture_fixture_support as F
import explorer_read_prerequisite as P


class Client:
    def __init__(self, module, actions):
        self.native_tools = module.EXPLORER_TOOLS
        self.native_tool_choice = "auto"
        self.actions = iter(actions)
        self.allowed = []

    def complete(self, _messages):
        self.allowed.append([t["function"]["name"] for t in self.native_tools])
        return json.dumps(next(self.actions))


def setup(tmp_path, patched):
    root = tmp_path / "isolated"
    root.mkdir()
    shutil.copytree(
        S.KIT / ".local-agents",
        root / ".local-agents",
        ignore=shutil.ignore_patterns("__pycache__", "tests"),
    )
    for path in ("src/code.py", "tests/test_code.py", "context/dependency.py"):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")
    runtime_path = root / ".local-agents/explorer-runtime.py"
    # Keep the historical before/after control meaningful after production migration.
    frozen = (
        S.KIT
        / "benchmarks/work/harness-convergence"
        / "reviewer-dependency-evidence-20261020-1/cells/json-1/isolated"
        / ".local-agents/explorer-runtime.py"
    )
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == (
        "1857ed8585fbe0bc85bbdf94ced5dfd67165cab93c1632be42221f5ac55dda5d"
    )
    shutil.copy2(frozen, runtime_path)
    if patched:
        P.install(runtime_path, root)
    module = F.load(runtime_path, "read_prerequisite_" + str(patched))
    return root, module


def finish(paths):
    return {
        "action": "FINISH_SUCCESS",
        "relevant_files": [paths[0]],
        "relevant_tests": [paths[1]],
        "findings": [p + " line 1 defines x" for p in paths],
        "call_flow": [],
        "uncertainties": [],
        "citations": [{"path": p, "line": 1, "claim": "defines x"} for p in paths],
    }


@pytest.mark.parametrize("patched", [False, True])
def test_missing_dependency_keeps_actual_read_opportunity(tmp_path, patched):
    root, module = setup(tmp_path, patched)
    paths = ["src/code.py", "tests/test_code.py", "context/dependency.py"]
    actions = [{"action": "READ_FILE", "path": p} for p in paths[:2]]
    actions += [
        finish(paths[:2]),
        {"action": "READ_FILE", "path": paths[2]},
        finish(paths),
    ]
    client = Client(module, actions)
    runtime = module.ExplorerRuntime(
        root,
        "Inspect code and tests",
        {"explorer_mode": "investigate", "explorer_required_citation_paths": paths},
        client,
    )
    report = runtime.run()
    if patched:
        assert report["status"] == "success"
        assert paths[2] in runtime.read_files
        assert "READ_FILE" in client.allowed[3]
        assert report["budget_usage"]["protocol_errors"] == 1
    else:
        assert report["status"] == "failed"
        assert paths[2] not in runtime.read_files
        assert client.allowed[3] == ["FINISH_SUCCESS"]


def test_all_sources_read_retains_one_shot_report_only_gate(tmp_path):
    root, module = setup(tmp_path, True)
    paths = ["src/code.py", "tests/test_code.py"]
    bad = finish(paths)
    bad["findings"] = []
    bad["citations"] = []
    client = Client(
        module,
        [{"action": "READ_FILE", "path": p} for p in paths] + [bad, finish(paths)],
    )
    runtime = module.ExplorerRuntime(
        root,
        "Inspect code and tests",
        {"explorer_required_citation_paths": paths},
        client,
    )
    result = runtime.run()
    assert result["status"] == "success"
    assert client.allowed[-1] == ["FINISH_SUCCESS"]


def test_unread_source_is_never_accepted_by_patch(tmp_path):
    root, module = setup(tmp_path, True)
    paths = ["src/code.py", "tests/test_code.py", "context/dependency.py"]
    wrong = finish(paths)
    wrong["relevant_files"] = copy.deepcopy(paths)
    client = Client(
        module, [{"action": "READ_FILE", "path": p} for p in paths[:2]] + [wrong] * 6
    )
    runtime = module.ExplorerRuntime(
        root,
        "Inspect code and tests",
        {"explorer_required_citation_paths": paths, "max_explorer_model_turns": 8},
        client,
    )
    report = runtime.run()
    assert report["status"] == "failed" and paths[2] not in runtime.read_files


def test_patch_refuses_production_path(tmp_path):
    path = S.KIT / ".local-agents/explorer-runtime.py"
    before = S.sha(path)
    with pytest.raises(ValueError):
        P.install(path, tmp_path)
    assert S.sha(path) == before
