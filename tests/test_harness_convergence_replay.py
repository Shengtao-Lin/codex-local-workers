"""R1 controls on the real frozen runtime; no model/network calls.

Equivalent newline proposals must follow SafeEditor semantics. Failures remain
ordinary test failures (not xfail), so the registered R2 live gate stays closed.
"""

import copy
import io
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / ".local-agents/tests"))
import test_local_unit as unit_helpers
import test_single_function_context as single
import test_single_function_terminal as terminal
import test_worker_runtime as helpers

R = single.R
runtime = single.runtime


@pytest.mark.parametrize("file_style", ["lf", "crlf", "bom-crlf"])
@pytest.mark.parametrize("proposal_style", ["lf", "crlf"])
def test_r1_single_function_guard_matches_safe_editor_newlines(
    runtime, tmp_path, file_style, proposal_style
):
    path = runtime.repo_root / single.SPEC["path"]
    text = single.SOURCE.replace("\n", "\r\n") if file_style != "lf" else single.SOURCE
    raw = text.encode("utf-8")
    if file_style == "bom-crlf":
        raw = b"\xef\xbb\xbf" + raw
    path.write_bytes(raw)
    current = json.loads(single.messages(runtime)[1]["content"])["target"]
    find = "def target():\n    return 1"
    replace = "def target():\n    return 2"
    if proposal_style == "crlf":
        find, replace = find.replace("\n", "\r\n"), replace.replace("\n", "\r\n")
    args = {
        "path": single.SPEC["path"],
        "expected_sha256": current["sha256"],
        "find": find,
        "replace": replace,
    }
    # Separate workspace demonstrates that this exact proposal is accepted by
    # the trusted editor, without changing the runtime workspace first.
    reference_path = tmp_path / single.SPEC["path"]
    reference_path.parent.mkdir(parents=True)
    reference_path.write_bytes(raw)
    reference = R.SAFE_EDIT.SafeEditor(
        tmp_path, allowed_modify=[single.SPEC["path"]], allowed_create=[]
    )
    reference.replace(args["path"], find, replace, args["expected_sha256"])
    runtime.safe_replace(args)
    assert path.read_bytes() == reference_path.read_bytes()
    assert runtime.edit_revision == 1
    assert runtime.validation is None


def test_r1_block_after_validation_keeps_actual_validation_facts(tmp_path):
    instance = terminal.runtime_at(tmp_path)
    instance.write_lock.acquire()
    instance._prepare_run_archive()
    try:
        instance.safe_replace(single.edit(instance))
        from unittest.mock import patch

        with patch.object(instance, "_run_command", side_effect=terminal.fake_command):
            instance.validate({"contract_check": instance.contract_check_template()})
        facts = instance.validation
        refs = list(instance.validation_refs)
        _, report = instance.execute(
            {
                "action": "FINISH_BLOCKED",
                "arguments": {
                    "reason_code": "model_blocked",
                    "reason": "Incorrect model completion judgment",
                },
            }
        )
        assert report["status"] == "blocked"
        assert instance.validation is facts
        assert instance.validation.status == "passed"
        assert instance.validation_refs == refs
    finally:
        instance.close()


def test_r1_context_delivers_all_contracts_without_other_function(runtime):
    messages = single.messages(runtime)
    current = json.loads(messages[1]["content"])
    for field in (
        "required_behavior",
        "acceptance_criteria",
        "acceptance_scenarios",
        "required_order",
        "forbidden_orderings",
        "scope",
        "focused_tests",
    ):
        assert current["packet"][field] == runtime.packet[field]
    assert current["target"]["dependencies"] == single.SPEC["dependencies"]
    assert "def other" not in current["target"]["source"]
    assert (
        current["target"]["sha256"] == runtime.editor.read_bytes(single.SPEC["path"])[1]
    )


def test_r1_missing_required_context_fails_before_request(runtime):
    runtime.packet.pop("required_behavior")
    with pytest.raises(KeyError, match="required_behavior"):
        single.messages(runtime)


def test_r1_newline_only_proposal_is_not_an_edit(runtime):
    args = single.edit(
        runtime,
        find="def target():\r\n    return 1",
        replace="def target():\n    return 1",
    )
    with pytest.raises(R.WorkerError, match="identical after newline normalization"):
        runtime.safe_replace(args)
    assert runtime.edit_revision == 0
    assert runtime.repairs == 0
    assert (runtime.repo_root / single.SPEC["path"]).read_text() == single.SOURCE


def test_r1_actual_http_request_preserves_contract_and_dependency(runtime):
    rendered = single.messages(runtime)
    client = R.LMStudioClient(
        "http://fixture.invalid/v1",
        "fixture-model",
        1,
        action_schema=R.CODER_ACTION_SCHEMA,
        context_length=24576,
    )
    captured = []

    def transport(request, **kwargs):
        captured.append(json.loads(request.data))
        return io.BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": '{"action":"FINISH_FAILED","arguments":{}}'
                            },
                        }
                    ]
                }
            ).encode()
        )

    with patch.object(R.urllib.request, "urlopen", side_effect=transport):
        client.complete(rendered)
    assert len(captured) == 1
    assert captured[0]["messages"] == rendered
    payload = json.loads(captured[0]["messages"][1]["content"])
    assert payload["packet"]["required_behavior"] == runtime.packet["required_behavior"]
    assert payload["target"]["dependencies"] == runtime.single_function["dependencies"]
    assert (
        captured[0]["response_format"]["json_schema"]["schema"] == R.CODER_ACTION_SCHEMA
    )


