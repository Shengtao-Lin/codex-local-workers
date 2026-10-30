"""Narrow exposed-draft experiment; reuse preparation, runner and canonical gates."""

import argparse
import copy
import json
import shutil
import subprocess
import time
from pathlib import Path

import bounded_evidence_run as RUN
import bounded_evidence_support as S
import bounded_evidence_tasks as T

OLD = S.BATCH
BATCH = S.KIT / "benchmarks/work/harness-convergence/feedback-recovery-20261018-1"
ORDER = ["T1-A1", "T1-B1", "T2-B1", "T2-A1", "T1-B2", "T1-A2", "T2-A2", "T2-B2"]


def prepare():
    old_registration = S.read(OLD / "registration-v2-draft.json")
    pins = dict(old_registration["pins"])
    assert all(S.sha(p) == sha for p, sha in pins.items()), "Historical candidate drift"
    for name in (
        "benchmarks/feedback_receipt_candidate.py",
        "benchmarks/feedback_receipt_entry.py",
        "benchmarks/feedback_receipt_unit.py",
        "benchmarks/feedback_recovery_trial.py",
        "tests/test_feedback_receipt.py",
        "docs/feedback-recovery-diagnostic.md",
    ):
        pins[str(S.KIT / name)] = S.sha(S.KIT / name)
    baseline_names = (
        subprocess.check_output(
            ["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], cwd=S.KIT
        )
        .decode()
        .split("\0")
    )
    S.save(
        BATCH / "baseline.json",
        {
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "weekly_used": 10,
            "stop_used": 20,
            "files": {
                p: S.sha(S.KIT / p)
                for p in baseline_names
                if p and (S.KIT / p).is_file()
            },
            "model_residency": "Muse only, Q4_K_M/context24576/parallel1; no Python batch process",
            "authorization": "Latest user explicitly authorizes autonomous experiments and iteration until critical decision or20%used",
        },
    )
    S.save(BATCH / "candidate-freeze.json", {"pins": pins})
    tasks = copy.deepcopy(S.read(OLD / "task-freeze-v4.json")["tasks"])
    old_cells = S.read(OLD / "cells-v4.json")
    sources = {"T1": "T1-A2", "T2": "T2-A1"}
    for topic, cell in sources.items():
        info = tasks[topic]
        template = BATCH / "templates" / topic
        shutil.copytree(
            info["root"],
            template,
            ignore=shutil.ignore_patterns("__pycache__", ".ruff_cache"),
        )
        draft = Path(old_cells[cell]["root"]) / "src/product/code.py"
        recorded = S.read(OLD / "live-results" / cell / "result.json")[
            "final_source_sha256"
        ]
        assert S.sha(draft) == recorded
        shutil.copyfile(draft, template / "src/product/code.py")
        info["root"] = str(template)
        info["draft_origin"] = {"cell": cell, "sha256": recorded, "exposure": "EXPOSED"}
        info["inputs"]["src/product/code.py"] = recorded
    S.BATCH = BATCH
    T.WORK, T.SUFFIX, T.ORDER = BATCH, "-v4", ORDER
    T.prepare_cells(tasks)
    cells = S.read(BATCH / "cells-v4.json")
    for cell, row in cells.items():
        root = Path(row["root"])
        identity = {
            "task_id": "receipt-" + row["task"],
            "unit_id": "receipt-" + row["task"],
            "run_id": "receipt-20261018-" + cell,
        }
        packet_path = root / ".agent/packet.json"
        packet = S.read(packet_path)
        packet.update(identity)
        packet["feature_id"] = "receipt-" + row["task"]
        packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        policy_path = root / T.F.POLICY_PATH
        policy = S.read(policy_path)
        policy["identity"] = identity
        policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        row["capture_policy_sha256"] = S.sha(policy_path)
        row["files"][".agent/packet.json"] = S.sha(packet_path)
        row["files"][T.F.POLICY_PATH] = S.sha(policy_path)
        config_path = root / ".agent/config.json"
        config = S.read(config_path)
        config["experimental_bounded_evidence"] = "A"
        config["experimental_explicit_noop_receipt"] = cell.split("-")[1][0] == "B"
        # These are unexecuted new inputs, not historical archives.
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        row["files"][".agent/config.json"] = S.sha(config_path)
        row["private_tests"] = old_cells[sources[row["task"]]]["private_tests"]
        preflight = T.run(
            [
                S.PYTHON,
                "-B",
                S.KIT / "benchmarks/feedback_receipt_entry.py",
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
        S.save(BATCH / "preflight" / (cell + ".json"), preflight)
        assert preflight["exit_code"] == 0, preflight
    S.save(BATCH / "cells-receipt.json", cells)
    registration = {
        "order": ORDER,
        "pins": pins,
        "weekly_stop": 20,
        "budget": {
            "requests": 12,
            "effective_edits": 3,
            "post_edit_checks": 3,
            "initial_checks": 1,
            "protocol_recoveries": 2,
            "formatter": 1,
            "noop_stop": 2,
            "seconds": 900,
        },
        "arms": {
            "A": "old feedback, proposal only",
            "B": "explicit no_op receipt, proposal only",
        },
        "tasks": {k: tasks[k] for k in sources},
        "cells_sha256": S.sha(BATCH / "cells-receipt.json"),
        "gate": "B>=3/4finalaccepted, B>A, both tasks accepted, zero false pass; diagnostic value only notR4",
        "ordinary_failure": "HOLD but finish fixed order; no replacement or retry packet",
        "reviewer_controls": "One frozen correct and one known null regression, unchanged Reviewer, separate denominator",
        "model": {
            "coder": "qwen/qwen3-coder-30b",
            "reviewer": "meta/muse-glimmer",
            "single_resident": True,
        },
        "authority": "Current user authorizes this autonomous bounded stage; no role/default/scope change",
    }
    S.save(BATCH / "registration.json", registration)


def run(cell, used, observed):
    S.BATCH = BATCH
    RUN.REGISTRATION = BATCH / "registration.json"
    original_read = S.read

    def read(path):
        return original_read(
            BATCH / "cells-receipt.json"
            if Path(path) == BATCH / "cells-v4.json"
            else path
        )

    S.read = read

    def authorize(_approval, actual, at):
        assert 0 <= actual < 20 and 0 <= time.time() - at <= 120, (
            "Fresh usage below20% required"
        )
        reg = S.read(RUN.REGISTRATION)
        assert S.sha(BATCH / "cells-receipt.json") == reg["cells_sha256"]
        controls = (BATCH / "controls-v2.xml").read_text(encoding="utf-8")
        import xml.etree.ElementTree as ET

        suites = ET.fromstring(controls).iter("testsuite")
        assert all(
            int(s.get("errors", 0)) == int(s.get("failures", 0)) == 0 for s in suites
        )

    RUN.authorize = authorize
    original_run = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(x) for x in argv]
        old = str(S.KIT / "benchmarks/bounded_evidence_unit.py")
        if old in argv:
            argv[argv.index(old)] = str(S.KIT / "benchmarks/feedback_receipt_unit.py")
        return original_run(argv, *args, **kwargs)

    subprocess.run = dispatch
    return RUN.run_cell(cell, BATCH / "registration.json", used, observed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell")
    parser.add_argument("--weekly-used", type=int)
    parser.add_argument("--usage-observed-at", type=float)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
        print("Eight exposed-draft pairs prepared; no live")
    else:
        result = run(args.cell, args.weekly_used, args.usage_observed_at)
        print(result["cell"], "stop_batch=", result["stop_batch"])
