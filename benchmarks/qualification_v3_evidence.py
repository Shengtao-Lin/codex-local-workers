"""Primary-controlled evidence and immutable decisions for candidate three."""

import argparse
import json

import qualification_controls as controls
import qualification_evidence as evidence
import qualification_matrix_status as status
import qualification_matrix_v3 as candidate
from capability_fit import write

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "action",
        choices=("evidence", "record", "explorer", "integrate", "control", "snapshot"),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="qual-unit")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary")
    parser.add_argument("--effective", choices=("yes", "no"))
    args = parser.parse_args()
    candidate.configure()
    if args.action == "evidence":
        controls.evidence(args.identity, args.unit)
    elif args.action == "record":
        controls.record(args.identity, args.unit, args.decision, args.summary)
    elif args.action == "explorer":
        evidence.explorer(args.identity, args.summary, "explorer.json")
    elif args.action == "integrate":
        evidence.integrate(args.identity)
    elif args.action == "control":
        evidence.control(args.identity, args.effective == "yes", args.summary)
    else:
        facts = status.status()
        write(candidate.BASE / args.identity, facts)
        print(json.dumps(facts, indent=2))
