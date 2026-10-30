"""Audit sealed inputs and exercise real gates with scripted, offline proposals."""

import copy
import json
import re
import shutil
import sys

import bounded_evidence_candidate as C
import bounded_evidence_support as S
import bounded_evidence_tasks as TASKS
import capture_fixture_support as F

CELLS = S.BATCH / "cells-v4.json"
TASK_FREEZE = S.BATCH / "task-freeze-v4.json"
ARTIFACTS = S.BATCH / "readiness-v2"


def clone(row, target):
    root = target / "isolated"
    for path, digest in row["files"].items():
        source = __import__("pathlib").Path(row["root"]) / path
        if S.sha(source) != digest:
            raise ValueError("Prepared input drift: " + path)
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    return root


def runtime_at(root, responses):
    config, packet = (
        S.read(root / ".agent/config.json"),
        S.read(root / ".agent/packet.json"),
    )
    worker = F.load(root / ".local-agents/worker-runtime.py", "readiness_worker")
    host = F.load(root / ".local-agents/host-proposal.py", "readiness_host")
    C.install_binding(worker, F.POLICY_PATH, S.sha(root / F.POLICY_PATH))
    cls = C.make_runtime(worker, host)

    class Client:
        structured_output = True
        action_schema = copy.deepcopy(C.UNIFIED.SPAN.D.INTERFACE.WHOLE_SCHEMA)
        native_tools = None
        timeout = 180
        calls = 0

        def complete(self, messages):
            self.calls += 1
            return json.dumps(responses[self.calls - 1])

    runtime = cls(root, packet, config, Client())
    runtime.preflight()
    return runtime, host


