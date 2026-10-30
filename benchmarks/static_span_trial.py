"""Approved formal comparison before any conditional fresh-task migration."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import repair_representation_diagnostic as D

T, KIT = D.T, D.KIT
BATCH = KIT / "benchmarks/work/harness-convergence/static-span-formal-20261018-1"
ORDER = [
    f"{arm}-{n}"
    for n in (1, 2, 3)
    for arm in (("old", "new") if n != 2 else ("new", "old"))
]


def prepare(used):
    assert 0 <= used < 15
    assert (
        T.read(D.BATCH / "decision.json")["status"]
        == "PASS_NARROW_REPRESENTATION_DIAGNOSTIC"
    )
    assert all(
        T.sha(p) == sha for p, sha in T.read(D.BATCH / "freeze.json")["pins"].items()
    )
    BATCH.mkdir(exist_ok=False)
    paths = set(
        T.git("ls-files", "-m", "-o", "--exclude-standard", "-z").split("\0")
    ) - {""}
    T.save(
        BATCH / "baseline.json",
        {
            "head": T.git("rev-parse", "HEAD").strip(),
            "status": T.git("status", "--short"),
            "files": {p: T.sha(KIT / p) for p in paths if (KIT / p).is_file()},
        },
    )
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Human approved formal candidate and conditional migration; new candidate here, unchanged frozen Reviewer",
            "feature_id": "formal-static-span",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Public metadata compatibility, validation/epoch and edit routing boundaries",
            "owned_contract_ids": ["metadata"],
            "dependencies": [
                "narrow-representation-diagnostic",
                "frozen-reviewer-and-capture",
            ],
            "order": ORDER,
            "registered_units": 6,
            "fresh_holdout": False,
            "coder_budget": {
                "requests": 6,
                "validations": 3,
                "model_edits": 3,
                "formatter": 1,
                "seconds": 900,
            },
            "reviewer_budget": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
            },
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
            },
            "single_residency": True,
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "criterion": "New3/3 canonical complete chains accepted by Primary, not below old; all original12 tests/Ruff/Pyright/capture and independent Reviewer. Stop if safety/infra/frozen drift or new3/3 unreachable. Retain NOT_RUN, never replace failures.",
            "routing": "Initial whole-function proposal unchanged. Only a unique real Pyright missing parameter annotation at an owned inner helper header gets a hash-bound one-line response; unknown/ambiguous/outside diagnostics remain whole, never gain scope.",
            "protocol": "Host-v1 validation/unknown worker assessment and original canonical gate unchanged; explicit schema + scheduling + static-span flags seal actual trusted config",
            "conditional_migration": "Only after this gate PASS, independently register/freeze three unexposed units, two repeats/two arms, original6/6 and per-task2/2 standard; do not reopen old12-cell batch",
            "production_changes": False,
            "commit_push": False,
            "siblings": "read-only",
        },
    )


def cells():
    seed = T.read(D.S.O.M.BATCH / "prepared-cells-v3.json")["metadata-candidate-1"]
    assert all(T.sha(Path(seed["root"]) / p) == sha for p, sha in seed["files"].items())
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for relative in seed["files"]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(seed["root"]) / relative, path)
        packet, config = (
            T.read(root / ".agent/packet.json"),
            T.read(root / ".agent/config.json"),
        )
        policy = T.read(root / "acceptance/capture-policy.json")
        packet["run_id"] = "formal-span-" + name
        config.update(
            experimental_output_channel="schema",
            coder_structured_output=True,
            experimental_prevalidation_format=True,
            experimental_static_span_repair=name.startswith("new-"),
        )
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
            "files": D.S.O.M.source_map(root),
            "policy_sha256": T.sha(root / "acceptance/capture-policy.json"),
        }
    T.save(BATCH / "cells.json", rows)


def controls():
    outcomes = []
    for name, row in T.read(BATCH / "cells.json").items():
        root = Path(row["root"])
        argv = [
            D.S.O.M.PYTHON,
            "-B",
            KIT / "benchmarks/static_span_coder_entry.py",
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
        good = D.S.O.M.command(argv, root)
        assert good["exit_code"] == 0, good
        bad_config = T.read(root / ".agent/config.json")
        bad_config["experimental_static_span_repair"] = "true"
        invalid_path = BATCH / (name + "-invalid.json")
        T.save(invalid_path, bad_config)
        bad = D.S.O.M.command([*argv[:-1], invalid_path], root)
        assert bad["exit_code"] != 0 and "Explicit span boolean" in bad["stderr"], bad
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
        outcomes.append({"case": name, "positive": good, "negative": bad})
    T.save(BATCH / "entry-controls.json", {"model_calls": 0, "outcomes": outcomes})


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v1.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("error", "failure", "skipped")
    )
    assert len(T.read(BATCH / "entry-controls.json")["outcomes"]) == 6
    pins = T.read(D.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    paths = [
        Path(__file__),
        KIT / "benchmarks/coder_static_span.py",
        KIT / "benchmarks/static_span_coder_entry.py",
        KIT / "benchmarks/static_span_unit_entry.py",
        KIT / "tests/test_static_span_formal.py",
        BATCH / "registration.json",
        BATCH / "cells.json",
        BATCH / "entry-controls.json",
        BATCH / "controls-v1.xml",
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in paths}}}
    )


def run(name, used):
    assert name in ORDER
    for previous in ORDER[: ORDER.index(name)]:
        if previous.startswith("new-"):
            cell = BATCH / "cases" / previous
            assert T.read(cell / "result.json")["eligible_for_primary"]
            assert T.read(cell / "primary-decision.json")["decision"] == "accept"
    original = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(x) for x in argv]
        old = str(KIT / "benchmarks/output_channel_unit.py")
        if old in argv:
            argv[argv.index(old)] = str(KIT / "benchmarks/static_span_unit_entry.py")
        return original(argv, *args, **kwargs)

    old_batch, old_order = D.S.O.BATCH, D.S.O.ORDER
    D.S.O.BATCH, D.S.O.ORDER = BATCH, ORDER
    subprocess.run = dispatch
    try:
        D.S.O.run(name, used)
    finally:
        subprocess.run = original
        D.S.O.BATCH, D.S.O.ORDER = old_batch, old_order


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["prepare", "cells", "controls", "freeze", "run"]
    )
    parser.add_argument("--used", type=int, default=3)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "cells": cells,
        "controls": controls,
        "freeze": freeze,
        "run": lambda: run(args.case, args.used),
    }[args.action]()
