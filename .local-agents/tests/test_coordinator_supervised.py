from __future__ import annotations

import importlib.util
import hashlib
import json
import copy
from contextlib import contextmanager
from pathlib import Path

import pytest

import test_coordinator_contract as fixtures

pytest_plugins = [fixtures.__name__]


SPEC = importlib.util.spec_from_file_location(
    "supervised_under_test", Path(__file__).resolve().parents[1] / "coordinator-supervised.py"
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)


@pytest.mark.parametrize("stale", [False, True])
def test_feature_ready_returns_verified_handoff_without_acceptance_or_dispatch(
    tmp_path, plan, monkeypatch, stale
):
    from contextlib import nullcontext

    plan["units"] = plan["units"][:1]
    plan["contracts"] = plan["contracts"][:1]
    unit_id = plan["units"][0]["unit_id"]
    source = tmp_path / "tests/test_lease_fencing.py"
    source.parent.mkdir()
    source.write_text("assert True\n")
    proof_hash = ENTRY.CONTRACT.authority_fingerprint(plan)
    review = tmp_path / ".agent/primary-reviews" / plan["feature_id"] / f"{unit_id}.json"
    review.parent.mkdir(parents=True)
    review.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": plan["feature_id"],
                "unit_id": unit_id,
                "plan_revision": plan["plan_revision"],
                "primary_plan_sha256": proof_hash,
                "decision": "accept",
                "evidence": ["synthetic boundary fixture"],
                "changed_files": ["tests/test_lease_fencing.py"],
            }
        )
    )
    integration = tmp_path / ".agent/integration" / plan["feature_id"] / "validation.json"
    integration.parent.mkdir(parents=True)
    integration.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": plan["feature_id"],
                "plan_revision": plan["plan_revision"],
                "primary_plan_sha256": proof_hash,
                "integration_risk": plan["integration_risk"],
                "status": "passed",
                "checks": [{"id": "fixture", "status": "passed", "exit_code": 0}],
                "files": [
                    {
                        "path": "tests/test_lease_fencing.py",
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    }
                ],
            }
        )
    )

    class Client:
        def complete(self, messages):
            return json.dumps({"decision": "FEATURE_READY", "unit_id": unit_id})

    monkeypatch.setattr(ENTRY.MODEL.RESIDENCY, "role_model_lease", lambda *a: nullcontext())
    args = dict(
        root=tmp_path,
        plan=plan,
        context={
            "identity": {
                "unit_id": unit_id,
                "run_id": "ready-probe",
                "attempt": 1,
                "packet_revision": 1,
            }
        },
        request={},
        explorer={},
        run_refs={unit_id: {}},
        config={},
        config_path=tmp_path / "config.json",
        authorized=True,
        expected_sequence=0,
        client=Client(),
        router=lambda **k: pytest.fail("worker dispatched"),
    )
    if stale:
        source.write_text("changed\n")
        with pytest.raises(ValueError, match="changed after validation"):
            ENTRY.run_step(**args)
    else:
        code, result = ENTRY.run_step(**args)
        assert code == 0 and result["status"] == "primary_final_review_required"
        assert result["feature_accepted"] is False
        assert result["handoff"]["integration_status"] == "verified_passed"
        assert result["handoff"]["changed_paths"] == ["tests/test_lease_fencing.py"]
        assert (Path(result["archive"]) / "primary-handoff.json").exists()
    assert not (tmp_path / ".agent/coordinator" / plan["feature_id"] / "state.json").exists()


def inputs(tmp_path, packet_pair):
    plan, packet = packet_pair
    return dict(
        root=tmp_path,
        plan=plan,
        context={
            "identity": {
                "unit_id": packet["unit_id"],
                "run_id": packet["run_id"],
                "attempt": packet["attempt"],
                "packet_revision": packet["packet_revision"],
            }
        },
        request={},
        explorer={},
        run_refs={},
        config={"single_model_residency": False},
        config_path=tmp_path / "config.json",
        authorized=True,
        expected_sequence=0,
        client=object(),
    )


@pytest.mark.parametrize(
    "change,match",
    [
        ({"authorized": False}, "authorization"),
        ({"expected_sequence": 1}, "stale"),
        ({"expected_sequence": True}, "stale"),
    ],
)
def test_preflight_never_calls_model_or_creates_archive(
    tmp_path, packet_pair, monkeypatch, change, match
):
    args = inputs(tmp_path, packet_pair)
    args.update(change)
    monkeypatch.setattr(ENTRY.MODEL, "probe", lambda *a, **k: pytest.fail("model called"))
    with pytest.raises(ValueError, match=match):
        ENTRY.run_step(**args)
    assert not (tmp_path / ".agent").exists()


