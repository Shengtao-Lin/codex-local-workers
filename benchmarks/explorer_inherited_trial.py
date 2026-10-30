"""Two exposed zero-edit failures; fresh local diagnosis, automatic child handoff."""

import json
import math
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import explorer_recovery_controller as C
import explorer_trace_trial as E
import mapping_recovery_trial as M
import reasoning_wire_candidate as W

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/explorer-inherited-recovery-20261020-1"
)
ORDER = ["for-1", "all-1"]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def command(root, replay=None):
    argv = M.command(root, "unit", replay) + [
        "--failure-source",
        "--repair-start",
        "--reviewer-forward-reasoning",
    ]
    argv[argv.index("--packet") + 1] = str(root / ".agent/child-packet.json")
    return argv


def bind_child(root, parent, report):
    feedback = C.research_feedback(
        report, root, {"src/product/code.py", "tests/test_contract.py"}
    )
    credits = C.remaining_credits(parent)
    old = parent["identity"]
    child = {
        "schema_version": 2,
        "task_id": old["task_id"],
        "unit_id": old["unit_id"],
        "run_id": old["run_id"] + "-research",
        "packet_revision": 2,
        "parent_run_id": old["run_id"],
        "preserve_contract": True,
        "review_feedback": feedback,
    }
    S.save(root / ".agent/child-packet.json", child)
    policy_path = root / "acceptance/capture-policy.json"
    config_path = root / ".agent/config.json"
    policy, config = S.read(policy_path), S.read(config_path)
    before = {"policy": policy, "config": config}
    # Only generated per-run identity and experiment credits change, not contracts/tests.
    S.save(root / ".agent/pre-recovery-controls.json", before)
    policy["identity"] = {k: child[k] for k in ("task_id", "unit_id", "run_id")}
    write(policy_path, policy)
    config["experimental_capture_policy_sha256"] = S.sha(policy_path)
    config["experimental_recovery_credits"] = credits
    write(config_path, config)
    S.save(
        root / ".agent/generated-recovery-controls.json",
        {
            "identity": policy["identity"],
            "credits": credits,
            "config_sha256": S.sha(config_path),
            "policy_sha256": S.sha(policy_path),
        },
    )
    return child


def prepare():
    for name, expected in [("offline-controls-v2.xml", 29), ("route-controls.xml", 6)]:
        cases = list(ET.parse(BATCH / name).iter("testcase"))
        assert len(cases) == expected and not any(
            c.find(tag) is not None
            for c in cases
            for tag in ("failure", "error", "skipped")
        )
    rows = {}
    for cell in ORDER:
        old = S.read(M.BATCH / "cells.json")[cell]
        origin = Path(old["root"])
        parent = S.read(origin / ".agent/unit-report.json")
        C.remaining_credits(parent)
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            assert S.sha(origin / name) == digest
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin / name, dest)
        identity = old["identity"]
        archive = (
            Path(".agent/tasks") / identity["task_id"] / "runs" / identity["run_id"]
        )
        shutil.copytree(origin / archive, root / archive)
        W.patch_client(root / ".local-agents/worker-runtime.py")
        research = root.parent / "research"
        for name in old["files"]:
            if name == ".agent/packet.json" or name.startswith("acceptance/"):
                continue
            dest = research / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, dest)
        config = S.read(research / ".agent/config.json")
        config.update(
            explorer_mode="investigate",
            explorer_answer_protocol=False,
            explorer_required_citation_paths=[
                "src/product/code.py",
                "tests/test_contract.py",
            ],
        )
        write(research / ".agent/config.json", config)
        before = {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
        }
        offline = BATCH / "offline" / cell / "isolated"
        shutil.copytree(root, offline)
        # Synthetic note/reference only in no-network preparation, never live input.
        bind_child(
            offline,
            parent,
            {
                "status": "success",
                "findings": ["Offline transport control only."],
                "observed_hashes": {
                    p: S.sha(offline / p)
                    for p in ("src/product/code.py", "tests/test_contract.py")
                },
            },
        )
        replay = offline.parent / "replay.json"
        S.save(
            replay,
            [
                {
                    "replacement": T.extract(
                        M.E.BATCH / "reference-checks/mapping/src/product/code.py",
                        "mapping",
                    )
                }
            ],
        )
        proof = T.run(command(offline, replay), offline, timeout=180)
        S.save(offline.parent / "process.json", proof)
        assert proof["exit_code"] == 0, proof
        rows[cell] = {
            "root": str(root),
            "research": str(research),
            "parent": parent,
            "identity": identity,
            "files": before,
            "research_files": {
                p.relative_to(research).as_posix(): S.sha(p)
                for p in research.rglob("*")
                if p.is_file()
            },
        }
    S.save(BATCH / "cells.json", rows)
    names = [
        "consolidated_harness.py",
        "consolidated_entry.py",
        "explorer_recovery_controller.py",
        "explorer_inherited_trial.py",
        "reviewer_capture_entry.py",
        "reviewer_contract_first.py",
        "failed_test_source.py",
        "failure_source_rules.py",
        "initial_repair_rules.py",
        "static_focus_rules.py",
        "repair_phase_rules.py",
        "literal_check_feedback.py",
    ]
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 2,
            "weekly_stop": 50,
            "batch_seconds": 6000,
            "pins": {
                str(S.KIT / "benchmarks" / n): S.sha(S.KIT / "benchmarks" / n)
                for n in names
            },
            "exposure": "Same exposed mapping contract, two different frozen bad implementations; not new tasks/holdout.",
            "candidate": "One fresh investigate Explorer per frozen zero-edit parent, hash-bound untrusted notes to inherited Coder, current checks then fresh unchanged Reviewer. No intermediate Primary semantic guidance.",
            "budget": "Parent+child Coder combined12 requests/3 edits/3 postchecks/12 format preparations/2 protocol recoveries/900 execution seconds; separate fresh initial check in each invocation (max2), supplemental checks max16 each. Explorer16 turns/600s, unchanged Reviewer16 requests/600s; single residency, per-cell2520s outer bound.",
            "gate": "Both fresh causal research and child full checks+Reviewer+Primary acceptance; any ordinary failure HOLD but complete second diagnostic cell. No Reviewer semantic rework autoauthorization.",
            "stop": "Unsafe edits/input drift, infra/transport, weekly50 or fixed deadline. No replacement runs.",
            "cost": "Primary prepared experiment/controller; runtime diagnosis and handoff not manually curated. Parent costs reported separately and combined, no savings claim.",
        },
    )
    print(
        "Two child no-network handoffs passed; fixed fresh-research recovery registered"
    )


