"""Diagnostic config split never relaxes canonical Coder validation checks."""

import copy
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "benchmarks"))
sys.path.insert(0, str(KIT / ".local-agents/tests"))
import harness_r4_real_review as H
import reviewer_evidence_state as OBS
import reviewer_experiment_entry as ENTRY
import test_reviewer_compact_dto as T


def build(row, config, name, adapter=ENTRY):
    root = Path(row["root"])
    module = H.R.load(root / ".local-agents/reviewer-runtime.py", name)
    identity = {**row["identity"], "review_id": "offline-" + name.replace("_", "-")}
    runtime = adapter.install(module)(root, identity, config, T.H.FakeClient([]))
    return runtime, module


def test_every_copied_byte_and_excluded_original_are_preserved():
    registry = H.B.read(H.BATCH / "registration.json")
    assert len(registry["cells"]) == 2 and registry["not_transfer_credit"]
    for row in registry["cells"]:
        root = Path(row["root"])
        for path, source in row["copied_inputs"].items():
            assert (
                H.B.sha(root / path)
                == source["sha256"]
                == H.B.sha(Path(source["origin"]))
            )
        for item in row["excluded_prior_review_outputs"].values():
            assert H.B.sha(Path(item["path"])) == item["sha256"]
        assert not (root / ".agent/current-task.json").exists()
        config = H.B.read(root / ".agent/experiment-config.json")
        original = H.B.read(Path(row["origin"]) / ".agent/config.json")
        assert {k: v for k, v in config.items() if k not in ENTRY.SWITCHES} == original
        runtime, _ = build(row, config, "origin_" + row["id"])
        assert runtime.max_turns == 16 and runtime.max_protocol_errors == 4
        assert not runtime.read_lines
        assert (
            runtime.initial_payload()["owned_contract_ids"]
            == runtime.packet["owned_contract_ids"]
        )


@pytest.mark.parametrize(
    "field",
    [
        "reviewer_model",
        "coder_model",
        "max_reviewer_turns",
        "max_model_turns",
        "validation_profiles",
        "unknown_override",
    ],
)
def test_substantive_or_unknown_config_change_still_fails_hash(field):
    row = H.B.read(H.BATCH / "registration.json")["cells"][0]
    config = copy.deepcopy(
        H.B.read(Path(row["root"]) / ".agent/experiment-config.json")
    )
    config[field] = (
        {} if field == "validation_profiles" else 99 if "turns" in field else "changed"
    )
    with pytest.raises(ValueError, match="Trusted host configuration changed"):
        build(row, config, "bad_" + field)


@pytest.mark.parametrize("value", [False, None, "true"])
def test_unapproved_adapter_switch_rejected(value):
    row = H.B.read(H.BATCH / "registration.json")["cells"][0]
    config = H.B.read(Path(row["root"]) / ".agent/experiment-config.json")
    config["reviewer_evidence_state"] = value
    with pytest.raises(RuntimeError, match="explicitly enabled"):
        build(row, config, "disabled")


def test_all_sixteen_payloads_and_tool_protocol_are_identical():
    for row in H.B.read(H.E.BATCH / "registration.json")["cells"]:
        config = H.B.read(Path(row["root"]) / ".agent/experiment-config.json")
        a, _ = build(row, config, "equiv_" + row["id"], adapter=OBS)
        b, _ = build(row, config, "equiv_" + row["id"], adapter=ENTRY)
        assert a.initial_payload() == b.initial_payload()
        assert a.system_prompt() == b.system_prompt()
        assert a.report_template() == b.report_template()
        for path in ("src/product/target.py", "tests/test_target.py"):
            assert a.read_file({"path": path}) == b.read_file({"path": path})


def test_actual_cli_bridge_with_http_stub(tmp_path, monkeypatch):
    save = T.D.B.save

    def save_config(path, value):
        if path.name == "config.json":
            value = {**value, "reviewer_evidence_state": True}
        return save(path, value)

    monkeypatch.setattr(T.D, "ADAPTER", H.ADAPTER)
    monkeypatch.setattr(T.D.B, "save", save_config)
    T.test_actual_cli_serializes_provenance_with_http_stub(tmp_path)
    assert (
        H.B.read(tmp_path / "result.json")["evidence_observation_protocol"]
        == OBS.PROTOCOL
    )