def test_escalation_is_archived_without_proposal_or_dispatch(tmp_path, packet_pair, monkeypatch):
    args = inputs(tmp_path, packet_pair)
    calls = []

    def probe(plan, context, mode, client, **kwargs):
        calls.append(mode)
        return {
            "status": "protocol_valid",
            "output": {
                "decision": "ESCALATE_PRIMARY",
                "unit_id": context["identity"]["unit_id"],
                "reason_code": "primary-review-needed",
            },
        }

    from contextlib import nullcontext

    monkeypatch.setattr(ENTRY.MODEL.RESIDENCY, "role_model_lease", lambda *a: nullcontext())
    monkeypatch.setattr(ENTRY.MODEL, "probe", probe)
    args["router"] = lambda **k: pytest.fail("worker dispatched")
    code, result = ENTRY.run_step(**args)
    assert code == 0
    assert calls == ["decision"]
    archive = Path(result["archive"])
    assert (archive / "authorization.json").exists()
    assert (archive / "decision-gate.json").exists()
    assert not (archive / "packet.json").exists()
    with pytest.raises(FileExistsError):
        ENTRY.run_step(**args)
    assert calls == ["decision"]
    original_decision = (archive / "decision.json").read_bytes()
    args["proposal_id"] = "primary-authorized-proposal-2"
    code, revised = ENTRY.run_step(**args)
    assert code == 0 and revised["archive"] != str(archive)
    assert (archive / "decision.json").read_bytes() == original_decision
    assert calls == ["decision", "decision"]


def test_new_proposal_id_cannot_replay_partial_coder_archive(tmp_path, packet_pair, monkeypatch):
    args = inputs(tmp_path, packet_pair)
    identity = args["context"]["identity"]
    execution = tmp_path / ".agent/tasks" / args["plan"]["task_id"] / "runs" / identity["run_id"]
    execution.mkdir(parents=True)
    args["proposal_id"] = "another-proposal"
    monkeypatch.setattr(ENTRY.MODEL, "probe", lambda *a, **k: pytest.fail("model called"))
    with pytest.raises(ValueError, match="cannot replay execution"):
        ENTRY.run_step(**args)


