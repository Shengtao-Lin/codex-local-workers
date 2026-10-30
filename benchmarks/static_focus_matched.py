"""Matched code-repair diagnosis; no Reviewer or full-chain acceptance credit."""

import argparse
import os
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import normal_task_trial as N
import supervised_feedback_trial as F
import supervised_repair_phase as P
import supervised_self_audit as A

BATCH = S.KIT / "benchmarks/work/harness-convergence/static-focus-matched-20261020-1"
ORDER = [
    "one-A-1",
    "one-B-1",
    "two-B-1",
    "two-A-1",
    "two-A-2",
    "two-B-2",
    "one-B-2",
    "one-A-2",
]


def command(root, mode="coder", replay=None):
    cell = root.parent.name
    argv = P.command(root, mode, replay)
    if "-B-" in cell:
        argv.append("--static-focus")
    if mode == "coder":
        argv[argv.index("--report") + 1] = str(root / ".agent/unit-report.json")
        argv += ["--summary", str(root / ".agent/unit-summary.json")]
    return argv


def prepare():
    if not (A.BATCH / "decision.json").exists():
        raise ValueError("Prior conditional stage not closed")
    old = S.read(F.OLD / "cells.json")["json-1"]
    sources = {}
    for label, previous in (("one", "json-1"), ("two", "json-2")):
        identity = "self-audit-20261020-1-" + previous
        origin = (
            A.BATCH
            / "cells"
            / previous
            / "isolated/.agent/tasks"
            / identity
            / "runs"
            / identity
            / "preparation-1.json"
        )
        sources[label] = {
            "origin": str(origin),
            "origin_sha256": S.sha(origin),
            "source": S.read(origin)["candidate"],
        }
    rows = {}
    for cell in ORDER:
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if name == old["target"]:
                source = F.OLD / "templates/json" / name
            if S.sha(source) != digest:
                raise ValueError("Frozen source drift")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        starter = sources[cell.split("-")[0]]
        (root / old["target"]).write_text(
            starter["source"], encoding="utf-8", newline="\n"
        )
        identity = {
            k: "static-focus-20261020-1-" + cell
            for k in ("task_id", "unit_id", "run_id")
        }
        packet = S.read(root / ".agent/packet.json")
        packet.update(identity)
        policy = S.read(root / "acceptance/capture-policy.json")
        policy["identity"] = identity
        for path, value in (
            (root / ".agent/packet.json", packet),
            (root / "acceptance/capture-policy.json", policy),
        ):
            import json

            path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        config = S.read(root / ".agent/config.json")
        config["experimental_capture_policy_sha256"] = S.sha(
            root / "acceptance/capture-policy.json"
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        if cell in ("one-A-1", "two-B-1"):
            baseline = [
                T.run(cmd, root)
                for cmd in (
                    [
                        S.PYTHON,
                        "-B",
                        "-m",
                        "pytest",
                        "-q",
                        "tests",
                        old["private_tests"],
                    ],
                    [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
                    [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
                    [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
                )
            ]
            S.save(BATCH / "baseline-proofs" / (cell + ".json"), baseline)
            if (
                any(item["exit_code"] for item in baseline[:3])
                or baseline[3]["exit_code"] != 1
                or "reportMissingParameterType" not in baseline[3]["stdout"]
            ):
                raise ValueError(
                    "Starter must pass behavior/lint with only missing parameter typing"
                )
        rows[cell] = {
            **old,
            "root": str(root),
            "identity": identity,
            "starter": {k: v for k, v in starter.items() if k != "source"},
            "files": {p: S.sha(root / p) for p in old["files"]},
        }
    S.save(BATCH / "cells.json", rows)
    # Probe each arm through the actual no-network unit entry on a separate copy.
    for cell in ("one-A-1", "two-B-1"):
        row = rows[cell]
        root = BATCH / "offline" / cell / "isolated"
        shutil.copytree(row["root"], root)
        reference = T.extract(
            F.OLD / "reference-checks/json" / old["target"], "canonical_json"
        )
        replay = root.parent / "replay.json"
        S.save(replay, [{"replacement": reference}])
        result = T.run(command(root, "unit", replay), root, timeout=180)
        S.save(root.parent / "process.json", result)
        if result["exit_code"]:
            raise ValueError("Offline arm probe failed")
    pins = dict(S.read(A.BATCH / "registration.json")["pins"])
    lineage = {}
    for name, digest in list(pins.items()):
        if S.sha(name) != digest:
            snapshot = BATCH / "candidate-preimages" / Path(name).name
            if not snapshot.exists() or S.sha(snapshot) != digest:
                raise ValueError("Unexpected ancestor drift: " + name)
            lineage[name] = {
                "old_sha256": digest,
                "snapshot": str(snapshot),
                "new_sha256": S.sha(name),
            }
            pins[str(snapshot)] = digest
            pins[name] = S.sha(name)
    for path in (
        Path(__file__).resolve(),
        S.KIT / "benchmarks/static_focus_rules.py",
        BATCH / "cells.json",
    ):
        pins[str(path)] = S.sha(path)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "pins": pins,
            "lineage": lineage,
            "weekly_stop": 40,
            "batch_seconds": 14400,
            "registered": 8,
            "A": "Minimal repair phase with existing raw static check output",
            "B": "Same facts plus version-bound rule/path/line/message from existing runtime parser; old action instructions omitted",
            "matching": "Two actual exposed model drafts, behavior/private tests already pass, only missing parameter annotations; same approved inputs and budgets, balanced arm order. No gold or extra semantic hint supplied.",
            "gate": "Coder-only diagnostic: B4/4 complete independent configured checks and no safety drift; compare A. Zero full-chain acceptance credit, Reviewer NOT_RUN by design.",
            "continue_rule": "Complete eight ordinary outcomes, no replacements; infra/safety/40% stop",
            "budget": {
                "requests": 12,
                "edits": 3,
                "post_edit_checks": 3,
                "seconds": 900,
            },
        },
    )
    print("Eight matched Coder-only diagnostic cells frozen")


def run(cell, used, observed):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    N.run(
        cell,
        used,
        observed,
        batch=BATCH,
        order=ORDER,
        build_command=command,
        usage_limit=40,
        batch_seconds=14400,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare"])
    parser.parse_args()
    prepare()
