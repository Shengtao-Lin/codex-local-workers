"""No-model integration and fail-closed controls for the new opt-in protocol."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(
        "host_test_" + name.replace("-", "_"), KIT / ".local-agents" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


W = load("worker-runtime")
H = load("host-proposal")
U = load("local-unit")
R = load("reviewer-runtime")


class Client:
    timeout = 30

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        return json.dumps(next(self.responses))


def build(root, responses=None, *, green=False):
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src/example.py").write_text(
        "def value():\n    return " + ("2" if green else "1") + "\n", encoding="utf-8"
    )
    (root / "tests/test_example.py").write_text(
        "from src.example import value\ndef test_value():\n    assert value() == 2\n",
        encoding="utf-8",
    )
    packet = {
        "schema_version": 2,
        "task_id": "host-test",
        "unit_id": "value",
        "run_id": "run-1",
        "goal": "Return 2",
        "plan_revision": 1,
        "packet_revision": 1,
        "scope": {
            "read": ["src", "tests"],
            "modify": ["src/example.py"],
            "create": [],
            "readonly": ["tests"],
            "forbidden": [],
        },
        "required_behavior": [{"id": "value", "text": "Return 2"}],
        "required_order": ["Compute before returning"],
        "forbidden_orderings": [],
        "acceptance_criteria": ["Tests pass"],
        "focused_tests": ["tests/test_example.py"],
        "validation_profile": "focused",
        "contract_check_required": True,
        "limits": {"max_model_turns": 6, "max_local_repairs": 2},
    }
    config = {
        "host_proposal_enabled": True,
        "coder_structured_output": False,
        "coder_single_function": {
            "path": "src/example.py",
            "symbol": "value",
            "dependencies": "No dependencies",
        },
        "validation_profiles": {
            "focused": {
                "python": sys.executable,
                "compile": True,
                "pytest_argv": ["-B", "-m", "pytest"],
                "commands": [
                    {
                        "id": "static-control",
                        "argv": [
                            "{python}",
                            "-B",
                            "-c",
                            "print('independent configured check')",
                        ],
                    }
                ],
            }
        },
    }
    client = Client(
        responses
        if responses is not None
        else [{"replacement": "def value():\n    return 2"}]
    )
    runtime = H.make_runtime_class(W)(root, packet, config, client)
    return runtime, config, client


@pytest.fixture
def passed(tmp_path):
    runtime, config, client = build(tmp_path)
    report = runtime.run()
    assert report["status"] == H.PROTOCOL.PENDING, report
    assert len(client.calls) == 1
    assert runtime.validation_count == 2
    assert report["validation"]["contract_check"] is None
    return runtime, config, report


def test_current_real_evidence_enters_unchanged_reviewer(passed):
    runtime, config, report = passed
    identity = U.verify_handoff(runtime.repo_root, report, config=config)
    reviewer = R.ReviewerRuntime(
        runtime.repo_root,
        {
            **identity,
            "review_id": "review-1",
            "execution_protocol": H.PROTOCOL.PROTOCOL,
        },
        config,
        Client([]),
    )
    assert reviewer.packet["required_order"]
    assert reviewer.validation["contract_check"] is None
    assert reviewer.handoff["status"] == H.PROTOCOL.PENDING


@pytest.mark.parametrize(
    "mutation",
    [
        "no_optin",
        "unknown_protocol",
        "source_changed",
        "test_changed",
        "manifest_missing",
        "contract_forgery",
        "check_removed",
        "junit_changed",
        "packet_changed",
        "config_changed",
        "legacy_status",
    ],
)
def test_handoff_negative_controls(passed, mutation):
    runtime, config, report = passed
    archive, root = runtime.archive.run_root, runtime.repo_root
    if mutation == "no_optin":
        config = {}
    elif mutation == "unknown_protocol":
        report["execution_protocol"] = "future-v99"
    elif mutation in {"source_changed", "test_changed"}:
        path = root / (
            "src/example.py"
            if mutation == "source_changed"
            else "tests/test_example.py"
        )
        path.write_text(path.read_text() + "\n# external change\n", encoding="utf-8")
    elif mutation == "manifest_missing":
        (archive / "host-validation-facts.json").rename(
            archive / "removed-manifest.json"
        )
    elif mutation == "config_changed":
        config = {**config, "changed": True}
    elif mutation == "legacy_status":
        report["status"] = "ready_for_review"
    else:
        name = {
            "contract_forgery": "validation.json",
            "check_removed": "validation.json",
            "junit_changed": "pytest-junit-2.xml",
            "packet_changed": "packet.json",
        }[mutation]
        path = archive / name
        if mutation == "junit_changed":
            path.write_text("<testsuites><testsuite/></testsuites>", encoding="utf-8")
        else:
            value = json.loads(path.read_text())
            if mutation == "contract_forgery":
                value["contract_check"] = {"required_order_confirmed": True}
            elif mutation == "check_removed":
                value["configured_checks"] = []
            else:
                value["required_behavior"] = []
            path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        U.verify_handoff(root, report, config=config)


def test_green_baseline_and_two_noops_do_not_qualify(tmp_path):
    runtime, _, client = build(
        tmp_path, [{"replacement": "def value():\n    return 2"}] * 2, green=True
    )
    report = runtime.run()
    assert report["status"] == "failed"
    assert "no progress" in report["failure_reason"]
    assert len(client.calls) == 2
    assert runtime.validation_count == 1
    assert not runtime.changed


def test_model_block_preserves_unknown_assessment(tmp_path):
    runtime, _, client = build(
        tmp_path, [{"blocked_reason": "Dependency evidence is missing"}]
    )
    report = runtime.run()
    assert report["status"] == "blocked"
    assert len(client.calls) == 1
    assert not (runtime.archive.run_root / "host-validation-facts.json").exists()


def test_plain_model_validate_cannot_bypass_contract(passed):
    runtime, _, _ = passed
    with pytest.raises(W.WorkerError):
        runtime._contract_check({}, diagnostic=True)
    with pytest.raises(W.WorkerError, match="not model actions"):
        runtime.validate({})


def test_duplicate_review_dispatch_is_rejected(passed):
    runtime, config, report = passed
    identity = U.verify_handoff(runtime.repo_root, report, config=config)
    request = {
        **identity,
        "review_id": "first",
        "execution_protocol": H.PROTOCOL.PROTOCOL,
    }
    first = R.ReviewerRuntime(runtime.repo_root, request, config, Client([]))
    first.prepare()
    second = R.ReviewerRuntime(
        runtime.repo_root, {**request, "review_id": "second"}, config, Client([])
    )
    with pytest.raises(
        (R.ReviewError, W.RUN_STATE.RunStateError), match="dispatch|already"
    ):
        second.prepare()


def test_qualified_interface_is_mechanically_unchanged():
    sys.path.insert(0, str(KIT / "benchmarks"))
    import harness_r2_boundary as old
    import harness_r2_output as output
    import harness_r2_rendering as rendering

    assert H.INTERFACE.WHOLE_SCHEMA == output.WHOLE_SCHEMA
    assert H.INTERFACE.WHOLE_PROMPT == output.WHOLE_PROMPT
    binding = {
        "path": output.B.SOURCE,
        "symbol": output.B.SYMBOL,
        "sha256": "a" * 64,
        "source": "def f():\n    return 1\n",
    }
    for suffix in ("", "\n", "\r\n"):
        raw = json.dumps({"replacement": "def f():\n    return 2" + suffix})
        args = H.INTERFACE.normalize_whole(raw, binding)
        assert args == output.normalize_whole(raw, binding)
        assert H.INTERFACE.terminal_boundary(args) == old.terminal_boundary(args)
    facts = {
        "target": {"source": binding["source"]},
        "validation_failure": {"diagnostics": [{"current_source_line": "line"}]},
    }
    assert H.INTERFACE.literal_input(facts) == rendering.literal_input(facts)


def test_checks_and_requests_are_bounded(tmp_path):
    runtime, _, client = build(
        tmp_path,
        [
            {"replacement": "def value():\n    return 3"},
            {"replacement": "def value():\n    return 4"},
        ],
    )
    report = runtime.run()
    assert report["status"] == "failed"
    assert runtime.validation_count == 3
    assert len(client.calls) == 2
    assert "budget exhausted" in report["failure_reason"]


def test_malformed_and_out_of_function_proposals_never_edit(tmp_path):
    runtime, _, client = build(
        tmp_path, [{"replacement": "def other():\n    return 2"}]
    )
    report = runtime.run()
    assert report["status"] != H.PROTOCOL.PENDING
    assert not runtime.changed
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "failure",
    [
        "zero_tests",
        "all_skipped",
        "false_assessment",
        "missing_check",
        "changed_command",
        "old_revision",
        "archive_escape",
    ],
)
def test_self_consistent_but_invalid_host_facts_fail_closed(passed, failure):
    runtime, config, report = passed
    root = runtime.archive.run_root
    manifest_path = root / "host-validation-facts.json"
    manifest = json.loads(manifest_path.read_text())
    validation = json.loads((root / "validation.json").read_text())
    if failure in {"zero_tests", "all_skipped"}:
        body = (
            ""
            if failure == "zero_tests"
            else '<testcase name="skip"><skipped/></testcase>'
        )
        (root / "pytest-junit-2.xml").write_text(
            "<testsuites><testsuite>" + body + "</testsuite></testsuites>",
            encoding="utf-8",
        )
    elif failure == "false_assessment":
        validation["contract_check"] = {"required_order_confirmed": False}
    elif failure == "missing_check":
        validation["configured_checks"] = []
    elif failure == "changed_command":
        validation["configured_checks"][0]["argv"] = ["not-the-command"]
    elif failure == "old_revision":
        manifest["edit_revision"] += 1
    else:
        manifest["artifact_hashes"]["../outside.json"] = "f" * 64
    (root / "validation.json").write_text(json.dumps(validation), encoding="utf-8")
    attempt_path = root / "validation-attempt-2.json"
    attempt = json.loads(attempt_path.read_text())
    attempt["validation"] = validation
    attempt_path.write_text(json.dumps(attempt), encoding="utf-8")
    for path in (root / "validation.json", attempt_path, root / "pytest-junit-2.xml"):
        manifest["artifact_hashes"][path.name] = H.PROTOCOL.digest(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        U.verify_handoff(runtime.repo_root, report, config=config)


def test_primary_cannot_accept_host_facts_without_reviewer(passed, monkeypatch):
    runtime, config, report = passed
    primary = load("record-review")
    config_path = runtime.repo_root / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record-review",
            "--repo",
            str(runtime.repo_root),
            "--config",
            str(config_path),
            "--task-id",
            report["task_id"],
            "--run-id",
            report["run_id"],
            "--decision",
            "accept",
            "--summary",
            "cannot bypass",
        ],
    )
    assert primary.main() != 0
    assert not (runtime.archive.run_root / "review.json").exists()
