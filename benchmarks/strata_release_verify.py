"""Final release verification ledger; does not modify or accept task history."""

import os
import sys

import bounded_evidence_support as S
from strata_native_trial import command

BASE = S.KIT / "benchmarks/work/harness-convergence"
BATCH = BASE / "strata-release-quality-20261023-1"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["KIT_STRATA_HARNESS_ROOT"] = "F:/Strata/harness"
    if (BATCH / "decision.json").exists():
        raise FileExistsError("Closed verification ledger is immutable")
    BATCH.mkdir(exist_ok=True)
    files = [
        ".local-agents/strata-worker.py", ".local-agents/bounded/generic_evidence.py",
        ".local-agents/bounded/prepare_unit.py", ".local-agents/bounded/consolidated_harness.py",
        ".local-agents/bounded/capture_fixture_support.py", ".local-agents/local-bounded-unit.py",
        ".local-agents/tests/test_generic_evidence.py", "tests/test_strata_release_candidate.py",
        "tools/install-strata-preview.py", "tools/install-strata-release.py", "tools/package-strata-preview.py",
        "benchmarks/strata_bridge_host.py", "benchmarks/strata_native_host_v4.py", "benchmarks/strata_artifacts.py",
        "benchmarks/strata_release_matrix.py", "benchmarks/strata_release_faults.py", "benchmarks/strata_package_smoke.py",
        "benchmarks/strata_example_control.py", "benchmarks/strata_generic_controls.py",
    ]
    groups = {
        "shared-kernel": [S.PYTHON, "-B", "-m", "pytest", "-q", ".local-agents/tests", "-p", "no:cacheprovider",
                          "--junitxml=" + str(BATCH / "shared-kernel.xml"), "--basetemp=C:/Users/Lin/.codex/local-workers/strata-release-shared-20261023-final"],
        "native-preparation": [S.PYTHON, "-B", "-m", "pytest", "-q", *sorted((S.KIT / "tests").glob("test_strata*.py")),
                               "tests/test_bounded_preparation.py", "tests/test_capture_manifest.py", "-p", "no:cacheprovider",
                               "--junitxml=" + str(BATCH / "native-preparation.xml"), "--basetemp=C:/Users/Lin/.codex/local-workers/strata-release-native-20261023-final"],
        "actual-native": ["F:/Strata/node/node.exe", "--test", "tests/strata_kit_tool_bridge.test.mjs", "tests/strata_native_agent_core.test.mjs"],
        "changed-python-lint": [S.PYTHON, "-B", "-m", "ruff", "check", *files],
    }
    rows = {}
    for name, args in groups.items():
        record = BATCH / (name + ".json")
        if record.exists():
            result = S.read(record)
            assert result["argv"] == [str(v) for v in args], "Cannot reuse different checks"
        else:
            result = command(args, S.KIT, timeout=240)
            S.save(record, result)
        rows[name] = result["exit_code"]
        print(name, result["exit_code"], result["stdout"][-250:], result["stderr"][-500:], flush=True)
    package = S.KIT / "benchmarks/work/releases/strata-worker-0.1.0-preview.1"
    for name in S.read(package / "manifest.json"):
        if name.endswith(".py"):
            path = package / name
            compile(path.read_bytes(), str(path), "exec")
    matrix = S.read(BASE / "strata-release-v4-20261023-2/decision.json")
    assert matrix["accepted"] == 6 and matrix["executed"] == 6
    assert S.read(BASE / "strata-release-faults-20261023-2/decision.json")["status"] == "PASS_OFFLINE_FAULTS"
    assert S.read(BASE / "strata-package-smoke-20261023-1/decision.json")["status"] == "PASS_PACKAGE_INSTALL_SMOKE"
    S.save(BATCH / "decision.json", {
        "status": "READY_LIMITED_SUPERVISED_STRATA_PREVIEW" if all(v == 0 for v in rows.values()) else "HOLD_RELEASE_QUALITY",
        "checks": rows, "matrix": matrix, "archive": "benchmarks/work/releases/strata-worker-0.1.0-preview.zip",
        "weekly_used_observed": 1, "weekly_stop": 50,
        "no_commit_or_push": True, "production_defaults_changed": False,
        "not_general_or_production_autonomy": True,
        "remaining": ["no fresh Local Reviewer in this path", "no live semantic repair proof", "no unseen repo/multifile/skills/Web/Coordinator qualification", "cloud savings unknown"],
    })


if __name__ == "__main__":
    main()
