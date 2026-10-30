"""Create-only real host controls on an exposed frozen project; ZERO inference."""

import copy
import os
import shutil
import subprocess
import sys
from pathlib import Path

import bounded_evidence_support as S
import project_caller_trial as J

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-bridge-host-20261023-2"
ORIGIN = BATCH.parent / "strata-complex-20261023-2"
TARGET = "src/evaluation_harness/adapters/common.py"
CASES = ["read-edit-check", "forbidden-read", "stale-version", "wrong-target"]


def run(argv, root):
    result = subprocess.run(
        [str(v) for v in argv],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        check=False,
    )
    return {
        "argv": [str(v) for v in argv],
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main():
    assert not BATCH.exists(), "Create-only control batch"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    prior = S.read(ORIGIN / "registration.json")
    assert all(S.sha(p) == h for p, h in prior["pins"].items())
    S.save(
        BATCH / "registration.json",
        {
            "batch_id": BATCH.name,
            "type": "offline_native_to_real_installed_host",
            "cases": CASES,
            "weekly_cap": 40,
            "weekly_used_start": 34,
            "model_calls": 0,
            "sdk_profiles": 0,
            "old_capture_profile_unchanged": True,
            "gate": "Real read/proposal/check/canonical handoff; forbidden read/stale hash/wrong target rejected; final handoff rejects incomplete or stale evidence",
            "exposure": "Existing raw parser task/reference, offline harness control NOT model/task qualification",
            "pins": {
                str(p): S.sha(p)
                for p in [
                    Path(__file__),
                    Path(__file__).with_name("strata_bridge_host.py"),
                    Path(__file__).with_name("strata_native_replay.mjs"),
                    Path(__file__).with_name("strata_kit_tool_bridge.mjs"),
                ]
            },
            "scope": "New isolated copies only, historical source/runtime/model/defaults untouched",
        },
    )
    rows = []
    for case in CASES:
        root = BATCH / case / "isolated"
        J.copy_project(ORIGIN / "templates/raw", root)
        installed = ORIGIN / "cells/raw-1/isolated"
        shutil.copytree(installed / ".local-agents", root / ".local-agents")
        shutil.copyfile(installed / "AGENTS.md", root / "AGENTS.md")
        identity = {
            k: BATCH.name + "-" + case for k in ("task_id", "unit_id", "run_id")
        }
        packet = {**S.read(installed / ".agent/packet.json"), **identity}
        config = S.read(installed / ".agent/config.json")
        for name, value in [
            ("packet", packet),
            ("config", config),
            ("capture-spec", S.read(installed / ".agent/capture-spec.json")),
        ]:
            S.save(root / f".agent/{name}.json", value)
        prepare = run(
            [
                S.PYTHON,
                "-B",
                root / ".local-agents/local-bounded-prepare.py",
                "--packet",
                ".agent/packet.json",
                "--config",
                ".agent/config.json",
                "--capture-spec",
                ".agent/capture-spec.json",
                "--apply",
            ],
            root,
        )
        S.save(root.parent / "prepare.json", prepare)
        assert prepare["exit_code"] == 0, prepare
        proposal = {
            "name": "kit_propose",
            "arguments": {
                "path": TARGET,
                "expected_sha256": "@current",
                "content": J.function_source(
                    ORIGIN / "references/raw" / TARGET, "mapping_raw"
                ),
            },
        }
        if case == "read-edit-check":
            actions = [
                {
                    "name": "kit_read",
                    "arguments": {
                        "path": "src/evaluation_harness/canonical/models.py",
                        "start_line": 1,
                        "end_line": 20,
                    },
                },
                proposal,
            ]
        elif case == "forbidden-read":
            actions = [
                {
                    "name": "kit_read",
                    "arguments": {
                        "path": ".agent/packet.json",
                        "start_line": 1,
                        "end_line": 2,
                    },
                }
            ]
        else:
            actions = [copy.deepcopy(proposal)]
            if case == "stale-version":
                actions[0]["arguments"]["expected_sha256"] = "f" * 64
            else:
                actions[0]["arguments"]["path"] = "tests/unit/test_local_worker_raw.py"
        program = root.parent / "native-program.json"
        S.save(program, actions)
        prepared = root / ".agent/prepared" / identity["run_id"]
        result = run(
            [
                S.PYTHON,
                "-B",
                Path(__file__).with_name("strata_bridge_host.py"),
                "--packet",
                prepared / "packet.json",
                "--config",
                prepared / "config.json",
                "--program",
                program,
            ],
            root,
        )
        S.save(root.parent / "process.json", result)
        assert (root / ".agent/native-host-summary.json").exists(), result
        summary = S.read(root / ".agent/native-host-summary.json")
        rows.append({"case": case, **summary, "root": str(root)})
        actual = summary["actual"]
        assert actual["model_requests"] == 0
        if case == "read-edit-check":
            assert result["exit_code"] == 0 and summary["host_handoff_verified"], result
            assert actual["requests"] == 2 and actual["evidence_actions"] == 1
            assert actual["edits"] == actual["post_edit_checks"] == 1
        else:
            assert result["exit_code"] != 0 and not summary["host_handoff_verified"], (
                result
            )
            assert (
                summary["status"] == "policy_violation"
                and actual["edits"] == actual["post_edit_checks"] == 0
            )
            assert S.sha(root / TARGET) == S.sha(ORIGIN / "templates/raw" / TARGET)
        print(case + ": " + summary["status"], flush=True)
    S.save(BATCH / "results.json", rows)
    # Independently authenticate actual canonical handoff; forged convenience
    # summaries or report statuses must not grant acceptance.
    root = Path(rows[0]["root"])
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F

    gate = F.load(root / ".local-agents/local-unit.py", "bridge_control_gate")
    report = S.read(root / ".agent/native-host-report.json")
    config = S.read(root / ".agent/prepared" / report["run_id"] / "config.json")
    gate.verify_handoff(root, report, config=config)
    independent = [
        J.run_check(
            [
                S.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "tests",
                ORIGIN / "private/raw/test_independent.py",
            ],
            root,
        ),
        J.run_check(
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"], root
        ),
        J.run_check([S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root),
        J.run_check([S.PYTHON, "-B", "-m", "pyright"], root),
    ]
    S.save(BATCH / "independent-checks.json", independent)
    assert all(c["exit_code"] == 0 for c in independent), independent
    bad = copy.deepcopy(report)
    bad["validation"]["configured_checks"] = []
    # Canonical validation, not convenience summaries, is authoritative.
    gate.verify_handoff(root, bad, config=config)
    S.save(
        BATCH / "convenience-control.json",
        {
            "status": "PASS",
            "reason": "Summary mutation ignored; valid unchanged canonical evidence still required",
        },
    )
    rejected = []
    archive = root / ".agent/tasks" / report["task_id"] / "runs" / report["run_id"]
    packet = S.read(archive / "packet.json")
    handoff = S.read(archive / "handoff.json")
    validation = S.read(archive / "validation.json")
    bad_validation = copy.deepcopy(validation)
    bad_validation["configured_checks"] = []
    try:
        gate.HOST.verify(root, archive, packet, handoff, bad_validation, config)
    except (ValueError, RuntimeError) as exc:
        rejected.append({"case": "missing_checks", "reason": str(exc)})
    assert len(rejected) == 1
    bad_validation = copy.deepcopy(validation)
    bad_validation["focused_tests"]["junit"]["executed"] = 0
    try:
        gate.HOST.verify(root, archive, packet, handoff, bad_validation, config)
    except (ValueError, RuntimeError) as exc:
        rejected.append({"case": "zero_tests", "reason": str(exc)})
    assert len(rejected) == 2
    protected = root / "tests/unit/test_local_worker_raw.py"
    # Deliberate drift ONLY in this new disposable control workspace, after
    # positive evidence has been archived. The previous report remains immutable.
    with protected.open("a", encoding="utf-8") as stream:
        stream.write("\n# Offline post-validation drift negative control\n")
    try:
        gate.verify_handoff(root, report, config=config)
    except (ValueError, RuntimeError) as exc:
        rejected.append({"case": "post_validation_drift", "reason": str(exc)})
    assert len(rejected) == 3
    S.save(BATCH / "gate-negatives.json", rejected)
    assert all(S.sha(p) == h for p, h in prior["pins"].items())
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_OFFLINE_REAL_HOST_SEAM",
            "native_host_cases": len(rows),
            "handoff_negatives": len(rejected),
            "provider_calls": 0,
            "production_acceptance": False,
            "old_capture_profile_unchanged": True,
            "limitations": "Scripted native tools, not SDK Agent/local-model routing; single frozen function; positive workspace deliberately drifted AFTER archived validation for gate negative; generic profile and multi-file/test authoring remain pending",
        },
    )
    print("PASS offline real host seam; no provider calls", flush=True)


if __name__ == "__main__":
    main()
