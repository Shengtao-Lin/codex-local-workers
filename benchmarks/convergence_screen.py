"""Reuse the fixed qualification corpus against a fresh portable runtime freeze."""

import argparse
from pathlib import Path

import qualification_matrix_v6 as existing
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "convergence-screen-1"
SNAPSHOT = WORK / "convergence-runtime-1"


def configure():
    existing.BASE, existing.SNAPSHOT = BASE, SNAPSHOT
    existing.configure()
    return existing.previous.prior.MATRIX


def prepare():
    existing.BASE, existing.SNAPSHOT = BASE, SNAPSHOT
    existing.prepare()
    paths = [Path(__file__), KIT / "docs/stability-convergence-candidate.md"]
    write(
        BASE / "convergence-policy.json",
        {
            "weekly_used_start": 30,
            "weekly_used_ceiling": 40,
            "candidate": "current portable runtime with existing qualified opt-ins",
            "experimental_toolregistry_adapters": False,
            "screen": [
                "display-default-r1",
                "async-first-present-r1",
                "label-rollup-r1",
            ],
            "stop": "two independent same-signature infrastructure failures; or completed fixed matrix; or actual weekly used >=40",
            "coordinator_allowed": False,
            "historical_metadata_ceiling_superseded": True,
            "files": {str(p.resolve()): digest(p) for p in paths},
            "global_config_sha256": digest(KIT / ".local-agents/config.json"),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "preflight", "unit", "explore"))
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="qual-unit")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        policy = read(BASE / "convergence-policy.json")
        for path, sha in policy["files"].items():
            if digest(Path(path)) != sha:
                raise ValueError("convergence policy/driver changed")
        matrix = configure()
        if args.action == "preflight":
            matrix.preflight()
        elif args.action == "explore":
            matrix.explore(args.identity)
        else:
            matrix.run(args.identity, args.unit)
