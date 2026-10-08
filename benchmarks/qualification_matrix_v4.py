"""Pre-registered retention/output-recovery candidate, same known-task matrix."""

import argparse
import json
from pathlib import Path

import qualification_matrix_v3 as prior
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-matrix-4"
SNAPSHOT = WORK / "qualification-matrix-baseline-4"


def configure():
    prior.BASE, prior.SNAPSHOT = BASE, SNAPSHOT
    prior.configure()
    prior.CONTROLS.BASE = WORK / "qualification-controls-4"
    original = prior.MATRIX.MIXED.prepare

    def prepare_case(case_id, repetition, config_path, batch, suite="v1"):
        config = read(config_path)
        config["coder_repair_focus_retention"] = "latest"
        config["explorer_output_limit_recovery"] = True
        path = BASE / "input-configs" / f"{case_id}-{batch}-r{repetition}.json"
        write(path, config)
        return original(case_id, repetition, path, batch + "4", suite)

    prior.MATRIX.MIXED.prepare = prepare_case


def prepare():
    configure()
    prior.MATRIX.prepare()
    previous = read(WORK / "qualification-matrix-3/corpus.json")
    current = read(BASE / "corpus.json")
    assert previous == current
    drivers = (
        Path(__file__).resolve(),
        Path(prior.__file__),
        Path(prior.MATRIX.MIXED.__file__),
        Path(prior.STATUS.__file__),
    )
    write(
        BASE / "presentation-policy.json",
        {
            "classification": "Known-task candidate screen, not unseen transfer; old failures immutable",
            "drivers": {str(path): digest(path) for path in drivers},
            "same_sources_and_protected_tests": True,
            "same_contracts_and_observables": True,
            "scope_or_risk_lowered": False,
            "reference_code_forwarded": False,
            "coder_axis": "Existing latest repair-focus retention only; obsolete failure prompts removed, packet and source evidence retained. No larger budget or new semantic hint.",
            "explorer_axis": "Opt-in one-shot report-only output-limit recovery; no budget increase, no partial action execution, same proof requirements.",
            "screen": "Run lookup-fallback two fresh repetitions first. If either fails, close Coder-retention qualification branch; do not run unchanged third repetition or complete an ineligible matrix merely for a score. Explorer-only diagnostic remains separate.",
            "qualification": "Only if screen passes and D10 independent review accepted, complete all 14 initial units, four Explorer calls, eight fresh controls, two integration chains with Primary decisions. Prior success not carried forward.",
            "weekly_used_ceiling": 70,
        },
    )
    print(
        "Frozen same contracts, sources, protected tests; two-call retention screen before full matrix"
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
