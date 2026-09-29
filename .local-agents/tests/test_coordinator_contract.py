from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "coordinator_contract_under_test", ROOT / "coordinator-contract.py"
)
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)
ROUTE_SPEC = importlib.util.spec_from_file_location(
    "coordinator_localization_under_test", ROOT / "coordinator-localization.py"
)
assert ROUTE_SPEC is not None and ROUTE_SPEC.loader is not None
ROUTE = importlib.util.module_from_spec(ROUTE_SPEC)
ROUTE_SPEC.loader.exec_module(ROUTE)


@pytest.fixture
def plan() -> dict:
    return json.loads((ROOT / "example-feature-plan.json").read_text(encoding="utf-8"))


def test_example_plan_keeps_high_risk_atomic_unit(plan: dict) -> None:
    result = CONTRACT.validate_feature_plan(plan)
    assert result["effective_unit_risk"] == {
        "lease-test-support": "medium",
        "worker-success-finalization": "high",
        "lease-documentation": "small",
    }


def test_durable_state_rejects_stale_or_foreign_plan(plan: dict) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / ".agent" / "coordinator-state.json"
        initial = CONTRACT.load_coordinator_state(plan, root, path)
        assert initial["sequence"] == 0
        saved = CONTRACT.persist_coordinator_transition(
            plan,
            root,
            path,
            expected_sequence=0,
            transition=lambda state: CONTRACT.record_policy_block(
                plan, state, "lease-test-support", "unsupported-capability"
            ),
        )
        assert saved["sequence"] == 1
        assert CONTRACT.load_coordinator_state(plan, root, path) == saved
        with pytest.raises(ValueError, match="sequence is stale"):
            CONTRACT.persist_coordinator_transition(
                plan,
                root,
                path,
                expected_sequence=0,
                transition=lambda state: state,
            )
        assert CONTRACT.load_coordinator_state(plan, root, path) == saved
        revised = copy.deepcopy(plan)
        revised["plan_revision"] += 1
        with pytest.raises(ValueError, match="differs from Primary plan"):
            CONTRACT.load_coordinator_state(revised, root, path)


def test_durable_state_rejects_lock_corruption_and_outside_path(plan: dict) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / ".agent" / "coordinator-state.json"
        path.parent.mkdir()
        lock = path.with_name(path.name + ".lock")
        lock.write_text("occupied", encoding="utf-8")
        with pytest.raises(ValueError, match="writer lock exists"):
            CONTRACT.persist_coordinator_transition(
                plan, root, path, expected_sequence=0, transition=lambda state: state
            )
        assert lock.read_text(encoding="utf-8") == "occupied"
        lock.unlink()
        path.write_text("{broken", encoding="utf-8")
        with pytest.raises(ValueError, match="unreadable"):
            CONTRACT.load_coordinator_state(plan, root, path)
        with pytest.raises(ValueError, match="inside repository"):
            CONTRACT.load_coordinator_state(plan, root, root / "elsewhere.json")


def test_contract_floor_clamps_coordinator_proposal(plan: dict) -> None:
    plan["units"][1]["risk"] = "small"
    assert (
        CONTRACT.validate_feature_plan(plan)["effective_unit_risk"]["worker-success-finalization"]
        == "high"
    )


@pytest.mark.parametrize("defect", ["unknown", "duplicate", "unowned"])
def test_contract_membership_fails_closed(plan: dict, defect: str) -> None:
    broken = copy.deepcopy(plan)
    if defect == "unknown":
        broken["units"][0]["owned_contract_ids"] = ["invented"]
        expected = "unknown contract"
    elif defect == "duplicate":
        broken["units"][1]["owned_contract_ids"].append("lease-event-order-evidence")
        expected = "already owned"
    else:
        broken["contracts"].append(
            {"id": "unowned-test", "risk_floor": "small", "text": "Unowned behavior."}
        )
        expected = "unowned contract"
    with pytest.raises(ValueError, match=expected):
        CONTRACT.validate_feature_plan(broken)


def test_dependency_cycle_and_unknown_dependency_are_rejected(plan: dict) -> None:
    plan["units"][0]["dependencies"] = ["lease-documentation"]
    with pytest.raises(ValueError, match="dependency cycle"):
        CONTRACT.validate_feature_plan(plan)
    plan["units"][0]["dependencies"] = ["missing-unit"]
    with pytest.raises(ValueError, match="unknown dependency"):
        CONTRACT.validate_feature_plan(plan)


@pytest.fixture
def packet_pair() -> tuple[dict, dict]:
    packet = json.loads((ROOT / "example-packet.json").read_text(encoding="utf-8"))
    packet["scope"]["forbidden"] = [".agent", "AGENTS.md"]
    plan = {
        "schema_version": 1,
        "plan_revision": 1,
        "task_id": "example-01",
        "feature_id": "example-feature",
        "feature_risk": "high",
        "integration_risk": "high",
        "contracts": [
            {
                "id": "behavior-1",
                "risk_floor": "high",
                "text": packet["required_behavior"][0]["text"],
            }
        ],
        "units": [
            {
                "unit_id": "example-behavior",
                "risk": "small",
                "owner": "local-coder",
                "dependencies": [],
                "owned_contract_ids": ["behavior-1"],
                "scope_authority": {
                    "read_roots": ["src", "tests"],
                    "modify": ["src/example.py", "src/example_api.py"],
                    "create": ["tests/test_example_supplement.py"],
                    "readonly": ["tests/test_example.py"],
                    "forbidden": [".agent", "AGENTS.md"],
                },
                "packet_contract": {
                    "acceptance_criteria": copy.deepcopy(packet["acceptance_criteria"]),
                    "acceptance_scenarios": copy.deepcopy(packet["acceptance_scenarios"]),
                    "required_order": list(packet["required_order"]),
                    "forbidden_orderings": list(packet["forbidden_orderings"]),
                    "validation_profile": packet["validation_profile"],
                    "required_focused_tests": ["tests/test_example.py"],
                },
            }
        ],
    }
    packet["primary_plan_sha256"] = CONTRACT.authority_fingerprint(plan)
    return plan, packet


