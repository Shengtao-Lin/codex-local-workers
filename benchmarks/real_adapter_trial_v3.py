"""Verify the transitive package closure before the final source freeze."""

import argparse
import ast
import json
from pathlib import Path

import real_adapter_trial_v2 as previous
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read

trial = previous.trial


def configure():
    previous.configure()
    trial.PATHS = (*trial.PATHS, "src/evaluation_harness/errors.py")
    trial.FROZEN = KIT / "benchmarks/fixtures/real-adapter-datetime-v3"
    trial.BASE = WORK / "real-adapter-datetime-trial-3"


def verify_import_closure():
    paths = set(trial.PATHS)
    for relative in paths:
        if not relative.startswith("src/") or not relative.endswith(".py"):
            continue
        tree = ast.parse((trial.SOURCE / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not (
                node.module or ""
            ).startswith("evaluation_harness"):
                continue
            module = "src/" + node.module.replace(".", "/")
            if module + ".py" not in paths and module + "/__init__.py" not in paths:
                raise ValueError("uncopied real dependency: " + node.module)


def freeze():
    verify_import_closure()
    previous.freeze()
    write(
        trial.FROZEN / "closure.json",
        {
            "driver_sha256": digest(Path(__file__)),
            "transitive_local_imports_verified": True,
            "retained_failed_preparations": [
                "real-adapter-datetime-trial-1",
                "real-adapter-datetime-trial-2",
            ],
        },
    )


def preflight():
    if digest(Path(__file__)) != read(trial.FROZEN / "closure.json")["driver_sha256"]:
        raise ValueError("closure driver drift")
    previous.preflight()
    contract = read(trial.BASE / "task-contract.json")
    contract["feature_id"] = "real-adapter-datetime-trial-3"
    contract["note"] = (
        "Use this versioned contract for future delegation, not the retained parent helper's legacy label. No live local-worker packet exists yet."
    )
    write(trial.BASE / "task-contract-v3.json", contract)
    write(
        trial.FROZEN / "trial-summary.json",
        {
            "fixture_ready": True,
            "active_version": 3,
            "feature_id": contract["feature_id"],
            "original_files": len(trial.PATHS),
            "reference_tests_passed": 10,
            "original_tests": 3,
            "primary_added_tests": 7,
            "mutants": {
                "naive": ["test_naive_string_utc", "test_real_adapter_roundtrip"],
                "swallow": ["test_invalid_string", "test_real_adapter_roundtrip"],
                "combined": [
                    "test_invalid_string",
                    "test_naive_string_utc",
                    "test_real_adapter_roundtrip",
                ],
            },
            "all_mutants_detected": True,
            "source_project_modified": False,
            "local_model_calls": 0,
            "real_project_deployment": False,
            "current_status": "Prepared and deterministically preflighted. E/C/R and optional supervised Coordinator trial not yet run.",
            "selection": "Restore the existing private _datetime contract in the combined candidate; actual original adapter, sample models, registry, original adapter tests and trace fixtures retained. Reject broader source/caller/schema edits.",
            "environment_limitations": "Existing kit Python3.12/pytest9.1.1 is not sibling pytest<9 env; missing pytest-asyncio produces warning; no async tests needed. Pyright unavailable/not run. No packages installed.",
            "candidate": str(trial.BASE / "combined"),
            "contract": str(trial.BASE / "task-contract-v3.json"),
            "local_preflight": str(trial.BASE / "preflight.json"),
            "historical_preparation_failures": "v1 missing registry and wrong added-test formatting; v2 missing errors dependency. Retained without overwriting; zero model-quality failures.",
        },
    )
    print(
        json.dumps(
            {
                "active_fixture": str(trial.FROZEN),
                "contract": str(trial.BASE / "task-contract-v3.json"),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "preflight"))
    args = parser.parse_args()
    configure()
    freeze() if args.action == "freeze" else preflight()
