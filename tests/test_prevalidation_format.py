"""Scripted scheduling controls; gold second proposal is NOT model evidence."""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_coder_entry as BIND
import capture_fixture_support as F
import coder_output_channel as OUTPUT
import coder_prevalidation_format as PREPARE
import output_channel_trial as OLD
import prevalidation_format_audit as AUDIT


def setup_runtime(tmp_path, *, prepared=True, protected_edit=False):
    row = OLD.T.read(OLD.BATCH / "cells.json")["schema-1"]
    root = tmp_path / "isolated"
    root.mkdir()
    # Copy only pristine registered files, not the failed draft/current history.
    seed = OLD.T.read(OLD.M.BATCH / "prepared-cells-v3.json")["metadata-candidate-1"]
    for relative in seed["files"]:
        dst = root / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(seed["root"]) / relative, dst)
    config, packet = (
        OLD.T.read(root / ".agent/config.json"),
        OLD.T.read(root / ".agent/packet.json"),
    )
    config.update(
        coder_structured_output=True,
        experimental_output_channel="schema",
        experimental_prevalidation_format=prepared,
    )
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
    worker = F.load(
        root / ".local-agents/worker-runtime.py", "scheduled_worker_" + tmp_path.name
    )
    host = F.load(
        root / ".local-agents/host-proposal.py", "scheduled_host_" + tmp_path.name
    )
    policy_sha = OLD.T.sha(root / F.POLICY_PATH)
    BIND.install(worker, F.POLICY_PATH, policy_sha)
    cls = OUTPUT.make_runtime(worker, host, "schema")
    if prepared:
        cls = PREPARE.make_runtime(worker, cls)
    previous = Path(row["root"]) / ".agent/tasks/fresh-metadata/runs/output-schema-1"
    first = OLD.T.read(previous / "proposal-response-1.json")["raw"]

    class Scripted:
        timeout = 180
        structured_output = True
        action_schema = OUTPUT.F.load(
            OLD.KIT / ".local-agents/proposal-interface.py",
            "scheduled_schema_" + tmp_path.name,
        ).WHOLE_SCHEMA
        native_tools = None
        typed_action_arguments = False
        calls = 0

        def complete(self, messages):
            self.calls += 1
            if self.calls == 1:
                return first
            facts = host.INTERFACE.restore_literal(messages[1]["content"])
            assert "reportMissingParameterType" in json.dumps(
                facts["validation_failure"]
            )
            # Script only the exact remaining static repair, not a different
            # reference algorithm whose unformatted layout adds another failure.
            source = facts["target"]["source"]
            assert source.count("def check_finite(obj):") == 1
            return json.dumps(
                {
                    "replacement": source.replace(
                        "def check_finite(obj):", "def check_finite(obj: Any) -> None:"
                    )
                }
            )

    client = Scripted()
    runtime = cls(root, packet, config, client)
    runtime.preflight()
    commands = []
    execute = runtime._run_command

    def observed(argv):
        commands.append(argv)
        result = execute(argv)
        if protected_edit and "format" in argv and "--check" not in argv:
            if protected_edit == "semantic":
                path = root / "src/product/metadata.py"
                source = path.read_text(encoding="utf-8")
                assert source.count("return value") == 1
                path.write_text(
                    source.replace("return value", "return {}"), encoding="utf-8"
                )
            else:
                path = root / "tests/test_metadata.py"
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n# forbidden change\n",
                    encoding="utf-8",
                )
        return result

    runtime._run_command = observed
    return runtime, client, root, packet, config, commands


def test_old_schedule_still_fails_before_second_proposal(tmp_path):
    runtime, client, _root, _packet, _config, commands = setup_runtime(
        tmp_path, prepared=False
    )
    report = runtime.run()
    assert report["status"] == "failed"
    assert report["failure_reason"] == "Host patch/check budget exhausted"
    assert client.calls == 1
    assert runtime.validation_count == 3
    assert sum("format" in cmd and "--check" not in cmd for cmd in commands) == 1


@pytest.mark.parametrize("tamper", ["none", "source", "protected"])
def test_new_schedule_repairs_then_original_gate_checks_current_inputs(
    tmp_path, tamper
):
    runtime, client, root, packet, config, commands = setup_runtime(tmp_path)
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert report["worker_assessment"] is None
    assert client.calls == 2
    assert runtime.validation_count == runtime.host_check_cap == 3
    assert runtime.host_edits == 2
    assert runtime.edit_revision == 3  # two proposals plus existing guarded formatter
    assert sum("format" in cmd and "--check" not in cmd for cmd in commands) == 1
    assert sum("pytest" in cmd for cmd in commands) == 3
    receipt = OLD.T.read(runtime.archive.run_root / "prevalidation-format.json")
    assert receipt["validation_count_before"] == receipt["validation_count_after"] == 1
    assert (
        receipt["kind"] == "preparation_not_validation"
        and receipt["acceptance_credit"] is False
    )
    assert receipt["edit_revision_before"] == 1 and receipt["edit_revision_after"] == 2
    assert not (runtime.archive.run_root / "validation-attempt-4.json").exists()
    gate = F.load(root / ".local-agents/local-unit.py", "scheduled_gate_" + tamper)
    if tamper == "none":
        assert (
            gate.verify_handoff(root, report, config=config)["run_id"]
            == packet["run_id"]
        )
    else:
        path = root / (
            "src/product/metadata.py"
            if tamper == "source"
            else "tests/test_metadata.py"
        )
        path.write_text(
            path.read_text(encoding="utf-8") + "\n# stale input\n", encoding="utf-8"
        )
        with pytest.raises((ValueError, RuntimeError)):
            gate.verify_handoff(root, report, config=config)
    if tamper == "none":
        # Persist actual command ledger and preparation receipt outside pytest
        # temp files for independent inspection. Never calls a real model.
        OLD.T.save(
            AUDIT.BATCH / "scripted-command-ledger.json",
            {
                "model_calls": 0,
                "scripted_proposals": client.calls,
                "validation_attempts": runtime.validation_count,
                "commands": [[str(x) for x in cmd] for cmd in commands],
                "preparation": receipt,
                "report_status": report["status"],
                "interpretation": "More actual pytest executions than the old failed run, but not more than the unchanged 3-run ceiling. No cloud/local capability credit.",
            },
        )


def test_formatter_cannot_change_protected_input(tmp_path):
    runtime, client, _root, _packet, _config, _commands = setup_runtime(
        tmp_path, protected_edit=True
    )
    report = runtime.run()
    assert report["status"] == "policy_violation"
    assert "outside this run's writable files" in report["failure_reason"]
    assert client.calls == 1


def test_explicit_opt_in_and_budget_before_preparation():
    class Worker:
        WorkerError = RuntimeError
        PolicyViolation = RuntimeError

    class Parent:
        def __init__(self, *args):
            self.validation_count = self.host_check_cap = 3

        def _introduced_text_quality_issues(self):
            pytest.fail("exhausted budget must reject before preparation")

    cls = PREPARE.make_runtime(Worker, Parent)
    with pytest.raises(RuntimeError, match="explicit opt-in"):
        cls(None, None, {}, None)
    runtime = cls(None, None, {"experimental_prevalidation_format": True}, None)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        runtime.host_validate()


def test_formatter_cannot_change_source_semantics(tmp_path):
    runtime, client, _root, _packet, _config, _commands = setup_runtime(
        tmp_path, protected_edit="semantic"
    )
    report = runtime.run()
    assert report["status"] == "policy_violation"
    assert "formatter changed source semantics" in report["failure_reason"]
    assert client.calls == 1
