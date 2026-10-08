"""Primary evidence checks for the three-unit packet-preparation pilot.

Writes immutable observations, never infers Primary semantic acceptance.
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import coordinator_label_pilot as pilot
from capability_fit import write
from inherited_context_recovery import digest, read


def context(identity):
    contract = pilot.configure()
    cell = next(c for c in pilot.matrix.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    return contract, cell, root, read(root / ".agent/feature-plan.json")


def provenance(contract, cell, root, plan, require_all=False):
    expected, refs = dict(cell["hashes"]), {}
    for unit in cell["units"]:
        packet = read(root / f".agent/{unit}-bound.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        if not (archive / "handoff.json").exists():
            continue
        for change in read(archive / "handoff.json")["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
        if (archive / "review.json").exists():
            refs[unit] = {k: packet[k] for k in ("task_id", "run_id")}
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    accepted = contract.accepted_units_from_archives(plan, root, refs)
    if require_all and accepted != set(cell["units"]):
        raise ValueError("all three units require immutable Primary acceptance")
    return expected, refs, accepted


def counts(path):
    total = {k: 0 for k in ("tests", "failures", "errors", "skipped")}
    for suite in ET.parse(path).getroot().iter("testsuite"):
        for key in total:
            total[key] += int(suite.get(key, 0))
    return total


def unit_check(identity, unit):
    contract, cell, root, plan = context(identity)
    expected, _, _ = provenance(contract, cell, root, plan)
    packet = read(root / f".agent/{unit}-bound.json")
    label = unit + "-independent-1"
    junit = root / ".agent" / (label + ".xml")
    temporary = root / (label + "-temp")
    if junit.exists() or temporary.exists():
        raise FileExistsError("independent observation must not overwrite history")
    layer = pilot.matrix.SCOPE.FA.LAYER
    checks = [
        layer.command(
            root,
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                *packet["focused_tests"],
                "-q",
                "-p",
                "no:cacheprovider",
                f"--basetemp={temporary}",
                f"--junitxml={junit}",
            ],
        ),
        layer.command(root, [sys.executable, "-m", "ruff", "check", "src", "tests"]),
        layer.command(
            root, [sys.executable, "-m", "ruff", "format", "--check", "src", "tests"]
        ),
    ]
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    observed = counts(junit)
    passed = observed == {
        "tests": len(packet["focused_tests"]),
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    } and all(c["exit"] == 0 for c in checks)
    report = {
        "checks": checks,
        "junit": observed,
        "passed": passed,
        "inputs_unchanged": True,
        "driver_sha256": digest(Path(__file__)),
        "primary_accepted": False,
    }
    write(root / ".agent" / (label + ".json"), report)
    print(json.dumps(report))
    if not passed:
        raise ValueError("independent focused/static checks failed")


def integrate(identity):
    contract, cell, root, plan = context(identity)
    expected, refs, accepted = provenance(contract, cell, root, plan, True)
    checks = pilot.matrix.SCOPE.FA.LAYER.check(root, "feature-integration")
    pilot.matrix.SCOPE.FA.LAYER.verify_hashes(root, expected)
    junit = root / ".agent/feature-integration.xml"
    observed = counts(junit)
    report = {
        "accepted_units": sorted(accepted),
        "checks": checks,
        "junit": observed,
        "inputs_unchanged": True,
        "primary_feature_accepted": False,
        "driver_sha256": digest(Path(__file__)),
    }
    write(root / ".agent/feature-integration.json", report)
    if (
        observed != {"tests": 7, "failures": 0, "errors": 0, "skipped": 0}
        or not checks["all_checks_pass"]
    ):
        raise ValueError(
            "integration needs seven executed passing tests and static checks"
        )
    evidence = {
        "schema_version": 1,
        "feature_id": plan["feature_id"],
        "plan_revision": plan["plan_revision"],
        "primary_plan_sha256": contract.authority_fingerprint(plan),
        "integration_risk": plan["integration_risk"],
        "status": "passed",
        "checks": [
            {"id": f"integration-{i}", "status": "passed", "exit_code": c["exit"]}
            for i, c in enumerate(checks["checks"])
        ],
        "files": [{"path": p, "sha256": sha} for p, sha in expected.items()],
        "junit_sha256": digest(junit),
        "source_evidence": ".agent/feature-integration.json",
        "primary_feature_accepted": False,
    }
    write(
        root / ".agent/integration" / plan["feature_id"] / "validation.json", evidence
    )
    contract.verify_integration_archive(plan, root, refs)
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("unit-check", "integrate"))
    parser.add_argument("identity")
    parser.add_argument("--unit", default="normalize-unit")
    args = parser.parse_args()
    if args.action == "unit-check":
        unit_check(args.identity, args.unit)
    else:
        integrate(args.identity)
