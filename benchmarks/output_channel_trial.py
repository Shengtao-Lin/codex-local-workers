"""Append-only, exposed-task transport diagnostic. Not a fresh transfer gate."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import capture_transfer_matrix as M
import harness_capture_transport as T

KIT = T.KIT
BATCH = KIT / "benchmarks/work/harness-convergence/output-channel-20261018-1"
ORDER = [
    f"{arm}-{n}"
    for n in (1, 2, 3)
    for arm in (("raw", "schema") if n != 2 else ("schema", "raw"))
]


def prepare(used):
    assert 0 <= used < 15
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
            "authorization": "User explicitly approved independent output-channel comparison and resumed goal",
            "feature_id": "exposed-metadata-output-channel",
            "risk": "high",
            "risk_rationale": "Public validation compatibility; scope isolation does not reduce semantic risk",
            "owned_contract_ids": ["metadata"],
            "dependencies": [],
            "order": ORDER,
            "registered_units": 6,
            "fresh_holdout": False,
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
            },
            "coder_budget_per_unit": {
                "requests": 6,
                "edits": 3,
                "validations": 3,
                "seconds": 900,
            },
            "reviewer_budget_per_unit": {"requests": 16, "errors": 4, "seconds": 600},
            "criterion": "Diagnostic arm requires 3/3 full chains, protected/private tests and Primary review; no product or fresh-transfer credit. Complete all six, retain failures, no retries or live edits.",
            "representation_difference": "Raw complete source versus constrained WHOLE_SCHEMA; same restored literal facts, safety and semantic gates. Raw has no structured blocked_reason alternative.",
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "production_changes": False,
            "commit_push": False,
            "single_residency": True,
        },
    )


def cells():
    old = T.read(M.BATCH / "prepared-cells-v3.json")["metadata-candidate-1"]
    seed = Path(old["root"])
    assert all(T.sha(seed / p) == sha for p, sha in old["files"].items())
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for relative in old["files"]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(seed / relative, path)
        packet, config = (
            T.read(root / ".agent/packet.json"),
            T.read(root / ".agent/config.json"),
        )
        packet["run_id"] = "output-" + name
        # Identity changes, not behavior/test changes. Capture policy uses the
        # same source/probes/dependencies; its producer/helper bytes are pinned.
        policy = T.read(root / "acceptance/capture-policy.json")
        policy["identity"] = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
        config["experimental_output_channel"] = name.split("-")[0]
        config["coder_structured_output"] = name.startswith("schema-")
        for relative, value in (
            (".agent/packet.json", packet),
            (".agent/config.json", config),
            ("acceptance/capture-policy.json", policy),
        ):
            # Newly created isolated inputs only; never modify the seed/archive.
            (root / relative).write_text(
                json.dumps(value, indent=2) + "\n", encoding="utf-8"
            )
        rows[name] = {
            "root": str(root),
            "files": M.source_map(root),
            "policy_sha256": T.sha(root / "acceptance/capture-policy.json"),
        }
    T.save(BATCH / "cells.json", rows)


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v3.xml")
    assert len(tree.findall(".//testcase")) >= 20
    assert not any(tree.findall(".//" + k) for k in ("failure", "error", "skipped"))
    old = T.read(M.BATCH / "live-freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in old.items())
    extra = [
        Path(__file__),
        KIT / "benchmarks/coder_output_channel.py",
        KIT / "benchmarks/output_channel_unit.py",
        KIT / "tests/test_output_channel.py",
        BATCH / "registration.json",
        BATCH / "cells.json",
        BATCH / "controls-v3.xml",
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**old, **{str(p): T.sha(p) for p in extra}}}
    )


def run(name, used):
    assert 0 <= used < 15 and name in ORDER
    for previous in ORDER[: ORDER.index(name)]:
        assert (BATCH / "cases" / previous / "result.json").exists()
    assert all(
        T.sha(p) == sha for p, sha in T.read(BATCH / "freeze.json")["pins"].items()
    )
    row = T.read(BATCH / "cells.json")[name]
    root = Path(row["root"])
    cell = root.parent
    assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
    T.save(
        cell / "started.json",
        {"weekly_used": used, "time": time.time(), "no_retry": True},
    )
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(KIT / "benchmarks/r3_capture"),
        "R3_WIRE_DIR": str(cell / "wire"),
    }
    argv = [
        M.PYTHON,
        "-B",
        KIT / "benchmarks/output_channel_unit.py",
        "--coder-runtime-dir",
        root / ".local-agents",
        "--capture-policy-sha256",
        row["policy_sha256"],
        "--packet",
        root / ".agent/packet.json",
        "--config",
        root / ".agent/config.json",
        "--coder-report",
        cell / "coder.json",
        "--review-report",
        cell / "reviewer.json",
        "--summary",
        cell / "unit-summary.json",
    ]
    start = time.monotonic()
    process = subprocess.run(
        [str(x) for x in argv],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    T.save(
        cell / "entry-result.json",
        {
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "seconds": time.monotonic() - start,
        },
    )
    (cell / "checks").mkdir()
    checks = [
        M.command(
            [
                M.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_metadata.py",
                M.BATCH / "private/metadata/test_private_metadata.py",
                "--junitxml=" + str(cell / "checks/junit.xml"),
            ],
            root,
            {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(root / "src"),
            },
        )
    ]
    checks += [
        M.command(
            [M.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"], root
        ),
        M.command([M.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root),
        M.command([M.PYTHON, "-B", "-m", "pyright", "--pythonpath", M.PYTHON], root),
    ]
    T.save(cell / "checks/results.json", checks)
    writable = T.read(root / ".agent/packet.json")["scope"]["modify"]
    drift = [
        p
        for p, sha in row["files"].items()
        if p not in writable and T.sha(root / p) != sha
    ]
    coder = T.read(cell / "coder.json") if (cell / "coder.json").exists() else {}
    reviewer = (
        T.read(cell / "reviewer.json") if (cell / "reviewer.json").exists() else {}
    )
    T.save(
        cell / "result.json",
        {
            "coder_status": coder.get("status"),
            "failure_reason": coder.get("failure_reason"),
            "reviewer_decision": reviewer.get("decision"),
            "protected_drift": drift,
            "checks": [c["exit_code"] for c in checks],
            "eligible_for_primary": process.returncode == 0
            and not drift
            and all(c["exit_code"] == 0 for c in checks),
            "seconds": time.monotonic() - start,
        },
    )
    print(json.dumps(T.read(cell / "result.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "cells", "freeze", "run"])
    parser.add_argument("--used", type=int, default=2)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "cells": cells,
        "freeze": freeze,
        "run": lambda: run(args.case, args.used),
    }[args.action]()
