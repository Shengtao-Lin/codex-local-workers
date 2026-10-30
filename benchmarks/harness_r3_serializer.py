"""Authorized serializer-only R3 candidate. Old batches remain immutable."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_r3_origin_fixed as F

B, P, R = F.B, F.P, F.R
PRIOR = F.BATCH
BATCH = B.KIT / "benchmarks/work/harness-convergence/r3-serializer-20261016-1"


def bind():
    F.BATCH = BATCH
    R.BATCH = BATCH


def checkpoint(used):
    assert 0 <= used < 30
    BATCH.mkdir(exist_ok=False)
    files = {Path(p) for p in B.read(PRIOR / "baseline.json")}
    files.update(B.files(PRIOR))
    listing = B.command(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    assert listing["exit_code"] == 0
    files.update(B.KIT / p for p in listing["stdout"].split("\0") if p)
    baseline = {}
    for index, path in enumerate(sorted(files)):
        if path.is_file():
            baseline[str(path)] = B.sha(path)
        if index and index % 25000 == 0:
            print(f"Checkpoint {index}", flush=True)
    B.save(BATCH / "baseline.json", baseline)
    for relative in (
        ".local-agents/worker-runtime.py",
        "docs/local-model-harness-convergence-plan.md",
    ):
        destination = BATCH / "checkpoint" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(B.KIT / relative, destination)
    B.save(
        BATCH / "environment.json",
        {
            "weekly_used": used,
            "ceiling": 30,
            "git_head": B.command(["git", "rev-parse", "HEAD"]),
            "git_status": B.command(["git", "status", "--short"]),
            "models": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
        },
    )
    registration = B.read(PRIOR / "registration.json")
    registration.update(
        usage_start=used,
        prior_batch=str(PRIOR),
        authorized_goal="Autonomous phased progression through R4, stop at weekly used 30% or material user decision",
        experiment_change="Only compact serializer preserves explicitly present execution_protocol and worker_assessment; no inference or receiver change",
        r4_live_authorized=True,
        no_live_candidate_changes=True,
    )
    B.save(BATCH / "registration.json", registration)


def prepare():
    prior_freeze = B.read(PRIOR / "live-freeze-approved.json")
    R.assert_files(
        B.KIT,
        prior_freeze["candidate_and_driver"],
        except_paths=(".local-agents/worker-runtime.py",),
    )
    installer = R.load(
        B.KIT / "scripts/install_local_agents.py", "serializer_installer"
    )
    target = BATCH / "install-target"
    target.mkdir(exist_ok=False)
    source = BATCH / "install-source"
    source.mkdir(exist_ok=False)
    shutil.copyfile(B.KIT / "AGENTS.md", source / "AGENTS.md")
    shutil.copytree(
        B.KIT / ".local-agents",
        source / ".local-agents",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"),
    )
    preview = installer.install(source, target)
    installed = installer.install(source, target, apply=True)
    again = installer.install(source, target)
    assert not again["copy"] and not again["conflict"]
    assert not (target / ".local-agents/config.json").exists()
    B.save(
        BATCH / "installation.json",
        {
            "preview": preview,
            "installed": installed,
            "idempotent": again,
            "default_enabled": False,
        },
    )
    old_cases = B.read(PRIOR / "prepared-cases.json")
    cases = {}
    for name in P.ORDER:
        task, arm, _ = name.split("-")
        old_root = PRIOR / "cases" / name / "isolated"
        source = (
            B.KIT
            / "benchmarks/work/harness-convergence/r2-rendering-20261014-1/cases/json-1/isolated"
            if task == "repair"
            else old_root
        )
        F.O.require_origin(source, F.origins()[task])
        root = BATCH / "cases" / name / "isolated"
        P.copy_inputs(source, root)
        R.assert_files(
            old_root,
            {
                p: h
                for p, h in old_cases[name].items()
                if p.startswith((".local-agents/", ".agent/"))
            },
        )
        runtime = (
            target / ".local-agents"
            if arm == "candidate"
            else old_root / ".local-agents"
        )
        shutil.copytree(
            runtime,
            root / ".local-agents",
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "*.pyc", "config.json"
            ),
        )
        packet = B.read(old_root / ".agent/packet.json")
        packet["run_id"] = "r3-serializer-20261016-" + name
        B.save(root / ".agent/packet.json", packet)
        shutil.copyfile(old_root / ".agent/config.json", root / ".agent/config.json")
        F.O.require_origin(root, F.origins()[task])
        cases[name] = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
    B.save(BATCH / "prepared-cases.json", cases)
    B.save(BATCH / "origin-anchors.json", B.read(PRIOR / "origin-anchors.json"))
    bind()
    F.preflight()


def freeze():
    for name in ("serializer-controls-v3.xml", "regression.xml", "interface-regression.xml"):
        tree = ET.parse(BATCH / name)
        assert tree.findall(".//testcase") and not any(
            tree.findall(".//" + k) for k in ("failure", "error", "skipped")
        )
    assert B.read(BATCH / "initial-controls-passed.json")["all_12"]
    old = B.read(PRIOR / "live-freeze-approved.json")
    R.assert_files(
        B.KIT,
        old["candidate_and_driver"],
        except_paths=(".local-agents/worker-runtime.py",),
    )
    for name, row in B.read(P.BATCH / "holdouts-freeze.json")["cases"].items():
        R.assert_files(P.BATCH / "holdouts-v2" / name, row["files"])
    paths = [
        ".local-agents/worker-runtime.py",
        "benchmarks/harness_r3_serializer.py",
        "tests/test_host_cli_protocol.py",
    ]
    candidate = {**old["candidate_and_driver"], **{p: B.sha(B.KIT / p) for p in paths}}
    B.save(
        BATCH / "live-freeze-approved.json",
        {
            **old,
            "candidate_and_driver": candidate,
            "registration": B.sha(BATCH / "registration.json"),
            "prepared_cases": B.sha(BATCH / "prepared-cases.json"),
            "origin_anchors": B.sha(BATCH / "origin-anchors.json"),
            "initial_controls": B.sha(BATCH / "initial-controls-passed.json"),
            "authorized_serializer_repair": True,
        },
    )
    print("Serializer candidate frozen", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "prepare", "freeze", "run"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "run":
        bind()
        F.run(args.case, args.used)
    elif args.action == "checkpoint":
        checkpoint(args.used)
    else:
        globals()[args.action]()
