"""Separately registered R3 replay with upstream origins and failure predicates.

Only experiment assembly changes. The hash-pinned old engine is reused with an
explicit output-directory binding; its source and all production code stay frozen.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_fixture_origin as O
import harness_r3_run as R

B, P = R.B, R.P
OLD = P.BATCH
PREVIOUS = OLD / "preparation-v2"
BATCH = B.KIT / "benchmarks/work/harness-convergence/r3-origin-fixed-20261015-1"
ORIGINS = {
    "repair": (
        B.KIT
        / "benchmarks/work/harness-convergence/r2-rendering-20261014-1/freeze.json",
        "json-1",
    ),
    "presence": (P.PRESENCE.parent.parent / "freeze.json", "presence-1"),
}


def origins():
    return {
        task: O.source_inputs(B.read(path)["cases"][case])
        for task, (path, case) in ORIGINS.items()
    }


def expected(task):
    prefix = "test_meaningful_assistant_text_across_all_messages"
    return {
        "exits": [0, 0, 1, 0] if task == "repair" else [1, 0, 0, 0],
        "tests": 11 if task == "repair" else 9,
        "failures": []
        if task == "repair"
        else [f"{prefix}[messages{i}-0.0]" for i in (1, 2, 3, 6)],
        "lint": [[B.SOURCE, "E501", 84, 101], [B.SOURCE, "E501", 90, 101]]
        if task == "repair"
        else [],
    }


def require_predicate(task, observation):
    want = expected(task)
    if observation != want:
        raise ValueError(
            f"Wrong initial failure predicate for {task}: {observation!r}, expected {want!r}"
        )


def check_start(name, phase):
    case = BATCH / "cases" / name
    root = case / "isolated"
    task = name.split("-")[0]
    O.require_origin(root, origins()[task])
    R.assert_files(root, B.read(BATCH / "prepared-cases.json")[name])
    output = case / phase
    output.mkdir(exist_ok=False)
    packet = B.read(root / ".agent/packet.json")
    commands = [
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *packet["focused_tests"],
            "--junitxml=" + str(output / "pytest.xml"),
            "--basetemp=" + str(output / "pytest-temp"),
        ],
        ["-m", "ruff", "format", "--check", "src", "tests"],
        ["-m", "ruff", "check", "--no-cache", "--output-format=json", "src", "tests"],
        ["-m", "pyright", "--pythonpath", str(P.PYTHON)],
    ]
    rows = [B.command([str(P.PYTHON), "-B", *args], cwd=root) for args in commands]
    B.save(output / "checks.json", rows)
    tree = ET.parse(output / "pytest.xml")
    tests = tree.findall(".//testcase")
    assert not tree.findall(".//error") and not tree.findall(".//skipped")
    lint = json.loads(rows[2]["stdout"])
    observation = {
        "exits": [row["exit_code"] for row in rows],
        "tests": len(tests),
        "failures": sorted(
            t.attrib["name"] for t in tests if t.find("failure") is not None
        ),
        "lint": sorted(
            [
                Path(row["filename"]).relative_to(root).as_posix(),
                row["code"],
                row["location"]["row"],
                row["location"]["column"],
            ]
            for row in lint
        ),
    }
    B.save(output / "predicate.json", observation)
    require_predicate(task, observation)
    O.require_origin(root, origins()[task])
    R.assert_files(root, B.read(BATCH / "prepared-cases.json")[name])
    print(name + " " + phase + " origin + failure predicate PASS", flush=True)


def prepare(used):
    assert 0 <= used < 30
    R.assert_files(
        B.KIT, B.read(PREVIOUS / "live-freeze-approved.json")["candidate_and_driver"]
    )
    BATCH.mkdir(exist_ok=False)
    # Preserve current state, including the entire invalid experiment, not its old pre-edit hashes.
    paths = {Path(p) for p in B.read(OLD / "baseline.json")}
    paths.update(B.files(OLD))
    tracked = B.command(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    assert tracked["exit_code"] == 0
    paths.update(B.KIT / p for p in tracked["stdout"].split("\0") if p)
    paths.add(B.KIT / ".local-agents/config.json")
    baseline = {}
    for index, path in enumerate(sorted(paths)):
        if path.is_file():
            baseline[str(path)] = B.sha(path)
        if index and index % 20000 == 0:
            print(f"Snapshot {index} paths", flush=True)
    B.save(BATCH / "baseline.json", baseline)
    B.save(
        BATCH / "environment.json",
        {
            "weekly_used": used,
            "ceiling": 30,
            "git_head": B.command(["git", "rev-parse", "HEAD"]),
            "git_status": B.command(["git", "status", "--short"]),
            "models": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
            "siblings": {
                repo: B.command(["git", "status", "--short"], cwd=B.KIT.parent / repo)
                for repo in ("agent-evaluation-harness", "agent-runtime-kit")
            },
        },
    )
    registration = B.read(PREVIOUS / "registration.json")
    registration.update(
        usage_start=used,
        prior_invalid_batch=str(OLD),
        experiment_change="Upstream pre-run source/test hash plus exact expected failure predicate before live; no candidate change",
        user_authorized=True,
        initial_predicates={t: expected(t) for t in ORIGINS},
        primary_active_seconds=None,
    )
    B.save(BATCH / "registration.json", registration)
    old_cases = B.read(PREVIOUS / "prepared-cases.json")
    cases = {}
    for name in P.ORDER:
        task = name.split("-")[0]
        old_root = PREVIOUS / "cases" / name / "isolated"
        source = (
            B.KIT
            / "benchmarks/work/harness-convergence/r2-rendering-20261014-1/cases/json-1/isolated"
            if task == "repair"
            else old_root
        )
        O.require_origin(source, origins()[task])
        root = BATCH / "cases" / name / "isolated"
        P.copy_inputs(source, root)
        R.assert_files(
            old_root,
            {
                p: h
                for p, h in old_cases[name].items()
                if p.startswith((".local-agents/", ".agent/"))
            },
        )
        shutil.copytree(
            old_root / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        packet = B.read(old_root / ".agent/packet.json")
        packet["run_id"] = "r3-origin-fixed-20261015-" + name
        B.save(root / ".agent/packet.json", packet)
        shutil.copyfile(old_root / ".agent/config.json", root / ".agent/config.json")
        O.require_origin(root, origins()[task])
        cases[name] = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
    B.save(BATCH / "prepared-cases.json", cases)
    B.save(
        BATCH / "origin-anchors.json",
        {
            "upstream": {
                task: {"path": str(path), "sha256": B.sha(path), "case": case}
                for task, (path, case) in ORIGINS.items()
            },
            "inputs": origins(),
        },
    )
    print("Registered corrected 12-cell batch; frozen candidate unchanged", flush=True)


def engine():
    # Explicit directory adapter, not an edit to the old engine or old evidence.
    R.BATCH = BATCH
    return R


def preflight():
    engine().preflight()
    for name in P.ORDER:
        check_start(name, "initial-controls")
    B.save(BATCH / "initial-controls-passed.json", {"all_12": True, "model_calls": 0})


def freeze():
    assert B.read(BATCH / "initial-controls-passed.json")["all_12"]
    for name in ("controls-5.xml", "regression-final-2.xml", "wire-control.xml"):
        tree = ET.parse(OLD / name)
        assert tree.findall(".//testcase") and not any(
            tree.findall(".//" + kind) for kind in ("failure", "error", "skipped")
        )
    controls = ET.parse(BATCH / "origin-controls.xml")
    assert len(controls.findall(".//testcase")) >= 10
    assert not any(
        controls.findall(".//" + kind) for kind in ("failure", "error", "skipped")
    )
    old = B.read(PREVIOUS / "live-freeze-approved.json")
    R.assert_files(B.KIT, old["candidate_and_driver"])
    assert B.read(PREVIOUS / "installation.json")["default_enabled"] is False
    for name, row in B.read(OLD / "holdouts-freeze.json")["cases"].items():
        R.assert_files(OLD / "holdouts-v2" / name, row["files"])
    paths = [
        "benchmarks/harness_r3_origin_fixed.py",
        "benchmarks/harness_fixture_origin.py",
        "benchmarks/harness_convergence.py",
        "tests/test_r3_origin_fixed.py",
    ]
    candidate = {**old["candidate_and_driver"], **{p: B.sha(B.KIT / p) for p in paths}}
    B.save(
        BATCH / "live-freeze-approved.json",
        {
            **old,
            "candidate_and_driver": candidate,
            "registration": B.sha(BATCH / "registration.json"),
            "prepared_cases": B.sha(BATCH / "prepared-cases.json"),
            "origin_anchors": B.sha(BATCH / "origin-anchors.json"),
            "initial_controls": B.sha(BATCH / "initial-controls-passed.json"),
            "no_new_candidate": True,
        },
    )
    print("Corrected batch live freeze sealed", flush=True)


def run(name, used):
    assert name in P.ORDER and 0 <= used < 30
    frozen = B.read(BATCH / "live-freeze-approved.json")
    R.assert_files(B.KIT, frozen["candidate_and_driver"])
    assert B.sha(BATCH / "origin-anchors.json") == frozen["origin_anchors"]
    assert B.sha(BATCH / "initial-controls-passed.json") == frozen["initial_controls"]
    anchors = B.read(BATCH / "origin-anchors.json")
    for row in anchors["upstream"].values():
        assert B.sha(Path(row["path"])) == row["sha256"]
    assert origins() == anchors["inputs"]
    for previous in P.ORDER[: P.ORDER.index(name)]:
        row = B.read(BATCH / "cases" / previous / "result.json")
        if "-candidate-" in previous:
            assert row["eligible_for_primary"], "Candidate gate unreachable"
            accepted = B.read(BATCH / "cases" / previous / "primary-decision.json")
            assert accepted["decision"] == "accept"
    check_start(name, "pre-invocation-controls")
    engine().run(name, used)


def preserve():
    drift = []
    baseline = B.read(BATCH / "baseline.json")
    for index, (name, digest) in enumerate(baseline.items()):
        path = Path(name)
        if not path.is_file() or B.sha(path) != digest:
            drift.append(name)
        if index and index % 20000 == 0:
            print(f"Audited {index} paths", flush=True)
    B.save(
        BATCH / "preservation.json",
        {
            "checked": len(baseline),
            "drift": drift,
            "passed": not drift,
            "at": time.time(),
        },
    )
    print(json.dumps({"checked": len(baseline), "drift": drift}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["prepare", "preflight", "freeze", "run", "preserve"]
    )
    parser.add_argument("--case")
    parser.add_argument("--used", type=int)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "run":
        run(args.case, args.used)
    else:
        globals()[args.action]()
