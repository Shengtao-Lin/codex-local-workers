"""Fresh wrap qualification with explicit split semantics and unchanged tests."""

import argparse
import copy
import json
import sys
from pathlib import Path

import coordinator_quixbugs_wrap as original
from capability_fit import WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "coordinator-wrap-policy-1"
SNAPSHOT = WORK / "coordinator-wrap-policy-baseline-1"
pilot, split = original.pilot, original.split
POLICY = (
    "Additional explicit split policy: while the remaining text exceeds cols, "
    "choose its rightmost space boundary at an offset in 1..cols. If there is no "
    "such positive boundary, emit exactly cols characters. Do not choose offset "
    "zero, which cannot advance, and do not substitute a fixed one-character "
    "fallback for arbitrary cols. Preserve spaces, order, and the complete final "
    "remainder. This output policy is a labelled supplemental contract, not an "
    "upstream requirement. For text='  abc', cols=2, the required result is "
    "[' ', ' a', 'bc']; for text=' ab', cols=1 it is [' ', 'a', 'b']. "
    "Protected assertions are unchanged from the previous cohort."
)


def case():
    result = copy.deepcopy(original.case())
    result["units"][0]["contract"] += " " + POLICY
    result["units"][0]["acceptance_scenarios"][1]["observables"].update(
        split_policy_input="  abc",
        split_policy_cols=2,
        split_policy_expected=[" ", " a", "bc"],
    )
    return result


def configure():
    pilot.BASE, pilot.SNAPSHOT, pilot.fixture = BASE, SNAPSHOT, sys.modules[__name__]
    split.BASE, split.SNAPSHOT = BASE, SNAPSHOT
    split.QUESTIONS = {
        "flow": (["src/product/target.py", "tests/test_target.py"], original.QUESTION)
    }
    return pilot.configure()


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    contract = configure()
    write(BASE / "corpus.json", {"cases": [case()]})
    write(BASE / "primary-oracles.json", read(original.BASE / "primary-oracles.json"))
    prior = read(original.BASE / "manifest.json")["cells"][0]
    config = read(Path(prior["root"]) / ".agent/config.json")
    cells = []
    for repetition in (1, 2, 3):
        for arm in ("control", "coordinator"):
            settings = copy.deepcopy(config)
            settings["coordinator_enabled"] = arm == "coordinator"
            settings["explorer_required_citation_paths"] = split.QUESTIONS["flow"][0]
            config_path = BASE / f"{arm}-r{repetition}-config.json"
            write(config_path, settings)
            root = Path(
                pilot.matrix.MIXED.prepare(
                    "quixbugs-wrap",
                    1,
                    config_path,
                    f"wrappolicy1-r{repetition}-{arm}",
                )["root"]
            )
            plan = read(root / ".agent/feature-plan.json")
            packet = read(root / ".agent/normalize-unit-reference.json")
            packet["primary_plan_sha256"] = contract.authority_fingerprint(plan)
            packet = contract.validate_unit_packet(plan, packet)
            load_worker(SNAPSHOT).validate_packet(packet)
            write(root / ".agent/normalize-unit-bound.json", packet)
            paths = [
                *case()["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/feature-plan.json",
                ".agent/normalize-unit-bound.json",
            ]
            cells.append(
                {
                    "id": f"{arm}-r{repetition}",
                    "arm": arm,
                    "round": repetition,
                    "case": "quixbugs-wrap",
                    "root": str(root),
                    "units": ["normalize-unit"],
                    "hashes": {p: digest(root / p) for p in paths},
                }
            )
    write(
        BASE / "manifest.json",
        {
            "runtime": str(SNAPSHOT),
            "cells": cells,
            "drivers": {
                str(Path(p).resolve()): digest(Path(p))
                for p in (__file__, original.__file__, pilot.__file__, split.__file__)
            },
        },
    )
    write(
        BASE / "registration.json",
        {
            "functional_risk": "medium",
            "qualification_risk": "high",
            "risk_rationale": "Pure private helper fixture; Primary retains release authority.",
            "weekly_used_start": 8,
            "weekly_used_ceiling": 18,
            "criterion": "Three fresh successful chains per arm, fresh independently accepted Explorer, Coder validation, independent Reviewer, Primary review and integration. No failures hidden.",
            "changed_axis": "Explicit supplemental split policy; same tests and original buggy starting source; current node-ID prefetch fix in both arms.",
            "models_budgets_changed": False,
            "old_results_overwritten": False,
            "semantic_contract_examples_supplied": True,
            "reference_code_supplied": False,
            "coordinator_authority": "Bounded proposal only; no architecture, scope changes or acceptance.",
            "cost_savings_claim": False,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    pilot.matrix.preflight()
    print(
        json.dumps(
            {
                "prepared": len(cells),
                "all_preflight_pass": read(BASE / "preflight-1.json")["all_pass"],
            }
        )
    )


def run(identity):
    configure()
    root = split.root_for(identity)
    adjudication = read(root / ".agent/flow-explorer-primary.json")
    if (
        not adjudication["success"]
        or digest(root / ".agent/flow-explorer.json") != adjudication["report_sha256"]
    ):
        raise ValueError("fresh accepted Explorer required")
    actual_read = pilot.read

    def selected(path):
        return actual_read(
            root / ".agent/flow-explorer.json"
            if Path(path) == root / ".agent/explorer.json"
            else path
        )

    pilot.read = selected
    pilot.run(identity, "normalize-unit")


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
    if args.action == "prepare":
        prepare()
    else:
        configure()
        pilot.matrix.verify()
        if args.action == "explore":
            split.explore(args.identity, "flow")
        elif args.action == "adjudicate":
            split.adjudicate(args.identity, "flow", args.summary)
        elif args.action == "run":
            run(args.identity)
        elif args.action == "check":
            original.evidence.unit_check(args.identity, "normalize-unit")
        elif args.action == "integrate":
            original.evidence.integrate(args.identity)
        else:
            import qualification_controls

            qualification_controls.record(
                args.identity, "normalize-unit", "accept", args.summary
            )
