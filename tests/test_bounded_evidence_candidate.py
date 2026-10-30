"""No-network checks for actual A/B dispatcher and canonical evidence."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import bounded_evidence_candidate as C
import capture_fixture_support as F
from test_evidence_budget_preparation import (  # noqa: F401 - fixture reuse
    client_type,
    setup_runtime,
)


@pytest.fixture
def build(request):
    root, packet, config, _worker, _host, _cls, _archive = request.getfixturevalue(
        "setup_runtime"
    )
    config.update(
        experimental_bounded_evidence="B",
        experimental_evidence_files=[
            "src/product/metadata.py",
            "tests/test_cyclic_metadata.py",
        ],
    )

    def create(responses, arm="B"):
        config["experimental_bounded_evidence"] = arm
        worker = F.load(
            root / ".local-agents/worker-runtime.py", "bounded_control_worker"
        )
        host = F.load(root / ".local-agents/host-proposal.py", "bounded_control_host")
        policy_sha = F.P.digest(root / F.POLICY_PATH)
        C.install_binding(worker, F.POLICY_PATH, policy_sha)
        cls = C.make_runtime(worker, host)

        class Client(client_type()):
            def complete(self, messages):
                self.calls += 1
                value = responses[self.calls - 1]
                if callable(value):
                    return value(messages, worker, host)
                return json.dumps(value)

        runtime = cls(root, packet, config, Client())
        runtime.preflight()
        return runtime, worker, host

    return create


def test_read_search_then_block(build):
    runtime, _w, _h = build(
        [
            {"search": {"path": "tests/test_cyclic_metadata.py", "query": "test_"}},
            {
                "read": {
                    "path": "tests/test_cyclic_metadata.py",
                    "start_line": 1,
                    "end_line": 12,
                }
            },
            {"blocked_reason": "control ends"},
        ]
    )
    report = runtime.run()
    assert report["status"] == "blocked"
    assert runtime.ledger["requests"] == 3 and runtime.ledger["evidence_actions"] == 2
    request = F.P.json.loads(
        (runtime.archive.run_root / "proposal-request-3.json").read_text()
    )
    facts = _h.INTERFACE.restore_literal(request["messages"][1]["content"])
    assert len(facts["evidence_observations"]) == 2
    assert "VALIDATE" not in json.dumps(facts["evidence_observations"])


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "acceptance/capture-policy.json",
        ".agent/packet.json",
        "tests/not-approved.py",
    ],
)
def test_private_or_unapproved_evidence_stops(build, path):
    runtime, _w, _h = build([{"read": {"path": path, "start_line": 1, "end_line": 2}}])
    report = runtime.run()
    assert report["status"] == "policy_violation"
    assert runtime.ledger["effective_edits"] == runtime.ledger["evidence_actions"] == 0


def test_protocol_and_length_recover_without_edit(build):
    def length(_messages, worker, _host):
        raise worker.ModelRequestError("output_token_limit", "truncated", {})

    runtime, _w, _h = build([lambda *_: "{broken", length, {"blocked_reason": "end"}])
    report = runtime.run()
    assert report["status"] == "blocked"
    assert (
        runtime.ledger["requests"] == 3 and runtime.ledger["protocol_recoveries"] == 2
    )
    assert runtime.validation_count == 1 and runtime.host_edits == 0


def test_protocol_recovery_is_bounded(build):
    runtime, _w, _h = build([lambda *_: "invalid"] * 3)
    assert "Protocol recovery budget" in runtime.run()["failure_reason"]
    assert runtime.client.calls == 3 and runtime.ledger["protocol_recoveries"] == 2


def test_duplicate_reads_stop(build):
    request = {
        "read": {
            "path": "tests/test_cyclic_metadata.py",
            "start_line": 1,
            "end_line": 10,
        }
    }
    runtime, _w, _h = build([request] * 4)
    assert "no progress" in runtime.run()["failure_reason"]
    assert runtime.client.calls == 4


def test_a_rejects_read_action_without_free_calls(build):
    runtime, _w, _h = build(
        [
            {
                "read": {
                    "path": "tests/test_cyclic_metadata.py",
                    "start_line": 1,
                    "end_line": 2,
                }
            },
            {"blocked_reason": "end"},
        ],
        "A",
    )
    assert runtime.run()["status"] == "blocked"
    assert runtime.ledger["requests"] == 2 and runtime.ledger["evidence_actions"] == 0


def test_noop_budget(build):
    def noop(messages, _w, host):
        facts = host.INTERFACE.restore_literal(messages[1]["content"])
        return json.dumps({"replacement": facts["target"]["source"]})

    runtime, _w, _h = build([noop, noop], "A")
    assert "Two unchanged" in runtime.run()["failure_reason"]
    assert runtime.ledger["noops"] == 2 and runtime.validation_count == 1


def test_read_range_protocol_guard(build):
    runtime, _w, _h = build(
        [
            {
                "read": {
                    "path": "tests/test_cyclic_metadata.py",
                    "start_line": 1,
                    "end_line": 121,
                }
            },
            {"blocked_reason": "end"},
        ]
    )
    assert runtime.run()["status"] == "blocked"
    assert (
        runtime.ledger["protocol_recoveries"] == 1
        and runtime.ledger["evidence_actions"] == 0
    )


@pytest.mark.parametrize("arm", ["A", "B"])
def test_three_edits_and_last_request_validation(build, arm):
    def draft(_messages, _worker, _host):
        archive = (
            F.KIT
            / "benchmarks/work/harness-convergence/unified-preparation-20261018-1/cases/new-1/isolated/.agent/tasks/fresh-metadata/runs/unified-new-1"
        )
        return json.loads((archive / "proposal-response-1.json").read_text())["raw"]

    def second(messages, _worker, host):
        facts = host.INTERFACE.restore_literal(messages[1]["content"])
        assert "RUF013" in json.dumps(facts["validation_failure"])
        # A target-source observation from before editing must be gone.
        assert not any(
            "src/product/metadata.py" in item["hashes"]
            for item in facts["evidence_observations"]
        )
        return json.dumps(
            {
                "replacement": facts["repair_span"]["source"].replace(
                    "seen: set[int] = None", "seen: set[str] | None = None"
                )
            }
        )

    def third(messages, _worker, host):
        facts = host.INTERFACE.restore_literal(messages[1]["content"])
        assert "str" in json.dumps(facts["validation_failure"])
        return json.dumps(
            {
                "replacement": facts["target"]["source"].replace(
                    "seen: set[str] | None = None", "seen: set[int] | None = None"
                )
            }
        )

    def noop(messages, _worker, host):
        return json.dumps(
            {
                "replacement": host.INTERFACE.restore_literal(messages[1]["content"])[
                    "target"
                ]["source"]
            }
        )

    responses = []
    if arm == "B":
        responses = [
            {
                "read": {
                    "path": "src/product/metadata.py",
                    "start_line": n,
                    "end_line": n,
                }
            }
            for n in range(1, 7)
        ]
        responses += [lambda *_: "{broken", lambda *_: "{broken", noop]
    runtime, _worker, _host = build([*responses, draft, second, third], arm)
    report = runtime.run()
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert runtime.ledger["requests"] == (12 if arm == "B" else 3)
    assert (
        runtime.host_edits == 3
        and runtime.validation_count == 4
        and runtime.edit_revision == 4
    )
    assert (
        runtime.ledger["initial_checks"] == 1
        and runtime.ledger["post_edit_checks"] == 3
    )
    assert runtime.ledger["formatter"] == 1
    gate = F.load(
        runtime.repo_root / ".local-agents/local-unit.py", "bounded_gate_control"
    )
    identity = gate.verify_handoff(runtime.repo_root, report, config=runtime.config)
    # The frozen Reviewer must actually authenticate and construct its inputs.
    request_path = runtime.repo_root / ".agent/offline-review-request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                **identity,
                "review_id": "offline-control",
                "execution_protocol": report["execution_protocol"],
            }
        ),
        encoding="utf-8",
    )
    config_path = runtime.repo_root / ".agent/offline-review-config.json"
    config_path.write_text(
        json.dumps(
            {
                **runtime.config,
                "reviewer_compact_report": True,
                "reviewer_evidence_state": True,
            }
        ),
        encoding="utf-8",
    )
    inspected = subprocess.run(
        [
            sys.executable,
            "-B",
            str(F.KIT / "benchmarks/reviewer_capture_entry.py"),
            "--runtime-dir",
            str(runtime.repo_root / ".local-agents"),
            "--capture-policy",
            F.POLICY_PATH,
            "--capture-policy-sha256",
            F.P.digest(runtime.repo_root / F.POLICY_PATH),
            "--inspect-only",
            "--request",
            str(request_path),
            "--config",
            str(config_path),
            "--report",
            str(runtime.repo_root / ".agent/offline-review-inspection.json"),
        ],
        cwd=runtime.repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert inspected.returncode == 0, inspected.stderr
    source = runtime.repo_root / "src/product/metadata.py"
    source.write_bytes(source.read_bytes() + b"\n# stale control\n")
    with pytest.raises((RuntimeError, ValueError)):
        gate.verify_handoff(runtime.repo_root, report, config=runtime.config)


def test_total_request_budget_and_evidence_cap(build):
    responses = [
        {
            "read": {
                "path": "tests/test_cyclic_metadata.py",
                "start_line": n,
                "end_line": n,
            }
        }
        for n in range(1, 8)
    ]
    runtime, _w, _h = build(responses)
    assert "Evidence action budget" in runtime.run()["failure_reason"]
    assert runtime.ledger["requests"] == 7 and runtime.ledger["evidence_actions"] == 6


def test_duplicate_json_key_and_fake_validation_rejected(build):
    runtime, _w, _h = build(
        [
            lambda *_: '{"blocked_reason":"x","blocked_reason":"y"}',
            {"VALIDATE": {}},
            {"blocked_reason": "end"},
        ]
    )
    assert runtime.run()["status"] == "blocked"
    assert runtime.ledger["protocol_recoveries"] == 2


def test_deadline_does_not_start_next_request(build):
    def expire(_messages, _worker, _host):
        runtime.deadline = 0
        return json.dumps({"blocked_reason": "too late"})

    runtime, _w, _h = build([expire])
    report = runtime.run()
    assert report["status"] == "interrupted" and runtime.client.calls == 1


@pytest.mark.parametrize("arm", ["A", "B"])
def test_installed_entry_preflight_no_model(build, arm):
    runtime, _w, _h = build([], arm)
    runtime.close()
    config_path = runtime.repo_root / ".agent/installed-control-config.json"
    config_path.write_text(json.dumps(runtime.config), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(F.KIT / "benchmarks/bounded_evidence_entry.py"),
            "--runtime-dir",
            str(runtime.repo_root / ".local-agents"),
            "--capture-policy-sha256",
            F.P.digest(runtime.repo_root / F.POLICY_PATH),
            "--preflight-only",
            "--packet",
            str(runtime.repo_root / ".agent/packet.json"),
            "--config",
            str(config_path),
        ],
        cwd=runtime.repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["model_calls"] == 0
