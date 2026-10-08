"""Independent integration evidence after immutable Primary unit acceptances."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import dependent_retention_chain as CHAIN
from capability_fit import WORK, write


def check(cohort, repetition):
    base = (WORK / cohort).resolve()
    base.relative_to(WORK.resolve())
    manifest = CHAIN.read(base / "manifest.json")
    root = Path(next(c for c in manifest["cells"] if c["round"] == repetition)["root"])
    report = root / ".agent/primary-integration-1.json"
    junit = root / ".agent/primary-integration-1.xml"
    if report.exists() or junit.exists():
        raise ValueError("immutable integration already exists")
    CHAIN.SNAPSHOT = Path(manifest["runtime"])
    refs, final_hashes = {}, {}
    for unit in ("limit-contract", "report-roundtrip"):
        packet = CHAIN.read(root / f".agent/{unit}-bound.json")
        refs[unit] = {k: packet[k] for k in ("task_id", "run_id")}
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        for change in CHAIN.read(archive / "handoff.json")["changed_files"]:
            final_hashes[change["path"]] = change["final_sha256"]
    accepted = CHAIN.load_contract().accepted_units_from_archives(
        CHAIN.read(root / ".agent/feature-plan.json"), root, refs
    )
    if accepted != set(refs):
        raise ValueError("incomplete accepted dependencies")
    cell = next(c for c in manifest["cells"] if c["round"] == repetition)
    expected = {**cell["hashes"], **final_hashes}
    for relative, sha in expected.items():
        if CHAIN.digest(root / relative) != sha:
            raise ValueError("frozen or accepted file drift: " + relative)
    results = []
    for args in (
        ["-B", "-m", "pytest", "tests", "-q", "--junitxml=" + str(junit)],
        ["-m", "ruff", "check", "src", "tests"],
        ["-m", "ruff", "format", "--check", "src", "tests"],
    ):
        result = subprocess.run(
            [sys.executable, *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        results.append(
            {
                "argv": args,
                "exit": result.returncode,
                "output": result.stdout + result.stderr,
            }
        )
    unchanged = all(CHAIN.digest(root / p) == sha for p, sha in expected.items())
    evidence = {
        "accepted_units": sorted(accepted),
        "commands": results,
        "inputs_unchanged": unchanged,
        "file_hashes": expected,
        "passed": unchanged and all(r["exit"] == 0 for r in results),
        "primary_feature_accepted": False,
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    write(report, evidence)
    print(json.dumps(evidence), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--round", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    check(args.cohort, args.round)
