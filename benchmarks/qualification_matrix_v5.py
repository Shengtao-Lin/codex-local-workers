"""Fresh same-task qualification after accepted bounded Explorer convergence fix."""

import argparse
import json
from pathlib import Path

import qualification_matrix_v3 as prior
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-matrix-5"
SNAPSHOT = WORK / "qualification-matrix-baseline-5"


def configure():
    prior.BASE, prior.SNAPSHOT = BASE, SNAPSHOT
    prior.configure()
    prior.CONTROLS.BASE = WORK / "qualification-controls-5"
    original = prior.MATRIX.MIXED.prepare

    def prepare_case(case_id, repetition, config_path, batch, suite="v1"):
        config = read(config_path)
        config["coder_repair_focus_retention"] = "latest"
        config["explorer_output_limit_recovery"] = True
        config["explorer_duplicate_action_report_recovery"] = True
        path = BASE / "input-configs" / f"{case_id}-{batch}-r{repetition}.json"
        write(path, config)
        return original(case_id, repetition, path, batch + "5", suite)

    prior.MATRIX.MIXED.prepare = prepare_case


def prepare():
    configure()
    prior.MATRIX.prepare()
    assert read(WORK / "qualification-matrix-4/corpus.json") == read(
        BASE / "corpus.json"
    )
    drivers = (
        Path(__file__).resolve(),
        Path(prior.__file__),
        Path(prior.MATRIX.MIXED.__file__),
        Path(prior.STATUS.__file__),
    )
    write(
        BASE / "presentation-policy.json",
        {
            "classification": "Fresh known-task qualification; old failures immutable, no unseen-transfer claim",
            "drivers": {str(path): digest(path) for path in drivers},
            "same_sources_and_protected_tests": True,
            "same_contracts_and_observables": True,
            "scope_or_risk_lowered": False,
            "reference_code_forwarded": False,
            "coder_axis": "Same latest repair-focus retention as cohort 4",
            "explorer_axis": "D10 plus D11 opt-in; shared existing one-shot and proof gate, no larger budget",
            "screen": "Four fresh Explorer calls first. Any failure closes this qualification branch before remaining Coder/control work; no unchanged replay.",
            "qualification": "All 14 initial units accepted, four independently adjudicated Explorer successes, eight fresh controls and both integration chains. No historical success copied forward.",
            "weekly_used_ceiling": 70,
        },
    )
    print(
        "Frozen cohort 5: same fixed corpus; Explorer screen before implementation matrix"
    )


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
