"""Offline new-protocol boundaries; no compatibility or model credit."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / ".local-agents/tests"))
import host_proposal_kernel as host
import test_worker_runtime as helpers
import test_single_function_context as single


@pytest.fixture
def instance(tmp_path):
    helpers.WorkerRuntimeTests().make_tree(tmp_path)
    (tmp_path / single.SPEC["path"]).write_text(single.SOURCE, encoding="utf-8")
    config = {"host_proposal_enabled": True, "coder_single_function": single.SPEC,
              "coder_block_edits_only": True, "python": sys.executable,
              "validation_profiles": {"python-focused": {
                  "python": sys.executable, "commands": [{"id": "static", "argv": ["{python}", "--version"]}]}}}
    packet = helpers.packet_v2()
    packet["contract_check_required"] = True
    runtime = host.HostProposalRuntime(tmp_path, packet, config, helpers.FakeClient([]))
    runtime.write_lock.acquire()
    runtime._prepare_run_archive()
    try:
        yield runtime
    finally:
        runtime.close()


def execute_checks(instance, *, failed=False):
    def command(argv):
        junit = next((a.split("=", 1)[1] for a in argv if a.startswith("--junitxml=")), None)
        if junit:
            Path(junit).write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
                                   '<testcase name="observed"/></testsuite></testsuites>', encoding="utf-8")
        return {"status": "failed" if failed else "passed", "exit_code": int(failed),
                "output": "observed", "argv": argv}
    with patch.object(instance, "_run_command", side_effect=command):
        instance.validate_host()


def edit(instance):
    current = json.loads(host.WORKER.SINGLE_FUNCTION.messages(instance, [])[1]["content"])["target"]
    instance.safe_replace({"path": single.SPEC["path"], "expected_sha256": current["sha256"],
                           "find": "return 1", "replace": "return 2"})


def test_host_checks_do_not_manufacture_confirmation_or_legacy_success(instance):
    edit(instance)
    execute_checks(instance)
    assert instance.validation.contract_check is None
    assert instance.last_contract_check is None
    assert not instance._validated_terminal_state()
    report = instance.complete_host()
    assert report["status"] == host.PENDING
    assert host.verify_host_handoff(instance.repo_root, report, enabled=True)["protocol"] == host.PROTOCOL
    with pytest.raises(ValueError):
        host.verify_host_handoff(instance.repo_root, report)


@pytest.mark.parametrize("case", ["baseline", "failed", "drift"])
def test_host_cannot_complete_invalid_validation(instance, case):
    if case != "baseline":
        edit(instance)
    execute_checks(instance, failed=case == "failed")
    if case == "drift":
        (instance.repo_root / single.SPEC["path"]).write_text(single.SOURCE)
    with pytest.raises(host.WORKER.WorkerError):
        instance.complete_host()


def test_model_validate_without_confirmation_still_rejected(instance):
    with pytest.raises(host.WORKER.WorkerError, match="requires contract_check"):
        instance.validate({})
    assert not instance._host_validation_active


@pytest.mark.parametrize("case", ["unknown-version", "legacy-state", "confirmation", "checks", "identity", "zero", "junit-failure", "outside-scope", "drift"])
def test_new_handoff_fails_closed_on_corrupt_evidence(instance, case):
    edit(instance)
    execute_checks(instance)
    report = instance.complete_host()
    archive = instance.archive.run_root
    if case == "drift":
        (instance.repo_root / single.SPEC["path"]).write_text(single.SOURCE)
    elif case == "junit-failure":
        path = instance.repo_root / instance.validation.focused_tests["junit"]["path"]
        path.write_text('<testsuites><testcase><failure/></testcase></testsuites>')
    else:
        name = {"unknown-version": "execution-protocol.json", "legacy-state": "handoff.json",
                "confirmation": "validation.json", "checks": "validation.json", "identity": "packet.json",
                "zero": "validation.json", "outside-scope": "changes.json"}[case]
        path = archive / name
        data = json.loads(path.read_text())
        if case == "unknown-version":
            data["protocol"] = "unknown"
        elif case == "legacy-state":
            data["status"] = "ready_for_review"
        elif case == "confirmation":
            data["contract_check"] = {"required_order_confirmed": True}
        elif case == "checks":
            data["configured_checks"] = []
        elif case == "identity":
            data["unit_id"] = "wrong-unit"
        elif case == "zero":
            data["focused_tests"]["junit"]["executed"] = 0
        else:
            data["runtime_edits"] = [{"path": "tests/test_example.py"}]
        path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        host.verify_host_handoff(instance.repo_root, report, enabled=True)
