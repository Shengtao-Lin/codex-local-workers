"""Fresh known-task release matrix; proactive post-edit field guidance only."""

import argparse
import json
from pathlib import Path

import qualification_matrix_v5 as previous
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-matrix-6"
SNAPSHOT = WORK / "qualification-matrix-baseline-6"


def configure():
    previous.BASE, previous.SNAPSHOT = BASE, SNAPSHOT
    previous.configure()
    previous.prior.CONTROLS.BASE = WORK / "qualification-controls-6"
    original = previous.prior.MATRIX.MIXED.prepare

    def prepare_case(case_id, repetition, config_path, batch, suite="v1"):
        config = read(config_path)
        config["coder_post_edit_validation_hint"] = True
        path = BASE / "hint-configs" / f"{case_id}-{batch}-r{repetition}.json"
        write(path, config)
        return original(case_id, repetition, path, batch + "6", suite)

    previous.prior.MATRIX.MIXED.prepare = prepare_case


def prepare():
    configure()
    previous.prior.MATRIX.prepare()
    assert read(BASE / "corpus.json") == read(
        WORK / "qualification-matrix-5/corpus.json"
    )
    drivers = [
        Path(__file__).resolve(),
        Path(previous.__file__),
        Path(previous.prior.__file__),
        Path(previous.prior.MATRIX.MIXED.__file__),
        Path(previous.prior.STATUS.__file__),
    ]
    write(
        BASE / "presentation-policy.json",
        {
            "classification": "Known-task requalification, not unseen transfer; old failures immutable",
            "drivers": {str(path): digest(path) for path in drivers},
            "same_sources_and_protected_tests": True,
            "same_contracts_and_observables": True,
            "scope_or_risk_lowered": False,
            "reference_code_forwarded": False,
            "changed_axis": "D12 optional post-edit packet field shape with null ordering confirmations; no automatic validation, permission/budget/gate change. D10/D11 and latest retention unchanged.",
            "screen": "Two fresh async-first-present calls first, then four fresh Explorer calls; any failure stops queued subsequent work. Independently adjudicated acceptance, not just exit zero.",
            "qualification": "All 14 initial units accepted, Explorer 4/4, eight fresh effective controls, two accepted dependency integration chains. No copied historical success.",
            "weekly_used_ceiling": 70,
        },
    )
    print("Frozen candidate 6 with same corpus; async and Explorer screen first")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "preflight",
            "unit",
            "explore",
            "controls-prepare",
            "control",
            "evidence",
            "record",
            "adjudicate-explorer",
            "integrate",
            "adjudicate-control",
            "status",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="qual-unit")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary")
    parser.add_argument("--effective", choices=("yes", "no"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        configure()
        import qualification_evidence as evidence

        prior = previous.prior
        if args.action == "preflight":
            prior.MATRIX.preflight()
        elif args.action == "unit":
            prior.MATRIX.run(args.identity, args.unit)
        elif args.action == "explore":
            prior.MATRIX.explore(args.identity)
        elif args.action == "controls-prepare":
            prior.CONTROLS.prepare()
        elif args.action == "control":
            prior.CONTROLS.run(args.identity)
        elif args.action == "evidence":
            prior.CONTROLS.evidence(args.identity, args.unit)
        elif args.action == "record":
            prior.CONTROLS.record(args.identity, args.unit, args.decision, args.summary)
        elif args.action == "adjudicate-explorer":
            evidence.explorer(args.identity, args.summary)
        elif args.action == "integrate":
            evidence.integrate(args.identity)
        elif args.action == "adjudicate-control":
            evidence.control(args.identity, args.effective == "yes", args.summary)
        else:
            print(json.dumps(prior.STATUS.status(), indent=2))