@pytest.mark.parametrize("stale_source", [False, True])
@pytest.mark.parametrize("managed", [False, "run", "reuse"])
def test_proposal_dispatch_has_real_evidence_and_releases_model_lease(
    tmp_path, packet_pair, monkeypatch, stale_source, managed
):
    args = inputs(tmp_path, packet_pair)
    _, packet = packet_pair
    source = tmp_path / "src/example.py"
    source.parent.mkdir()
    source.write_text("def target():\n    return 1\n", encoding="utf-8")
    args["request"] = {
        "capability": "localization_only",
        "task_id": packet["task_id"],
        "unit_id": packet["unit_id"],
        "question": "Where is target defined?",
    }
    args["explorer"] = {
        "status": "success",
        "explorer_mode": "locate",
        "semantic_verdict": "not_evaluated",
        "task": args["request"]["question"],
        "task_id": packet["task_id"],
        "uncertainties": [],
        "source_refs": [
            {
                "path": "src/example.py",
                "start_line": 1,
                "end_line": 1,
                "kind": "definition",
                "quote": "def target():",
                "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        ],
    }
    proposal = {
        key: packet[key]
        for key in (
            "unit_id",
            "run_id",
            "attempt",
            "packet_revision",
            "goal",
            "edit_targets",
            "focused_tests",
            "supplemental_tests",
            "implementation_guidance",
        )
    }
    proposal["scope"] = {key: packet["scope"][key] for key in ("read", "modify", "create")}
    lease_active = False

    @contextmanager
    def lease(*args):
        nonlocal lease_active
        lease_active = True
        try:
            yield
        finally:
            lease_active = False

    class Client:
        def __init__(self):
            values = [
                json.dumps({"decision": "CONTINUE", "unit_id": packet["unit_id"]}),
            ]
            if managed:
                values.append(
                    json.dumps(
                        {
                            "action": "REUSE_EVIDENCE" if managed == "reuse" else "RUN_EXPLORER",
                            "unit_id": packet["unit_id"],
                        }
                    ),
                )
            values.append(json.dumps(proposal))
            self.outputs = iter(values)

        def complete(self, messages):
            assert lease_active
            if "Generate a bounded proposal" in messages[0]["content"]:
                supplied = json.loads(messages[1]["content"])["context"]
                expected = report if managed else args["explorer"]
                assert supplied["source_refs"] == expected["source_refs"]
            return next(self.outputs)

    args["client"] = Client()
    monkeypatch.setattr(ENTRY.MODEL.RESIDENCY, "role_model_lease", lease)
    dispatched = []

    def router(**kwargs):
        assert not lease_active
        assert kwargs["authorized_sequence"] == 0
        assert json.loads(kwargs["packet_path"].read_text())["primary_plan_sha256"]
        dispatched.append(kwargs)
        return 0, {"status": "primary_review_required"}

    args["router"] = router
    if managed:
        args["manage_exploration"] = True
        args["config"]["explorer_mode"] = "locate"
        report = args["explorer"]
        if managed == "run":
            args["explorer"] = {}

        def explorer_runner(root, request, config_path, report_path):
            assert managed == "run", "reuse must not launch Explorer"
            assert not lease_active
            assert request == args["request"]
            return {"exit_code": 0, "report": report}

        args["explorer_runner"] = explorer_runner
    if stale_source:
        source.write_text("def different():\n    return 1\n", encoding="utf-8")
        if managed == "reuse":
            code, result = ENTRY.run_step(**args)
            assert code == 1 and result["stage"] == "exploration"
        else:
            with pytest.raises(ValueError):
                ENTRY.run_step(**args)
        assert dispatched == []
    else:
        code, result = ENTRY.run_step(**args)
        assert code == 0 and len(dispatched) == 1
        assert result["feature_accepted"] is False
        assert (Path(result["archive"]) / "result.json").exists()
        assert "source_refs" not in args["context"]
        observed_context = json.loads(
            (Path(result["archive"]) / "proposal-context.json").read_text()
        )
        assert observed_context["source_refs"]


@pytest.mark.parametrize(
    "outputs,expected",
    [
        ([{"action": "REUSE_EVIDENCE", "unit_id": "example-behavior"}] * 2, "protocol_failed"),
        ([{"action": "RUN_EXPLORER", "unit_id": "outside"}] * 2, "protocol_failed"),
        ([{"action": "SKIP", "unit_id": "example-behavior"}] * 2, "protocol_failed"),
        ([{"action": "RUN_EXPLORER", "unit_id": "example-behavior"}], "protocol_valid"),
    ],
)
def test_exploration_choice_cannot_skip_missing_evidence_or_change_unit(outputs, expected):
    class Client:
        def __init__(self):
            self.outputs = iter(outputs)

        def complete(self, messages):
            return json.dumps(next(self.outputs))

    result = ENTRY.EXPLORATION.choose(
        {"identity": {"unit_id": "example-behavior"}}, {}, {}, Client()
    )
    assert result["status"] == expected
    assert result["feature_accepted"] is False


@pytest.mark.parametrize("corrected", [False, True])
def test_exploration_archives_request_stats_on_correction_and_failure(corrected):
    class Client:
        def __init__(self):
            self.turn = 0
            self.last_request_stats = {}

        def complete(self, messages):
            self.turn += 1
            self.last_request_stats = {"response_usage": {"total_tokens": self.turn}}
            if self.turn == 2 and corrected:
                return '{"action":"RUN_EXPLORER","unit_id":"example-behavior"}'
            return "invalid private output"

    client = Client()
    result = ENTRY.EXPLORATION.choose({"identity": {"unit_id": "example-behavior"}}, {}, {}, client)
    assert result["status"] == ("protocol_valid" if corrected else "protocol_failed")
    assert [item["response_usage"]["total_tokens"] for item in result["model_requests"]] == [1, 2]
    client.last_request_stats["response_usage"]["total_tokens"] = 99
    assert result["model_requests"][1]["response_usage"]["total_tokens"] == 2
    assert "private" not in json.dumps(result["model_requests"])
    assert result["feature_accepted"] is False


def recovery_inputs(tmp_path, packet_pair):
    args = inputs(tmp_path, packet_pair)
    plan, old = packet_pair
    parent = tmp_path / ".agent/tasks" / plan["task_id"] / "runs" / old["run_id"]
    parent.mkdir(parents=True)
    old_path = parent / "packet.json"
    old_path.write_text(json.dumps(old), encoding="utf-8")
    completed = parent / "completed.json"
    completed.write_text(json.dumps({"status": "failed"}), encoding="utf-8")
    state_path = tmp_path / ".agent/coordinator" / plan["feature_id"] / "state.json"
    for sequence, decision in enumerate(
        [
            {"decision": "CONTINUE", "unit_id": old["unit_id"]},
            {"decision": "REWORK_LOCAL", "unit_id": old["unit_id"], "reason_code": "test-failed"},
        ]
    ):
        ENTRY.CONTRACT.persist_coordinator_transition(
            plan,
            tmp_path,
            state_path,
            expected_sequence=sequence,
            transition=lambda state, choice=decision: ENTRY.CONTRACT.apply_coordinator_decision(
                plan,
                state,
                choice,
                expected_sequence=state["sequence"],
                repo_root=tmp_path,
                run_refs={},
            ),
        )
    identity = dict(args["context"]["identity"])
    identity.update(
        run_id="rework-a2", attempt=old["attempt"] + 1, packet_revision=old["packet_revision"] + 1
    )
    args["context"]["identity"] = identity
    auth_path = (
        tmp_path
        / ".agent/primary-reviews"
        / plan["feature_id"]
        / "recovery"
        / f"{old['run_id']}.json"
    )
    auth_path.parent.mkdir(parents=True)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    auth = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "task_id": plan["task_id"],
        "unit_id": old["unit_id"],
        "failed_run_id": old["run_id"],
        "new_run_id": identity["run_id"],
        "primary_plan_sha256": ENTRY.CONTRACT.authority_fingerprint(plan),
        "failed_packet_sha256": digest(old_path),
        "archived_packet_sha256": digest(old_path),
        "completed_sha256": digest(completed),
        "expected_sequence": 1,
        "decision": "REWORK_LOCAL",
        "reason_code": "test-failed",
        "primary_rationale": "Synthetic terminal recovery fixture.",
    }
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    args.update(expected_sequence=2, recovery_authorization_path=auth_path)
    return args, completed


@pytest.mark.parametrize("defect", ["completed", "run-id", "attempt", "sequence"])
def test_recovery_preflight_rejects_stale_or_wrong_grant_before_model(
    tmp_path, packet_pair, monkeypatch, defect
):
    args, completed = recovery_inputs(tmp_path, packet_pair)
    if defect == "completed":
        completed.write_text(json.dumps({"status": "interrupted"}))
    elif defect == "run-id":
        args["context"]["identity"]["run_id"] = "unapproved-a2"
    elif defect == "attempt":
        args["context"]["identity"]["attempt"] -= 1
    else:
        args["expected_sequence"] = 3
    monkeypatch.setattr(ENTRY.MODEL, "probe", lambda *a, **k: pytest.fail("model called"))
    with pytest.raises(ValueError):
        ENTRY.run_step(**args)
    assert not (tmp_path / ".agent/coordinator" / args["plan"]["feature_id"] / "proposals").exists()


def test_primary_recovery_allows_model_rework_gate_without_state_write(
    tmp_path, packet_pair, monkeypatch
):
    from contextlib import nullcontext

    args, _ = recovery_inputs(tmp_path, packet_pair)
    state_path = tmp_path / ".agent/coordinator" / args["plan"]["feature_id"] / "state.json"
    before = state_path.read_bytes()
    calls = []

    def probe(plan, context, mode, client, **kwargs):
        calls.append(mode)
        if mode == "decision":
            assert (
                kwargs["execution_evidence"]["primary_authorized_rework"]["new_run_id"]
                == "rework-a2"
            )
            assert (
                kwargs["execution_evidence"]["primary_authorized_rework"][
                    "eligible_for_rework_proposal"
                ]
                is True
            )
            return {
                "status": "protocol_valid",
                "output": {
                    "decision": "REWORK_LOCAL",
                    "unit_id": context["identity"]["unit_id"],
                    "reason_code": "focused-repair",
                },
            }
        return {"status": "protocol_failed"}

    monkeypatch.setattr(ENTRY.MODEL.RESIDENCY, "role_model_lease", lambda *a: nullcontext())
    monkeypatch.setattr(ENTRY.MODEL, "probe", probe)
    args["router"] = lambda **k: pytest.fail("worker dispatched")
    original = copy.deepcopy(args["context"])
    code, result = ENTRY.run_step(**args)
    assert code == 1 and result["stage"] == "proposal"
    assert calls == ["decision", "proposal"]
    assert state_path.read_bytes() == before
    assert args["context"] == original
