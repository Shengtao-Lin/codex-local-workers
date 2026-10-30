"""Terminal promotion must use actual validation and unchanged model acknowledgements."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import test_single_function_context as single
import test_worker_runtime as helpers

R = helpers.RUNTIME


def runtime_at(root, *, ordering=False):
    helpers.WorkerRuntimeTests().make_tree(root)
    (root / single.SPEC["path"]).write_text(single.SOURCE, encoding="utf-8")
    packet = helpers.packet_v2()
    packet["contract_check_required"] = True
    if ordering:
        packet["required_order"] = ["Return only after the required operation."]
    config = {
        "python": sys.executable,
        "coder_single_function": single.SPEC,
        "coder_block_edits_only": True,
        "validation_profiles": {
            "python-focused": {
                "python": sys.executable,
                "commands": [{"id": "static", "argv": ["{python}", "--version"]}],
            }
        },
    }
    return R.WorkerRuntime(root, packet, config, helpers.FakeClient([]))


def fake_command(argv, *, fail=False, zero=False):
    junit = next((a.split("=", 1)[1] for a in argv if a.startswith("--junitxml=")), None)
    if junit:
        Path(junit).write_text(
            '<testsuites><testsuite tests="'
            + str(0 if zero else 1)
            + '" failures="0" errors="0" skipped="0" /></testsuites>',
            encoding="utf-8",
        )
    return {
        "status": "failed" if fail and not junit else "passed",
        "exit_code": int(fail and not junit),
        "output": "observed check",
        "argv": argv,
    }


@pytest.mark.parametrize(
    "case", ["baseline", "missing", "unknown", "false", "static-fail", "zero", "valid", "drift"]
)
def test_promotion_controls(tmp_path, case):
    runtime = runtime_at(tmp_path, ordering=case in {"unknown", "false"})
    runtime.write_lock.acquire()
    runtime._prepare_run_archive()
    check = runtime.contract_check_template()
    if case in {"unknown", "false"}:
        check["required_order_confirmed"] = None if case == "unknown" else False
    try:
        if case != "baseline":
            runtime.safe_replace(single.edit(runtime))
        args = {} if case == "missing" else {"contract_check": check}
        with patch.object(
            runtime,
            "_run_command",
            side_effect=lambda argv: fake_command(
                argv, fail=case == "static-fail", zero=case == "zero"
            ),
        ):
            if case == "missing":
                with pytest.raises(R.WorkerError, match="requires contract_check"):
                    runtime.validate(args)
            else:
                runtime.validate(args)
        if case == "drift":
            (tmp_path / single.SPEC["path"]).write_text(
                single.SOURCE.replace("return 1", "return 8")
            )
        assert runtime._validated_terminal_state() == (case == "valid")
        if case in {"unknown", "false"}:
            assert (
                runtime.validation.contract_check["required_order_confirmed"]
                is check["required_order_confirmed"]
            )
        if case == "valid":
            archive = json.loads((tmp_path / runtime.validation_refs[-1]).read_text())
            assert archive["phase"] == "final"
            assert runtime.validation_phase == "final"
    finally:
        runtime.close()


def test_default_check_enters_existing_nudge_then_finalizes_without_executing_extra_edit(tmp_path):
    runtime = runtime_at(tmp_path)
    steps = []

    def complete(messages):
        steps.append(messages)
        number = len(steps)
        if number == 1:
            envelope = {"action": "SAFE_REPLACE", "arguments": single.edit(runtime)}
        elif number == 2:
            envelope = {
                "action": "VALIDATE",
                "arguments": {"contract_check": runtime.contract_check_template()},
            }
        else:
            envelope = {
                "action": "SAFE_REPLACE",
                "arguments": {
                    "path": single.SPEC["path"],
                    "expected_sha256": "0" * 64,
                    "find": "return 2",
                    "replace": "return 9",
                },
            }
        return json.dumps(envelope)

    with (
        patch.object(runtime.client, "complete", side_effect=complete),
        patch.object(runtime, "_run_command", side_effect=fake_command),
    ):
        report = runtime.run()
    assert report["status"] == "ready_for_review"
    assert len(steps) == 4
    assert (tmp_path / single.SPEC["path"]).read_text() == single.SOURCE.replace(
        "return 1", "return 2"
    )
    events = (tmp_path / report["evidence_refs"]["run_archive"] / "events.jsonl").read_text()
    assert "single_function_terminal_promoted" in events
    assert "validated_terminal_nudge_issued" in events
    assert "validated_terminal_runtime_finalized" in events
