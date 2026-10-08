"""Observed integration to terminal recommendation; never accepts a feature."""

import argparse
import importlib.util
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import coordinator_receipt_pilot as pilot
from capability_fit import write
from inherited_context_recovery import digest, read


def finish(identity):
    contract = pilot.configure()
    cell = next(c for c in pilot.matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    plan = read(root / ".agent/feature-plan.json")
    integration = read(root / ".agent/feature-integration.json")
    refs, expected = {}, dict(cell["hashes"])
    for unit in cell["units"]:
        packet = read(root / f".agent/{unit}-bound.json")
        refs[unit] = {k: packet[k] for k in ("task_id", "run_id")}
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        for change in read(archive / "handoff.json")["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
    if contract.accepted_units_from_archives(plan, root, refs) != set(cell["units"]):
        raise ValueError("unaccepted unit")
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    suites = (
        ET.parse(root / ".agent/feature-integration.xml").getroot().iter("testsuite")
    )
    counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.get(key, 0))
    if counts != {"tests": 4, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError("integration JUnit not four executed passing tests")
    if (
        not integration["inputs_unchanged"]
        or not integration["checks"]["all_checks_pass"]
    ):
        raise ValueError("integration failed")
    evidence = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": contract.authority_fingerprint(plan),
        "integration_risk": plan["integration_risk"],
        "status": "passed",
        "checks": [
            {"id": f"integration-{i}", "status": "passed", "exit_code": c["exit"]}
            for i, c in enumerate(integration["checks"]["checks"])
        ],
        "files": [{"path": p, "sha256": sha} for p, sha in expected.items()],
        "source_evidence": ".agent/feature-integration.json",
        "junit_sha256": digest(root / ".agent/feature-integration.xml"),
        "primary_feature_accepted": False,
    }
    write(
        root / ".agent/integration" / plan["feature_id"] / "validation.json", evidence
    )
    contract.verify_integration_archive(plan, root, refs)
    if cell["arm"] != "coordinator":
        print(
            "Control integration provenance verified; Primary final review remains required"
        )
        return
    spec = importlib.util.spec_from_file_location(
        "receipt_finish_model", pilot.SNAPSHOT / ".local-agents/coordinator-runtime.py"
    )
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    config = read(root / ".agent/config.json")
    client = model.WORKER.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        structured_output=False,
        timeout=config["coordinator_request_timeout_seconds"],
        max_tokens=config["coordinator_max_tokens"],
        context_length=config["coordinator_context_length"],
    )
    state = contract.load_coordinator_state(
        plan, root, root / ".agent/coordinator" / plan["feature_id"] / "state.json"
    )
    execution = contract.verified_execution_evidence(plan, root, state, refs)
    write(
        root / ".agent/coordinator-finish-registration.json",
        {
            "driver_sha256": digest(Path(__file__)),
            "purpose": "Additional fresh terminal recommendation probe after actual integration; no worker dispatch, acceptance or E/C/R credit",
            "runtime_execution": execution,
        },
    )
    started = time.monotonic()
    with model.RESIDENCY.role_model_lease(client, config):
        result = model.probe(
            plan,
            {
                "question": "Recommend the next bounded step from verified execution facts. No tool call, acceptance or further worker execution."
            },
            "decision",
            client,
            execution_evidence=execution,
            reasoning_strength=config["coordinator_reasoning_strength"],
        )
    write(root / ".agent/coordinator-finish-model.json", result)
    gate = (
        contract.gate_model_decision(
            plan,
            root,
            state,
            result["output"],
            refs,
            expected_sequence=state["sequence"],
        )
        if result["status"] == "protocol_valid"
        else None
    )
    report = {
        "seconds": time.monotonic() - started,
        "gate": gate,
        "expected_feature_ready": bool(
            gate and gate["decision"]["decision"] == "FEATURE_READY"
        ),
        "dispatch_allowed": False,
        "primary_feature_accepted": False,
    }
    write(root / ".agent/coordinator-finish-result.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("identity")
    finish(parser.parse_args().identity)
