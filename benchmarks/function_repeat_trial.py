"""Second independently frozen batch; share runner, never mutate old globals."""

import argparse
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import consolidated_harness as H
import normal_task_trial as N

BATCH = S.KIT / "benchmarks/work/harness-convergence/function-normal-repeat-20261019-1"
ORDER = list(N.ORDER)


def command(root, mode="unit", replay=None):
    argv = N.command(root, mode, replay)
    argv.remove("--preserve-existing-imports")
    argv.append("--function-output")
    return argv


def checkpoint():
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], cwd=S.KIT
        )
        .decode()
        .split("\0")
    )
    S.save(
        BATCH / "baseline.json",
        {"files": {p: S.sha(S.KIT / p) for p in paths if p and (S.KIT / p).is_file()}},
    )
    for name in (
        "consolidated_harness.py",
        "consolidated_entry.py",
        "normal_task_trial.py",
        "normal_task_close.py",
    ):
        dest = BATCH / "candidate-preimages" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write((S.KIT / "benchmarks" / name).read_bytes())


def prepare(used):
    rows = {}
    for cell in ORDER:
        row = N.prepare_cell(
            cell.rsplit("-", 1)[0], BATCH / "cells" / cell, "function-" + cell
        )
        root = Path(row["root"])
        packet = S.read(root / ".agent/packet.json")
        packet["primary_plan_sha256"] = S.sha(S.KIT / "docs/function-output-stage.md")
        (root / ".agent/packet.json").write_text(
            __import__("json").dumps(packet, indent=2), encoding="utf-8"
        )
        row["files"][".agent/packet.json"] = S.sha(root / ".agent/packet.json")
        rows[cell] = row
    S.save(BATCH / "cells.json", rows)
    cases = list(ET.parse(BATCH / "controls.xml").iter("testcase"))
    if len(cases) != 12 or any(
        c.find(tag) is not None
        for c in cases
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("Twelve function-format controls required")
    pins = dict(S.read(N.BATCH / "registration.json")["pins"])
    lineage = {}
    for name in (
        "consolidated_harness.py",
        "consolidated_entry.py",
        "normal_task_trial.py",
    ):
        path = str(S.KIT / "benchmarks" / name)
        archived = BATCH / "candidate-preimages" / name
        if S.sha(archived) != pins[path]:
            raise ValueError("Prior frozen version must be preserved")
        lineage[path] = {
            "old_sha256": pins[path],
            "preserved_at": str(archived),
            "new_sha256": S.sha(path),
        }
        pins[str(archived)] = pins[path]
        pins[path] = S.sha(path)
    for path in (
        Path(__file__),
        S.KIT / "benchmarks/function_proposal_rules.py",
        S.KIT / "tests/test_function_proposal_entry.py",
        S.KIT / "docs/function-output-stage.md",
        BATCH / "cells.json",
        BATCH / "controls.xml",
    ):
        pins[str(path)] = S.sha(path)
    if any(S.sha(p) != sha for p, sha in pins.items()):
        raise ValueError("Unaccounted ancestor/candidate drift")
    S.save(
        BATCH / "registration.json",
        {
            "authorization": "Latest user permits autonomous bounded analysis/optimization, stop at key design decision or20%used",
            "order": ORDER,
            "registered": 4,
            "pins": pins,
            "lineage": lineage,
            "feature_id": "function-output-normal-repeat",
            "risk": "high compatibility boundary; same atomic contracts",
            "owned_contracts": ["request_keys", "single_content"],
            "dependencies": [],
            "candidate": "Function-only output; host structural assembly and unchanged original checks; same full-module input",
            "budget": H.BUDGET,
            "reviewer_budget": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
            },
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context": 24576,
                "single_residency": True,
            },
            "gate": "4/4 independent complete chains, each task2/2, no assistance/scope/protected drift; exposed repeats only",
            "continue_rule": "Ordinary failure HOLD but finish diagnostic order; stop infrastructure/safety/protected drift/20%used/time; no replacement/rerun",
            "weekly_used_start": used,
            "weekly_stop": 20,
            "unit_seconds": 2220,
            "batch_seconds": 10800,
            "no_new_roles_or_permissions": True,
            "release": "NotR4/R5 or production; old2/4 and Reviewer negatives remain",
            "context_limit": "Input same complete module; not a context-trimming experiment. Output budget4096 unchanged",
        },
    )
    print("New four-cell function-output batch frozen, no live yet")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["checkpoint", "prepare", "run"])
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    if args.mode == "checkpoint":
        checkpoint()
    elif args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        N.run(
            args.cell,
            args.weekly_used,
            args.observed_at,
            batch=BATCH,
            order=ORDER,
            build_command=command,
        )
