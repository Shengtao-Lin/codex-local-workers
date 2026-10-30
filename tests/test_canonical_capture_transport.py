"""Real validation/canonical consumer negatives; all clients are scripted offline."""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import reviewer_canonical_capture as C
import reviewer_capture_entry as ENTRY


@pytest.fixture
def ready(tmp_path, request):
    root = tmp_path / "isolated"
    root.mkdir()
    runtime_dir = root / ".local-agents"
    runtime_dir.mkdir()
    for path in (F.KIT / ".local-agents").glob("*.py"):
        shutil.copyfile(path, runtime_dir / path.name)
    (root / "src/product").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src/product/target.py").write_text(
        "def increment(value):\n    return value - 1\n", encoding="utf-8"
    )
    (root / "tests/test_increment.py").write_text(
        "from src.product.target import increment\n\ndef test_increment():\n    assert increment(2) == 3\n",
        encoding="utf-8",
    )
    identity = {
        "task_id": "capture-test",
        "unit_id": "increment",
        "run_id": "attempt-1",
    }
    target = {
        "path": "src/product/target.py",
        "module": "_capture_pure_target",
        "symbol": "increment",
    }
    policy, policy_sha = F.install_material(
        root,
        identity,
        source_paths=[target["path"]],
        target=target,
        family="json-call-model-dump-v1"
        if getattr(request, "param", None) == "generic"
        else "fixed-pure-increment-v1",
        cases=[{"args": [v], "kwargs": {}} for v in (2, -2, 0)]
        if getattr(request, "param", None) == "generic"
        else [2, -2, 0],
        writable=[target["path"]],
        python=sys.executable,
    )
    protected = [F.POLICY_PATH, F.PRODUCER, F.HELPER]
    packet = {
        "schema_version": 2,
        **identity,
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Increment integers by one.",
        "validation_profile": "python-focused",
        "scope": {
            "read": ["src", "tests", *protected],
            "modify": [target["path"]],
            "create": [],
            "readonly": ["tests/test_increment.py", *protected],
            "forbidden": [],
        },
        "required_behavior": [{"id": "increment", "text": "Return input plus one."}],
        "acceptance_criteria": [{"id": "focused", "text": "Focused tests pass."}],
        "focused_tests": ["tests/test_increment.py"],
        "limits": {"max_model_turns": 8},
    }
    config = {
        "reviewer_assessment_protocol": True,
        "reviewer_evidence_ids": True,
        "validation_profiles": {
            "python-focused": {
                "python": sys.executable,
                "compile": True,
                "pytest_argv": ["-B", "-m", "pytest", "-q"],
                "commands": [F.command()],
            }
        },
    }
    worker = F.load(
        runtime_dir / "worker-runtime.py", "capture_worker_" + tmp_path.name
    )

    class Client:
        step = 0

        def complete(self, messages):
            self.step += 1
            if self.step == 1:
                action = {"action": "READ_FILE", "arguments": {"path": target["path"]}}
            elif self.step == 2:
                observation = json.loads(messages[-1]["content"].split("\n", 1)[1])
                action = {
                    "action": "SAFE_REPLACE",
                    "arguments": {
                        "path": target["path"],
                        "expected_sha256": observation["sha256"],
                        "find": "return value - 1",
                        "replace": "return value + 1",
                    },
                }
            elif self.step == 3:
                action = {"action": "VALIDATE", "arguments": {}}
            else:
                action = {
                    "action": "FINISH_SUCCESS",
                    "arguments": {
                        "summary": ["Implemented increment."],
                        "remaining_uncertainty": [],
                    },
                }
            return json.dumps(action)

    coder = worker.WorkerRuntime(root, packet, config, Client())
    F.bind_before_coder(coder, policy, policy_sha)
    report = coder.run()
    assert report["status"] == "ready_for_review", report
    reviewer_module = F.load(
        runtime_dir / "reviewer-runtime.py", "capture_reviewer_" + tmp_path.name
    )
    reviewer = reviewer_module.ReviewerRuntime(
        root, {**identity, "review_id": "capture-offline"}, config, object()
    )
    return reviewer, policy, policy_sha


def test_authentic_capture(ready):
    runtime, _policy, sha = ready
    profiles, provenance = C.load_capture(runtime, F.POLICY_PATH, sha)
    assert [e["outcome"]["value"] for e in profiles[0]["examples"]] == [3, -1, 1]
    assert provenance["protocol"] == C.PROTOCOL
    assert C.load_capture(runtime, F.POLICY_PATH, sha) == (profiles, provenance)


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "policy",
        "producer",
        "helper",
        "expected-sha",
        "missing-epoch",
        "validation",
        "junit",
    ],
)
def test_canonical_negative(ready, change):
    runtime, policy, sha = ready
    if change in {"source", "policy", "producer", "helper"}:
        path = {
            "source": policy["target"]["path"],
            "policy": F.POLICY_PATH,
            "producer": F.PRODUCER,
            "helper": F.HELPER,
        }[change]
        with (runtime.repo_root / path).open("a", encoding="utf-8") as stream:
            stream.write("\n# changed\n")
    elif change == "expected-sha":
        sha = "0" * 64
    elif change == "missing-epoch":
        runtime.expected_inputs.pop(F.HELPER)
    elif change == "validation":
        runtime.validation["configured_checks"] = []
    else:
        path = runtime.repo_root / runtime.validation["focused_tests"]["junit"]["path"]
        path.write_text(
            '<testsuites><testsuite tests="1"><testcase name="skip"><skipped/></testcase></testsuite></testsuites>',
            encoding="utf-8",
        )
    with pytest.raises((ValueError, RuntimeError)):
        C.load_capture(runtime, F.POLICY_PATH, sha)


