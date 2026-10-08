"""Fresh transfer registration after full-project-rule preparation diagnostic."""

import argparse
import json
import sys
from pathlib import Path

import coordinator_datetime_transfer as transfer
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-datetime-transfer-2"


def configure():
    transfer.BASE = BASE
    transfer.INITIAL = transfer.INITIAL.replace(
        "from datetime import UTC as UTC, datetime",
        "from datetime import UTC as UTC\nfrom datetime import datetime",
    )
    return transfer.configure()


def verify():
    registration = read(BASE / "checked-registration.json")
    if digest(Path(__file__)) != registration["driver_sha256"]:
        raise ValueError("checked driver drift")
    if not registration["full_rules_baseline_pass"]:
        raise ValueError("full mandatory checks required before worker")
    transfer.pilot.matrix.verify()


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
    parser.add_argument("--summary")
    args = parser.parse_args()
    configure()
    if args.action == "prepare":
        transfer.prepare()
        observations = []
        for cell in transfer.pilot.matrix.verify()["cells"]:
            root = Path(cell["root"])
            for argv in (
                [sys.executable, "-m", "ruff", "check", "src", "tests"],
                [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"],
            ):
                observations.append(
                    transfer.pilot.matrix.SCOPE.FA.LAYER.command(root, argv)
                )
        passed = all(item["exit"] == 0 for item in observations)
        write(
            BASE / "checked-registration.json",
            {
                "driver_sha256": digest(Path(__file__)),
                "full_rules_baseline_pass": passed,
                "checks": observations,
                "prior_preparation_diagnostic": "coordinator-datetime-transfer-1",
                "mandatory_rules": ["E", "F", "I", "UP", "B", "ASYNC", "RUF"],
                "not_established": [
                    "whole-project Pyright",
                    "production bug",
                    "deployed feature",
                    "cloud saving",
                    "Primary active time",
                ],
            },
        )
        if not passed:
            raise ValueError("initial fixture checks failed; no Coder authorized")
    else:
        verify()
        if args.action == "explore":
            transfer.split.explore(args.identity, "flow")
        elif args.action == "adjudicate":
            transfer.split.adjudicate(args.identity, "flow", args.summary)
        elif args.action == "run":
            transfer.run(args.identity)
        elif args.action == "check":
            transfer.evidence.unit_check(args.identity, "normalize-unit")
        elif args.action == "integrate":
            transfer.evidence.integrate(args.identity)
        else:
            import qualification_controls

            qualification_controls.record(
                args.identity, "normalize-unit", "accept", args.summary
            )
    print(json.dumps({"action": args.action, "base": str(BASE)}))
