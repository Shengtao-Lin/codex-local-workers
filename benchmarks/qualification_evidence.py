"""Primary-only independent adjudication helpers; never decides semantic findings."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import qualification_controls as CONTROLS
import qualification_matrix as MATRIX
from capability_fit import write
from inherited_context_recovery import digest, read


def explorer(identity, summary, report_name="explorer.json"):
    cell = next(c for c in MATRIX.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    if report_name not in (
        "explorer.json",
        "explorer-startup2.json",
        "explorer-guided2.json",
    ):
        raise ValueError("unknown Explorer artifact")
    report = read(root / ".agent" / report_name)
    checks = []
    for ref in report.get("source_refs", []):
        path = ref["path"]
        source = root / path
        if digest(source) != ref["source_hash"]:
            matches = list((root / ".agent/tasks").glob(f"*/runs/*/preimages/{path}"))
            matches = [p for p in matches if digest(p) == ref["source_hash"]]
            if len(matches) != 1:
                raise ValueError("no unique original Explorer citation source")
            source = matches[0]
        lines = source.read_text(encoding="utf-8").splitlines()
        start, end = ref["start_line"], ref["end_line"]
        okay = (
            path in cell["hashes"]
            and 1 <= start <= end <= len(lines)
            and ref["quote"] == "\n".join(lines[start - 1 : end])
        )
        checks.append({"path": path, "valid": okay})
    if (
        report["status"] != "success"
        or not checks
        or not all(c["valid"] for c in checks)
    ):
        raise ValueError("Explorer evidence not valid")
    # Caller explicitly supplies Primary semantic adjudication, not inferred from status.
    recovery = report_name == "explorer-guided2.json"
    write(
        root
        / (
            ".agent/explorer-guided-primary-adjudication.json"
            if recovery
            else ".agent/explorer-primary-adjudication.json"
        ),
        {
            "success": True,
            "qualification_credit": not recovery,
            "citation_checks": checks,
            "primary_semantic_summary": summary,
            "cache_hit": report.get("cache", {}).get("hit"),
            "source": "Primary read actual caller/helper/test evidence",
        },
    )
    print(json.dumps(checks))


def integrate(identity):
    cell = next(c for c in MATRIX.verify()["cells"] if c["id"] == identity)
    if len(cell["units"]) != 2:
        raise ValueError("expected dependent chain")
    root = Path(cell["root"])
    MATRIX.CHAIN.SNAPSHOT = MATRIX.SNAPSHOT
    contract = MATRIX.CHAIN.load_contract()
    refs = {}
    expected = dict(cell["hashes"])
    for unit in cell["units"]:
        startup = root / f".agent/{unit}-startup2-bound.json"
        packet = read(
            startup if startup.exists() else root / f".agent/{unit}-bound.json"
        )
        refs[unit] = {k: packet[k] for k in ("task_id", "run_id")}
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        if read(archive / "review.json")["decision"] != "accept":
            raise ValueError("integration needs actual Primary acceptance")
        for change in read(archive / "handoff.json")["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
    accepted = contract.accepted_units_from_archives(
        read(root / ".agent/feature-plan.json"), root, refs
    )
    if set(cell["units"]) != accepted:
        raise ValueError("accepted dependency provenance invalid")
    MATRIX.SCOPE.FA.LAYER.verify_hashes(root, expected)
    checks = MATRIX.SCOPE.FA.LAYER.check(root, "feature-integration")
    MATRIX.SCOPE.FA.LAYER.verify_hashes(root, expected)
    write(
        root / ".agent/feature-integration.json",
        {
            "accepted_units": sorted(accepted),
            "checks": checks,
            "inputs_unchanged": True,
            "primary_feature_accepted": False,
        },
    )
    print(json.dumps(checks))


def control(identity, effective, summary):
    cell = next(c for c in CONTROLS.verify()["controls"] if c["id"] == identity)
    root = Path(cell["root"])
    probe = """
import json
from product.target import TARGET
RESULT
"""
    if identity.startswith("display-default"):
        probe = probe.replace("TARGET", "display_name").replace(
            "RESULT",
            "print(json.dumps({'empty':display_name({'name':''}), 'none':display_name({'name':None}), 'missing':display_name({})}))",
        )
    else:
        probe = probe.replace("TARGET", "lookup_or").replace(
            "RESULT",
            "error=RuntimeError('same')\ndef fetch(key):\n    raise error\ntry:\n    lookup_or(fetch,'k','default')\nexcept RuntimeError as caught:\n    print(json.dumps({'propagated':caught is error}))\nelse:\n    print(json.dumps({'propagated':False}))",
        )
    process = subprocess.run(
        [sys.executable, "-B", "-c", "import sys; sys.path.insert(0,'src');" + probe],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    facts = json.loads(process.stdout)
    report = read(root / ".agent/reviewer.json")
    correct = (
        (facts == {"empty": "", "none": None, "missing": "unnamed"})
        if identity.startswith("display-default")
        else facts["propagated"]
    )
    if correct == cell["has_defect_primary_only"]:
        raise ValueError("control does not match frozen defect identity")
    write(
        root / ".agent/primary-control-adjudication.json",
        {
            "effective": effective,
            "primary_semantic_summary": summary,
            "observed": facts,
            "boundary_correct": correct,
            "reviewer_decision": report.get("decision"),
            "findings": report.get("findings"),
            "has_defect": cell["has_defect_primary_only"],
        },
    )
    packet = read(root / ".agent/qual-unit-reference.json")
    decision = (
        "rework"
        if cell["has_defect_primary_only"]
        else "accept"
        if report.get("decision") == "pass_to_primary"
        else "replan"
    )
    subprocess.run(
        [
            sys.executable,
            str(MATRIX.SNAPSHOT / ".local-agents/record-review.py"),
            "--repo",
            str(root),
            "--task-id",
            packet["task_id"],
            "--run-id",
            packet["run_id"],
            "--decision",
            decision,
            "--summary",
            summary,
        ],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("explorer", "integrate", "control"))
    parser.add_argument("identity")
    parser.add_argument("--summary")
    parser.add_argument("--effective", choices=("yes", "no"))
    parser.add_argument("--report-file", default="explorer.json")
    args = parser.parse_args()
    if args.action == "explorer":
        explorer(args.identity, args.summary, args.report_file)
    elif args.action == "integrate":
        integrate(args.identity)
    else:
        control(args.identity, args.effective == "yes", args.summary)
