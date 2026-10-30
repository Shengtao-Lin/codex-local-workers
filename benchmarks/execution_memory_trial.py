"""Fixed paired diagnostic of host-observed short-term execution continuity."""

import argparse
import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import normal_task_trial as N
import supervised_feedback_trial as F
import supervised_repair_phase as P

BATCH = S.KIT / "benchmarks/work/harness-convergence/execution-memory-20261020-1"
ORDER = [
    "json-A-1",
    "json-B-1",
    "ids-B-1",
    "ids-A-1",
    "raw-A-1",
    "raw-B-1",
    "json-B-2",
    "json-A-2",
    "ids-A-2",
    "ids-B-2",
    "raw-B-2",
    "raw-A-2",
]


def command(root, mode="coder", replay=None):
    argv = P.command(root, mode, replay) + ["--static-focus"]
    if "-B-" in root.parent.name:
        argv.append("--execution-memory")
    if mode == "coder":
        argv[argv.index("--report") + 1] = str(root / ".agent/unit-report.json")
        argv += ["--summary", str(root / ".agent/unit-summary.json")]
    return argv


def prepare():
    controls = list(ET.parse(BATCH / "offline-controls-v3.xml").iter("testcase"))
    if len(controls) != 17 or any(
        c.find(tag) is not None
        for c in controls
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All17 offline controls required")
    rows = {}
    for cell in ORDER:
        topic, _arm, repeat = cell.split("-")
        old = S.read(F.OLD / "cells.json")[topic + "-" + repeat]
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if name == old["target"]:
                source = F.OLD / "templates" / topic / name
            if S.sha(source) != digest:
                raise ValueError("Frozen upstream mismatch: " + name)
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        identity = {
            k: "execution-memory-20261020-1-" + cell
            for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(root / ".agent/packet.json")
        packet.update(identity)
        policy = S.read(root / "acceptance/capture-policy.json")
        policy["identity"] = identity
        config = S.read(root / ".agent/config.json")
        for path, value in (
            (root / ".agent/packet.json", packet),
            (root / "acceptance/capture-policy.json", policy),
        ):
            path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        config["experimental_capture_policy_sha256"] = S.sha(
            root / "acceptance/capture-policy.json"
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        rows[cell] = {
            **old,
            "root": str(root),
            "identity": identity,
            "files": {p: S.sha(root / p) for p in old["files"]},
        }
    S.save(BATCH / "cells.json", rows)
    for topic in ("json", "ids", "raw"):
        a, b = [Path(rows[f"{topic}-{arm}-1"]["root"]) for arm in ("A", "B")]
        for name in rows[f"{topic}-A-1"]["files"]:
            if name not in {
                ".agent/packet.json",
                ".agent/config.json",
                "acceptance/capture-policy.json",
            } and S.sha(a / name) != S.sha(b / name):
                raise ValueError("Arm input mismatch")
        for name, omit in (
            (".agent/packet.json", {"task_id", "unit_id", "run_id"}),
            (".agent/config.json", {"experimental_capture_policy_sha256"}),
            ("acceptance/capture-policy.json", {"identity"}),
        ):
            values = [
                {k: v for k, v in S.read(p / name).items() if k not in omit}
                for p in (a, b)
            ]
            if values[0] != values[1]:
                raise ValueError("Arm normalized input mismatch: " + name)
        for arm in ("A", "B"):
            source = BATCH / "cells" / f"{topic}-{arm}-1" / "isolated"
            root = BATCH / "offline" / f"{topic}-{arm}-1" / "isolated"
            shutil.copytree(source, root)
            symbol = S.read(root / ".agent/config.json")["coder_single_function"][
                "symbol"
            ]
            reference = T.extract(
                F.OLD / "reference-checks" / topic / rows[f"{topic}-A-1"]["target"],
                symbol,
            )
            replay = root.parent / "replay.json"
            S.save(replay, [{"replacement": reference}])
            result = T.run(command(root, "unit", replay), root, timeout=180)
            S.save(root.parent / "process.json", result)
            if result["exit_code"]:
                raise ValueError("No-model whole-chain control failed")
    modules = [
        "consolidated_harness.py",
        "consolidated_entry.py",
        "execution_memory.py",
        "continuity_rules.py",
        "static_focus_rules.py",
        "repair_phase_rules.py",
        "bounded_source_rules.py",
        "literal_check_feedback.py",
        "function_proposal_rules.py",
        "preserved_import_guard.py",
        "harness_protocol.py",
        "normal_task_trial.py",
        "bounded_evidence_tasks.py",
        "capture_fixture_support.py",
        "capture_validation_facts.py",
        "reviewer_capture_entry.py",
        "reviewer_canonical_capture.py",
        "supervised_repair_phase.py",
        "supervised_bounded_trial.py",
        "function_repeat_trial.py",
        "execution_memory_trial.py",
    ]
    pins = {
        str(S.KIT / "benchmarks" / p): S.sha(S.KIT / "benchmarks" / p) for p in modules
    }
    for p in (BATCH / "cells.json", BATCH / "offline-controls-v3.xml"):
        pins[str(p)] = S.sha(p)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 12,
            "pins": pins,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "A": "Current static-focused bounded-source candidate",
            "B": "A plus last three host-observed attempt transitions (source hashes, actual diff excerpt, check status changes, noops/recoveries). No extra evidence, reads, requirements or hints.",
            "budget": {
                "requests": 12,
                "edits": 3,
                "initial_checks": 1,
                "post_edit_checks": 3,
                "seconds": 900,
                "output_tokens": 4096,
            },
            "tasks": "Three exposed task families, two repetitions per arm; exact upstream starting sources and same checks. No holdout credit.",
            "continue_rule": "Complete all12 ordinary outcomes; stop infrastructure/safety/protected drift, deadline or used50. No rerun, no replacement, no hidden-test repair feedback.",
            "adoption": "Diagnostic support only if B has more independently checked completions, no worse combined noops and no family regression versus A. If no B continuation occurs, memory effect is unexercised. No product qualification; fresh Reviewer and Primary acceptance NOT_RUN by design.",
            "primary": "Once-only host implementation and frozen task preparation; per-cell only launch, observe and independent diff/check inspection. No semantic hints or code takeover. Cloud token/active-time unknown.",
        },
    )
    print(
        "12 matched Coder-only cells frozen; six no-network complete-chain replays passed"
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
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare"])
    parser.parse_args()
    prepare()
