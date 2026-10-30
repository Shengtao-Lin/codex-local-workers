"""Audit and freeze a real failure; matched semantic-guidance recovery experiments."""

import argparse
import copy
import json
import shutil

import real_selection_trial as selection
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read
from layer_isolation import command, verify_hashes

BASE = WORK / "limit-recovery-1"
FROZEN = KIT / "benchmarks/fixtures/limit-recovery-v1"
SOURCE = KIT.parent / "agent-evaluation-harness"
TASK = SOURCE / ".agent/tasks/limit-selection-20261008"
SNAPSHOT = selection.live.SNAPSHOT
PYTHON = SOURCE / ".venv/Scripts/python.exe"
COMMON = selection.COMMON
EXTRA = "tests/unit/test_limit_recovery.py"
SUPPORT = KIT / "benchmarks/fixtures/limit-recovery-extra/test_limit_recovery.py"
ARMS = ("control-1", "semantic-1", "semantic-2")
EXAMPLE = (
    "Concrete acceptance example, not a prescribed code shape: three distinct objects A,B,C have "
    "equal timestamp and equal identity. oldest limit2 returns A,B; newest limit2 returns C,B, "
    "not A,B. Original positions are 0,1,2. Ascending whole-key order is A,B,C; descending whole-key "
    "order is C,B,A. Do not negate datetime or string keys, compare payloads, or repeatedly search "
    "the input for positions. Position bookkeeping must use bounded linear work, preserve each "
    "occurrence, and leave precomputed callbacks and other policies unchanged. A native heap helper "
    "is allowed; the observable contract and protected tests decide equivalence."
)


