"""New clean roots after quota interruption; never reuse the partial old source."""

import argparse

import tool_plain_result_qualification as qualification
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read
from layer_isolation import verify_hashes

BASE = WORK / "tool-plain-result-3"
SNAPSHOT = WORK / "continuation-weekly30-baseline-1"


def configure():
    qualification.BASE, qualification.SNAPSHOT = BASE, SNAPSHOT
    qualification.configure()


def register():
    configure()
    verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    reference = qualification.reference
    positive = read(
        WORK / "tool-plain-result-2/positive/.agent/primary-positive-v12-2.json"
    )
    if positive["passed"] is not True or positive["tests"] != 19:
        raise ValueError("independent nineteen-test positive preflight required")
    write(
        BASE / "preflight.json",
        {
            "passed": True,
            "evidence": str(
                WORK / "tool-plain-result-2/positive/.agent/primary-positive-v12-2.json"
            ),
            "model_credit": False,
        },
    )
    write(
        BASE / "registration.json",
        {
            "arms": reference.ARMS,
            "weekly_ceiling": 30,
            "fixture": "v12 unchanged original source and nineteen protected tests",
            "risk": "High feature/unit/integration, unchanged atomic deadline/cancellation/public result invariant",
            "explorer": "Not invoked: same already-answered question, no duplicate credit",
            "credit": "Two new fresh roots under default sampling, not recovery or comparison with unfinished quota run. Keep all previous denominators and partial sources.",
            "reference_files": read(reference.REFERENCE / "provenance.json")["files"],
            "driver_sha256": digest(KIT / "benchmarks/tool_context_reference_trial.py"),
            "adapter_sha256": {
                name: digest(KIT / "benchmarks" / name)
                for name in reference.qualification.scope.ADAPTERS
            },
        },
    )
    write(
        BASE / "plain-registration.json",
        {
            "driver_sha256": digest(
                KIT / "benchmarks/tool_plain_result_qualification.py"
            ),
            "fixture_version": 12,
            "tests": 19,
            "weekly_ceiling": 30,
        },
    )
    write(
        BASE / "continuation-registration.json",
        {
            "driver_sha256": digest(
                KIT / "benchmarks/tool_plain_fresh_continuation.py"
            ),
            "weekly_ceiling": 30,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("register", "prepare", "run"))
    parser.add_argument("--arm", choices=("fresh-1", "fresh-2"), default="fresh-1")
    args = parser.parse_args()
    configure()
    if args.action == "register":
        register()
    else:
        verify_hashes(
            KIT / "benchmarks",
            {
                "tool_plain_fresh_continuation.py": read(
                    BASE / "continuation-registration.json"
                )["driver_sha256"]
            },
        )
        {"prepare": qualification.prepare, "run": qualification.run}[args.action](
            args.arm
        )