def run(cell, used, observed):
    assert 0 <= used < 50 and 0 <= time.time() - observed <= 120
    reg, rows = S.read(BATCH / "registration.json"), S.read(BATCH / "cells.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    for previous in ORDER[: ORDER.index(cell)]:
        assert not S.read(BATCH / "results" / previous / "result.json")["stop_batch"]
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    assert time.time() - S.read(clock)["epoch"] < 6000
    row = rows[cell]
    root, research = Path(row["root"]), Path(row["research"])
    assert all(S.sha(root / p) == h for p, h in row["files"].items())
    assert all(S.sha(research / p) == h for p, h in row["research_files"].items())
    S.save(
        BATCH / "results" / cell / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    started = time.monotonic()
    process = T.run(
        [
            S.PYTHON,
            "-B",
            research / ".local-agents/local-explore.py",
            "--task",
            E.QUESTION,
            "--task-id",
            BATCH.name + "-" + cell,
            "--config",
            research / ".agent/config.json",
            "--report",
            research / ".agent/explorer.json",
            "--full-report",
        ],
        research,
        timeout=720,
    )
    S.save(BATCH / "results" / cell / "explorer-process.json", process)
    assert all(S.sha(research / p) == h for p, h in row["research_files"].items())
    report = S.read(research / ".agent/explorer.json")
    child = bind_child(root, row["parent"], report)
    protected = {p: S.sha(root / p) for p in row["files"] if p != "src/product/code.py"}
    process = T.run(
        command(root),
        root,
        timeout=min(1800, math.floor(2520 - (time.monotonic() - started))),
    )
    coder = S.read(root / ".agent/unit-report.json")
    summary = S.read(root / ".agent/unit-summary.json")
    drift = [p for p, h in protected.items() if S.sha(root / p) != h]
    result = {
        "process": process,
        "identity": child,
        "coder_status": coder["status"],
        "reviewer_decision": summary["reviewer_decision"],
        "seconds": time.monotonic() - started,
        "protected_drift": drift,
        "stop_batch": bool(drift or coder.get("infra_failure")),
        "primary_final_acceptance": "PENDING",
        "fresh_explorer": True,
        "parent_coder": row["parent"]["consolidated_harness"],
        "child_coder": coder["consolidated_harness"],
    }
    S.save(BATCH / "results" / cell / "result.json", result)
    print(cell, result["coder_status"], result["reviewer_decision"], "Primary pending")