def freeze():
    BASE.mkdir(parents=True, exist_ok=False)
    FROZEN.mkdir(parents=True, exist_ok=False)
    provenance = read(selection.FROZEN / "provenance.json")
    paths = list(provenance["original_files"])
    for path in paths:
        target = FROZEN / path
        target.parent.mkdir(parents=True, exist_ok=True)
        # Historical preimage is the canonical optimization baseline, not current broken sibling.
        src = SOURCE / path
        if path == COMMON:
            src = TASK / "runs/limit-selection-20261008-a1/preimages" / path
        shutil.copyfile(src, target)
    acceptance = "tests/unit/test_limit_selection_acceptance.py"
    shutil.copyfile(SOURCE / acceptance, FROZEN / acceptance)
    shutil.copyfile(SUPPORT, FROZEN / EXTRA)
    paths += [acceptance, EXTRA]
    shutil.copytree(TASK, BASE / "historical-task")
    observations = []
    for run in sorted((TASK / "runs").iterdir()):
        packet = read(run / "packet.json")
        events = [
            json.loads(line)
            for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        attempts = []
        for path in sorted(run.glob("validation-attempt-*.json")):
            value = read(path)
            attempts.append(
                {
                    "path": str(path),
                    "sha256": digest(path),
                    "attempt": value["attempt"],
                    "edit_revision": value["edit_revision"],
                    "validation": value["validation"],
                }
            )
        observations.append(
            {
                "run": run.name,
                "packet": packet,
                "validations": attempts,
                "primary_review": read(run / "review.json"),
                "diff": (run / "cumulative.diff").read_text(encoding="utf-8"),
                "events": events,
                "max_context": max(
                    (
                        e["facts"].get("reported_context_utilization", 0)
                        for e in events
                        if e["event"] == "model_request"
                    ),
                    default=0,
                ),
            }
        )
    write(
        BASE / "historical-audit.json",
        {
            "observations": observations,
            "finding": "Algorithm/type/callback failures progress to reversed equal-key failure; negative index and quadratic search; repeated no-op refused. Contracts preserved; no context overflow evidence.",
            "history_hashes": {
                str(p.relative_to(TASK)): digest(p)
                for p in TASK.rglob("*")
                if p.is_file()
            },
        },
    )
    write(
        FROZEN / "provenance.json",
        {
            "files": {p: digest(FROZEN / p) for p in paths},
            "sibling_current_hashes": {
                p: digest(SOURCE / p) for p in provenance["original_files"]
            },
            "history": str(BASE / "historical-task"),
            "original_failed_calls": 3,
            "new_protected_test_sha256": digest(SUPPORT),
        },
    )
    write(
        BASE / "registration.json",
        {
            "arms": list(ARMS),
            "start": "Exact third-call broken source in independent roots",
            "difference": "Only advisory semantic example; same hard contract/tests/environment/model/budget",
            "weekly_used_start": 11,
            "weekly_ceiling": 15,
            "coordinator": False,
            "limits": "One control and two guided repeats, not statistical proof or restored original success",
            "strict_checks": "Original Ruff rules and strict Pyright on changed selection module; not whole-project qualification",
        },
    )
    print(json.dumps({"frozen": str(FROZEN), "historical_calls": len(observations)}))


def prepare(arm, *, clean_start=False, start_source=None, config_overrides=None):
    root = BASE / arm
    root.mkdir(parents=True, exist_ok=False)
    provenance = read(FROZEN / "provenance.json")
    verify_hashes(FROZEN, provenance["files"])
    for path in provenance["files"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / path, target)
    initial_source = start_source or (
        FROZEN / COMMON if clean_start else SOURCE / COMMON
    )
    shutil.copyfile(initial_source, root / COMMON)
    config = read(TASK / "config.json")
    config.update(config_overrides or {})
    config["coordinator_enabled"] = False
    config["python"] = str(PYTHON)
    profile = config["validation_profiles"]["project-strict"]
    profile["python"] = str(PYTHON)
    profile["pytest_argv"] = [
        "-B",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--basetemp=" + str(root / ".agent/test-temp"),
    ]
    profile["commands"] = [
        {
            "id": "ruff-format",
            "argv": [
                "{python}",
                "-B",
                "-m",
                "ruff",
                "format",
                "--check",
                "src",
                "tests",
            ],
        },
        {
            "id": "ruff-check",
            "argv": ["{python}", "-B", "-m", "ruff", "check", "src", "tests"],
        },
        {
            "id": "pyright",
            "argv": [
                "{python}",
                "-B",
                "-m",
                "pyright",
                "--project",
                ".agent/pyright.json",
                "--pythonpath",
                str(PYTHON),
            ],
        },
    ]
    write(root / ".agent/config.json", config)
    write(
        root / ".agent/pyright.json",
        {
            "include": ["../" + COMMON],
            "extraPaths": ["../src"],
            "typeCheckingMode": "strict",
            "pythonVersion": "3.11",
        },
    )
    packet = copy.deepcopy(read(TASK / "runs/limit-selection-20261008-a3/packet.json"))
    identity = BASE.name + "-" + arm
    packet = {k: v for k, v in packet.items() if not k.startswith("_")}
    for key in ("parent_run_id", "preserve_contract", "primary_plan_sha256"):
        packet.pop(key, None)
    packet.update(
        task_id=identity,
        feature_id=identity,
        run_id=identity + "-a1",
        attempt=1,
        packet_revision=1,
        plan_revision=1,
    )
    packet["scope"]["read"] = ["src", "tests"]
    packet["scope"]["readonly"] = [
        p
        for p in provenance["files"]
        if p != COMMON and p.startswith(("src/", "tests/"))
    ]
    packet["focused_tests"].append(EXTRA)
    packet["required_behavior"].append(
        {
            "id": "position-cost",
            "risk_floor": "medium",
            "text": "Position bookkeeping must not repeatedly linearly search the input; on 512 equal-timestamp unique-key records k8, fewer than 8192 identity equality comparisons in either order. Preserve duplicate occurrences and original input positions.",
        }
    )
    packet["owned_contract_ids"].append("position-cost")
    packet["implementation_guidance"] = []
    if clean_start:
        packet["review_feedback"] = [
            {
                "finding_id": "stable-selection-semantic-check",
                "contract_id": "limit-equivalence",
                "source_anchor": "select_records",
                "verify_in_review": True,
                "text": "Review the changed function and protected ties/callback/cost tests. Verify oldest stable and newest reverse-stable occurrence order, payload exclusion from comparison, all callbacks before comparison and bounded position bookkeeping. An anchor or passing test alone is not semantic proof.",
            }
        ]
    if arm.startswith("semantic"):
        packet["implementation_guidance"] = [EXAMPLE]
    load_worker(SNAPSHOT).validate_packet(packet)
    write(root / ".agent/packet.json", packet)
    write(
        root / ".agent/manifest.json",
        {
            "files": {p: digest(root / p) for p in provenance["files"]},
            "packet_sha256": digest(root / ".agent/packet.json"),
            "config_sha256": digest(root / ".agent/config.json"),
        },
    )
    tests = command(
        root,
        [
            str(PYTHON),
            "-B",
            "-m",
            "pytest",
            *packet["focused_tests"],
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=" + str(root / ".agent/baseline-temp"),
            "--junitxml=" + str(root / ".agent/baseline.xml"),
        ],
    )
    write(root / ".agent/baseline.json", tests)
    print(
        json.dumps(
            {
                "root": str(root),
                "baseline_exit": tests["exit"],
                "output": tests["output"][-650:],
            }
        )
    )


def run(arm):
    root = BASE / arm
    result = command(
        root,
        [
            str(PYTHON),
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/packet.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ],
        timeout=1500,
    )
    write(root / ".agent/invocation.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "prepare", "run"))
    parser.add_argument("--arm", choices=ARMS)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze()
    elif args.action == "prepare":
        prepare(args.arm)
    else:
        run(args.arm)
