"""Approved paired live scheduling diagnostic; no modification of old batches."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import output_channel_trial as O
import prevalidation_format_audit as A

T, KIT = O.T, O.KIT
BATCH = KIT / "benchmarks/work/harness-convergence/scheduling-live-20261018-1"
ORDER = [
    f"{arm}-{n}"
    for n in (1, 2, 3)
    for arm in (("old", "new") if n != 2 else ("new", "old"))
]


def prepare(used):
    assert 0 <= used < 15
    assert T.read(A.BATCH / "decision.json")["status"] == "PASS_OFFLINE_SCHEDULING_ONLY"
    assert all(
        T.sha(p) == sha for p, sha in T.read(A.BATCH / "freeze.json")["pins"].items()
    )
    BATCH.mkdir(exist_ok=False)
    files = set(
        T.git("ls-files", "-m", "-o", "--exclude-standard", "-z").split("\0")
    ) - {""}
    T.save(
        BATCH / "baseline.json",
        {
            "head": T.git("rev-parse", "HEAD").strip(),
            "status": T.git("status", "--short"),
            "files": {p: T.sha(KIT / p) for p in sorted(files) if (KIT / p).is_file()},
        },
    )
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Human explicitly approved the separately requested scheduling live comparison",
            "feature_id": "metadata-check-scheduling",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Validation epoch/acceptance and public metadata compatibility",
            "owned_contract_ids": ["metadata"],
            "dependencies": ["frozen-schema-output", "offline-scheduling-controls"],
            "order": ORDER,
            "registered_units": 6,
            "fresh_holdout": False,
            "arms": {
                "old": "Frozen schema host schedule",
                "new": "Same schema host plus eligible prevalidation formatting",
            },
            "coder_budget_per_unit": {
                "requests": 6,
                "validation_attempts": 3,
                "model_edits": 3,
                "formatter_commands": 1,
                "seconds": 900,
            },
            "reviewer_budget_per_unit": {
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
            "criterion": "New schedule3/3 complete accepted chains, not below old schedule. All six fixed cells execute unless usage, safety, frozen drift or infrastructure requires stopping. Preserve every failure; no in-batch adjustments or retries.",
            "qualification": "Exposed-task scheduling diagnostic only; no fresh transfer or product acceptance",
            "fixed_contract_and_protected_tests": str(O.M.BATCH / "registration.json"),
            "actual_cost": "Useful execution counts may increase within unchanged ceilings; report actual requests/validation/formatter/checks separately",
            "production_changes": False,
            "commit_push": False,
            "siblings": "read-only",
        },
    )


def cells():
    seed = T.read(O.M.BATCH / "prepared-cells-v3.json")["metadata-candidate-1"]
    assert all(T.sha(Path(seed["root"]) / p) == sha for p, sha in seed["files"].items())
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for relative in seed["files"]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(seed["root"]) / relative, path)
        packet = T.read(root / ".agent/packet.json")
        config = T.read(root / ".agent/config.json")
        policy = T.read(root / "acceptance/capture-policy.json")
        packet["run_id"] = "schedule-" + name
        config.update(
            experimental_output_channel="schema",
            coder_structured_output=True,
            experimental_prevalidation_format=name.startswith("new-"),
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
            "files": O.M.source_map(root),
            "policy_sha256": T.sha(root / "acceptance/capture-policy.json"),
        }
    T.save(BATCH / "cells.json", rows)


def controls():
    outcomes = []
    for name, row in T.read(BATCH / "cells.json").items():
        root = Path(row["root"])
        argv = [
            O.M.PYTHON,
            "-B",
            KIT / "benchmarks/scheduled_coder_entry.py",
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
        positive = O.M.command(argv, root)
        assert positive["exit_code"] == 0, positive
        bad = T.read(root / ".agent/config.json")
        bad["coder_structured_output"] = False
        negative_path = BATCH / (name + "-invalid-config.json")
        T.save(negative_path, bad)
        negative = O.M.command([*argv[:-1], negative_path], root)
        assert (
            negative["exit_code"] != 0 and "transport mismatch" in negative["stderr"]
        ), negative
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
        outcomes.append({"case": name, "positive": positive, "negative": negative})
    T.save(BATCH / "entry-controls.json", {"model_calls": 0, "outcomes": outcomes})


def freeze():
    assert len(T.read(BATCH / "entry-controls.json")["outcomes"]) == 6
    pins = T.read(A.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    files = [
        Path(__file__),
        KIT / "benchmarks/scheduled_coder_entry.py",
        KIT / "benchmarks/scheduled_unit_entry.py",
        BATCH / "registration.json",
        BATCH / "cells.json",
        BATCH / "entry-controls.json",
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in files}}}
    )


def run(name, used):
    # Reuse the frozen collector and every independent check verbatim, changing
    # only its registered batch/order and the explicit installed entry path.
    original = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(x) for x in argv]
        old = str(KIT / "benchmarks/output_channel_unit.py")
        if old in argv:
            argv[argv.index(old)] = str(KIT / "benchmarks/scheduled_unit_entry.py")
        return original(argv, *args, **kwargs)

    old_batch, old_order = O.BATCH, O.ORDER
    O.BATCH, O.ORDER = BATCH, ORDER
    subprocess.run = dispatch
    try:
        O.run(name, used)
    finally:
        subprocess.run = original
        O.BATCH, O.ORDER = old_batch, old_order


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["prepare", "cells", "controls", "freeze", "run"]
    )
    parser.add_argument("--used", type=int, default=2)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "cells": cells,
        "controls": controls,
        "freeze": freeze,
        "run": lambda: run(args.case, args.used),
    }[args.action]()