def test_localization_dispatch_requires_current_in_scope_evidence(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "src" / "example.py"
        source.parent.mkdir()
        source.write_text("def target():\n    return 1\n", encoding="utf-8")
        request = {
            "capability": "localization_only",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": "Where is target defined?",
        }
        ref = {
            "path": "src/example.py",
            "start_line": 1,
            "end_line": 1,
            "kind": "definition",
            "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            "quote": "def target():",
        }
        report = {
            "status": "success",
            "explorer_mode": "locate",
            "semantic_verdict": "not_evaluated",
            "task": request["question"],
            "task_id": packet["task_id"],
            "uncertainties": [],
            "source_refs": [ref],
        }
        assert (
            CONTRACT.validate_localization_dispatch(plan, packet, request, report, repo_root=root)[
                "capability"
            ]
            == "localization_only"
        )
        request["capability"] = "semantic_investigation"
        with pytest.raises(ValueError, match="unsupported exploration capability"):
            CONTRACT.validate_localization_dispatch(plan, packet, request, report, repo_root=root)
        request["capability"] = "localization_only"
        source.write_text("def target():\n    return 2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="source_ref is stale"):
            CONTRACT.validate_localization_dispatch(plan, packet, request, report, repo_root=root)


def test_bounded_packet_materializer_derives_primary_obligations(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, existing = packet_pair
    proposal = {
        "unit_id": existing["unit_id"],
        "run_id": "example-01-generated",
        "attempt": 1,
        "packet_revision": 1,
        "goal": "Implement the scoped observable behavior.",
        "scope": {
            "read": ["src", "tests"],
            "modify": ["src/example.py"],
            "create": [],
        },
        "edit_targets": [{"path": "src/example.py", "anchor": "def example_behavior"}],
        "focused_tests": ["tests/test_example.py"],
        "supplemental_tests": [],
        "implementation_guidance": ["Keep the existing public API."],
    }
    generated = CONTRACT.materialize_bounded_packet(plan, proposal)
    assert generated["risk"]["unit"] == "high"
    assert generated["scope"]["modify"] == ["src/example.py"]
    assert generated["required_behavior"][0]["text"] == plan["contracts"][0]["text"]
    assert (
        generated["acceptance_scenarios"]
        == plan["units"][0]["packet_contract"]["acceptance_scenarios"]
    )
    assert generated["primary_plan_sha256"] == CONTRACT.authority_fingerprint(plan)
    with pytest.raises(ValueError, match="authority-bearing fields"):
        CONTRACT.materialize_bounded_packet(
            plan, {**proposal, "required_behavior": [{"id": "behavior-1", "text": "weaker"}]}
        )
    widened = copy.deepcopy(proposal)
    widened["scope"]["modify"] = ["src/outside.py"]
    widened["edit_targets"][0]["path"] = "src/outside.py"
    with pytest.raises(ValueError, match="exceeds Primary authority"):
        CONTRACT.materialize_bounded_packet(plan, widened)


def test_restricted_route_dispatches_once_without_accepting_unit(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "src" / "example.py"
        source.parent.mkdir()
        source.write_text("def target():\n    return 1\n", encoding="utf-8")
        packet_path = root / "packet.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        request = {
            "capability": "localization_only",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": "Where is target defined?",
        }
        report = {
            "status": "success",
            "explorer_mode": "locate",
            "semantic_verdict": "not_evaluated",
            "task": request["question"],
            "task_id": packet["task_id"],
            "uncertainties": [],
            "source_refs": [
                {
                    "path": "src/example.py",
                    "start_line": 1,
                    "end_line": 1,
                    "kind": "definition",
                    "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "quote": "def target():",
                }
            ],
        }
        state_path = root / ".agent" / "coordinator" / "state.json"
        calls = []

        def fake_unit(*args: object) -> tuple[int, dict]:
            calls.append(args)
            return 0, {"reviewer_decision": "pass_to_primary"}

        def run() -> tuple[int, dict]:
            return ROUTE.run_localization_unit(
                repo_root=root,
                plan=plan,
                packet_path=packet_path,
                request=request,
                explorer_report=report,
                state_path=state_path,
                run_refs={},
                config_path=root / "config.json",
                coder_report_path=root / "coder.json",
                review_report_path=root / "review.json",
                unit_runner=fake_unit,
            )

        code, result = run()
        assert code == 0
        assert result["status"] == "primary_review_required"
        dispatch = json.loads(Path(result["dispatch_record"]).read_text(encoding="utf-8"))
        assert dispatch["run_id"] == packet["run_id"]
        assert dispatch["source_refs"][0]["path"] == "src/example.py"
        assert "quote" not in dispatch["source_refs"][0]
        assert len(calls) == 1
        state = CONTRACT.load_coordinator_state(plan, root, state_path)
        assert state["units"][packet["unit_id"]]["phase"] == "running"
        assert "accepted_units" not in state
        inspection = ROUTE.inspect_running_dispatch(
            repo_root=root, plan=plan, packet_path=packet_path, state_path=state_path
        )
        assert inspection["status"] == "archive_missing_or_incomplete"
        assert inspection["automatic_retry_allowed"] is False
        with pytest.raises(ValueError, match="already running"):
            run()
        assert len(calls) == 1
        state_path.unlink()
        with pytest.raises(ValueError, match="already has a dispatch record"):
            run()
        assert len(calls) == 1


def test_restricted_route_rejects_semantic_capability_before_state_write(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    with TemporaryDirectory() as directory:
        root = Path(directory)
        packet_path = root / "packet.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        state_path = root / ".agent" / "coordinator" / "state.json"
        request = {
            "capability": "semantic_investigation",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": "Why does the algorithm fail?",
        }

        def unexpected_unit(*_args: object) -> tuple[int, dict]:
            raise AssertionError("dispatched")

        with pytest.raises(ValueError, match="unsupported exploration capability"):
            ROUTE.run_localization_unit(
                repo_root=root,
                plan=plan,
                packet_path=packet_path,
                request=request,
                explorer_report={},
                state_path=state_path,
                run_refs={},
                config_path=root / "config.json",
                coder_report_path=root / "coder.json",
                review_report_path=root / "review.json",
                unit_runner=unexpected_unit,
            )
        assert not state_path.exists()


def test_route_crash_records_infra_and_requires_primary_recovery(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "src" / "example.py"
        source.parent.mkdir()
        source.write_text("def target():\n    return 1\n", encoding="utf-8")
        packet_path = root / "packet.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        state_path = root / ".agent" / "coordinator" / "state.json"
        request = {
            "capability": "localization_only",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": "Where is target defined?",
        }
        report = {
            "status": "success",
            "explorer_mode": "locate",
            "semantic_verdict": "not_evaluated",
            "task": request["question"],
            "task_id": packet["task_id"],
            "uncertainties": [],
            "source_refs": [
                {
                    "path": "src/example.py",
                    "start_line": 1,
                    "end_line": 1,
                    "kind": "definition",
                    "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "quote": "def target():",
                }
            ],
        }

        def interrupted_unit(*_args: object) -> tuple[int, dict]:
            raise OSError("simulated worker process loss")

        kwargs = {
            "repo_root": root,
            "plan": plan,
            "packet_path": packet_path,
            "request": request,
            "explorer_report": report,
            "state_path": state_path,
            "run_refs": {},
            "config_path": root / "config.json",
            "coder_report_path": root / "coder.json",
            "review_report_path": root / "review.json",
        }
        code, result = ROUTE.run_localization_unit(**kwargs, unit_runner=interrupted_unit)
        assert code == 2
        assert result["next_action_required"] == "primary_inspect_archives_before_recovery"
        assert Path(result["dispatch_record"]).is_file()
        recovered = CONTRACT.load_coordinator_state(plan, root, state_path)
        assert recovered["sequence"] == 2
        assert recovered["infra_failure_count"] == 1
        assert recovered["units"][packet["unit_id"]]["phase"] == "running"
        with pytest.raises(ValueError, match="Primary recovery required"):
            ROUTE.run_localization_unit(**kwargs, unit_runner=interrupted_unit)
        with pytest.raises(ValueError, match="only a completed failed Coder run"):
            ROUTE.recover_terminal_failed_unit(
                repo_root=root,
                plan=plan,
                failed_packet_path=packet_path,
                state_path=state_path,
                authorization_path=root / ".agent" / "missing.json",
                run_refs={},
            )


def test_terminal_failed_run_needs_primary_authorization_and_new_run_id(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    packet["scope"]["modify"] = ["src/example.py"]
    packet["edit_targets"] = [
        item for item in packet["edit_targets"] if item["path"] == "src/example.py"
    ]
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "src" / "example.py"
        source.parent.mkdir()
        source.write_text("def target():\n    return 1\n", encoding="utf-8")
        packet_path = root / "packet.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        state_path = root / ".agent" / "coordinator" / "state.json"
        request = {
            "capability": "localization_only",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": "Where is target defined?",
        }
        report = {
            "status": "success",
            "explorer_mode": "locate",
            "semantic_verdict": "not_evaluated",
            "task": request["question"],
            "task_id": packet["task_id"],
            "uncertainties": [],
            "source_refs": [
                {
                    "path": "src/example.py",
                    "start_line": 1,
                    "end_line": 1,
                    "kind": "definition",
                    "source_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "quote": "def target():",
                }
            ],
        }
        run_root = root / ".agent" / "tasks" / packet["task_id"] / "runs" / packet["run_id"]

        def failed_unit(*_args: object) -> tuple[int, dict]:
            run_root.mkdir(parents=True)
            (run_root / "packet.json").write_text(
                json.dumps(packet, sort_keys=True, indent=2), encoding="utf-8"
            )
            (run_root / "completed.json").write_text(
                json.dumps({"status": "failed"}), encoding="utf-8"
            )
            return 2, {"status": "failed"}

        base = {
            "repo_root": root,
            "plan": plan,
            "request": request,
            "explorer_report": report,
            "state_path": state_path,
            "run_refs": {},
            "config_path": root / "config.json",
            "coder_report_path": root / "coder.json",
            "review_report_path": root / "review.json",
        }
        code, _result = ROUTE.run_localization_unit(
            **base, packet_path=packet_path, unit_runner=failed_unit
        )
        assert code == 2
        authorization_path = (
            root
            / ".agent"
            / "primary-reviews"
            / plan["feature_id"]
            / "recovery"
            / f"{packet['run_id']}.json"
        )
        authorization_path.parent.mkdir(parents=True)
        authorization = {
            "schema_version": 1,
            "feature_id": plan["feature_id"],
            "task_id": plan["task_id"],
            "unit_id": packet["unit_id"],
            "failed_run_id": packet["run_id"],
            "new_run_id": "example-01-a2",
            "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
            "failed_packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
            "archived_packet_sha256": hashlib.sha256(
                (run_root / "packet.json").read_bytes()
            ).hexdigest(),
            "completed_sha256": hashlib.sha256(
                (run_root / "completed.json").read_bytes()
            ).hexdigest(),
            "expected_sequence": 1,
            "decision": "REWORK_LOCAL",
            "reason_code": "focused-test-failed",
            "primary_rationale": "The completed Coder run failed focused validation.",
        }
        assert authorization["failed_packet_sha256"] != authorization["archived_packet_sha256"]
        authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
        altered = dict(authorization)
        altered["completed_sha256"] = "0" * 64
        authorization_path.write_text(json.dumps(altered), encoding="utf-8")
        with pytest.raises(ValueError, match="stale or names different archive evidence"):
            ROUTE.recover_terminal_failed_unit(
                repo_root=root,
                plan=plan,
                failed_packet_path=packet_path,
                state_path=state_path,
                authorization_path=authorization_path,
                run_refs={},
            )
        assert CONTRACT.load_coordinator_state(plan, root, state_path)["sequence"] == 1
        authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
        recovered = ROUTE.recover_terminal_failed_unit(
            repo_root=root,
            plan=plan,
            failed_packet_path=packet_path,
            state_path=state_path,
            authorization_path=authorization_path,
            run_refs={},
        )
        assert recovered["status"] == "primary_authorized_rework"
        state = CONTRACT.load_coordinator_state(plan, root, state_path)
        assert state["sequence"] == 2
        assert state["units"][packet["unit_id"]]["phase"] == "rework"
        archived_packet_path = run_root / "packet.json"
        archived_bytes = archived_packet_path.read_bytes()
        archived_packet_path.write_text(json.dumps(packet), encoding="utf-8")
        next_packet = copy.deepcopy(packet)
        next_packet["run_id"] = "example-01-a2"
        next_packet["attempt"] = 2
        next_packet["packet_revision"] = 2
        next_path = root / "packet-a2.json"
        next_path.write_text(json.dumps(next_packet), encoding="utf-8")
        with pytest.raises(ValueError, match="rework parent archive is stale"):
            ROUTE.run_localization_unit(
                **base,
                packet_path=next_path,
                recovery_authorization_path=authorization_path,
                unit_runner=lambda *_args: (0, {}),
            )
        archived_packet_path.write_bytes(archived_bytes)
        with pytest.raises(ValueError, match="unit is not running"):
            ROUTE.recover_terminal_failed_unit(
                repo_root=root,
                plan=plan,
                failed_packet_path=packet_path,
                state_path=state_path,
                authorization_path=authorization_path,
                run_refs={},
            )
        with pytest.raises(ValueError, match="needs Primary recovery authorization"):
            ROUTE.run_localization_unit(
                **base,
                packet_path=next_path,
                unit_runner=lambda *_args: (0, {}),
            )
        expanded = copy.deepcopy(next_packet)
        expanded["scope"]["modify"].append("src/example_api.py")
        expanded["edit_targets"].append({"path": "src/example_api.py", "anchor": "def example_api"})
        next_path.write_text(json.dumps(expanded), encoding="utf-8")
        with pytest.raises(ValueError, match="expands prior modify scope"):
            ROUTE.run_localization_unit(
                **base,
                packet_path=next_path,
                recovery_authorization_path=authorization_path,
                unit_runner=lambda *_args: (0, {}),
            )
        next_path.write_text(json.dumps(next_packet), encoding="utf-8")
        code, result = ROUTE.run_localization_unit(
            **base,
            packet_path=next_path,
            recovery_authorization_path=authorization_path,
            unit_runner=lambda *_args: (0, {"reviewer_decision": "pass_to_primary"}),
        )
        assert code == 0
        assert result["state_sequence"] == 3
        assert (
            CONTRACT.load_coordinator_state(plan, root, state_path)["units"][packet["unit_id"]][
                "phase"
            ]
            == "running"
        )


def test_locator_selects_two_authorized_files_and_rejects_unscoped_only(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    with TemporaryDirectory() as directory:
        root = Path(directory)
        src = root / "src"
        src.mkdir()
        paths = (src / "example.py", src / "example_api.py", src / "other.py")
        for path in paths:
            path.write_text("def target():\n    return 1\n", encoding="utf-8")
        request = {
            "capability": "localization_only",
            "task_id": packet["task_id"],
            "unit_id": packet["unit_id"],
            "question": "Which files implement the target?",
        }

        def ref(path: Path) -> dict:
            return {
                "path": path.relative_to(root).as_posix(),
                "start_line": 1,
                "end_line": 1,
                "kind": "definition",
                "source_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                "quote": "def target():",
            }

        report = {
            "status": "success",
            "explorer_mode": "locate",
            "semantic_verdict": "not_evaluated",
            "task": request["question"],
            "task_id": packet["task_id"],
            "uncertainties": [],
            "source_refs": [ref(paths[2])],
        }
        with pytest.raises(ValueError, match="authorized implementation target"):
            CONTRACT.validate_localization_dispatch(plan, packet, request, report, repo_root=root)
        report["source_refs"] = [ref(paths[0]), ref(paths[1])]
        result = CONTRACT.validate_localization_dispatch(
            plan, packet, request, report, repo_root=root
        )
        assert len(result["source_refs"]) == 2


def packet_for_lease_worker(plan: dict, run_id: str) -> dict:
    unit = next(item for item in plan["units"] if item["unit_id"] == "worker-success-finalization")
    obligations = unit["packet_contract"]
    return {
        "schema_version": 2,
        "task_id": "lease-fencing",
        "feature_id": plan["feature_id"],
        "unit_id": unit["unit_id"],
        "run_id": run_id,
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
        "goal": "Enforce the lease after the handler and before finalization.",
        "risk": {
            "feature": plan["feature_risk"],
            "unit": unit["risk"],
            "integration": plan["integration_risk"],
            "reasons": ["Transaction finalization ordering."],
        },
        "dependencies": unit["dependencies"],
        "owned_contract_ids": unit["owned_contract_ids"],
        "scope": {
            "read": unit["scope_authority"]["read_roots"],
            "readonly": unit["scope_authority"]["readonly"],
            "modify": unit["scope_authority"]["modify"],
            "create": [],
            "forbidden": unit["scope_authority"]["forbidden"],
        },
        "edit_targets": [{"path": "src/agent_runtime/worker.py", "anchor": "def execute"}],
        "focused_tests": obligations["required_focused_tests"],
        "required_behavior": [
            {"id": item["id"], "text": item["text"], "risk_floor": item["risk_floor"]}
            for item in plan["contracts"]
            if item["id"] in unit["owned_contract_ids"]
        ],
        "acceptance_criteria": obligations["acceptance_criteria"],
        "acceptance_scenarios": obligations["acceptance_scenarios"],
        "required_order": obligations["required_order"],
        "forbidden_orderings": obligations["forbidden_orderings"],
        "validation_profile": obligations["validation_profile"],
    }


def test_packet_uses_existing_schema_and_clamps_risk(packet_pair: tuple[dict, dict]) -> None:
    plan, packet = packet_pair
    original = copy.deepcopy(packet)
    normalized = CONTRACT.validate_unit_packet(plan, packet)
    assert normalized["risk"]["unit"] == "high"
    assert packet == original


def test_packet_rejects_foreign_contract_and_schema(packet_pair: tuple[dict, dict]) -> None:
    plan, packet = packet_pair
    packet["owned_contract_ids"] = ["new-contract"]
    with pytest.raises(ValueError, match="owned contracts differ"):
        CONTRACT.validate_unit_packet(plan, packet)
    packet["owned_contract_ids"] = ["behavior-1"]
    packet["required_behavior"][0]["id"] = "new-contract"
    with pytest.raises(ValueError, match="undeclared contract"):
        CONTRACT.validate_unit_packet(plan, packet)
    packet["required_behavior"][0]["id"] = "behavior-1"
    packet["schema_version"] = 1
    with pytest.raises(ValueError, match="schema version 2"):
        CONTRACT.validate_unit_packet(plan, packet)


def test_packet_rejects_stale_primary_plan(packet_pair: tuple[dict, dict]) -> None:
    plan, packet = packet_pair
    plan["contracts"][0]["text"] = "Revised required behavior."
    with pytest.raises(ValueError, match="fingerprint is missing or stale"):
        CONTRACT.validate_unit_packet(plan, packet)
    plan["contracts"][0]["text"] = packet["required_behavior"][0]["text"]
    plan["plan_revision"] = 2
    with pytest.raises(ValueError, match="plan_revision differs"):
        CONTRACT.validate_unit_packet(plan, packet)


def test_malformed_plan_and_packet_ids_fail_with_contract_errors(
    packet_pair: tuple[dict, dict],
) -> None:
    plan, packet = packet_pair
    plan["units"][0]["packet_contract"]["required_focused_tests"] = [None]
    with pytest.raises(ValueError, match="required_focused_tests"):
        CONTRACT.validate_feature_plan(plan)
    plan["units"][0]["packet_contract"]["required_focused_tests"] = ["tests/test_example.py"]
    packet["required_behavior"][0]["id"] = ["behavior-1"]
    with pytest.raises(ValueError, match="required_behavior.id"):
        CONTRACT.validate_unit_packet(plan, packet)


@pytest.mark.parametrize(
    ("field", "change", "error"),
    [
        ("contract", "weaken", "changed Primary contract text"),
        ("read", ".", "read path exceeds Primary authority"),
        ("modify", "src/other.py", "modify path exceeds Primary authority"),
        ("create", "tests/test_unapproved.py", "create path exceeds Primary authority"),
        ("readonly", "remove", "omitted Primary protected"),
        ("forbidden", "remove", "omitted Primary forbidden"),
    ],
)
def test_packet_cannot_expand_scope_or_weaken_behavior(
    packet_pair: tuple[dict, dict], field: str, change: str, error: str
) -> None:
    plan, packet = packet_pair
    if field == "contract":
        packet["required_behavior"][0]["text"] = change
    elif field == "read":
        packet["scope"]["read"] = [change]
    elif field in {"modify", "create"}:
        packet["scope"][field].append(change)
        if field == "modify":
            packet["edit_targets"].append({"path": change, "anchor": "def other"})
            packet["scope"]["read"].append("src/other.py")
        else:
            packet["scope"]["read"].append(change)
    else:
        packet["scope"][field] = []
    with pytest.raises(ValueError, match=error):
        CONTRACT.validate_unit_packet(plan, packet)


def test_primary_scope_ceiling_rejects_traversal(plan: dict) -> None:
    plan["units"][1]["scope_authority"]["modify"] = ["../other.py"]
    with pytest.raises(ValueError, match="normalized repository-relative path"):
        CONTRACT.validate_feature_plan(plan)


@pytest.mark.parametrize(
    ("field", "error"),
    [
        ("acceptance_criteria", "changed Primary acceptance_criteria"),
        ("acceptance_scenarios", "changed Primary acceptance_scenarios"),
        ("required_order", "changed Primary required_order"),
        ("forbidden_orderings", "changed Primary forbidden_orderings"),
        ("validation_profile", "changed Primary validation_profile"),
        ("focused_tests", "omitted Primary required focused tests"),
    ],
)
def test_packet_cannot_drop_primary_acceptance(
    packet_pair: tuple[dict, dict], field: str, error: str
) -> None:
    plan, packet = packet_pair
    if field == "acceptance_criteria":
        packet[field][0]["text"] = "Only compile succeeds."
    elif field == "acceptance_scenarios":
        packet[field][0]["observables"] = {"commit_calls": 0}
    elif field in {"required_order", "forbidden_orderings"}:
        packet[field] = []
    elif field == "validation_profile":
        packet[field] = "different-profile"
    else:
        packet[field] = ["tests/test_example_supplement.py"]
    with pytest.raises(ValueError, match=error):
        CONTRACT.validate_unit_packet(plan, packet)


def test_decision_is_closed_enum_with_reason_for_rework(plan: dict) -> None:
    unit_id = "worker-success-finalization"
    assert (
        CONTRACT.validate_decision(
            plan,
            {"decision": "REWORK_LOCAL", "unit_id": unit_id, "reason_code": "focused-test-red"},
        )["reason_code"]
        == "focused-test-red"
    )
    with pytest.raises(ValueError, match="legal enum"):
        CONTRACT.validate_decision(plan, {"decision": "ACCEPT", "unit_id": unit_id})
    with pytest.raises(ValueError, match="reason_code"):
        CONTRACT.validate_decision(plan, {"decision": "REWORK_LOCAL", "unit_id": unit_id})
    with pytest.raises(ValueError, match="unknown unit"):
        CONTRACT.validate_decision(plan, {"decision": "CONTINUE", "unit_id": "invented"})
    with pytest.raises(ValueError, match="unknown fields"):
        CONTRACT.validate_decision(
            plan, {"decision": "FEATURE_READY", "unit_id": unit_id, "accepted": True}
        )


def test_transition_blocks_dependency_and_premature_feature_ready(plan: dict) -> None:
    downstream = "worker-success-finalization"
    request = {"decision": "CONTINUE", "unit_id": downstream}
    with pytest.raises(ValueError, match="dependencies are not accepted"):
        CONTRACT._validate_decision_transition(plan, request, primary_accepted_units=set())
    assert (
        CONTRACT._validate_decision_transition(
            plan, request, primary_accepted_units={"lease-test-support"}
        )
        == request
    )
    ready = {"decision": "FEATURE_READY", "unit_id": downstream}
    with pytest.raises(ValueError, match="unaccepted units"):
        CONTRACT._validate_decision_transition(
            plan, ready, primary_accepted_units={"lease-test-support", downstream}
        )
    with pytest.raises(ValueError, match="integration evidence is unverified"):
        CONTRACT._validate_decision_transition(
            plan,
            ready,
            primary_accepted_units={unit["unit_id"] for unit in plan["units"]},
        )
    assert (
        CONTRACT._validate_decision_transition(
            plan,
            ready,
            primary_accepted_units={unit["unit_id"] for unit in plan["units"]},
            integration_verified=True,
        )
        == ready
    )


def test_transition_never_reworks_accepted_unit(plan: dict) -> None:
    with pytest.raises(ValueError, match="cannot locally rework accepted unit"):
        CONTRACT._validate_decision_transition(
            plan,
            {
                "decision": "REWORK_LOCAL",
                "unit_id": "lease-test-support",
                "reason_code": "focused-test-red",
            },
            primary_accepted_units={"lease-test-support"},
        )


def test_accepted_units_require_primary_and_reviewer_archives(plan: dict, tmp_path: Path) -> None:
    unit_id = "worker-success-finalization"
    task_id = "lease-fencing"
    run_id = "lease-test-a1"
    review_id = "auto-review-a1"
    task_root = tmp_path / ".agent" / "tasks" / task_id
    archive = task_root / "runs" / run_id
    reviewer = task_root / "reviews" / review_id
    archive.mkdir(parents=True)
    reviewer.mkdir(parents=True)
    identity = {
        "task_id": task_id,
        "feature_id": plan["feature_id"],
        "unit_id": unit_id,
        "run_id": run_id,
        "plan_revision": plan["plan_revision"],
    }
    records = {
        archive / "review.json": {
            "task_id": task_id,
            "unit_id": unit_id,
            "run_id": run_id,
            "decision": "accept",
            "worker_status": "ready_for_review",
            "local_review_id": review_id,
        },
        archive / "handoff.json": {"identity": identity, "status": "ready_for_review"},
        archive / "completed.json": {"status": "ready_for_review"},
        archive / "packet.json": packet_for_lease_worker(plan, run_id),
        reviewer / "handoff.json": {
            "identity": {**identity, "review_id": review_id},
            "decision": "pass_to_primary",
        },
        reviewer / "completed.json": {"decision": "pass_to_primary"},
    }
    for path, value in records.items():
        path.write_text(json.dumps(value), encoding="utf-8")
    refs = {unit_id: {"task_id": task_id, "run_id": run_id}}
    assert CONTRACT.accepted_units_from_archives(plan, tmp_path, refs) == {unit_id}
    assert (
        CONTRACT.validate_decision_transition(
            plan,
            {"decision": "CONTINUE", "unit_id": "lease-documentation"},
            repo_root=tmp_path,
            run_refs=refs,
        )["decision"]
        == "CONTINUE"
    )

    (archive / "handoff.json").write_text(
        json.dumps(
            {
                **records[archive / "handoff.json"],
                "changed_files": [{"path": "src/agent_runtime/unapproved.py"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="changed path exceeds Primary authority"):
        CONTRACT.accepted_units_from_archives(plan, tmp_path, refs)
    (archive / "handoff.json").write_text(
        json.dumps(records[archive / "handoff.json"]), encoding="utf-8"
    )

    (reviewer / "completed.json").write_text(json.dumps({"decision": "rework"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Reviewer pass"):
        CONTRACT.accepted_units_from_archives(plan, tmp_path, refs)
    (reviewer / "completed.json").write_text(
        json.dumps({"decision": "pass_to_primary"}), encoding="utf-8"
    )
    (archive / "review.json").write_text(
        json.dumps({**records[archive / "review.json"], "decision": "rework"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="accepted Coder evidence"):
        CONTRACT.validate_decision_transition(
            plan,
            {"decision": "CONTINUE", "unit_id": "lease-documentation"},
            repo_root=tmp_path,
            run_refs=refs,
        )


def test_primary_owned_unit_uses_fixed_plan_bound_review(plan: dict, tmp_path: Path) -> None:
    unit_id = "lease-test-support"
    path = tmp_path / ".agent" / "primary-reviews" / plan["feature_id"] / f"{unit_id}.json"
    path.parent.mkdir(parents=True)
    review = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "unit_id": unit_id,
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
        "decision": "accept",
        "evidence": ["protected lease test authored and reviewed"],
    }
    path.write_text(json.dumps(review), encoding="utf-8")
    assert CONTRACT.accepted_units_from_archives(plan, tmp_path, {unit_id: {}}) == {unit_id}
    plan["contracts"][0]["text"] = "Weakened test contract."
    with pytest.raises(ValueError, match="missing or stale"):
        CONTRACT.accepted_units_from_archives(plan, tmp_path, {unit_id: {}})


def test_feature_ready_requires_fresh_integration_archive(plan: dict, tmp_path: Path) -> None:
    plan["units"] = plan["units"][:1]
    plan["contracts"] = plan["contracts"][:1]
    unit_id = "lease-test-support"
    source = tmp_path / "tests" / "test_lease_fencing.py"
    source.parent.mkdir()
    source.write_text("assert True\n", encoding="utf-8")
    review_path = tmp_path / ".agent" / "primary-reviews" / plan["feature_id"] / f"{unit_id}.json"
    review_path.parent.mkdir(parents=True)
    review_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_id": plan["feature_id"],
                "unit_id": unit_id,
                "plan_revision": plan["plan_revision"],
                "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
                "decision": "accept",
                "evidence": ["reviewed protected assertions"],
                "changed_files": ["tests/test_lease_fencing.py"],
            }
        ),
        encoding="utf-8",
    )
    decision = {"decision": "FEATURE_READY", "unit_id": unit_id}
    refs = {unit_id: {}}
    with pytest.raises(FileNotFoundError):
        CONTRACT.validate_decision_transition(plan, decision, repo_root=tmp_path, run_refs=refs)
    validation_path = tmp_path / ".agent" / "integration" / plan["feature_id"] / "validation.json"
    validation_path.parent.mkdir(parents=True)
    evidence = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": CONTRACT.authority_fingerprint(plan),
        "integration_risk": plan["integration_risk"],
        "status": "passed",
        "checks": [{"id": "focused-tests", "status": "passed", "exit_code": 0}],
        "files": [
            {
                "path": "tests/test_lease_fencing.py",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        ],
    }
    validation_path.write_text(json.dumps(evidence), encoding="utf-8")
    assert (
        CONTRACT.validate_decision_transition(plan, decision, repo_root=tmp_path, run_refs=refs)
        == decision
    )
    ready_state = CONTRACT.apply_coordinator_decision(
        plan,
        CONTRACT.new_coordinator_state(plan),
        decision,
        expected_sequence=0,
        repo_root=tmp_path,
        run_refs=refs,
    )
    assert ready_state["feature_phase"] == "ready"
    with pytest.raises(ValueError, match="feature is already ready"):
        CONTRACT.apply_coordinator_decision(
            plan,
            ready_state,
            decision,
            expected_sequence=1,
            repo_root=tmp_path,
            run_refs=refs,
        )
    other = tmp_path / "docs" / "unrelated.md"
    other.parent.mkdir()
    other.write_text("not the accepted test\n", encoding="utf-8")
    missing_change = copy.deepcopy(evidence)
    missing_change["files"] = [
        {"path": "docs/unrelated.md", "sha256": hashlib.sha256(other.read_bytes()).hexdigest()}
    ]
    validation_path.write_text(json.dumps(missing_change), encoding="utf-8")
    with pytest.raises(ValueError, match="omits accepted changes"):
        CONTRACT.validate_decision_transition(plan, decision, repo_root=tmp_path, run_refs=refs)
    validation_path.write_text(json.dumps(evidence), encoding="utf-8")
    source.write_text("assert False\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after validation"):
        CONTRACT.validate_decision_transition(plan, decision, repo_root=tmp_path, run_refs=refs)


def test_coordinator_memory_is_plan_bound_and_non_authoritative(plan: dict) -> None:
    state = CONTRACT.new_coordinator_state(plan)
    CONTRACT.validate_coordinator_state(plan, state)
    assert state["sequence"] == 0
    assert state["policy_violation_blocked_count"] == 0
    assert "accepted_units" not in state
    stale = copy.deepcopy(state)
    original_text = plan["contracts"][0]["text"]
    plan["contracts"][0]["text"] = "Revised Primary contract."
    with pytest.raises(ValueError, match="primary_plan_sha256"):
        CONTRACT.validate_coordinator_state(plan, stale)
    plan["contracts"][0]["text"] = original_text
    forged = copy.deepcopy(state)
    forged["units"]["lease-test-support"]["phase"] = "accepted"
    with pytest.raises(ValueError, match="phase is not legal"):
        CONTRACT.validate_coordinator_state(plan, forged)


def test_coordinator_memory_advances_only_after_archive_gate(plan: dict, tmp_path: Path) -> None:
    state = CONTRACT.new_coordinator_state(plan)
    first = "lease-test-support"
    allowed = CONTRACT.apply_coordinator_decision(
        plan,
        state,
        {"decision": "CONTINUE", "unit_id": first},
        expected_sequence=0,
        repo_root=tmp_path,
        run_refs={},
    )
    assert state["sequence"] == 0
    assert allowed["sequence"] == 1
    assert allowed["units"][first]["phase"] == "running"
    with pytest.raises(ValueError, match="sequence is stale"):
        CONTRACT.apply_coordinator_decision(
            plan,
            allowed,
            {"decision": "REWORK_LOCAL", "unit_id": first, "reason_code": "failed-test"},
            expected_sequence=0,
            repo_root=tmp_path,
            run_refs={},
        )
    with pytest.raises(ValueError, match="dependencies are not accepted"):
        CONTRACT.apply_coordinator_decision(
            plan,
            allowed,
            {"decision": "CONTINUE", "unit_id": "worker-success-finalization"},
            expected_sequence=1,
            repo_root=tmp_path,
            run_refs={},
        )
    assert allowed["sequence"] == 1
    rework = CONTRACT.apply_coordinator_decision(
        plan,
        allowed,
        {"decision": "REWORK_LOCAL", "unit_id": first, "reason_code": "failed-test"},
        expected_sequence=1,
        repo_root=tmp_path,
        run_refs={},
    )
    assert rework["units"][first] == {
        "phase": "rework",
        "rework_count": 1,
        "last_failure_signature": "failed-test",
    }
    blocked = CONTRACT.record_policy_block(plan, rework, first, "scope-escape")
    assert blocked["policy_violation_blocked_count"] == 1
    assert blocked["infra_failure_count"] == 0
    assert blocked["recent_events"][-1]["outcome"] == "blocked"
    assert blocked["units"][first] == rework["units"][first]
    infra = CONTRACT.record_infra_failure(plan, blocked, first, "model-http-400")
    assert infra["infra_failure_count"] == 1
    assert infra["policy_violation_blocked_count"] == 1
    assert infra["units"][first] == blocked["units"][first]
    forged_infra = copy.deepcopy(infra)
    forged_infra["infra_failure_count"] = 0
    with pytest.raises(ValueError, match="infra counter"):
        CONTRACT.validate_coordinator_state(plan, forged_infra)
    forged = copy.deepcopy(blocked)
    forged["policy_violation_blocked_count"] = 0
    with pytest.raises(ValueError, match="policy counter"):
        CONTRACT.validate_coordinator_state(plan, forged)
    forged = copy.deepcopy(blocked)
    forged["recent_events"] = []
    with pytest.raises(ValueError, match="lacks recent events"):
        CONTRACT.validate_coordinator_state(plan, forged)
    escalated = CONTRACT.apply_coordinator_decision(
        plan,
        blocked,
        {"decision": "ESCALATE_PRIMARY", "unit_id": first, "reason_code": "semantic-failure"},
        expected_sequence=blocked["sequence"],
        repo_root=tmp_path,
        run_refs={},
    )
    with pytest.raises(ValueError, match="escalated unit needs"):
        CONTRACT.apply_coordinator_decision(
            plan,
            escalated,
            {"decision": "CONTINUE", "unit_id": first},
            expected_sequence=escalated["sequence"],
            repo_root=tmp_path,
            run_refs={},
        )
