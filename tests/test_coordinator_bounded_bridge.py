"""Real offline host archive + synthetic review metadata, never live qualification."""

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest
from test_installable_bounded import F, L, S, archive, project

BRIDGE = F.load(S.KIT / ".local-agents/coordinator-bounded.py", "bridge_control")


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture(scope="module")
def sample():
    with tempfile.TemporaryDirectory(prefix="bounded-bridge-control-") as directory:
        root = Path(directory)
        packet, config = project(root, "labels", "bridge-offline")
        consumer_path = "src/product/consumer.py"
        (root / consumer_path).write_text("VALUE = 1\n", encoding="utf-8")
        packet["scope"]["readonly"].append(consumer_path)
        for item in packet["acceptance_scenarios"]:
            item.setdefault(
                "observables",
                {"contract": "Protected normal, error and boundary cases"},
            )
        consumer_behavior = {
            "id": "consumer",
            "text": "Consume the independently accepted labels result without altering producer behavior",
            "risk_floor": "high",
            "implementation_ref": {"path": consumer_path, "symbol": "consume"},
        }
        consumer_packet = copy.deepcopy(packet)
        consumer_packet.update(
            unit_id="consumer",
            run_id="consumer-run",
            dependencies=[packet["unit_id"]],
            owned_contract_ids=["consumer"],
            required_behavior=[consumer_behavior],
        )
        consumer_packet["scope"]["modify"] = [consumer_path]
        consumer_packet["edit_targets"] = [
            {"path": consumer_path, "anchor": "def consume("}
        ]
        consumer_packet["scope"]["readonly"].remove(consumer_path)
        consumer_packet["scope"]["readonly"].append("src/product/code.py")
        plan = {
            "schema_version": 1,
            "plan_revision": packet["plan_revision"],
            "feature_id": packet["feature_id"],
            "task_id": packet["task_id"],
            "feature_risk": "high",
            "integration_risk": "high",
            "contracts": copy.deepcopy(packet["required_behavior"])
            + [consumer_behavior],
            "units": [],
        }
        for proposed in (packet, consumer_packet):
            scope = proposed["scope"]
            plan["units"].append(
                {
                    "unit_id": proposed["unit_id"],
                    "owner": "local-coder",
                    "risk": "high",
                    "dependencies": proposed["dependencies"],
                    "owned_contract_ids": proposed["owned_contract_ids"],
                    "scope_authority": {
                        "read_roots": scope["read"],
                        **{
                            k: scope[k]
                            for k in ("modify", "create", "readonly", "forbidden")
                        },
                    },
                    "packet_contract": {
                        **{
                            k: proposed[k]
                            for k in (
                                "acceptance_criteria",
                                "acceptance_scenarios",
                                "required_order",
                                "forbidden_orderings",
                                "validation_profile",
                            )
                        },
                        "required_focused_tests": proposed["focused_tests"],
                    },
                }
            )
        for proposed in (packet, consumer_packet):
            proposed["primary_plan_sha256"] = BRIDGE.CONTRACT.authority_fingerprint(
                plan
            )
            BRIDGE.CONTRACT.validate_unit_packet(plan, proposed)
        write(root / ".agent/packet.json", packet)
        # Mock the model transport, not the verifier. No HTTP/role loading occurs.
        # The separate CLI-replay rejection control below preserves scripted provenance.
        previous_bounded = {
            name: module
            for name, module in sys.modules.items()
            if name == "bounded" or name.startswith("bounded.")
        }
        sys.path.insert(0, str(root / ".local-agents"))
        try:
            entry = F.load(
                root / ".local-agents/local-bounded-unit.py", "bridge_mock_entry"
            )
        finally:
            sys.path.pop(0)
        worker = F.load(root / ".local-agents/worker-runtime.py", "bridge_mock_worker")
        client = entry.ReplayClient(
            [{"replacement": L.TASKS["labels"]["reference"]}], worker
        )
        client.offline = False
        runtime = entry.H.make_runtime(worker, proposal_rules=entry.RULES)(
            root, packet, config, client
        )
        try:
            runtime.preflight()
            outcome = runtime.run()
            assert outcome["status"] == BRIDGE.GATE.HOST.PENDING
        finally:
            runtime.close()
            for name in list(sys.modules):
                if name == "bounded" or name.startswith("bounded."):
                    sys.modules.pop(name)
            sys.modules.update(previous_bounded)
        run_root = archive(root)
        identity = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
        review_id = "offline-synthetic-review"
        review_root = root / ".agent/tasks" / packet["task_id"] / "reviews" / review_id
        review_root.mkdir(parents=True)
        report = {
            "identity": {**identity, "review_id": review_id},
            "decision": "pass_to_primary",
            "findings": [],
            "reviewer_model_calls": 1,
            "verified_contract_ids": packet["owned_contract_ids"],
            "runtime_facts": {
                "read_only": True,
                "inputs_unchanged": True,
                "observed_read_hashes": {
                    p: S.sha(root / p)
                    for p in ("src/product/code.py", "tests/test_contract.py")
                },
            },
        }
        write(review_root / "handoff.json", report)
        write(review_root / "completed.json", {"decision": "pass_to_primary"})
        disposition = BRIDGE.DISPOSITION.adjudicate(
            report,
            S.sha(review_root / "handoff.json"),
            {
                "schema_version": 1,
                "authority": "primary",
                "identity": report["identity"],
                "report_sha256": S.sha(review_root / "handoff.json"),
                "resolution": "cleared",
                "evidence": [
                    "Synthetic offline control, not real semantic review or acceptance"
                ],
                "findings": [],
            },
        )
        write(
            run_root / "review.json",
            {
                **identity,
                "decision": "accept",
                "worker_status": BRIDGE.GATE.HOST.PENDING,
                "local_review_id": review_id,
                "review_disposition": disposition,
            },
        )
        catalog = {
            b["id"]: {
                "family": BRIDGE.FAMILY,
                **b["implementation_ref"],
                "qualification_evidence": "Synthetic offline route control, not live qualification",
            }
            for b in plan["contracts"]
        }
        consumer_config = copy.deepcopy(config)
        consumer_config["coder_single_function"] = {
            "path": consumer_path,
            "symbol": "consume",
        }
        yield {
            "root": root,
            "packet": packet,
            "config": config,
            "plan": plan,
            "catalog": catalog,
            "ref": {"task_id": packet["task_id"], "run_id": packet["run_id"]},
            "run": run_root,
            "review": review_root,
            "consumer_packet": consumer_packet,
            "consumer_config": consumer_config,
        }


