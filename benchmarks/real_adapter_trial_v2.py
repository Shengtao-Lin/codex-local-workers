"""Complete original package closure; retain failed v1 preparation untouched."""

import argparse
import json
from pathlib import Path

import real_adapter_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read


def configure():
    trial.FROZEN = KIT / "benchmarks/fixtures/real-adapter-datetime-v2"
    trial.BASE = WORK / "real-adapter-datetime-trial-2"
    trial.PATHS = (*trial.PATHS, "src/evaluation_harness/adapters/registry.py")


def freeze():
    trial.freeze()
    write(
        trial.FROZEN / "revision.json",
        {
            "driver_sha256": digest(Path(__file__)),
            "previous_failed_preparation": "real-adapter-datetime-trial-1",
            "changes": "Copy real package registry dependency; supplemental tests formatted with original project config; format generated private-helper mutants only",
        },
    )


def preflight():
    revision = read(trial.FROZEN / "revision.json")
    if digest(Path(__file__)) != revision["driver_sha256"]:
        raise ValueError("revision driver drift")
    original = trial.command

    def measured(root, argv, timeout=180):
        if root.name != "reference" and "pytest" in argv:
            formatting = original(root, [argv[0], "-m", "ruff", "format", trial.COMMON])
            write(root / "mutant-format-preparation.json", formatting)
            if formatting["exit"]:
                raise ValueError("candidate formatting failed")
        return original(root, argv, timeout)

    trial.command = measured
    trial.preflight()
    write(
        trial.BASE / "readiness.json",
        {
            "fixture_ready": True,
            "model_calls": 0,
            "classification": "Full real modules and original tests; faults deliberately injected only in private helper. Not a production bug/deployment or local-role success result.",
            "feature_identity": "real-adapter-datetime-trial-2",
            "plan_identity_note": "Parent helper emits legacy task-contract label real-adapter-datetime-trial-1; use this fresh v2 identity when materializing any live schema-v2 packet. No worker packet has yet been created.",
            "frozen_source": str(trial.FROZEN),
            "candidate": str(trial.BASE / "combined"),
            "worker_reference_exclusion": [
                str(trial.FROZEN),
                str(trial.BASE / "reference"),
                str(trial.BASE / "naive"),
                str(trial.BASE / "swallow"),
            ],
            "pytest_environment_difference": "Diagnostic pytest9.1.1 vs source dev constraint <9; pytest-asyncio absent, warning preserved, tests are synchronous. Pyright unavailable. No environment equivalence claimed.",
            "next": "Fresh bounded Explorer on candidate only, one private-helper Coder packet, automatic fresh Reviewer, Primary and ten-test real adapter integration. Coordinator optional and Primary-supervised, not a three-unit requirement.",
        },
    )
    print(json.dumps({"readiness": str(trial.BASE / "readiness.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("freeze", "preflight"))
    args = parser.parse_args()
    configure()
    freeze() if args.action == "freeze" else preflight()
