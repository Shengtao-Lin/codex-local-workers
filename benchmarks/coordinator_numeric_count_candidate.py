"""Fresh numeric screen with explicit required-path count repair feedback."""

import argparse
from pathlib import Path

import coordinator_numeric_candidate as candidate
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-numeric-pilot-3"
SNAPSHOT = WORK / "coordinator-report-baseline-2"


def configure():
    original = candidate.numeric.pilot.matrix.MIXED.prepare

    def prepare(case, repetition, config, batch, suite="v1"):
        return original(
            case, repetition, config, batch.replace("numeric2-", "numeric3-"), suite
        )

    candidate.numeric.pilot.matrix.MIXED.prepare = prepare
    candidate.BASE, candidate.SNAPSHOT = BASE, SNAPSHOT
    return candidate.configure()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "adjudicate",
            "run",
            "check",
            "record",
            "integrate",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        candidate.numeric.prepare()
        write(
            BASE / "candidate-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "investigation_driver_sha256": digest(Path(candidate.__file__)),
                "runtime": str(SNAPSHOT),
                "weekly_used_ceiling": 15,
                "previous_failed_cohort": "coordinator-numeric-pilot-2",
                "order": ["control-r1", "coordinator-r1"],
                "question_hard_contract_model_or_budget_changes": False,
                "change": "Required citation paths and six-object count explicitly retained in one-shot report-only correction",
                "readiness_rule": "Two fresh Explorer accepts and direct control chain C/R/Primary plus seven-test integration before Coordinator testing",
            },
        )
    else:
        registration = read(BASE / "candidate-registration.json")
        if (
            digest(Path(__file__)) != registration["driver_sha256"]
            or digest(Path(candidate.__file__))
            != registration["investigation_driver_sha256"]
        ):
            raise ValueError("candidate driver drift")
        if args.action == "explore":
            candidate.explore(args.identity)
        elif args.action == "adjudicate":
            import qualification_evidence as evidence

            evidence.explorer(args.identity, args.summary)
        elif args.action == "run":
            for cell in candidate.numeric.pilot.matrix.verify()["cells"]:
                if not read(
                    Path(cell["root"]) / ".agent/explorer-primary-adjudication.json"
                )["success"]:
                    raise ValueError("both fresh Explorers must be accepted")
            candidate.numeric.pilot.run(args.identity, args.unit)
        elif args.action == "check":
            candidate.numeric.evidence.unit_check(args.identity, args.unit)
        elif args.action == "integrate":
            candidate.numeric.evidence.integrate(args.identity)
        else:
            import qualification_controls as evidence

            evidence.record(args.identity, args.unit, "accept", args.summary)
