"""Current-runtime retention test of qualified three-unit numeric composition."""

import argparse
import json
import re
from pathlib import Path

import coordinator_numeric_repeat as repeat
from capability_fit import WORK, write
from inherited_context_recovery import digest

BASE = WORK / "coordinator-limited-retention-1"
SNAPSHOT = WORK / "coordinator-wrap-policy-baseline-1"
_contract = None


def configure():
    global _contract
    if _contract is None:
        original = repeat.split.candidate.numeric.pilot.matrix.MIXED.prepare

        def fresh(case, repetition, config, batch, suite="v1"):
            return original(
                case,
                repetition,
                config,
                re.sub(r"numeric\d+-", "limitedretention1-", batch),
                suite,
            )

        repeat.split.candidate.numeric.pilot.matrix.MIXED.prepare = fresh
        repeat.BASE, repeat.split.SNAPSHOT = BASE, SNAPSHOT
        _contract = repeat.configure()
    return _contract


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
    matrix = repeat.split.candidate.numeric.pilot.matrix
    if args.action == "prepare":
        repeat.split.candidate.numeric.prepare()
        write(
            BASE / "repeat-registration.json",
            {
                "drivers": {
                    str(Path(p).resolve()): digest(Path(p))
                    for p in (__file__, repeat.__file__, repeat.split.__file__)
                },
                "snapshot": str(SNAPSHOT),
                "questions": repeat.split.QUESTIONS,
                "weekly_used_ceiling": 18,
                "changed_axis": "Current node-ID repair-prefetch runtime, fresh globally distinct tasks; qualified numeric/normalization/sequential async composition unchanged",
                "criterion": "Four fresh accepted Explorers, six real successful Coder+fresh Reviewer+Primary accepts and two seven-test integrations; no semantic retry or Primary edits. Otherwise no current-runtime retention GO.",
                "qualification_risk": "high",
                "functional_unit_feature_integration_risk": "medium",
                "excluded": "QuixBugs split/loop family remains unqualified; old and current failed results retained",
                "cloud_tokens": None,
                "primary_active_seconds": None,
            },
        )
        print(json.dumps({"registered": str(BASE)}))
    else:
        repeat.verify_registration()
        if args.action == "explore":
            original_invoke = matrix.SCOPE.invoke

            def invoke(root, name, argv):
                return original_invoke(root, name + "-" + args.mode, argv)

            matrix.SCOPE.invoke = invoke
            repeat.split.explore(args.identity, args.mode)
        elif args.action == "adjudicate":
            repeat.split.adjudicate(args.identity, args.mode, args.summary)
        elif args.action == "run":
            repeat.run(args.identity, args.unit)
        elif args.action == "check":
            repeat.split.candidate.numeric.evidence.unit_check(args.identity, args.unit)
        elif args.action == "record":
            import qualification_controls as controls

            controls.record(args.identity, args.unit, "accept", args.summary)
        elif args.action == "integrate":
            repeat.split.candidate.numeric.evidence.integrate(args.identity)
        else:
            import coordinator_numeric_comparison as comparison

            repeat.split.configure = configure
            comparison.main()