def run_control(topic, row):
    saved = ARTIFACTS / "offline-chain-results" / (topic + ".json")
    if saved.exists():
        return S.read(saved)
    root = clone(row, ARTIFACTS / "offline-full-chain" / topic)
    reference = S.BATCH / "task-preparation-v4/private" / topic / "reference.py"
    source = reference.read_text(encoding="utf-8")
    worker = F.load(root / ".local-agents/worker-runtime.py", "readiness_symbol_loader")
    block = worker.SINGLE_FUNCTION.target(source, TASKS.TASKS[topic]["symbol"])[3]
    runtime, _host = runtime_at(root, [{"replacement": block}])
    report = runtime.run()
    if report["status"] != "validation_passed_pending_review":
        raise ValueError({"task": topic, "report": report})
    gate = F.load(root / ".local-agents/local-unit.py", "readiness_unit_gate")
    identity = gate.verify_handoff(root, report, config=runtime.config)
    request = root / ".agent/offline-request.json"
    config = root / ".agent/offline-review-config.json"
    S.save(
        request,
        {
            "schema_version": 1,
            **identity,
            "review_id": "offline-" + topic,
            "execution_protocol": report["execution_protocol"],
        },
    )
    S.save(
        config,
        {
            **runtime.config,
            "reviewer_compact_report": True,
            "reviewer_evidence_state": True,
        },
    )
    inspected = TASKS.run(
        [
            sys.executable,
            "-B",
            S.KIT / "benchmarks/reviewer_capture_entry.py",
            "--runtime-dir",
            root / ".local-agents",
            "--capture-policy",
            F.POLICY_PATH,
            "--capture-policy-sha256",
            S.sha(root / F.POLICY_PATH),
            "--inspect-only",
            "--request",
            request,
            "--config",
            config,
            "--report",
            root / ".agent/reviewer-input.json",
        ],
        root,
    )
    private = TASKS.run(
        [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", row["private_tests"]], root
    )
    result = {
        "simulated_proposals": 1,
        "model_calls": 0,
        "coder_status": report["status"],
        "ledger": report["bounded_evidence"],
        "handoff_verified": True,
        "reviewer_input_inspection": inspected,
        "independent_checks": private,
        "reviewer_semantic_decision": "NOT_RUN",
        "Primary_acceptance": "NOT_A_LIVE_RESULT",
    }
    S.save(ARTIFACTS / "offline-chain-results" / (topic + ".json"), result)
    if inspected["exit_code"] or private["exit_code"]:
        raise ValueError("Offline final-chain control failed: " + topic)
    return result


def initial_context(row, label):
    saved = ARTIFACTS / "input-messages" / (label + ".json")
    if saved.exists():
        messages = S.read(saved)["messages"]
        return messages[0]["content"], C.UNIFIED.SPAN.D.INTERFACE.restore_literal(
            messages[1]["content"]
        )
    root = clone(row, ARTIFACTS / "input-inspection" / label)
    runtime, host = runtime_at(root, [])
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        runtime.host_validate()
        messages, binding = runtime.proposal_context()
        S.save(
            ARTIFACTS / "input-messages" / (label + ".json"),
            {"messages": messages, "binding": binding},
        )
        return messages[0]["content"], host.INTERFACE.restore_literal(
            messages[1]["content"]
        )
    finally:
        runtime.close()


def main():
    freeze = S.read(S.BATCH / "candidate-freeze.json")
    if any(S.sha(p) != digest for p, digest in freeze["pins"].items()):
        raise ValueError("Candidate drift")
    cells, tasks = S.read(CELLS), S.read(TASK_FREEZE)["tasks"]
    results = {"cells": {}, "pairs": {}, "offline_chains": {}}
    for name, row in cells.items():
        root = __import__("pathlib").Path(row["root"])
        if any(S.sha(root / p) != digest for p, digest in row["files"].items()):
            raise ValueError("Cell changed before inspection: " + name)
        if any(
            S.sha(root / p) != digest
            for p, digest in tasks[row["task"]]["inputs"].items()
        ):
            raise ValueError("Cell does not match frozen upstream-derived start")
        config = S.read(root / ".agent/config.json")
        expected_facts = sorted(
            p for p in tasks[row["task"]]["inputs"] if p.startswith(("src/", "tests/"))
        )
        if config["experimental_evidence_files"] != expected_facts:
            raise ValueError("Fact set differs from sealed public inputs")
        if any(
            (root / p).exists()
            for p in ("private", "reference.py", "test_independent.py")
        ):
            raise ValueError("Private material copied to Worker root")
        checked = TASKS.run(
            [
                sys.executable,
                "-B",
                S.KIT / "benchmarks/bounded_evidence_entry.py",
                "--runtime-dir",
                root / ".local-agents",
                "--capture-policy-sha256",
                row["capture_policy_sha256"],
                "--packet",
                root / ".agent/packet.json",
                "--config",
                root / ".agent/config.json",
                "--preflight-only",
            ],
            root,
        )
        results["cells"][name] = checked
        if checked["exit_code"]:
            S.save(ARTIFACTS / "readiness-failure.json", results)
            raise ValueError("Installed preflight failed: " + name)
    for topic in TASKS.TASKS:
        initial = {
            arm: initial_context(cells[topic + "-" + arm + "1"], topic + "-" + arm)
            for arm in ("A", "B")
        }

        # Absolute sandbox paths in raw check diagnostics can differ; preserve originals.
        def normalize(value, arm, topic=topic):
            if isinstance(value, dict):
                return {k: normalize(v, arm) for k, v in value.items()}
            if isinstance(value, list):
                return [normalize(v, arm) for v in value]
            if isinstance(value, str):
                path = str(
                    ARTIFACTS / "input-inspection" / (topic + "-" + arm) / "isolated"
                )
                value = value.replace(path, "<ROOT>").replace(
                    "bounded-20261018-" + topic + "-" + arm + "1", "<RUN>"
                )
                value = re.sub(r"(?<= object at )0x[0-9A-Fa-f]+", "<ADDRESS>", value)
                return re.sub(
                    r"(?m)^(\d+ (?:failed|passed).*?) in \d+(?:\.\d+)?s$",
                    r"\1 in <ELAPSED>s",
                    value,
                )
            return value

        a = normalize(initial["A"][1], "A")
        b = normalize(initial["B"][1], "B")
        packet_a = S.read(
            __import__("pathlib").Path(cells[topic + "-A1"]["root"])
            / ".agent/packet.json"
        )
        packets_match = True
        config_match = True
        for arm in ("A", "B"):
            for repeat in (1, 2):
                root = __import__("pathlib").Path(
                    cells[f"{topic}-{arm}{repeat}"]["root"]
                )
                packet = S.read(root / ".agent/packet.json")
                packets_match &= {k: v for k, v in packet.items() if k != "run_id"} == {
                    k: v for k, v in packet_a.items() if k != "run_id"
                }
                other = S.read(root / ".agent/config.json")
                base = S.read(
                    __import__("pathlib").Path(cells[topic + "-A1"]["root"])
                    / ".agent/config.json"
                )
                config_match &= {
                    k: v
                    for k, v in other.items()
                    if k != "experimental_bounded_evidence"
                } == {
                    k: v
                    for k, v in base.items()
                    if k != "experimental_bounded_evidence"
                }
        results["pairs"][topic] = {
            "initial_facts_equal_excluding_run_paths_and_terminal_elapsed": a == b,
            "system_delta_only_evidence_interface": initial["B"][0]
            == initial["A"][0] + "\n" + C.B_PROMPT,
            "packet_delta_only_run_id": packets_match,
            "config_delta_only_arm": config_match,
        }
        S.save(
            ARTIFACTS / "pair-controls-v3" / (topic + ".json"), results["pairs"][topic]
        )
        if not all(results["pairs"][topic].values()):
            raise ValueError("Paired input mismatch: " + topic)
        results["offline_chains"][topic] = run_control(topic, cells[topic + "-A1"])
    S.save(
        ARTIFACTS / "readiness.json",
        {
            "status": "OFFLINE_READY_FOR_SINGLE_LIVE_APPROVAL",
            "model_calls": 0,
            "results": results,
        },
    )


if __name__ == "__main__":
    main()
