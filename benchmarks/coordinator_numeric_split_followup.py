"""Distinct immutable invocation labels for multiple questions in one task."""

import argparse
from pathlib import Path

import coordinator_numeric_split as split
from capability_fit import write
from inherited_context_recovery import digest, read

if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("identity")
    parser.add_argument("--mode", choices=("flow", "parse"), required=True)
    args = parser.parse_args()
    split.configure()
    registration = read(split.BASE / "split-registration.json")
    if digest(Path(split.__file__)) != registration["driver_sha256"]:
        raise ValueError("original split driver drift")
    path = split.BASE / "invocation-label-registration.json"
    if not path.exists():
        write(
            path,
            {
                "driver_sha256": digest(Path(__file__)),
                "reason": "Use explorer-flow/explorer-parse immutable invocation labels; original control flow invocation retained. No question/model/runtime or outcome changes.",
            },
        )
    if read(path)["driver_sha256"] != digest(Path(__file__)):
        raise ValueError("followup driver drift")
    original = split.candidate.numeric.pilot.matrix.SCOPE.invoke

    def invoke(root, name, argv):
        return original(root, name + "-" + args.mode, argv)

    split.candidate.numeric.pilot.matrix.SCOPE.invoke = invoke
    split.explore(args.identity, args.mode)
