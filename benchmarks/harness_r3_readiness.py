"""Separate mechanical Reviewer-readiness stage, with unchanged Coder candidate."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_r3_serializer as S

B, P, R, F = S.B, S.P, S.R, S.F
PRIOR = S.BATCH
BATCH = B.KIT / "benchmarks/work/harness-convergence/r3-readiness-20261016-1"


def checkpoint(used):
    assert 0 <= used < 30
    BATCH.mkdir(exist_ok=False)
    paths = {Path(p) for p in B.read(PRIOR / "baseline.json")}
    paths.update(B.files(PRIOR))
    listing = B.command(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    assert listing["exit_code"] == 0
    paths.update(B.KIT / p for p in listing["stdout"].split("\0") if p)
    baseline = {str(p): B.sha(p) for p in sorted(paths) if p.is_file()}
    B.save(BATCH / "baseline.json", baseline)
    for name in (
        ".local-agents/reviewer-runtime.py",
        "docs/local-model-harness-convergence-plan.md",
    ):
        destination = BATCH / "checkpoint" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(B.KIT / name, destination)
    registration = B.read(PRIOR / "registration.json")
    registration.update(
        usage_start=used,
        prior_batch=str(PRIOR),
        experiment_change="Only Reviewer report-readiness equals existing full displayed coverage; add Primary implementation_ref to presence in both arms. No prompt/schema/model/budget change.",
        qualification_audit="Every pass requires semantically relevant bound implementation refs independently checked by Primary before acceptance",
        baseline="Original R0 runtime plus same caps, with identical declarative implementation_ref in both arms",
        stage_authority="2026-10-16 autonomous optimization through R4, fixed standards and explicit stage registration",
    )
    B.save(BATCH / "registration.json", registration)
    B.save(
        BATCH / "environment.json",
        {
            "weekly_used": used,
            "ceiling": 30,
            "head": B.command(["git", "rev-parse", "HEAD"]),
            "status": B.command(["git", "status", "--short"]),
            "models": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
        },
    )
    print("Readiness stage registered and baseline saved", flush=True)


def prepare():
    old = B.read(PRIOR / "live-freeze-approved.json")
    R.assert_files(
        B.KIT,
        old["candidate_and_driver"],
        except_paths=(".local-agents/reviewer-runtime.py",),
    )
    installer = R.load(B.KIT / "scripts/install_local_agents.py", "readiness_installer")
    source, target = BATCH / "install-source", BATCH / "install-target"
    source.mkdir()
    target.mkdir()
    shutil.copyfile(B.KIT / "AGENTS.md", source / "AGENTS.md")
    shutil.copytree(
        B.KIT / ".local-agents",
        source / ".local-agents",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"),
    )
    installed = installer.install(source, target, apply=True)
    again = installer.install(source, target)
    assert not again["copy"] and not again["conflict"]
    assert not (target / ".local-agents/config.json").exists()
    B.save(
        BATCH / "installation.json",
        {"installed": installed, "idempotent": again, "default_enabled": False},
    )
    cases = {}
    for name in P.ORDER:
        task, arm, _ = name.split("-")
        old_root = PRIOR / "cases" / name / "isolated"
        input_source = (
            B.KIT
            / "benchmarks/work/harness-convergence/r2-rendering-20261014-1/cases/json-1/isolated"
            if task == "repair"
            else F.PREVIOUS / "cases/presence-candidate-1/isolated"
        )
        F.O.require_origin(input_source, F.origins()[task])
        root = BATCH / "cases" / name / "isolated"
        P.copy_inputs(input_source, root)
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
        config = B.read(old_root / ".agent/config.json")
        packet["run_id"] = "r3-readiness-20261016-" + name
        binding = {k: config["coder_single_function"][k] for k in ("path", "symbol")}
        for behavior in packet["required_behavior"]:
            if "implementation_ref" in behavior:
                assert behavior["implementation_ref"] == binding
            behavior["implementation_ref"] = binding
        B.save(root / ".agent/packet.json", packet)
        B.save(root / ".agent/config.json", config)
        F.O.require_origin(root, F.origins()[task])
        cases[name] = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
    B.save(BATCH / "prepared-cases.json", cases)
    B.save(BATCH / "origin-anchors.json", B.read(PRIOR / "origin-anchors.json"))
    F.BATCH = BATCH
    F.preflight()


def freeze():
    for name in ("readiness-controls-final.xml", "regression-final.xml"):
        tree = ET.parse(BATCH / name)
        assert tree.findall(".//testcase") and not any(
            tree.findall(".//" + k) for k in ("failure", "error", "skipped")
        )
    assert B.read(BATCH / "initial-controls-passed.json")["all_12"]
    old = B.read(PRIOR / "live-freeze-approved.json")
    R.assert_files(
        B.KIT,
        old["candidate_and_driver"],
        except_paths=(".local-agents/reviewer-runtime.py",),
    )
    added = [
        ".local-agents/reviewer-runtime.py",
        "benchmarks/harness_r3_readiness.py",
        "tests/test_reviewer_report_readiness.py",
    ]
    B.save(
        BATCH / "live-freeze-approved.json",
        {
            **old,
            "candidate_and_driver": {
                **old["candidate_and_driver"],
                **{p: B.sha(B.KIT / p) for p in added},
            },
            "registration": B.sha(BATCH / "registration.json"),
            "prepared_cases": B.sha(BATCH / "prepared-cases.json"),
            "origin_anchors": B.sha(BATCH / "origin-anchors.json"),
            "initial_controls": B.sha(BATCH / "initial-controls-passed.json"),
            "authorized_readiness_repair": True,
        },
    )
    print("Readiness candidate frozen", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["checkpoint", "prepare", "freeze", "run"])
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "run":
        F.BATCH = BATCH
        F.run(args.case, args.used)
    elif args.action == "checkpoint":
        checkpoint(args.used)
    else:
        globals()[args.action]()
