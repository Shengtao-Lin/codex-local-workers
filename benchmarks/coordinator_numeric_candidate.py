"""Truthful focused investigation and bounded control-chain readiness candidate."""

import argparse
import json
import sys
from pathlib import Path

import coordinator_numeric_pilot as numeric
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-numeric-pilot-2"
SNAPSHOT = WORK / "coordinator-report-baseline-1"


def configure():
    numeric.BASE, numeric.SNAPSHOT = BASE, SNAPSHOT
    original = numeric.pilot.matrix.MIXED.prepare

    def fresh_prepare(case, repetition, config, batch, suite="v1"):
        return original(
            case, repetition, config, batch.replace("numeric1-", "numeric2-"), suite
        )

    numeric.pilot.matrix.MIXED.prepare = fresh_prepare
    return numeric.configure()


def explore(identity):
    cell = next(
        c for c in numeric.pilot.matrix.verify()["cells"] if c["id"] == identity
    )
    root = Path(cell["root"])
    numeric.pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, cell["hashes"])
    packet = read(root / ".agent/normalize-unit-bound.json")
    question = (
        "Where are the current public call chain, the separate numeric parser helper, and its protected acceptance assertions? "
        "Investigate actual current code, not the intended repaired flow. "
        "Likely files/symbols: src/product/entry.py run_batch; src/product/target.py labelled_receipt; "
        "src/product/labels.py normalize_labels; src/product/collector.py collect_values; "
        "src/product/schema.py parse_code (currently separate, do not assume it is called). "
        "In tests/test_target.py locate exact test_batch_roundtrip and test_batch_empty symbols: "
        "the integer-key assertion/receipt assertion and ValueError-before-fetch assertion are the relevant test evidence. "
        "Read all six actual paths. State current disconnected/missing behavior as uncertainty, not invented call flow. "
        "Return one bounded reference per required path, at most six references and 80 total cited lines; "
        "use small actual symbol ranges and one bounded test assertion range, not whole files. "
        "Literal SEARCH needs actual symbols, not phrases such as protected numeric roundtrip. "
        "Locations only; no repairs or predicted validation."
    )
    write(
        root / ".agent/focused-investigation.json",
        {
            "question": question,
            "previous_failed_cohort": "coordinator-numeric-pilot-1",
            "classification": "New focused investigation plus runtime fix, not isolated causal proof or overwritten baseline success",
        },
    )
    numeric.pilot.matrix.SCOPE.invoke(
        root,
        "explorer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--task",
            question,
            "--task-id",
            packet["task_id"],
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
    )
    print(json.dumps(read(root / ".agent/explorer.json")))


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
        numeric.prepare()
        write(
            BASE / "candidate-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "runtime": str(SNAPSHOT),
                "weekly_used_ceiling": 15,
                "supersedes_registration_ceiling": 10,
                "screen_order": ["control-r1", "coordinator-r1"],
                "readiness_rule": "Both fresh Explorers independently accepted and one full direct control chain C/R/Primary plus seven-test integration passed before authorizing Coordinator mixed testing",
                "hard_contract_fixture_or_role_changes": False,
                "runtime_and_question_both_changed": True,
            },
        )
    else:
        if (
            digest(Path(__file__))
            != read(BASE / "candidate-registration.json")["driver_sha256"]
        ):
            raise ValueError("candidate driver drift")
        if args.action == "explore":
            explore(args.identity)
        elif args.action == "adjudicate":
            import qualification_evidence as evidence

            evidence.explorer(args.identity, args.summary)
        elif args.action == "run":
            for cell in numeric.pilot.matrix.verify()["cells"]:
                root = Path(cell["root"])
                if not read(root / ".agent/explorer-primary-adjudication.json")[
                    "success"
                ]:
                    raise ValueError("both fresh Explorer calls must be accepted")
            numeric.pilot.run(args.identity, args.unit)
        elif args.action == "check":
            numeric.evidence.unit_check(args.identity, args.unit)
        elif args.action == "integrate":
            numeric.evidence.integrate(args.identity)
        else:
            import qualification_controls as evidence

            evidence.record(args.identity, args.unit, "accept", args.summary)