def verify(s, **kwargs):
    return BRIDGE.verify_accepted_unit(
        s["plan"],
        s["root"],
        s["packet"]["unit_id"],
        s["ref"],
        s["config"],
        s["catalog"],
        bridge_profile="bounded-v1",
        **kwargs,
    )


def test_current_archive_passes_without_status_translation(sample):
    before = S.sha(sample["run"] / "handoff.json")
    receipt = verify(sample)
    assert receipt["worker_status"] == "validation_passed_pending_review"
    assert receipt["dispatch_allowed"] is receipt["automatic_acceptance"] is False
    assert S.sha(sample["run"] / "handoff.json") == before


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest",
        "junit",
        "diff",
        "source",
        "test",
        "config",
        "plan",
        "protocol",
        "primary",
        "disposition",
        "reviewer",
        "reviewer_completed",
        "missing_primary",
        "unknown_family",
        "scope",
        "coordinator",
        "wrong_symbol",
        "wrong_ref",
        "missing_optin",
    ],
)
def test_evidence_and_authority_fail_closed(sample, mutation):
    s = {k: copy.deepcopy(v) if isinstance(v, dict) else v for k, v in sample.items()}
    path, payload = None, None
    if mutation in {
        "manifest",
        "protocol",
        "primary",
        "disposition",
        "reviewer",
        "reviewer_completed",
    }:
        choices = {
            "manifest": s["run"] / "host-validation-facts.json",
            "protocol": s["run"] / "handoff.json",
            "primary": s["run"] / "review.json",
            "disposition": s["run"] / "review.json",
            "reviewer": s["review"] / "handoff.json",
            "reviewer_completed": s["review"] / "completed.json",
        }
        path = choices[mutation]
        payload = S.read(path)
        if mutation == "manifest":
            payload["trusted_config_sha256"] = "0" * 64
        elif mutation == "protocol":
            payload["execution_protocol"] = "unknown-protocol"
        elif mutation == "primary":
            payload["decision"] = "replan"
        elif mutation == "disposition":
            payload.pop("review_disposition")
        elif mutation == "reviewer":
            payload["findings"] = [{"id": "unreviewed-new-finding"}]
        else:
            payload["decision"] = "rework"
    elif mutation in {"junit", "diff", "source", "test", "missing_primary"}:
        paths = {
            "junit": s["run"] / "junit.xml",
            "diff": s["run"] / "cumulative.diff",
            "source": s["root"] / "src/product/code.py",
            "test": s["root"] / "tests/test_contract.py",
            "missing_primary": s["run"] / "review.json",
        }
        path = paths[mutation]
        if mutation == "junit":
            path = next(s["run"].glob("*junit*.xml"), None)
            if path is None:
                path = Path(
                    S.read(s["run"] / "validation.json")["focused_tests"]["junit"][
                        "path"
                    ]
                )
    elif mutation == "config":
        s["config"]["max_validation_runs"] = 99
    elif mutation == "plan":
        s["plan"]["plan_revision"] += 1
    elif mutation == "unknown_family":
        s["catalog"]["labels"]["family"] = "arbitrary-architecture"
    elif mutation == "scope":
        s["catalog"]["labels"]["path"] = "tests/test_contract.py"
    elif mutation == "coordinator":
        s["config"]["coordinator_enabled"] = True
    elif mutation == "wrong_symbol":
        s["catalog"]["labels"]["symbol"] = "other"
    elif mutation == "wrong_ref":
        s["ref"]["run_id"] = "../foreign"
    original = path.read_bytes() if path else None
    try:
        if path and payload is not None:
            write(path, payload)
        elif path and mutation == "missing_primary":
            path.unlink()
        elif path:
            path.write_bytes(original + b"\nchanged control\n")
        with pytest.raises((ValueError, OSError, BRIDGE.GATE.HandoffError)):
            if mutation == "missing_optin":
                BRIDGE.verify_accepted_unit(
                    s["plan"],
                    s["root"],
                    s["packet"]["unit_id"],
                    s["ref"],
                    s["config"],
                    s["catalog"],
                )
            else:
                verify(s)
    finally:
        if path:
            path.write_bytes(original)
    verify(sample)


