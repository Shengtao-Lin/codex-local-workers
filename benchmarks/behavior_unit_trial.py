"""Frozen exposed-draft design comparison, same managed runner and gates."""

import argparse
import copy
import json
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_run as RUN
import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F

BATCH = S.KIT / "benchmarks/work/harness-convergence/behavior-unit-20261018-1"
OLD = S.BATCH
DRAFTS = S.KIT / "benchmarks/work/harness-convergence/feedback-recovery-20261018-3"
ORDER = ["T1-A1", "T1-B1", "T2-B1", "T2-A1", "T1-B2", "T1-A2", "T2-A2", "T2-B2"]
IMPORTS = [
    ["collections.abc", "Iterator", None],
    ["collections.abc", "Sequence", None],
    ["typing", "cast", None],
]


def unit_argv(argv):
    if not isinstance(argv, (list, tuple)):
        return argv
    values = [str(a) for a in argv]
    old = str(S.KIT / "benchmarks/bounded_evidence_unit.py")
    if old in values:
        values[values.index(old)] = str(S.KIT / "benchmarks/behavior_unit_unit.py")
    return values


def prepare(used):
    pins = dict(S.read(OLD / "registration-v2-draft.json")["pins"])
    assert all(S.sha(p) == sha for p, sha in pins.items())
    for name in [
        "benchmarks/behavior_unit_candidate.py",
        "benchmarks/behavior_unit_entry.py",
        "benchmarks/behavior_unit_unit.py",
        "benchmarks/behavior_unit_trial.py",
        "tests/test_behavior_unit_candidate.py",
        "docs/behavior-unit-diagnostic.md",
    ]:
        pins[str(S.KIT / name)] = S.sha(S.KIT / name)
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], cwd=S.KIT
        )
        .decode()
        .split("\0")
    )
    S.save(
        BATCH / "baseline.json",
        {
            "weekly_used": used,
            "stop_used": 20,
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "files": {
                p: S.sha(S.KIT / p) for p in names if p and (S.KIT / p).is_file()
            },
            "residency": "Muse only 24576/parallel1, no running Python batch",
        },
    )
    S.save(BATCH / "candidate-freeze.json", {"pins": pins})
    tasks = copy.deepcopy(S.read(OLD / "task-freeze-v4.json")["tasks"])
    old_cells = S.read(OLD / "cells-v4.json")
    for topic in ("T1", "T2"):
        info = tasks[topic]
        source = DRAFTS / "templates" / topic
        root = BATCH / "templates" / topic
        shutil.copytree(source, root)
        info["root"] = str(root)
        info["inputs"]["src/product/code.py"] = S.sha(root / "src/product/code.py")
        if topic == "T2":
            contract = T.TASKS[topic]["contract"].replace(
                "no other code/signature changes.",
                "no unrelated behavior or signature changes. Approved unit imports may adjust only existing collections.abc.Iterator/Sequence and typing.cast imports; no new dependencies or aliases.",
            )
            T.TASKS[topic] = {**T.TASKS[topic], "contract": contract}
            info["contract"] = contract
    S.BATCH = BATCH
    T.WORK, T.SUFFIX, T.ORDER = BATCH, "-prepared", ORDER
    T.prepare_cells(tasks)
    cells = S.read(BATCH / "cells-prepared.json")
    for cell, row in cells.items():
        root = Path(row["root"])
        identity = {
            "task_id": "behavior-" + row["task"],
            "unit_id": "behavior-" + row["task"],
            "run_id": "behavior-20261018-" + cell,
        }
        for relative in (".agent/packet.json", F.POLICY_PATH):
            path = root / relative
            data = S.read(path)
            if relative == F.POLICY_PATH:
                data["identity"] = identity
            else:
                data.update(identity)
                data["feature_id"] = "behavior-" + row["task"]
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            row["files"][relative] = S.sha(path)
        row["capture_policy_sha256"] = S.sha(root / F.POLICY_PATH)
        config_path = root / ".agent/config.json"
        config = S.read(config_path)
        config.update(
            experimental_bounded_evidence="A",
            experimental_behavior_unit=row["arm"] == "B",
            experimental_approved_imports=IMPORTS if row["task"] == "T2" else [],
        )
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        row["files"][".agent/config.json"] = S.sha(config_path)
        row["private_tests"] = old_cells[row["task"] + "-A1"]["private_tests"]
        checked = T.run(
            [
                S.PYTHON,
                "-B",
                S.KIT / "benchmarks/behavior_unit_entry.py",
                "--runtime-dir",
                root / ".local-agents",
                "--capture-policy-sha256",
                row["capture_policy_sha256"],
                "--preflight-only",
                "--packet",
                root / ".agent/packet.json",
                "--config",
                config_path,
            ],
            root,
        )
        S.save(BATCH / "preflight" / (cell + ".json"), checked)
        assert checked["exit_code"] == 0, checked
    S.save(BATCH / "cells.json", cells)
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "pins": pins,
            "cells_sha256": S.sha(BATCH / "cells.json"),
            "weekly_stop": 20,
            "registered": 8,
            "exposure": "EXPOSED frozen repair drafts, not transfer",
            "arms": {
                "A": "function-only/fail-fast",
                "B": "approved behavior unit/complete diagnostics",
            },
            "core_budget": {
                "requests": 12,
                "output_each": 4096,
                "edits": 3,
                "initial_checks": 1,
                "post_edit_checks": 3,
                "formatter": 1,
                "protocol_recoveries": 2,
                "noop_stop": 2,
                "seconds": 900,
                "supplemental_commands": 16,
                "all_configured_commands_conservative": 32,
            },
            "gate": "B>=3/4 finalaccepted and B>A, both tasks accepted, zero falsepass; diagnostic value only",
            "continue_rule": "ordinary failure HOLD but finish; infra/safety/drift/20% stop; no replacements",
            "model": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "single_resident": True,
            },
            "authority": "User approved behavior-unit/import and complete trusted diagnostic experiment; no production changes",
            "task_contracts": {t: T.TASKS[t]["contract"] for t in ("T1", "T2")},
        },
    )


def run(cell, used, at):
    S.BATCH = BATCH
    RUN.REGISTRATION = BATCH / "registration.json"
    original_read = S.read

    def read(path):
        return original_read(
            BATCH / "cells.json" if Path(path) == BATCH / "cells-v4.json" else path
        )

    S.read = read

    def authorize(_approval, observed, when):
        assert 0 <= observed < 20 and 0 <= time.time() - when <= 120
        reg = S.read(RUN.REGISTRATION)
        assert S.sha(BATCH / "cells.json") == reg["cells_sha256"]
        suites = ET.parse(BATCH / "controls-v3.xml").getroot().iter("testsuite")
        assert all(
            int(s.get("failures", 0)) == int(s.get("errors", 0)) == 0 for s in suites
        )

    RUN.authorize = authorize
    original_popen = subprocess.Popen

    def popen(argv, *args, **kwargs):
        actual = unit_argv(argv)
        if actual != argv:
            S.save(
                BATCH / "live-results" / cell / "actual-launch.json", {"argv": actual}
            )
        return original_popen(actual, *args, **kwargs)

    subprocess.Popen = popen
    return RUN.run_cell(cell, BATCH / "registration.json", used, at)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("--cell")
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--usage-observed-at", type=float)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
        print("Eight frozen units prepared; no live")
    else:
        result = run(args.cell, args.weekly_used, args.usage_observed_at)
        print(result["cell"], "stop_batch=", result["stop_batch"])
