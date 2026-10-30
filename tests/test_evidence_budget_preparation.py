"""No-model controls: three edits/checks and reusable bounded evidence methods."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import coder_output_channel as OUTPUT
import coder_prevalidation_format as FORMAT
import coder_unified_preparation as UNIFIED
import evidence_budget_preparation as PREP
import unified_preparation_trial as TRIAL


@pytest.fixture
def setup_runtime(tmp_path, monkeypatch):
    row = TRIAL.T.read(TRIAL.BATCH / "cells.json")["new-1"]
    old = Path(row["root"])
    archive = old / ".agent/tasks/fresh-metadata/runs/unified-new-1"
    preimages = {p["path"]: p for p in TRIAL.T.read(archive / "preimages.json")}
    root = tmp_path / "isolated"
    for name, sha in row["files"].items():
        source = old / name
        if TRIAL.T.sha(source) != sha:
            entry = preimages[name]
            assert entry["sha256"] == sha
            source = old / entry["archive_path"]
        assert TRIAL.T.sha(source) == sha
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    packet = TRIAL.T.read(root / ".agent/packet.json")
    config = TRIAL.T.read(root / ".agent/config.json")
    config.update(
        offline_budget_feasibility=True,
        max_model_turns=12,
        hard_max_model_turns=12,
        invocation_timeout_seconds=900,
    )
    packet["limits"].update(
        max_model_turns=12, hard_max_model_turns=12, max_validation_runs=4
    )
    (root / ".agent/packet.json").write_text(json.dumps(packet), encoding="utf-8")
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
    worker = F.load(
        root / ".local-agents/worker-runtime.py", "budget_worker_" + tmp_path.name
    )
    host = F.load(
        root / ".local-agents/host-proposal.py", "budget_host_" + tmp_path.name
    )
    PREP.install_offline_capture_binding(worker, F.POLICY_PATH, row["policy_sha256"])
    cls = PREP.align_for_offline_replay(
        worker,
        UNIFIED.make_runtime(
            worker,
            host,
            FORMAT.make_runtime(worker, OUTPUT.make_runtime(worker, host, "schema")),
        ),
    )

    # Fail if this offline replay ever attempts an HTTP model request.
    def deny_network(*args, **kwargs):
        raise AssertionError("Network is forbidden in offline preparation")

    monkeypatch.setattr(worker.urllib.request, "urlopen", deny_network)
    return root, packet, config, worker, host, cls, archive


def client_type():
    class Client:
        timeout = 180
        structured_output = True
        action_schema = UNIFIED.SPAN.D.INTERFACE.WHOLE_SCHEMA
        native_tools = None
        typed_action_arguments = False
        calls = 0

    return Client


def test_third_effective_edit_gets_fresh_canonical_validation(setup_runtime):
    root, packet, config, _worker, host, cls, archive = setup_runtime
    # Scripted proposals are offline controls, not model capability evidence.
    first = TRIAL.T.read(archive / "proposal-response-1.json")["raw"]

    class Client(client_type()):
        def complete(self, messages):
            self.calls += 1
            if self.calls == 1:
                return first
            facts = host.INTERFACE.restore_literal(messages[1]["content"])
            if self.calls == 2:
                assert "RUF013" in json.dumps(facts["validation_failure"])
                assert "repair_span" in facts
                return json.dumps(
                    {
                        "replacement": facts["repair_span"]["source"].replace(
                            "seen: set[int] = None", "seen: set[str] | None = None"
                        )
                    }
                )
            assert self.calls == 3
            assert "repair_span" not in facts
            assert "str" in json.dumps(facts["validation_failure"])
            return json.dumps(
                {
                    "replacement": facts["target"]["source"].replace(
                        "seen: set[str] | None = None", "seen: set[int] | None = None"
                    )
                }
            )

    client = Client()
    runtime = cls(root, packet, config, client)
    commands = []
    original = runtime._run_command

    def capture(argv):
        commands.append(argv)
        return original(argv)

    runtime._run_command = capture
    runtime.preflight()
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert runtime.host_edits == client.calls == 3
    assert runtime.validation_count == 4
    assert runtime.edit_revision == 4  # three model edits plus one formatter mutation
    assert sum("pytest" in argv for argv in commands) == 4
    assert sum("format" in argv and "--check" not in argv for argv in commands) == 1
    attempts = [
        TRIAL.T.read(runtime.archive.run_root / f"validation-attempt-{i}.json")
        for i in range(1, 5)
    ]
    assert [a["validation"]["status"] for a in attempts] == [
        "failed",
        "failed",
        "failed",
        "passed",
    ]
    gate = F.load(root / ".local-agents/local-unit.py", "budget_gate")
    gate.verify_handoff(root, report, config=config)
    # No further mutation can inherit the fourth check's acceptance evidence.
    target = root / "src/product/metadata.py"
    target.write_bytes(target.read_bytes() + b"\n# stale control\n")
    with pytest.raises((ValueError, RuntimeError)):
        gate.verify_handoff(root, report, config=config)


def test_read_search_reuse_scopes_and_duplicate_evidence(setup_runtime):
    root, packet, config, worker, _host, cls, _archive = setup_runtime
    runtime = cls(root, packet, config, client_type()())
    try:
        path = "tests/test_cyclic_metadata.py"
        first = runtime.read_file({"path": path, "start_line": 1, "end_line": 12})
        second = runtime.read_file({"path": path, "start_line": 1, "end_line": 12})
        assert first["new_evidence_count"] > 0
        assert second["status"] == "already_read" and second["new_evidence_count"] == 0
        result = runtime.search({"path": path, "query": "def test_", "max_results": 10})
        assert result["results"] and all(r["path"] == path for r in result["results"])
        with pytest.raises((worker.WorkerError, worker.SafeEditError)):
            runtime.read_file({"path": "../outside.py"})
        with pytest.raises((worker.WorkerError, worker.SafeEditError)):
            runtime.search({"path": "../", "query": "secret"})
        with pytest.raises((worker.WorkerError, worker.SafeEditError)):
            runtime.read_file({"path": path, "start_line": 1, "end_line": 251})
    finally:
        runtime.close()


def test_offline_opt_in_is_mandatory(setup_runtime):
    root, packet, config, worker, _host, cls, _archive = setup_runtime
    config.pop("offline_budget_feasibility")
    with pytest.raises(worker.WorkerError, match="opt-in"):
        cls(root, packet, config, client_type()())


def test_noops_do_not_spend_edits_or_checks(setup_runtime):
    root, packet, config, _worker, host, cls, _archive = setup_runtime

    class Client(client_type()):
        def complete(self, messages):
            self.calls += 1
            facts = host.INTERFACE.restore_literal(messages[1]["content"])
            return json.dumps({"replacement": facts["target"]["source"]})

    client = Client()
    runtime = cls(root, packet, config, client)
    runtime.preflight()
    report = runtime.run()
    assert report["status"] == "failed"
    assert "Two unchanged proposals" in report["failure_reason"]
    assert (
        client.calls == 2 and runtime.host_edits == 0 and runtime.validation_count == 1
    )
