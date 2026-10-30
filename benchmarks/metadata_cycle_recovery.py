"""One ordinary defect rework, frozen harness unchanged; not a new gate score."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import static_span_trial as S

T, KIT = S.T, S.KIT
BATCH = KIT / "benchmarks/work/harness-convergence/metadata-cycle-recovery-20261018-1"
TEST = "tests/test_cyclic_metadata.py"


def prepare(used):
    assert 0 <= used < 15
    assert T.read(S.BATCH / "decision.json")["conditional_migration_allowed"] is False
    pins = T.read(S.BATCH / "freeze.json")["pins"]
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
            "feature_id": "metadata-cycle-primary-rework",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Preserve original public invalid-input compatibility",
            "owned_contract_ids": ["metadata"],
            "dependencies": ["PRIMARY-METADATA-CYCLE-1"],
            "authority": "Ordinary bounded repair of Primary-confirmed defect under approved identical formal candidate; no new harness protocol, no conditional migration",
            "registered_units": 1,
            "new_harness_candidate": False,
            "criterion": "One bounded rework call, original contract/checks plus read-only confirmed-defect regression; original canonical handoff, independent Reviewer and Primary review required. No retry, no old-score rewrite or migration qualification.",
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
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "models_unchanged": True,
            "single_residency": True,
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    old = T.read(S.BATCH / "cells.json")["new-1"]
    root = BATCH / "cases/rework-1/isolated"
    root.mkdir(parents=True)
    for relative in old["files"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(old["root"]) / relative, path)
    shutil.copyfile(
        KIT / "benchmarks/fixtures/metadata-cycle-recovery-v1/test_cyclic_metadata.py",
        root / TEST,
    )
    packet, config = (
        T.read(root / ".agent/packet.json"),
        T.read(root / ".agent/config.json"),
    )
    packet["run_id"] = "cycle-recovery-1"
    packet["packet_revision"] += 1
    packet["focused_tests"].append(TEST)
    packet["scope"]["readonly"].append(TEST)
    packet["review_feedback"] = [
        {
            "finding_id": "PRIMARY-METADATA-CYCLE-1",
            "contract_id": "metadata",
            "text": "Primary confirmed that cyclic dict/list metadata originally raises ValueError, but this draft raises RecursionError before the existing JSON rejection. Preserve original rejection and input topology, including shared noncyclic aliases; do not change the original contract, source outside the target or protected tests. The new read-only test reproduces this existing-contract regression.",
            "source_anchor": "json.dumps",
            "verify_in_review": True,
        }
    ]
    policy = T.read(root / "acceptance/capture-policy.json")
    policy["identity"] = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
    policy["source_paths"].append(TEST)
    policy["readonly_hashes"][TEST] = T.sha(root / TEST)
    for relative, data in (
        (".agent/packet.json", packet),
        (".agent/config.json", config),
        ("acceptance/capture-policy.json", policy),
    ):
        (root / relative).write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
    row = {
        "root": str(root),
        "files": S.D.S.O.M.source_map(root),
        "policy_sha256": T.sha(root / "acceptance/capture-policy.json"),
    }
    T.save(BATCH / "cells.json", {"rework-1": row})


def controls():
    row = T.read(BATCH / "cells.json")["rework-1"]
    root = Path(row["root"])
    argv = [
        S.D.S.O.M.PYTHON,
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
    preflight = S.D.S.O.M.command(argv, root)
    assert preflight["exit_code"] == 0, preflight
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root / "src"),
    }
    baseline = S.D.S.O.M.command(
        [
            S.D.S.O.M.PYTHON,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            TEST,
            "--junitxml=" + str(BATCH / "negative-junit.xml"),
        ],
        root,
        env,
    )
    assert baseline["exit_code"] == 1 and "4 failed, 2 passed" in baseline["stdout"], (
        baseline
    )
    lint = [
        S.D.S.O.M.command(
            [S.D.S.O.M.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            root,
        ),
        S.D.S.O.M.command(
            [S.D.S.O.M.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root
        ),
    ]
    assert all(c["exit_code"] == 0 for c in lint), lint
    assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
    T.save(
        BATCH / "controls.json",
        {
            "preflight": preflight,
            "confirmed_draft_negative": baseline,
            "lint": lint,
            "model_calls": 0,
        },
    )


def freeze():
    assert T.read(BATCH / "controls.json")["model_calls"] == 0
    assert all(
        c["exit_code"] == 0 for c in T.read(BATCH / "positive-controls.json")["checks"]
    )
    pins = T.read(S.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    paths = [
        Path(__file__),
        KIT / "benchmarks/fixtures/metadata-cycle-recovery-v1/test_cyclic_metadata.py",
        BATCH / "registration.json",
        BATCH / "cells.json",
        BATCH / "controls.json",
        BATCH / "positive-controls.json",
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in paths}}}
    )


def positive():
    row = T.read(BATCH / "cells.json")["rework-1"]
    root = BATCH / "private-reference"
    root.mkdir()
    for relative in row["files"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(row["root"]) / relative, path)
    path = root / "src/product/metadata.py"
    source = path.read_text(encoding="utf-8")
    old = S.D.BOUNDARY.target(source, "validate_metadata")[3]
    reference = S.D.S.O.M.function(
        S.D.S.O.M.BATCH / "private/metadata/reference.py", "validate_metadata"
    )
    path.write_text(source.replace(old, reference, 1), encoding="utf-8")
    commands = [
        S.D.S.O.M.command([S.D.S.O.M.PYTHON, "-B", "-m", "ruff", "format", "src"], root)
    ]
    commands += [
        S.D.S.O.M.command(
            [
                S.D.S.O.M.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_metadata.py",
                TEST,
                S.D.S.O.M.BATCH / "private/metadata/test_private_metadata.py",
                "--junitxml=" + str(BATCH / "positive-junit.xml"),
            ],
            root,
            {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(root / "src"),
            },
        )
    ]
    commands += [
        S.D.S.O.M.command(
            [S.D.S.O.M.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            root,
        ),
        S.D.S.O.M.command(
            [S.D.S.O.M.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root
        ),
        S.D.S.O.M.command(
            [S.D.S.O.M.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.D.S.O.M.PYTHON],
            root,
        ),
    ]
    assert all(c["exit_code"] == 0 for c in commands), commands
    assert "18 passed" in commands[1]["stdout"]
    T.save(
        BATCH / "positive-controls.json",
        {
            "checks": commands,
            "model_calls": 0,
            "reference_outside_worker_scope": True,
            "source_sha256": T.sha(path),
            "protected_test_sha256": T.sha(root / TEST),
        },
    )


def run(used):
    original = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(x) for x in argv]
        old = str(KIT / "benchmarks/output_channel_unit.py")
        if old in argv:
            argv[argv.index(old)] = str(KIT / "benchmarks/static_span_unit_entry.py")
        return original(argv, *args, **kwargs)

    old_batch, old_order = S.D.S.O.BATCH, S.D.S.O.ORDER
    S.D.S.O.BATCH, S.D.S.O.ORDER = BATCH, ["rework-1"]
    subprocess.run = dispatch
    try:
        S.D.S.O.run("rework-1", used)
    finally:
        subprocess.run = original
        S.D.S.O.BATCH, S.D.S.O.ORDER = old_batch, old_order
    root = Path(T.read(BATCH / "cells.json")["rework-1"]["root"])
    extra = S.D.S.O.M.command(
        [
            S.D.S.O.M.PYTHON,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_metadata.py",
            TEST,
            S.D.S.O.M.BATCH / "private/metadata/test_private_metadata.py",
            "--junitxml=" + str(BATCH / "independent-full-junit.xml"),
        ],
        root,
        {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src")},
    )
    T.save(BATCH / "independent-full-check.json", extra)
    print(
        json.dumps(
            {
                "independent_full_exit": extra["exit_code"],
                "original_gate_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["prepare", "controls", "positive", "freeze", "run"]
    )
    parser.add_argument("--used", type=int, default=3)
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "controls": controls,
        "positive": positive,
        "freeze": freeze,
        "run": lambda: run(args.used),
    }[args.action]()
