"""Autonomously authorized mechanical candidate; preserve every old failure."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import metadata_cycle_recovery as R

T, KIT = R.T, R.KIT
BATCH = KIT / "benchmarks/work/harness-convergence/unified-preparation-20261018-1"
ORDER = [
    f"{arm}-{n}"
    for n in (1, 2, 3)
    for arm in (("old", "new") if n != 2 else ("new", "old"))
]


def prepare(used):
    assert 0 <= used < 15
    pins = T.read(R.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    BATCH.mkdir(exist_ok=False)
    paths = set(
        T.git("ls-files", "-m", "-o", "--exclude-standard", "-z").split("\0")
    ) - {""}
    T.save(
        BATCH / "baseline.json",
        {
            "head": T.git("rev-parse", "HEAD").strip(),
            "files": {p: T.sha(KIT / p) for p in paths if (KIT / p).is_file()},
        },
    )
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Human delegated same-boundary mechanical candidates autonomously; no change to important authority boundaries",
            "feature_id": "unified-format-static-routing",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Validation epoch, edit binding and public invalid-input preservation",
            "owned_contract_ids": ["metadata"],
            "dependencies": ["closed-formal-span", "closed-cycle-recovery"],
            "order": ORDER,
            "registered_units": 6,
            "fresh_holdout": False,
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
            },
            "budget": {
                "coder_requests": 6,
                "validations": 3,
                "model_edits": 3,
                "formatter_commands": 1,
                "coder_seconds": 900,
                "reviewer_requests": 16,
                "reviewer_errors": 4,
                "reviewer_seconds": 600,
                "reviewer_output_tokens": 4096,
            },
            "criterion": "New3/3 Primary-accepted complete chains, not below old, all18 protected/private tests and unchanged Ruff/Pyright/capture. Stop if3/3 unreachable, safety/infra/drift or weekly ceiling. Do not replace failed samples.",
            "change": "One trusted AST-preserving formatter preparation before counted validation after the first edit; location-bound single-helper-header annotation repair also accepts one unambiguous Ruff diagnostic. Exact same header-shape/path/hash/guard and original handoff.",
            "out_of_scope": [
                "new models",
                "broader edit permission",
                "relaxed checks",
                "production defaults",
                "old-score rewriting",
            ],
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "single_residency": True,
            "production_changes": False,
            "commit_push": False,
            "siblings": "read-only",
        },
    )
    original_batch = R.BATCH
    R.BATCH = BATCH / "template"
    try:
        R.prepare(used)
        R.controls()
        R.positive()
    finally:
        R.BATCH = original_batch
    template = T.read(BATCH / "template/cells.json")["rework-1"]
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for relative in template["files"]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(template["root"]) / relative, path)
        packet, config = (
            T.read(root / ".agent/packet.json"),
            T.read(root / ".agent/config.json"),
        )
        policy = T.read(root / "acceptance/capture-policy.json")
        packet["run_id"] = "unified-" + name
        config["experimental_unified_preparation"] = name.startswith("new-")
        policy["identity"] = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
        for relative, data in (
            (".agent/packet.json", packet),
            (".agent/config.json", config),
            ("acceptance/capture-policy.json", policy),
        ):
            (root / relative).write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
        rows[name] = {
            "root": str(root),
            "files": R.S.D.S.O.M.source_map(root),
            "policy_sha256": T.sha(root / "acceptance/capture-policy.json"),
        }
    T.save(BATCH / "cells.json", rows)


def controls():
    outcomes = []
    for name, row in T.read(BATCH / "cells.json").items():
        root = Path(row["root"])
        argv = [
            R.S.D.S.O.M.PYTHON,
            "-B",
            KIT / "benchmarks/unified_coder_entry.py",
            "--preflight-only",
            "--runtime-dir",
            root / ".local-agents",
            "--capture-policy",
            "acceptance/capture-policy.json",
            "--capture-policy-sha256",
            row["policy_sha256"],
            "--packet",
            root / ".agent/packet.json",
            "--config",
            root / ".agent/config.json",
        ]
        good = R.S.D.S.O.M.command(argv, root)
        assert good["exit_code"] == 0, good
        config = T.read(root / ".agent/config.json")
        config["experimental_unified_preparation"] = "true"
        invalid = BATCH / (name + "-invalid.json")
        T.save(invalid, config)
        bad = R.S.D.S.O.M.command([*argv[:-1], invalid], root)
        assert bad["exit_code"] != 0 and "Explicit unified boolean" in bad["stderr"], (
            bad
        )
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
        outcomes.append({"case": name, "positive": good, "negative": bad})
    T.save(BATCH / "entry-controls.json", {"outcomes": outcomes, "model_calls": 0})


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v1.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("error", "failure", "skipped")
    )
    assert len(T.read(BATCH / "entry-controls.json")["outcomes"]) == 6
    pins = T.read(R.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    paths = [
        Path(__file__),
        KIT / "benchmarks/coder_unified_preparation.py",
        KIT / "benchmarks/unified_coder_entry.py",
        KIT / "benchmarks/unified_unit_entry.py",
        KIT / "tests/test_unified_preparation.py",
        BATCH / "registration.json",
        BATCH / "cells.json",
        BATCH / "entry-controls.json",
        BATCH / "controls-v1.xml",
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in paths}}}
    )


def run(name, used):
    for previous in ORDER[: ORDER.index(name)]:
        if previous.startswith("new-"):
            assert (
                T.read(BATCH / "cases" / previous / "primary-decision.json")["decision"]
                == "accept"
            )
    original = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(x) for x in argv]
        old = str(KIT / "benchmarks/output_channel_unit.py")
        if old in argv:
            argv[argv.index(old)] = str(KIT / "benchmarks/unified_unit_entry.py")
        return original(argv, *args, **kwargs)

    old_batch, old_order = R.S.D.S.O.BATCH, R.S.D.S.O.ORDER
    R.S.D.S.O.BATCH, R.S.D.S.O.ORDER = BATCH, ORDER
    subprocess.run = dispatch
    try:
        R.S.D.S.O.run(name, used)
    finally:
        subprocess.run = original
        R.S.D.S.O.BATCH, R.S.D.S.O.ORDER = old_batch, old_order
    root = Path(T.read(BATCH / "cells.json")[name]["root"])
    full = R.S.D.S.O.M.command(
        [
            R.S.D.S.O.M.PYTHON,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_metadata.py",
            "tests/test_cyclic_metadata.py",
            R.S.D.S.O.M.BATCH / "private/metadata/test_private_metadata.py",
            "--junitxml=" + str(root.parent / "independent-full-junit.xml"),
        ],
        root,
        {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src")},
    )
    T.save(root.parent / "independent-full-check.json", full)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "controls", "freeze", "run"])
    parser.add_argument("--used", type=int, default=3)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "controls": controls,
        "freeze": freeze,
        "run": lambda: run(args.case, args.used),
    }[args.action]()
