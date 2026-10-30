"""No-model controls for the matched-input diagnostic runner."""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import harness_convergence_r2 as trial


@pytest.fixture
def root(tmp_path):
    for folder in ("src", "tests"):
        shutil.copytree(trial.base.FIXTURE / folder, tmp_path / folder)
    shutil.copyfile(trial.base.SHORT / trial.base.SOURCE, tmp_path / trial.base.SOURCE)
    shutil.copyfile(trial.base.FIXTURE / "pyproject.toml", tmp_path / "pyproject.toml")
    (tmp_path / ".agent").mkdir()
    for name in ("packet.json", "config.json"):
        shutil.copyfile(trial.base.LONG / ".agent" / name, tmp_path / ".agent" / name)
    return tmp_path


@pytest.mark.parametrize(
    "variant",
    [
        "valid",
        "stale",
        "scope",
        "noop",
        "newline-noop",
        "signature",
        "neighbor",
        "blocked",
    ],
)
def test_r2_guarded_proposals_preserve_scope_and_versions(root, variant):
    module = trial.load_runtime()
    before = (root / trial.base.SOURCE).read_bytes()
    text = before.decode("utf-8").replace("\r\n", "\n")
    block = trial.base.method(text)
    long_line = next(line for line in block.splitlines() if len(line) > 100)
    fixed = block.replace(
        long_line,
        '        """Get traces sequentially, preserving order and identity."""',
    )
    args = {
        "path": trial.base.SOURCE,
        "expected_sha256": trial.base.sha(root / trial.base.SOURCE),
        "find": block,
        "replace": fixed,
    }
    if variant == "stale":
        args["expected_sha256"] = "0" * 64
    elif variant == "scope":
        args["path"] = "tests/test_get_many.py"
    elif variant == "noop":
        args["replace"] = block
    elif variant == "newline-noop":
        args["replace"] = block.replace("\n", "\r\n")
    elif variant == "signature":
        args["replace"] = fixed.replace(
            "source_trace_ids: list[str]", "source_trace_ids: str"
        )
    elif variant == "neighbor":
        args["find"] = "class MlflowTraceSource:"
    response = (
        json.dumps(args) if variant != "blocked" else '{"blocked_reason":"Need scope"}'
    )
    lock = module.RepoWriteLock(root, "offline-control")
    lock.acquire()
    try:
        if variant in {"valid", "blocked"}:
            result = trial.apply_proposal(
                module, root, response, trial.base.sha(root / trial.base.SOURCE), lock
            )
            assert result["status"] == ("applied" if variant == "valid" else "blocked")
        else:
            with pytest.raises((ValueError, module.SafeEditError)):
                trial.apply_proposal(
                    module,
                    root,
                    response,
                    trial.base.sha(root / trial.base.SOURCE),
                    lock,
                )
        assert ((root / trial.base.SOURCE).read_bytes() != before) == (
            variant == "valid"
        )
    finally:
        lock.release()


@pytest.mark.parametrize("arm", ["minimal", "formal"])
def test_r2_context_contains_same_hard_contract_and_current_error(root, arm):
    error = f"{trial.base.SOURCE}:84:101: E501 Line too long (159 > 100)"
    facts = {
        "checks": [
            {"exit_code": 0, "stdout": ""},
            {"exit_code": 0, "stdout": ""},
            {"exit_code": 1, "stdout": error},
            {"exit_code": 0, "stdout": ""},
        ]
    }
    messages = trial.messages_for(root, arm, facts)
    assert len(messages) == 2
    assert messages[0]["content"] == trial.load_runtime().SINGLE_FUNCTION.PATCH_PROMPT
    current = json.loads(messages[1]["content"])
    contract = current["packet"] if arm == "formal" else current
    packet = trial.base.read(root / ".agent/packet.json")
    for key in (
        "required_behavior",
        "required_order",
        "forbidden_orderings",
        "acceptance_scenarios",
    ):
        assert contract[key] == packet[key]
    assert error in messages[1]["content"]
    assert current["target"]["sha256"] == trial.base.sha(root / trial.base.SOURCE)
    assert current["target"]["dependencies"] == trial.DEPENDENCIES
    assert (
        "current_validation_failure" in current
        if arm == "formal"
        else "validation_failure" in current
    )
