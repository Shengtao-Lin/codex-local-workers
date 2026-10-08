"""Fresh registered repeat of the frozen split-question numeric composition."""

import argparse
import json
from pathlib import Path

import coordinator_numeric_split as split
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-numeric-repeat-1"
ORIGINAL_CONFIGURE = split.configure
_contract = None


def configure():
    global _contract
    if _contract is None:
        original = split.candidate.numeric.pilot.matrix.MIXED.prepare

        def fresh(case, repetition, config, batch, suite="v1"):
            return original(
                case, repetition, config, batch.replace("numeric4-", "numeric5-"), suite
            )

        split.candidate.numeric.pilot.matrix.MIXED.prepare = fresh
        split.BASE = BASE
        _contract = ORIGINAL_CONFIGURE()
    return _contract


def verify_registration():
    registration = read(BASE / "repeat-registration.json")
    for path, sha in registration["drivers"].items():
        if digest(Path(path)) != sha:
            raise ValueError("repeat driver drift")


def run(identity, unit):
    for cell in split.candidate.numeric.pilot.matrix.verify()["cells"]:
        root = Path(cell["root"])
        for mode in split.QUESTIONS:
            primary = read(root / f".agent/{mode}-explorer-primary.json")
            if (
                not primary["success"]
                or digest(root / f".agent/{mode}-explorer.json")
                != primary["report_sha256"]
            ):
                raise ValueError("four intact accepted fresh Explorer reports required")
    root = split.root_for(identity)
    mode = "parse" if unit == "normalize-unit" else "flow"
    original = split.candidate.numeric.pilot.read

    def selected(path):
        if Path(path) == root / ".agent/explorer.json":
            return original(root / f".agent/{mode}-explorer.json")
        return original(path)

    split.candidate.numeric.pilot.read = selected
    split.candidate.numeric.pilot.run(identity, unit)


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
            "audit",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--mode", choices=("flow", "parse"))
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        split.candidate.numeric.prepare()
        write(
            BASE / "repeat-registration.json",
            {
                "drivers": {
                    str(Path(p).resolve()): digest(Path(p))
                    for p in (__file__, split.__file__)
                },
                "snapshot": str(split.SNAPSHOT),
                "questions": split.QUESTIONS,
                "weekly_used_ceiling": 15,
                "previous_cohort": str(WORK / "coordinator-numeric-pilot-4"),
                "changed_axis": "Fresh task/run/workspace identities only; unchanged fixture, questions, budgets and original models",
                "fresh_explorer_calls_required": 4,
                "primary_acceptance_never_automatic": True,
                "risk": {
                    "qualification": "high",
                    "functional_unit_feature_integration": "medium",
                },
                "next_stage": "If paired repeat passes, separately register protected failure/rework composition before restricted opt-in decision",
            },
        )
        print(json.dumps({"status": "registered", "base": str(BASE)}))
    else:
        verify_registration()
        if args.action == "explore":
            original = split.candidate.numeric.pilot.matrix.SCOPE.invoke

            def invoke(root, name, argv):
                return original(root, name + "-" + args.mode, argv)

            split.candidate.numeric.pilot.matrix.SCOPE.invoke = invoke
            split.explore(args.identity, args.mode)
        elif args.action == "adjudicate":
            split.adjudicate(args.identity, args.mode, args.summary)
        elif args.action == "run":
            run(args.identity, args.unit)
        elif args.action == "check":
            split.candidate.numeric.evidence.unit_check(args.identity, args.unit)
        elif args.action == "record":
            import qualification_controls as evidence

            evidence.record(args.identity, args.unit, "accept", args.summary)
        elif args.action == "integrate":
            split.candidate.numeric.evidence.integrate(args.identity)
        else:
            import coordinator_numeric_comparison as comparison

            split.configure = configure
            comparison.main()
