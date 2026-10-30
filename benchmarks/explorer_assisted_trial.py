"""Match raw facts against an existing Explorer's verified, untrusted causal notes."""

import argparse
import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import explorer_trace_trial as E
import mapping_recovery_trial as M
import normal_task_trial as N
import reasoning_wire_candidate as W

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/explorer-assisted-repair-20261020-1"
)
ORDER = ["repair-A-1", "repair-B-1", "repair-B-2", "repair-A-2"]


def command(root, mode="unit", replay=None):
    return M.command(root, mode, replay) + [
        "--failure-source",
        "--repair-start",
        "--reviewer-forward-reasoning",
    ]


def prepare():
    controls = list(ET.parse(BATCH / "offline-controls.xml").iter("testcase"))
    if len(controls) != 8 or any(
        c.find(tag) is not None
        for c in controls
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All8 guidance/transport/stop controls required")
    proof = S.read(E.BATCH / "decision.json")
    report_path = E.BATCH / "isolated/.agent/explorer.json"
    if proof["status"] != "PASS_CAUSAL_TRACE_SCOPED" or proof["report_sha256"] != S.sha(
        report_path
    ):
        raise ValueError("Verified Explorer report required")
    report = S.read(report_path)
    old = S.read(M.BATCH / "cells.json")["for-1"]
    old_root = Path(old["root"])
    for path, digest in report["observed_hashes"].items():
        if S.sha(old_root / path) != digest:
            raise ValueError("Explorer note source no longer applicable")
    rows = {}
    patches = []
    for cell in ORDER:
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = old_root / name
            if S.sha(source) != digest:
                raise ValueError("Frozen no-op starter changed")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        patches.append(W.patch_client(root / ".local-agents/worker-runtime.py"))
        identity = {
            k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(root / ".agent/packet.json")
        packet.update(identity)
        packet["implementation_guidance"] = []
        if "-B-" in cell:
            packet["implementation_guidance"] = [
                "Untrusted local Explorer research, advisory only, not new requirements. Report SHA256 "
                + S.sha(report_path),
                *report["findings"],
            ]
        policy = S.read(root / "acceptance/capture-policy.json")
        policy["identity"] = identity
        config = S.read(root / ".agent/config.json")
        for path, value in (
            (root / ".agent/packet.json", packet),
            (root / "acceptance/capture-policy.json", policy),
        ):
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        config["experimental_capture_policy_sha256"] = S.sha(
            root / "acceptance/capture-policy.json"
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        if cell.endswith("-1"):
            control = BATCH / "offline" / cell / "isolated"
            shutil.copytree(root, control)
            replay = control.parent / "replay.json"
            reference = T.extract(
                M.E.BATCH / "reference-checks/mapping/src/product/code.py", "mapping"
            )
            S.save(replay, [{"replacement": reference}])
            result = T.run(command(control, "unit", replay), control, timeout=180)
            S.save(control.parent / "process.json", result)
            if result["exit_code"]:
                raise ValueError("No-network complete handoff failed")
        rows[cell] = {
            **old,
            "root": str(root),
            "identity": identity,
            "files": {p: S.sha(root / p) for p in old["files"]},
        }
    S.save(BATCH / "client-patches.json", patches)
    S.save(BATCH / "cells.json", rows)
    paths = [
        S.KIT / "benchmarks" / name
        for name in (
            "consolidated_harness.py",
            "consolidated_entry.py",
            "reviewer_capture_entry.py",
            "reviewer_contract_first.py",
            "reasoning_wire_candidate.py",
            "initial_repair_rules.py",
            "failure_source_rules.py",
            "failed_test_source.py",
            "static_focus_rules.py",
            "repair_phase_rules.py",
            "literal_check_feedback.py",
            "normal_task_trial.py",
            "capture_fixture_support.py",
            "capture_validation_facts.py",
            "reviewer_canonical_capture.py",
            "explorer_assisted_trial.py",
        )
    ]
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "pins": {
                str(p): S.sha(p)
                for p in [
                    *paths,
                    BATCH / "cells.json",
                    BATCH / "offline-controls.xml",
                    report_path,
                ]
            },
            "A": "Current exact failing source, full failed-test evidence and repair-start header",
            "B": "A plus exact local Explorer causal findings in existing advisory implementation_guidance; no Primary algorithm or code supplied",
            "budget": {
                "requests": 12,
                "edits": 3,
                "post_edit_checks": 3,
                "initial_checks": 1,
                "seconds": 900,
            },
            "Reviewer": "Fresh Muse after actual checks, explicit existing medium/low reasoning forwarding, original4096 output/16requests/4errors/600sec; no change to gate or resampling",
            "gate": "B2/2 actual complete independent chains and source-correct, greater completion than A. Still only exposed E-assisted semantic repair, not Coder-only, R4, general capability or Coordinator release.",
            "continue_rule": "Complete4 ordinary quality outcomes; infra/safety/drift/deadline/weekly50 stop. No retry identical Reviewer until PASS. Incomplete Reviewer prevents acceptance.",
            "Primary": "Verified existing Explorer claims and source binding once; packet copying/launch/independent final inspection only. No semantic repair guidance or implementation. Actual cloud cost/time unknown.",
        },
    )
    print("Four E-assisted comparison cells frozen, authentic offline handoffs passed")


def run(cell, used, observed):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    N.run(
        cell,
        used,
        observed,
        batch=BATCH,
        order=ORDER,
        build_command=command,
        usage_limit=50,
        batch_seconds=10800,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare"])
    p.parse_args()
    prepare()
