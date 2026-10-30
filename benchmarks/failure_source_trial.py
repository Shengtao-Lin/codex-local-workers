"""Paired replay of real failed drafts, adding only approved failing-test source."""

import argparse
import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import mapping_recovery_trial as M
import normal_task_trial as N

BATCH = S.KIT / "benchmarks/work/harness-convergence/failure-source-20261020-1"
ORDER = [
    "for-A-1",
    "for-B-1",
    "all-B-1",
    "all-A-1",
    "all-A-2",
    "all-B-2",
    "for-B-2",
    "for-A-2",
]


def command(root, mode="coder", replay=None):
    argv = M.command(root, mode, replay)
    if "-B-" in root.parent.name:
        argv.append("--failure-source")
    return argv


def prepare(
    batch=BATCH,
    build_command=command,
    extra_pins=(),
    descriptions=None,
    conditional=None,
):
    BATCH = Path(batch)
    tests = list(ET.parse(BATCH / "offline-controls.xml").iter("testcase"))
    if len(tests) < 25 or any(
        t.find(tag) is not None
        for t in tests
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All new boundary and original entry controls required")
    if S.read(M.BATCH / "decision.json")["executed"] != 4:
        raise ValueError("Previous fixed recovery diagnostic incomplete")
    old_rows = S.read(M.BATCH / "cells.json")
    rows = {}
    for cell in ORDER:
        kind, _arm, repeat = cell.split("-")
        old = old_rows[kind + "-" + repeat]
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Old no-op starter drifted")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        identity = {
            k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(root / ".agent/packet.json")
        packet.update(identity)
        policy = S.read(root / "acceptance/capture-policy.json")
        policy["identity"] = identity
        config = S.read(root / ".agent/config.json")
        for p, v in (
            (root / ".agent/packet.json", packet),
            (root / "acceptance/capture-policy.json", policy),
        ):
            p.write_text(json.dumps(v, indent=2), encoding="utf-8")
        config["experimental_capture_policy_sha256"] = S.sha(
            root / "acceptance/capture-policy.json"
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        if repeat == "1":
            offline = BATCH / "offline" / cell / "isolated"
            shutil.copytree(root, offline)
            reference = T.extract(
                M.E.BATCH / "reference-checks/mapping/src/product/code.py", "mapping"
            )
            replay = offline.parent / "replay.json"
            S.save(replay, [{"replacement": reference}])
            result = T.run(build_command(offline, "unit", replay), offline, timeout=180)
            S.save(offline.parent / "process.json", result)
            if result["exit_code"]:
                raise ValueError("No-model whole-chain failed")
        rows[cell] = {
            **old,
            "root": str(root),
            "identity": identity,
            "files": {p: S.sha(root / p) for p in old["files"]},
        }
    S.save(BATCH / "cells.json", rows)
    paths = [
        S.KIT / "benchmarks" / name
        for name in (
            "consolidated_harness.py",
            "consolidated_entry.py",
            "literal_check_feedback.py",
            "static_focus_rules.py",
            "repair_phase_rules.py",
            "failure_source_rules.py",
            "failed_test_source.py",
            "failure_source_trial.py",
            "mapping_recovery_trial.py",
            "normal_task_trial.py",
            "bounded_source_rules.py",
            "capture_fixture_support.py",
            "capture_validation_facts.py",
            "reviewer_capture_entry.py",
            "reviewer_canonical_capture.py",
        )
    ]
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 8,
            "pins": {
                str(p): S.sha(p)
                for p in [
                    *paths,
                    *map(Path, extra_pins),
                    BATCH / "cells.json",
                    BATCH / "offline-controls.xml",
                ]
            },
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "A": "Current no-memory static-focused loop, original implement/repair phase unchanged",
            "B": "A plus host-read version-bound excerpt around actual failing focused-test line. Same approved facts; no new source permission, task-specific interpretation or gold/reference implementation.",
            "description_override": descriptions,
            "conditional": conditional,
            "budget": {
                "requests": 12,
                "edits": 3,
                "initial_checks": 1,
                "post_edit_checks": 3,
                "seconds": 900,
                "output_tokens": 4096,
            },
            "gate": "Narrow support only if B4/4 independently checked actual edits and greater completion than A, no safety or source-contract defect. Reviewer/full-chain acceptance NOT_RUN_DIAGNOSTIC. Not model-general or fresh-task qualification.",
            "continue_rule": "Complete8 ordinary outcomes; infra/safety/input drift/deadline/weekly50 stop. No resampling, hidden feedback or task-specific fix. Prior0/4 retained.",
            "primary": "Once-only host evidence adapter and fixed comparison preparation; during live no semantic coaching/takeover. Token/time savings not measured.",
        },
    )
    print(
        "Eight failing-source paired cells frozen; four no-model complete-chain replays passed"
    )


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
