"""Installed proposal-only CLI controls; all model/residency calls are scripted."""

import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
C = load("cli_route_existing_entry", ROOT / "coordinator-limited.py")
H = load("cli_route_adapter", ROOT / "coordinator-routing.py")
F = load("cli_route_fixture", ROOT / "tests/test_coordinator_limited.py")


@pytest.fixture
def case(tmp_path, monkeypatch):
    brief, raw, config_path, approval = F.LimitedEntryTests().fixture(tmp_path)
    catalog = {}
    for contract, unit in zip(brief["contracts"], raw["units"]):
        ref = {"path": unit["modify"][0], "symbol": unit["id"] + "_value"}
        contract["implementation_ref"] = ref
        catalog[contract["id"]] = {
            "family": H.FAMILY,
            **ref,
            "qualification_evidence": "Offline control only",
        }
        unit.pop("owner")
    config = {
        "python": sys.executable,
        "single_model_residency": True,
        "coordinator_enabled": True,
        "lmstudio_base_url": "http://127.0.0.1:12345/v1",
        "coordinator_model": "meta/muse-glimmer",
        "coordinator_reasoning_strength": "low",
    }
    inputs = {"brief": brief, "context": {}, "catalog": catalog, "config": config}
    paths = {key: tmp_path / ".agent" / (key + ".json") for key in inputs}
    calls, loads, leases = [], [], []

    class Client:
        last_request_stats = {}

        def complete(self, messages):
            calls.append(copy.deepcopy(messages))
            return json.dumps(raw)

    client = Client()

    @contextmanager
    def lease(selected, settings):
        assert selected is client and settings["single_model_residency"] is True
        leases.append("enter")
        yield
        leases.append("exit")

    def controlled_load(name, filename):
        loads.append(filename)
        return {
            "coordinator-routing.py": H,
            "worker-runtime.py": SimpleNamespace(LMStudioClient=lambda *a, **k: client),
            "model_residency.py": SimpleNamespace(role_model_lease=lease),
        }[filename]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(C, "load", controlled_load)
    output = tmp_path / ".agent/proposal.json"

    def invoke(*, action="propose", routed=True, authorized=True, context=True):
        for key, value in inputs.items():
            paths[key].write_text(json.dumps(value), encoding="utf-8")
        argv = [
            "coordinator-limited.py",
            action,
            "--brief",
            str(paths["brief"]),
            "--proposal",
            str(output),
            "--config",
            str(paths["config"]),
        ]
        if authorized:
            argv.append("--authorize-step")
        if context:
            argv += ["--context", str(paths["context"])]
        if routed:
            argv += ["--routing-catalog", str(paths["catalog"])]
        monkeypatch.setattr(sys, "argv", argv)
        return C.main()

    return SimpleNamespace(
        inputs=inputs,
        paths=paths,
        raw=raw,
        calls=calls,
        loads=loads,
        leases=leases,
        client=client,
        invoke=invoke,
        output=output,
        root=tmp_path,
    )


def test_explicit_cli_exactly_matches_direct_routing_api(case):
    expected = H.probe(
        case.inputs["brief"],
        {},
        case.client,
        H.bind_catalog(case.inputs["brief"], case.inputs["catalog"]),
        reasoning_strength="low",
    )
    direct = copy.deepcopy(case.calls)
    case.calls.clear()
    assert case.invoke() == 0
    assert json.loads(case.output.read_text(encoding="utf-8")) == expected
    assert case.calls == direct
    assert case.leases == ["enter", "exit"]
    assert expected["dispatch_allowed"] is False
    assert not (case.root / ".agent/approval.json").exists()
    assert not (case.root / ".agent/tasks").exists()


def test_omitted_option_keeps_legacy_wire_and_result(case):
    for unit in case.raw["units"]:
        unit["owner"] = "local-coder"
    expected = C.BRIEF.probe(case.inputs["brief"], {}, case.client, reasoning_strength="low")
    direct = copy.deepcopy(case.calls)
    case.calls.clear()
    assert case.invoke(routed=False) == 0
    assert json.loads(case.output.read_text(encoding="utf-8")) == expected
    assert case.calls == direct
    assert "coordinator-routing.py" not in case.loads


@pytest.mark.parametrize(
    "defect",
    [
        "authority",
        "disabled",
        "residency",
        "context",
        "catalog",
        "recipe",
        "stale-source",
        "existing-output",
    ],
)
def test_preflight_failure_never_loads_or_calls_model(case, defect):
    args = {}
    if defect == "authority":
        args["authorized"] = False
    elif defect == "disabled":
        case.inputs["config"]["coordinator_enabled"] = False
    elif defect == "residency":
        case.inputs["config"]["single_model_residency"] = False
    elif defect == "context":
        args["context"] = False
    elif defect == "catalog":
        case.inputs["catalog"]["producer"]["symbol"] = "different"
    elif defect == "recipe":
        case.inputs["brief"]["acceptance_catalog"]["producer"]["acceptance_criteria"] = []
    elif defect == "stale-source":
        (case.root / "src/a.py").write_text("value=2\n", encoding="utf-8")
    else:
        case.output.write_text("original immutable evidence", encoding="utf-8")
    assert case.invoke(**args) == 2
    assert case.calls == case.leases == []
    assert "worker-runtime.py" not in case.loads
    if defect == "existing-output":
        assert case.output.read_text(encoding="utf-8") == "original immutable evidence"
    else:
        assert not case.output.exists()


@pytest.mark.parametrize("action", ["approve", "dispatch", "inspect"])
def test_new_option_cannot_change_approval_or_execution(case, action):
    assert case.invoke(action=action) == 2
    assert case.calls == case.loads == case.leases == []
    assert not case.output.exists()


def test_model_owner_is_not_silently_rewritten(case):
    case.raw["units"][0]["owner"] = "local-coder"
    assert case.invoke() == 0  # Established proposal-status transport, not acceptance.
    result = json.loads(case.output.read_text(encoding="utf-8"))
    assert result["status"] == "proposal_failed"
    assert result["dispatch_allowed"] is False
    assert len(case.calls) == 2  # One bounded protocol correction only.
    assert all(not row["protocol_valid"] for row in result["attempts"])


def test_source_drift_during_call_cannot_create_current_proposal(case, monkeypatch):
    original = case.client.complete

    def changed(messages):
        result = original(messages)
        (case.root / "src/a.py").write_text("value=2\n", encoding="utf-8")
        return result

    monkeypatch.setattr(case.client, "complete", changed)
    assert case.invoke() == 2
    assert len(case.calls) == 1
    assert not case.output.exists()
    diagnostic = json.loads(case.output.with_suffix(".invalid.json").read_text(encoding="utf-8"))
    assert diagnostic["status"] == "proposal_invalidated"
    assert diagnostic["dispatch_allowed"] is False
    assert diagnostic["untrusted_attempt"]["attempts"][0]["protocol_valid"] is True
    assert "proposal" not in diagnostic  # Cannot feed it to the normal approval reader.


def test_existing_drift_diagnostic_blocks_rerun_before_loading(case):
    diagnostic = case.output.with_suffix(".invalid.json")
    diagnostic.write_text("retained prior failure", encoding="utf-8")
    assert case.invoke() == 2
    assert diagnostic.read_text(encoding="utf-8") == "retained prior failure"
    assert case.calls == case.leases == []
    assert not case.output.exists()