def test_r1_interruption_restart_cannot_reapply_or_dispatch_review(tmp_path):
    instance = terminal.runtime_at(tmp_path)
    count = []

    def complete(messages):
        count.append(messages)
        if len(count) == 1:
            return json.dumps(
                {"action": "SAFE_REPLACE", "arguments": single.edit(instance)}
            )
        raise KeyboardInterrupt("simulated user interruption after an applied edit")

    with patch.object(instance.client, "complete", side_effect=complete):
        first = instance.run()
    assert first["status"] == "interrupted"
    source = (tmp_path / single.SPEC["path"]).read_bytes()
    archive = tmp_path / first["evidence_refs"]["run_archive"]
    original = {p.name: p.read_bytes() for p in archive.iterdir() if p.is_file()}
    second = R.WorkerRuntime(
        tmp_path, helpers.packet_v2(), instance.config, helpers.FakeClient([])
    )
    report = second.run()
    assert report["status"] == "blocked"
    assert report["blocked"]["reason_code"] == "run_id_conflict"
    assert second.client.messages_seen == []
    assert (tmp_path / single.SPEC["path"]).read_bytes() == source
    assert {
        p.name: p.read_bytes() for p in archive.iterdir() if p.is_file()
    } == original
    coder_path, review_path = (
        tmp_path / "interrupted-coder.json",
        tmp_path / "review.json",
    )

    # Even a refreshed convenience report cannot authorize review of this interrupted archive.
    def invoke(argv, **kwargs):
        coder_path.write_text(json.dumps(first), encoding="utf-8")
        return Mock(returncode=130, stderr="interrupted")

    with patch.object(
        unit_helpers.UNIT.subprocess, "run", side_effect=invoke
    ) as command:
        code, handoff = unit_helpers.UNIT.run_unit(
            tmp_path,
            tmp_path / "packet.json",
            tmp_path / "config.json",
            coder_path,
            review_path,
        )
    assert code != 0
    assert command.call_count == 1
    assert handoff["reviewer_decision"] is None
    assert not review_path.exists()


def test_r1_review_reentry_does_not_redispatch_canonical_archive(tmp_path):
    unit = unit_helpers.UNIT
    report, archive = unit_helpers.HandoffTests().fixture(tmp_path)
    coder_path, reviewer_path = tmp_path / "coder.json", tmp_path / "reviewer.json"
    calls = []

    def invoke(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 1:
            coder_path.write_text(json.dumps(report), encoding="utf-8")
        else:
            reviewer_path.write_text('{"decision":"pass_to_primary"}', encoding="utf-8")
        return Mock(returncode=0, stderr="")

    with patch.object(unit.subprocess, "run", side_effect=invoke):
        code, _ = unit.run_unit(
            tmp_path,
            tmp_path / "packet.json",
            tmp_path / "config.json",
            coder_path,
            reviewer_path,
        )
    assert code == 0
    request = (archive / "auto-review-request.json").read_bytes()

    def repeat(argv, **kwargs):
        # Simulates a restarted wrapper receiving the same canonical successful run.
        coder_path.write_text(json.dumps(report) + "\n", encoding="utf-8")
        return Mock(returncode=0, stderr="")

    with patch.object(unit.subprocess, "run", side_effect=repeat) as repeated:
        code, _ = unit.run_unit(
            tmp_path,
            tmp_path / "packet.json",
            tmp_path / "config.json",
            coder_path,
            reviewer_path,
        )
    assert code != 0
    assert repeated.call_count == 1
    assert (archive / "auto-review-request.json").read_bytes() == request


def test_r1_two_units_cannot_exchange_source_or_validation(tmp_path):
    roots = [tmp_path / "a", tmp_path / "b"]
    instances = []
    try:
        for number, root in enumerate(roots):
            root.mkdir(parents=True)
            helpers.WorkerRuntimeTests().make_tree(root)
            (root / single.SPEC["path"]).write_text(
                single.SOURCE.replace("return 1", f"return {number + 1}")
            )
            packet = copy.deepcopy(helpers.packet_v2())
            packet["task_id"] = f"task-{number}"
            packet["unit_id"] = f"unit-{number}"
            packet["required_behavior"][0]["text"] = f"UNIT_SECRET_{number}"
            instance = R.WorkerRuntime(
                root,
                packet,
                {
                    "python": sys.executable,
                    "coder_single_function": single.SPEC,
                    "coder_block_edits_only": True,
                },
                helpers.FakeClient([]),
            )
            instance.write_lock.acquire()
            instance._prepare_run_archive()
            instances.append(instance)
        a, b = instances
        proposal = single.edit(a)
        with pytest.raises((R.WorkerError, R.SafeEditError)):
            b.safe_replace(proposal)
        assert b.edit_revision == 0
        for number, instance in enumerate(instances):
            body = json.dumps(single.messages(instance))
            assert f"UNIT_SECRET_{number}" in body
            assert f"UNIT_SECRET_{1 - number}" not in body
            result = instance.report("failed", [], "fixture", [])
            assert result["identity"]["unit_id"] == f"unit-{number}"
            assert not instance._validated_terminal_state()
    finally:
        for instance in instances:
            instance.close()
