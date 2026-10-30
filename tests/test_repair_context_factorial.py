"""Controls for task persistence, protected definitions, and equivalent edit scope."""

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(BENCH))
import repair_context_factorial as trial

RUNTIME = trial.common.load("factorial_control_runtime", trial.KIT / ".local-agents/worker-runtime.py")


@pytest.fixture
def root(tmp_path):
    source = tmp_path / trial.SOURCE
    source.parent.mkdir(parents=True)
    source.write_bytes((trial.OLD / trial.SOURCE).read_bytes())
    packet = copy.deepcopy(trial.common.read(trial.previous.OLD_RUN / "packet.json"))
    packet["scope"]["readonly"] = []
    trial.save(tmp_path / ".agent/packet.json", packet)
    return tmp_path


@pytest.mark.parametrize("context", ["minimal", "full"])
@pytest.mark.parametrize("output", ["code", "json"])
def test_task_and_current_version_survive_rebuilding_and_compaction(root, context, output):
    before = trial.messages_for(root, context, output)
    source = root / trial.SOURCE
    source.write_text(source.read_text(encoding="utf-8").replace("result.append", "result.append", 1) + "\n", encoding="utf-8")
    after = trial.messages_for(root, context, output, {"edit_rejected": "no-op"}, "previous untrusted response")
    for messages in (before, after):
        assert trial.REQUEST in messages[1]["content"]
        assert "method already exists" in messages[1]["content"]
        assert "sequential-trace-batch" in messages[1]["content"]
    assert json.loads(after[1]["content"])["sha256"] == trial.common.sha(source)
    assert json.loads(before[1]["content"])["sha256"] != json.loads(after[1]["content"])["sha256"]


def corrected(root):
    text = (root / trial.SOURCE).read_text(encoding="utf-8")
    _, _, _, block = trial.method_span(text)
    long_line = next(line for line in block.splitlines() if len(line) > 100)
    fixed = block.replace(long_line, '        """Get traces sequentially, preserving order and identity."""')
    return block, fixed


@pytest.mark.parametrize("output", ["code", "json"])
def test_valid_model_proposal_changes_only_target_method(root, output):
    block, fixed = corrected(root)
    source = root / trial.SOURCE
    before = source.read_text(encoding="utf-8")
    digest = trial.common.sha(source)
    response = fixed if output == "code" else json.dumps({"path": trial.SOURCE,
        "expected_sha256": digest, "find": block, "replace": fixed})
    trial.apply_proposal(RUNTIME, root, output, response, digest)
    assert source.read_text(encoding="utf-8") == before.replace(block, fixed)


@pytest.mark.parametrize("output", ["code", "json"])
@pytest.mark.parametrize("defect", ["extra_definition", "rename", "signature", "stale", "noop"])
def test_invalid_proposals_do_not_mutate(root, output, defect):
    block, fixed = corrected(root)
    source = root / trial.SOURCE
    before = source.read_bytes()
    digest = trial.common.sha(source)
    if defect == "extra_definition":
        fixed += "\n    def intruder(self):\n        return 1\n"
    elif defect == "rename":
        fixed = fixed.replace("def get_many", "def other")
    elif defect == "signature":
        fixed = fixed.replace("list[str]", "str", 1)
    elif defect == "noop":
        fixed = block
    response = fixed if output == "code" else json.dumps({"path": trial.SOURCE,
        "expected_sha256": digest, "find": block, "replace": fixed})
    observed = "0" * 64 if defect == "stale" else digest
    with pytest.raises((ValueError, SyntaxError, RUNTIME.SafeEditError)):
        trial.apply_proposal(RUNTIME, root, output, response, observed)
    assert source.read_bytes() == before


def test_json_model_hash_and_scope_are_enforced(root):
    block, fixed = corrected(root)
    source = root / trial.SOURCE
    before = source.read_bytes()
    digest = trial.common.sha(source)
    for path, proposed_hash in (("tests/protected.py", digest), (trial.SOURCE, "0" * 64)):
        response = json.dumps({"path": path, "expected_sha256": proposed_hash,
                               "find": block, "replace": fixed})
        with pytest.raises((ValueError, RUNTIME.SafeEditError)):
            trial.apply_proposal(RUNTIME, root, "json", response, digest)
        assert source.read_bytes() == before


def test_new_duplicate_guard_rejects_prior_live_failure(root, monkeypatch):
    source = root / trial.SOURCE
    prior = trial.previous.BASE / "simple-1/isolated" / trial.SOURCE
    source.write_bytes(prior.read_bytes())
    namespace = {}
    exec(compile(trial.GUARD, "definition-guard", "exec"), namespace)
    monkeypatch.chdir(root)
    with pytest.raises(AssertionError):
        namespace["test_no_duplicate_function_or_method_definitions"]()


def test_new_duplicate_guard_accepts_current_failed_lint_baseline(root, monkeypatch):
    namespace = {}
    exec(compile(trial.GUARD, "definition-guard", "exec"), namespace)
    monkeypatch.chdir(root)
    namespace["test_no_duplicate_function_or_method_definitions"]()
    assert len(ast.parse((root / trial.SOURCE).read_text(encoding="utf-8")).body) > 1