def test_semantic_fields_and_input_loss_rejected(ready):
    runtime, policy, sha = ready
    profiles, _ = C.load_capture(runtime, F.POLICY_PATH, sha)
    manifest = C.PRODUCER.manifest_for(runtime.repo_root, F.POLICY_PATH, policy)
    for change in ("expected", "verdict", "input"):
        mutated = copy.deepcopy(profiles)
        if change == "input":
            mutated[0]["examples"][0]["input"] = False
        else:
            mutated[0]["examples"][0][change] = "pass"
        with pytest.raises(C.CaptureRejected):
            C.validate_profiles(mutated, policy, manifest)


def test_installed_entry_is_lossless_and_offline(ready):
    runtime, _policy, sha = ready
    config = {
        **runtime.config,
        "reviewer_compact_report": True,
        "reviewer_evidence_state": True,
    }
    request_path = runtime.repo_root / "acceptance/offline-request.json"
    request_path.write_text(
        json.dumps({**runtime.request, "review_id": "entry-inspection"}),
        encoding="utf-8",
    )
    config_path = runtime.repo_root / "acceptance/offline-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    report_path = runtime.repo_root / ".agent/offline-capture-inspection.json"
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(F.KIT / "benchmarks/reviewer_capture_entry.py"),
            "--runtime-dir",
            str(runtime.repo_root / ".local-agents"),
            "--capture-policy",
            F.POLICY_PATH,
            "--capture-policy-sha256",
            sha,
            "--inspect-only",
            "--request",
            str(request_path),
            "--config",
            str(config_path),
            "--report",
            str(report_path),
        ],
        cwd=runtime.repo_root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    profiles, _ = C.load_capture(runtime, F.POLICY_PATH, sha)
    assert report["bundle"]["approved_observations"] == profiles
    assert report["model_calls"] == 0 and report["reviewer_acceptance"] is False


def test_semantic_adapter_rejects_post_bundle_drift(ready):
    runtime, policy, sha = ready
    module = F.load(
        runtime.repo_root / ".local-agents/reviewer-runtime.py", "capture_adapter_drift"
    )
    cls = ENTRY.install(module, F.POLICY_PATH, sha)
    reviewer = cls(
        runtime.repo_root,
        {**runtime.request, "review_id": "adapter-drift"},
        {
            **runtime.config,
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
        },
        object(),
    )
    reviewer.bundle()
    with (runtime.repo_root / policy["target"]["path"]).open(
        "a", encoding="utf-8"
    ) as stream:
        stream.write("\n# drift\n")
    with pytest.raises((ValueError, RuntimeError)):
        reviewer._assert_inputs_current()


@pytest.mark.parametrize("ready", ["generic"], indirect=True)
def test_generic_producer_installed_roundtrip(ready):
    runtime, policy, sha = ready
    profiles, _ = C.load_capture(runtime, F.POLICY_PATH, sha)
    assert profiles[0]["profile_id"] == policy["family"] == "json-call-model-dump-v1"
    assert [e["outcome"]["value"] for e in profiles[0]["examples"]] == [3, -1, 1]
    assert all(e["input_unchanged"] is True for e in profiles[0]["examples"])
    test_installed_entry_is_lossless_and_offline(ready)


@pytest.mark.parametrize(
    "change", ["command", "duplicate", "writable-policy", "identity", "archive-drift"]
)
def test_more_provenance_negatives(ready, change):
    runtime, _policy, sha = ready
    if change == "command":
        runtime.config["validation_profiles"]["python-focused"]["commands"][0][
            "argv"
        ].append("--extra")
    elif change == "duplicate":
        runtime.validation["configured_checks"].append(
            copy.deepcopy(runtime.validation["configured_checks"][0])
        )
    elif change == "writable-policy":
        runtime.packet["scope"]["modify"].append(F.POLICY_PATH)
    elif change == "identity":
        runtime.run_id = "another-run"
    else:
        C.load_capture(runtime, F.POLICY_PATH, sha)
        with (runtime.run_root / "cumulative.diff").open(
            "a", encoding="utf-8"
        ) as stream:
            stream.write("\n")
    with pytest.raises((ValueError, RuntimeError)):
        C.load_capture(runtime, F.POLICY_PATH, sha)
