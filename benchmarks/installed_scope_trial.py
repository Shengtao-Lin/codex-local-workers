"""Frozen repairs and real-source transfer through the installed bounded entry."""

import argparse
import json
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import limited_family_trial as L
import normal_task_trial as N

sys.path.insert(0, str(S.KIT / "tests"))
from test_installable_bounded import project

BASE = S.KIT / "benchmarks/work/harness-convergence"
BATCH = BASE / "installed-repair-20261021-3"
ORDER = ["static-1", "behavior-1", "behavior-2", "static-2"]
STARTS = {
    "static": """def merge_labels(defaults: dict[str, str], overrides: dict[str, str | None]) -> dict[str, str]:
    output = dict(defaults)
    for key, value in overrides.items():
        if value is None:
            output.pop(key, None)
        else:
            output[key] = value
    return result
""",
    "behavior": """def unique_records(records: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    by_key = {record[key]: record for record in records}
    return list(by_key.values())
""",
}


def command(root, mode="unit", replay=None):
    args = [
        S.PYTHON,
        "-B",
        root / ".local-agents/local-bounded-unit.py",
        "--mode",
        mode,
        "--packet",
        root / ".agent/packet.json",
        "--config",
        root / ".agent/config.json",
        "--report",
        root / ".agent/unit-report.json",
    ]
    if mode == "unit":
        args += [
            "--review-report",
            root / ".agent/reviewer-report.json",
            "--summary",
            root / ".agent/unit-summary.json",
        ]
    if replay:
        args += ["--replay", replay]
    return [str(value) for value in args]


def gate():
    path = BASE / "installable-bounded-20261021-1/controls-5.xml"
    suites = ET.parse(path).getroot().findall("testsuite")
    assert suites and all(
        int(s.get("failures", 0)) == int(s.get("errors", 0)) == 0 for s in suites
    )


def refresh_material(root, config):
    # Same observation function and schema, supplied by the installed distribution.
    for filename in ("capture_validation_facts.py", "reviewer_capture_envelope.py"):
        shutil.copyfile(
            root / ".local-agents/bounded" / filename, root / "acceptance" / filename
        )
    policy_path = root / "acceptance/capture-policy.json"
    policy = S.read(policy_path)
    policy["producer_sha256"] = S.sha(root / policy["producer_path"])
    policy["helper_sha256"] = S.sha(root / policy["helper_path"])
    policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    config["experimental_capture_policy_sha256"] = S.sha(policy_path)


def prepare(used):
    gate()
    assert 0 <= used < 50
    rows = {}
    for cell in ORDER:
        family = cell.split("-")[0]
        topic = "labels" if family == "static" else "unique"
        with tempfile.TemporaryDirectory(prefix="worker-repair-install-") as directory:
            staging = Path(directory)
            packet, config = project(staging, topic, BATCH.name + "-" + cell)
            root = BATCH / "cells" / cell / "isolated"
            shutil.copytree(staging, root)
        target = "src/product/code.py"
        (root / target).write_text(
            L.TASKS[topic]["header"] + "\n\n" + STARTS[family], encoding="utf-8"
        )
        formatted = T.run(
            [S.PYTHON, "-B", "-m", "ruff", "format", "src", "tests"], root
        )
        assert formatted["exit_code"] == 0
        packet["primary_plan_sha256"] = S.sha(__file__)
        (root / ".agent/packet.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8"
        )
        refresh_material(root, config)
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        # Verify the starting failure is genuine and not a zero-test setup error.
        initial = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], root)
        S.save(BATCH / "initial-controls" / (cell + ".json"), initial)
        assert initial["exit_code"] == 1 and " failed" in initial["stdout"]
        preflight = command(root, "preflight")
        preflight[preflight.index("--report") + 1] = root / ".agent/preflight.json"
        control = T.run(preflight, root)
        S.save(BATCH / "preflight" / (cell + ".json"), control)
        assert control["exit_code"] == 0
        if cell.endswith("-1"):
            proof = BATCH / "full-chain-replay" / family / "isolated"
            shutil.copytree(root, proof)
            replay = proof.parent / "reference.json"
            S.save(replay, [{"replacement": L.TASKS[topic]["reference"]}])
            result = T.run(command(proof, replay=replay), proof, timeout=180)
            S.save(proof.parent / "process.json", result)
            assert result["exit_code"] == 0
        rows[cell] = {
            "root": str(root),
            "topic": topic,
            "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
            "target": target,
            "private_tests": str(L.BATCH / "private" / topic / "test_independent.py"),
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
                and not any(
                    v in p.parts
                    for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
                )
            },
        }
    S.save(BATCH / "cells.json", rows)
    paths = [
        Path(__file__),
        S.KIT / "tests/test_installable_bounded.py",
        BATCH / "cells.json",
    ]
    paths += [
        p
        for p in (S.KIT / ".local-agents").rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    paths += [
        S.KIT / "benchmarks" / name
        for name in (
            "normal_task_trial.py",
            "supervised_record.py",
            "capture_fixture_support.py",
            "bounded_evidence_support.py",
            "bounded_evidence_tasks.py",
            "limited_family_trial.py",
        )
    ]
    paths += list((L.BATCH / "private").rglob("*.py"))
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 4,
            "weekly_used_start": used,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "pins": {str(p): S.sha(p) for p in paths},
            "candidate": "Installed default-off bounded-v1 with same rules, checks and contract-first Reviewer; installed fact producer, no historical provider",
            "gate": "4/4 independent complete accepts, each error family2/2, no Primary semantic hints/code takeover/safety drift",
            "continue_rule": "Ordinary failure HOLD but complete fixed order; infrastructure/safety/drift/time/weekly50 stop; no replacements",
            "risk": "high feature/unit/integration, unchanged public behavior contracts and protection tests",
            "models": "Unchanged Qwen/Muse, single residency",
            "budget": "12 requests,3effective edits,1initial+3post checks,900s; Reviewer16requests/4errors/600s;4096 output",
            "exposure": "Exposed contracts, controlled prebuilt wrong drafts; not new holdout or independent algorithm discovery. Static starter includes a prepared algorithm with one undefined return name; preparation cost retained.",
            "Primary": "Prepared error snapshots and contracts; no runtime hints, source fixes or automatic Reviewer-to-Coder rework",
        },
    )
    print("Four installed-entry repair units frozen after all offline gates")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        N.run(
            args.cell,
            args.weekly_used,
            args.observed_at,
            batch=BATCH,
            order=ORDER,
            build_command=command,
            usage_limit=50,
            batch_seconds=10800,
        )
