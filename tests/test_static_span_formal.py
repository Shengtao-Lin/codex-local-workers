"""Actual host/capture handoff replay and static-routing boundary negatives."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
import capture_fixture_support as F
import coder_static_span as SPAN
import repair_representation_diagnostic as D
import reviewer_canonical_capture as CAPTURE

OLD_TEST = F.load(
    F.KIT / "tests/test_prevalidation_format.py", "span_old_scheduling_tests"
)


@pytest.mark.parametrize(
    "change",
    [
        "none",
        "multiple_checks",
        "multiple_errors",
        "wrong_path",
        "outside_function",
        "outer_signature",
        "body_not_header",
        "different_rule",
        "different_parameter",
        "passed_check",
        "no_check",
    ],
)
def test_only_unique_real_owned_header_is_eligible(change):
    fixture = D.T.read(D.BATCH / "fixture.json")
    facts, binding = copy.deepcopy(fixture["facts"]), fixture["binding"]
    source = (D.BATCH / "snapshot.py").read_text(encoding="utf-8")
    root = Path(D.T.read(D.S.BATCH / "cells.json")["new-1"]["root"])
    checks = facts["validation_failure"]["configured_checks"]
    output = checks[0]["output"]
    if change == "multiple_checks":
        checks.append(copy.deepcopy(checks[0]))
    elif change == "multiple_errors":
        checks[0]["output"] += "\nother.py:1:1 - error: another error\n"
    elif change == "wrong_path":
        checks[0]["output"] = output.replace("metadata.py:", "protected.py:")
    elif change in {"outside_function", "outer_signature", "body_not_header"}:
        number = {
            "outside_function": 1,
            "outer_signature": binding["start_line"],
            "body_not_header": fixture["span"]["line"] + 1,
        }[change]
        checks[0]["output"] = output.replace(
            f":{fixture['span']['line']}:", f":{number}:"
        )
    elif change == "different_rule":
        checks[0]["output"] = output.replace(
            "reportMissingParameterType", "reportArgumentType"
        )
    elif change == "different_parameter":
        checks[0]["output"] = output.replace('parameter "obj"', 'parameter "other"')
    elif change == "passed_check":
        checks[0]["status"] = "passed"
    elif change == "no_check":
        checks.clear()
    found = SPAN.locate(facts, binding, source, root)
    assert found == (fixture["span"] if change == "none" else None)


def scripted(tmp_path, *, malformed=False):
    previous, old_client, root, packet, config, _commands = OLD_TEST.setup_runtime(
        tmp_path
    )
    parent = type(previous)
    previous.close()
    worker = sys.modules["scheduled_worker_" + tmp_path.name]
    host = sys.modules["scheduled_host_" + tmp_path.name]
    config["experimental_static_span_repair"] = True
    (root / ".agent/config.json").write_text(json.dumps(config), encoding="utf-8")
    cls = SPAN.make_runtime(worker, host, parent)
    old_complete = old_client.complete
    calls = []

    def complete(messages):
        calls.append(messages)
        if len(calls) == 1:
            assert "repair_span" not in host.INTERFACE.restore_literal(
                messages[1]["content"]
            )
            return old_complete(messages)
        facts = host.INTERFACE.restore_literal(messages[1]["content"])
        assert messages[0]["content"] == D.PROMPTS["span"]
        assert "reportMissingParameterType" in json.dumps(facts["validation_failure"])
        line = facts["repair_span"]["source"]
        if malformed:
            return json.dumps({"replacement": line + "\n        pass"})
        return json.dumps({"replacement": line.replace("(obj)", "(obj: Any)")})

    old_client.complete = complete
    runtime = cls(root, packet, config, old_client)
    runtime.preflight()
    report = runtime.run()
    return runtime, report, calls, root, packet, config


@pytest.mark.parametrize("change", ["none", "source", "protected", "forged_epoch"])
def test_actual_canonical_host_capture_and_negatives(tmp_path, change):
    runtime, report, calls, root, packet, config = scripted(tmp_path)
    assert report["status"] == "validation_passed_pending_review", report.get(
        "failure_reason"
    )
    assert report["worker_assessment"] is None and len(calls) == 2
    assert runtime.validation_count == 3 and runtime.host_edits == 2
    assert runtime.edit_revision == 3 and runtime.autoformat_used is True
    archive = runtime.archive.run_root
    assert D.T.read(archive / "static-span-route-1.json")["mode"] == "whole"
    assert D.T.read(archive / "static-span-route-2.json")["mode"] == "span"
    bound = D.T.read(archive / "static-span-binding-2.json")
    assert bound["code_repair_by_host"] is False
    assert bound["expanded_arguments"]["replace"] == bound["expanded_arguments"][
        "find"
    ].replace(bound["span_arguments"]["find"], bound["span_arguments"]["replace"], 1)
    reviewer_module = F.load(
        root / ".local-agents/reviewer-runtime.py", "formal_span_reviewer_" + change
    )
    request = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
    request.update(
        review_id="offline-span-review", execution_protocol=report["execution_protocol"]
    )
    reviewer = reviewer_module.ReviewerRuntime(root, request, config, object())
    policy_sha = D.T.sha(root / F.POLICY_PATH)
    if change == "none":
        profiles, provenance = CAPTURE.load_capture(reviewer, F.POLICY_PATH, policy_sha)
        assert profiles and provenance
        gate = F.load(root / ".local-agents/local-unit.py", "formal_span_offline_gate")
        assert (
            gate.verify_handoff(root, report, config=config)["run_id"]
            == packet["run_id"]
        )
    else:
        if change == "forged_epoch":
            reviewer.expected_inputs.pop(F.HELPER)
        else:
            path = root / (
                "src/product/metadata.py"
                if change == "source"
                else "tests/test_metadata.py"
            )
            path.write_bytes(path.read_bytes() + b"\n# changed\n")
        with pytest.raises((ValueError, RuntimeError)):
            CAPTURE.load_capture(reviewer, F.POLICY_PATH, policy_sha)


def test_malformed_span_never_becomes_full_edit_or_acceptance(tmp_path):
    runtime, report, calls, _root, _packet, _config = scripted(tmp_path, malformed=True)
    assert report["status"] == "failed"
    assert len(calls) == 6
    assert runtime.host_edits == 1 and runtime.validation_count == 2
    assert not (runtime.archive.run_root / "static-span-binding-2.json").exists()


def test_candidate_needs_explicit_opt_in():
    class Worker:
        WorkerError = RuntimeError

    class Interface:
        normalize_whole = None
        WHOLE_PROMPT = "old"

    class Host:
        INTERFACE = Interface()

    cls = SPAN.make_runtime(Worker, Host, object)
    with pytest.raises(RuntimeError, match="explicit opt-in"):
        cls(None, None, {}, None)
