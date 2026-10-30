"""Pre-change source reference is historical code, not a gold solution/rollback."""

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import exception_body_diagnostic as V

C, T, KIT, M, D = V.C, V.T, V.KIT, V.M, V.D
BATCH = KIT / "benchmarks/work/harness-convergence/exception-reference-20261018-1"
ORDER = [
    f"{a}-{n}"
    for n, arms in (
        (1, ("current", "both", "reference")),
        (2, ("reference", "current", "both")),
        (3, ("both", "reference", "current")),
    )
    for a in arms
]


def prepare(used):
    assert (
        0 <= used < 15
        and T.read(V.BATCH / "decision.json")["status"] == "NO_BODY_HIDING_RECOVERY"
    )
    pins = T.read(V.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    BATCH.mkdir(exist_ok=False)
    old = T.read(V.BATCH / "fixture.json")
    entry = next(
        p
        for p in T.read(C.RUN / "preimages.json")
        if p["path"] == old["binding"]["path"]
    )
    preimage = C.ORIGIN / entry["archive_path"]
    assert T.sha(preimage) == entry["sha256"]
    original_function = D.BOUNDARY.target(
        preimage.read_text(encoding="utf-8"), old["binding"]["symbol"]
    )[3]
    assert "except Exception" not in original_function
    reference = {
        "path": old["binding"]["path"],
        "module_preimage_sha256": entry["sha256"],
        "source": original_function,
        "provenance": "Actual canonical source preimage before feature implementation. Read-only historical context; does NOT satisfy the new singleton contract. Not current source, not a gold repair or acceptance.",
    }
    current = D.INTERFACE.restore_literal(old["user_message"])
    both = copy.deepcopy(current)
    both["pre_change_reference"] = reference
    historical = D.INTERFACE.restore_literal(old["hidden_user_message"])
    historical["pre_change_reference"] = reference
    fixture = {
        **old,
        "facts": current,
        "user_message": D.INTERFACE.literal_input(current),
        "both_user_message": D.INTERFACE.literal_input(both),
        "reference_user_message": D.INTERFACE.literal_input(historical),
        "reference_provenance": {
            "preimages_index": str(C.RUN / "preimages.json"),
            "index_sha256": T.sha(C.RUN / "preimages.json"),
            "actual_preimage": str(preimage),
            "sha256": T.sha(preimage),
        },
    }
    T.save(BATCH / "fixture.json", fixture)
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Ongoing goal and delegated bounded diagnostics; actual historical source only, no semantic guidance or rollback",
            "feature_id": "pinned-baseline-reference",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Historical/current source separation and compatibility preservation",
            "owned_contract_ids": ["messages_output"],
            "dependencies": ["closed-body-diagnostic"],
            "order": ORDER,
            "registered": 9,
            "fresh_holdout": False,
            "contrast": "Same neutral system and actual explicit contract/failures: current bad body, current+real pre-change reference, reference+hidden current body. Only historical/current source context changes.",
            "budget": {
                "proposals_per_cell": 1,
                "total_chat_requests": 9,
                "output_tokens": 4096,
                "formatter_commands": 0,
                "repairs": 0,
                "extra_probes": 0,
            },
            "criterion": "Per-arm3/3 original25 tests and all strict checks, protected drift0. Separate behavior/static, Primary review still needed. No full-chain/fresh credit. Fixed9, no reruns or gold/algorithm source.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "context": 24576,
                "parallel": 1,
            },
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    shutil.copyfile(V.BATCH / "snapshot.py", BATCH / "snapshot.py")
    seed = T.read(V.BATCH / "cells.json")["legacy-1"]
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for p, sha in seed["files"].items():
            source = (
                BATCH / "snapshot.py"
                if p == old["binding"]["path"]
                else Path(seed["root"]) / p
            )
            assert T.sha(source) == sha
            target = root / p
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        rows[name] = {"root": str(root), "files": M.source_map(root)}
    T.save(BATCH / "cells.json", rows)


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v1.xml")
    assert len(tree.findall(".//testcase")) == 4
    assert not any(tree.findall(".//" + k) for k in ("failure", "error", "skipped"))
    pins = T.read(V.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    paths = [
        Path(__file__),
        KIT / "tests/test_exception_reference.py",
        *[
            BATCH / p
            for p in (
                "registration.json",
                "fixture.json",
                "snapshot.py",
                "cells.json",
                "controls-v1.xml",
            )
        ],
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in paths}}}
    )


def sample(name, used):
    original_read = T.read

    def read(path):
        value = original_read(path)
        if Path(path) == BATCH / "fixture.json":
            if name.startswith("both-"):
                value["user_message"] = value["both_user_message"]
            elif name.startswith("reference-"):
                value["user_message"] = value["reference_user_message"]
        return value

    C.BATCH, C.ORDER = BATCH, ORDER
    D.PROMPTS.update(current=V.NEUTRAL, both=V.NEUTRAL, reference=V.NEUTRAL)
    T.read = read
    try:
        C.sample(name, used)
    finally:
        T.read = original_read


def run_all(used):
    assert 0 <= used < 15
    for name in ORDER:
        cell = BATCH / "cases" / name
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(KIT / "benchmarks/r3_capture"),
            "R3_WIRE_DIR": str(cell / "wire"),
        }
        p = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__)),
                "sample",
                "--case",
                name,
                "--used",
                str(used),
            ],
            env=env,
            cwd=KIT,
            check=False,
        )
        assert p.returncode == 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "freeze", "sample", "run-all"])
    p.add_argument("--used", type=int, required=True)
    p.add_argument("--case")
    args = p.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "freeze": freeze,
        "sample": lambda: sample(args.case, args.used),
        "run-all": lambda: run_all(args.used),
    }[args.action]()
