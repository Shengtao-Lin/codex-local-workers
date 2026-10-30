"""Independent observations plus explicit Primary adjudication; no keyword judging."""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import reviewer_evidence_candidate as trial
from capability_fit import WORK, write
from inherited_context_recovery import digest, read


def observe():
    registration = trial.verify()
    observations = []
    for cell in registration["controls"]:
        root = Path(cell["root"])
        report_path = root / ".agent/reviewer.json"
        if not report_path.exists():
            continue
        for path, sha in cell["protected_hashes"].items():
            if path != "src/product/target.py" and digest(root / path) != sha:
                raise ValueError("protected drift: " + path)
        if cell["id"].startswith("display-default"):
            code = """
from product.target import display_name
records = [{'name':''}, {'name':None}, {}, {'name':'Ada'}]
before = [dict(r) for r in records]
print(json.dumps({'values':[display_name(r) for r in records], 'unchanged':records == before}))
"""
        elif cell["id"].startswith("lookup-fallback"):
            code = """
from product.target import lookup_or
error = RuntimeError('same')
def broken(key):
    raise error
try:
    result = lookup_or(broken,'k','default')
except RuntimeError as caught:
    propagated = caught is error
else:
    propagated = False
values = [0,False,'',None,7]
print(json.dumps({'propagated':propagated, 'values':[lookup_or(lambda k:v,'k',99) for v in values]}))
"""
        else:
            code = "from product.target import increment\nprint(json.dumps({'values':[increment(x) for x in [-2,0,2]]}))"
        process = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import sys,json;sys.path.insert(0,'src');\n" + code,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        report = read(report_path)
        observations.append(
            {
                "id": cell["id"],
                "observed": json.loads(process.stdout),
                "source": (root / "src/product/target.py").read_text(encoding="utf-8"),
                "tests": (root / "tests/test_target.py").read_text(encoding="utf-8"),
                "report_sha256": digest(report_path),
                "decision": report.get("decision"),
                "findings": report.get("findings"),
                "unverified_claims": report.get("unverified_claims"),
                "contract_review": report.get("contract_review"),
                "validation_summary": report.get("validation_summary"),
                "failure_reason": report.get("failure_reason"),
            }
        )
    write(trial.BASE / "independent-observations-1.json", observations)
    print(json.dumps(observations, indent=2))


def finalize(adjudications):
    registration = trial.verify()
    observations = read(trial.BASE / "independent-observations-1.json")
    primary = read(Path(adjudications))
    if {r["id"] for r in primary} != {r["id"] for r in observations}:
        raise ValueError("Primary adjudication denominator mismatch")
    facts = {r["id"]: r for r in observations}
    cells = {r["id"]: r for r in registration["controls"]}
    for item in primary:
        identity = item["id"]
        cell, observation = cells[identity], facts[identity]
        root = Path(cell["root"])
        if digest(root / ".agent/reviewer.json") != observation["report_sha256"]:
            raise ValueError("report drift")
        write(
            root / ".agent/primary-control-adjudication.json",
            {
                **item,
                "report_sha256": observation["report_sha256"],
                "observed": observation["observed"],
                "synthetic_archive": True,
                "coder_credit": False,
            },
        )
        packet = read(root / ".agent/qual-unit-reference.json")
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(trial.SNAPSHOT / ".local-agents/record-review.py"),
                "--repo",
                str(root),
                "--task-id",
                packet["task_id"],
                "--run-id",
                packet["run_id"],
                "--decision",
                item["primary_decision"],
                "--summary",
                item["summary"],
            ],
            check=True,
            capture_output=True,
        )
    before = read(WORK / "reviewer-evidence-baseline-1/freeze.json")["files"]
    after = read(trial.SNAPSHOT / "freeze.json")["files"]
    differences = [p for p, sha in before.items() if after.get(p) != sha]
    expected = {
        ".local-agents/reviewer-runtime.py",
        ".local-agents/tests/test_reviewer_runtime.py",
    }
    if set(differences) != expected:
        raise ValueError("unexpected candidate scope: " + str(differences))
    suites = ET.parse(WORK.parent / "reviewer-evidence-regression-1.xml").getroot()
    suite = suites.find("testsuite")
    if suite is None or any(
        int(suite.get(k, "0")) for k in ("errors", "failures", "skipped")
    ):
        raise ValueError("regression not passed")
    good = sum(r["effective"] for r in primary)
    passed = len(primary) == len(cells) and good == len(cells)
    write(
        trial.BASE / "primary-screen-decision.json",
        {
            "decision": "pass" if passed else "hold",
            "correct": good,
            "executed": len(primary),
            "registered": len(cells),
            "candidate_scope": differences,
            "regression": suite.attrib,
            "real_rechecks": "pending" if passed else "not_started_screen_failed",
            "no_automatic_acceptance": True,
            "adjudications_sha256": digest(Path(adjudications)),
        },
    )
    print(
        "Primary screen decision:",
        "PASS" if passed else "HOLD",
        good,
        "/",
        len(primary),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("observe", "finalize"))
    parser.add_argument("--adjudications")
    args = parser.parse_args()
    if args.action == "observe":
        observe()
    else:
        finalize(args.adjudications)