def test_dependency_ready_requires_current_exact_accepted_archive(sample):
    s = sample
    kwargs = {"bridge_profile": "bounded-v1"}
    args = (
        s["plan"],
        s["root"],
        s["consumer_packet"],
        s["consumer_config"],
        s["catalog"],
    )
    with pytest.raises(ValueError, match="Dependency lacks"):
        BRIDGE.dependency_readiness(*args, {}, {}, **kwargs)
    unit_id = s["packet"]["unit_id"]
    receipt = BRIDGE.dependency_readiness(
        *args, {unit_id: s["ref"]}, {unit_id: s["config"]}, **kwargs
    )
    assert set(receipt["dependencies_verified"]) == {unit_id}
    assert receipt["eligible_for_primary_dispatch"] and not receipt["dispatch_allowed"]


def test_legacy_coordinator_still_rejects_pending_archive(sample):
    with pytest.raises(ValueError, match="accepted Coder evidence"):
        BRIDGE.CONTRACT.accepted_units_from_archives(
            sample["plan"], sample["root"], {sample["packet"]["unit_id"]: sample["ref"]}
        )


def test_scripted_provenance_is_not_live_acceptance(sample):
    s = sample
    handoff_path, manifest_path = (
        s["run"] / "handoff.json",
        s["run"] / "host-validation-facts.json",
    )
    original = {p: p.read_bytes() for p in (handoff_path, manifest_path)}
    try:
        handoff = S.read(handoff_path)
        handoff["consolidated_harness"]["actual"].update(
            model_requests=0, scripted_requests=1
        )
        write(handoff_path, handoff)
        manifest = S.read(manifest_path)
        manifest["artifact_hashes"]["handoff.json"] = S.sha(handoff_path)
        write(manifest_path, manifest)
        with pytest.raises(ValueError, match="Live Coder provenance"):
            verify(s)
    finally:
        for path, raw in original.items():
            path.write_bytes(raw)
    verify(s)


def test_cross_snapshot_transfer_binds_exact_readonly_producer_bytes(sample):
    s = sample
    consumer = s["root"] / "consumer-snapshot"
    path = "src/product/code.py"
    target = consumer / path
    target.parent.mkdir(parents=True)
    raw = (s["root"] / path).read_bytes()
    target.write_bytes(raw)
    unit = s["packet"]["unit_id"]
    args = (
        s["plan"],
        consumer,
        s["consumer_packet"],
        s["consumer_config"],
        s["catalog"],
        {unit: s["ref"]},
        {unit: s["config"]},
    )
    kwargs = {"bridge_profile": "bounded-v1", "dependency_roots": {unit: s["root"]}}
    with pytest.raises(ValueError, match="explicit trusted evidence root"):
        BRIDGE.dependency_readiness(*args, **kwargs)
    kwargs["evidence_root"] = s["root"]
    with pytest.raises(ValueError, match="Explicit immutable dependency transfer"):
        BRIDGE.dependency_readiness(*args, **kwargs)
    kwargs["transfer_paths"] = {unit: {"source": path, "destination": path}}
    receipt = BRIDGE.dependency_readiness(*args, **kwargs)
    assert receipt["dependencies_verified"][unit]["transfer"]["sha256"] == S.sha(target)
    assert not receipt["dispatch_allowed"]
    target.write_bytes(raw + b"\n# changed producer copy\n")
    with pytest.raises(ValueError, match="differs from accepted producer"):
        BRIDGE.dependency_readiness(*args, **kwargs)
    target.write_bytes(raw)
    kwargs["transfer_paths"][unit]["destination"] = "src/product/consumer.py"
    with pytest.raises(ValueError, match="read-only scope"):
        BRIDGE.dependency_readiness(*args, **kwargs)
