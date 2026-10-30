"""Negative controls for the opt-in normal-entry candidate; no model calls."""

import copy
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
import test_worker_runtime as helpers

R = helpers.RUNTIME
SOURCE = "def target():\n    return 1\n\n\ndef other():\n    return 9\n"
SPEC = {"path": "src/example.py", "symbol": "target", "dependencies": "No dependencies."}


@pytest.fixture
def runtime():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        helpers.WorkerRuntimeTests().make_tree(root)
        (root / SPEC["path"]).write_text(SOURCE, encoding="utf-8")
        instance = R.WorkerRuntime(
            root,
            helpers.packet_v2(),
            {
                "python": sys.executable,
                "coder_single_function": SPEC,
                "coder_block_edits_only": True,
            },
            helpers.FakeClient([]),
        )
        instance.write_lock.acquire()
        instance._prepare_run_archive()
        try:
            yield instance
        finally:
            instance.close()


def messages(runtime):
    return runtime._trim_messages(
        [{"role": "system", "content": "old"}, {"role": "user", "content": "old packet"}]
    )


def edit(runtime, **overrides):
    current = json.loads(messages(runtime)[1]["content"])["target"]
    return {
        "path": SPEC["path"],
        "expected_sha256": current["sha256"],
        "find": "return 1",
        "replace": "return 2",
        **overrides,
    }


@pytest.mark.parametrize(
    "override",
    [
        {"path": "tests/test_example.py"},
        {"find": "return 9", "replace": "return 3"},
        {"find": "def target():", "replace": "def target(x):"},
        {"find": "    return 1", "replace": "    return 2\n\ndef injected():\n    return 7"},
        {"expected_sha256": "0" * 64},
        {"replace": "return 1"},
    ],
)
def test_bad_edit_cannot_write(runtime, override):
    with pytest.raises((R.WorkerError, R.SafeEditError)):
        runtime.safe_replace(edit(runtime, **override))
    assert (runtime.repo_root / SPEC["path"]).read_text() == SOURCE


def test_concurrent_source_change_rejects_old_proposal(runtime):
    proposal = edit(runtime)
    path = runtime.repo_root / SPEC["path"]
    path.write_text(SOURCE.replace("return 1", "return 3"))
    with pytest.raises((R.WorkerError, R.SafeEditError)):
        runtime.safe_replace(proposal)
    assert "return 3" in path.read_text()


def test_context_keeps_task_constraints_and_current_version_not_full_file(runtime):
    before = json.loads(messages(runtime)[1]["content"])
    assert "def other" not in before["target"]["source"]
    assert before["contract_check_field_shape_not_confirmation"]["required_order_confirmed"] is None
    runtime.safe_replace(edit(runtime))
    after = json.loads(messages(runtime)[1]["content"])
    assert after["packet"] == before["packet"]
    assert after["target"]["sha256"] != before["target"]["sha256"]
    assert "return 2" in after["target"]["source"]
    assert runtime.last_contract_check is None


def test_other_write_actions_rejected(runtime):
    for action in [runtime.safe_create, runtime.safe_replace_line]:
        with pytest.raises(R.WorkerError, match="unavailable"):
            action({})


@pytest.mark.parametrize("variant", ["two-files", "create", "bad-shape"])
def test_invalid_configuration(variant):
    packet = helpers.packet_v2()
    spec = copy.deepcopy(SPEC)
    if variant == "two-files":
        packet["scope"]["modify"].append("src/another.py")
    elif variant == "create":
        packet["scope"]["create"] = ["src/new.py"]
    else:
        spec.pop("symbol")
    with pytest.raises(ValueError):
        R.SINGLE_FUNCTION.configure(spec, packet)


@pytest.mark.parametrize("case", ["drift", "formatter-failed", "semantics", "protected", "ok"])
def test_scoped_formatter_safety_and_invalidation(runtime, case):
    runtime.safe_replace(edit(runtime, replace="return 2  "))
    target = runtime.repo_root / SPEC["path"]
    runtime.validated_input_facts = {"old": "must be invalidated"}
    if case == "drift":
        target.write_text(target.read_text().replace("return 2", "return 8"))

    def formatter(argv):
        assert argv[-1:] == [SPEC["path"]]
        target.write_text(target.read_text().replace("return 2  ", "return 2"))
        if case == "semantics":
            target.write_text(target.read_text().replace("return 2", "return 6"))
        if case == "protected":
            (runtime.repo_root / "tests/test_example.py").write_text("# tampered\n")
        return {
            "status": "failed" if case == "formatter-failed" else "passed",
            "exit_code": 1 if case == "formatter-failed" else 0,
        }

    with patch.object(runtime, "_run_command", side_effect=formatter) as command:
        if case != "ok":
            with pytest.raises((R.WorkerError, R.PolicyViolation)):
                runtime._try_autoformat(Path(sys.executable))
        else:
            assert runtime._try_autoformat(Path(sys.executable))
            assert runtime.edit_revision == 2
            assert runtime.validated_input_facts is None
        if case == "drift":
            command.assert_not_called()
    assert not runtime._validated_terminal_state()


def test_finish_cannot_use_validation_from_before_edit(runtime):
    runtime.safe_replace(edit(runtime))
    with pytest.raises(R.WorkerError, match="successful VALIDATE"):
        runtime.execute({"action": "FINISH_SUCCESS", "arguments": {"summary": ["done"]}})
