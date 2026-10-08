"""Fresh EOF candidate: Explorer screen before any mixed-chain writer."""

import argparse
from pathlib import Path

import coordinator_label_pilot as pilot
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-label-pilot-4"
SNAPSHOT = WORK / "coordinator-eof-baseline-1"


def configure():
    pilot.BASE, pilot.SNAPSHOT = BASE, SNAPSHOT
    original = pilot.matrix.MIXED.prepare

    def fresh_prepare(case, repetition, config_path, batch, suite="v1"):
        return original(
            case, repetition, config_path, batch.replace("label3-", "label4-"), suite
        )

    pilot.matrix.MIXED.prepare = fresh_prepare
    return pilot.configure()


def verify():
    registration = read(BASE / "candidate-registration.json")
    if digest(Path(__file__)) != registration["driver_sha256"]:
        raise ValueError("candidate driver drift")
    if (
        digest(Path(__file__).parents[1] / "tests/test_explorer_eof_recovery.py")
        != registration["regression_test_sha256"]
    ):
        raise ValueError("candidate regression test drift")
    return pilot.matrix.verify()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "explore",
            "run",
            "record",
            "adjudicate-explorer",
            "unit-check",
            "integrate",
            "audit",
            "stage",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="normalize-unit")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        pilot.prepare()
        before = read(WORK / "qualification-matrix-baseline-6/freeze.json")["files"]
        after = read(SNAPSHOT / "freeze.json")["files"]
        changes = [p for p in before if after.get(p) != before[p]]
        if (
            changes != [".local-agents/explorer-runtime.py"]
            or before.keys() != after.keys()
        ):
            raise ValueError("candidate differs outside EOF runtime fix")
        write(
            BASE / "candidate-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "regression_test_sha256": digest(
                    Path(__file__).parents[1] / "tests/test_explorer_eof_recovery.py"
                ),
                "changed_production_files": changes,
                "explorer_screen_order": [
                    "coordinator-r1",
                    "control-r1",
                    "control-r2",
                    "coordinator-r2",
                ],
                "screen_rule": "All four fresh five-path Explorer calls independently accepted before any Coder. Any failure stops the candidate unchanged; no copied/guided success credit.",
                "chain_order_after_screen": [
                    "coordinator-r1",
                    "control-r1",
                    "control-r2",
                    "coordinator-r2",
                ],
                "unit_order": ["normalize-unit", "collect-unit", "receipt-unit"],
                "classification": "Same failed new-composition fixture, new runtime; not unseen transfer or an isolated live causal estimate",
                "weekly_used_ceiling": 10,
                "baseline_snapshot": str(SNAPSHOT),
                "previous_failed_cohort": "coordinator-label-pilot-3",
                "full_regression": "coordinator-eof-before-1/regression-1.xml",
            },
        )
    else:
        manifest = verify()
        if args.action == "explore":
            pilot.explore(args.identity)
        elif args.action == "run":
            for cell in manifest["cells"]:
                root = Path(cell["root"])
                if (
                    not read(root / ".agent/explorer-primary-adjudication.json")[
                        "success"
                    ]
                    or read(root / ".agent/explorer.json")["cache"]["hit"]
                ):
                    raise ValueError(
                        "four fresh independently accepted Explorers required"
                    )
            pilot.run(args.identity, args.unit)
        elif args.action in ("unit-check", "integrate"):
            import coordinator_label_evidence as evidence

            if args.action == "unit-check":
                evidence.unit_check(args.identity, args.unit)
            else:
                evidence.integrate(args.identity)
        elif args.action == "audit":
            import coordinator_label_audit as audit

            audit.main()
        elif args.action == "stage":
            import coordinator_label_stage as stage

            stage.main()
        else:
            import qualification_controls as controls
            import qualification_evidence as evidence

            if args.action == "record":
                controls.record(args.identity, args.unit, args.decision, args.summary)
            else:
                evidence.explorer(args.identity, args.summary)
