"""Resume only unexecuted terms cells after auditing mutable output indexes."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import harness_reviewer_terms as H

B = H.B
OUTPUTS = {".agent/current-task.json", ".agent/tasks/semantic-terms/state.json"}


def protected(files):
    return {path: sha for path, sha in files.items() if path not in OUTPUTS}


def audit():
    H.E.prior_unchanged()
    for path, sha in B.read(H.BATCH / "live-freeze.json")["pins"].items():
        assert B.sha(Path(path)) == sha
    rows = B.read(H.BATCH / "registration.json")["cells"]
    for row in rows:
        H.R.assert_files(Path(row["root"]), protected(row["files"]))
    return rows


def freeze():
    import xml.etree.ElementTree as ET

    rows = audit()
    first = B.read(H.BATCH / "cells/cell-01/result.json")
    assert set(first["protected_drift"]) == OUTPUTS
    for row in rows[1:]:
        assert not (Path(row["root"]).parent / "started.json").exists()
    tree = ET.parse(H.BATCH / "continuation-controls-v2.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + tag) for tag in ("error", "failure", "skipped")
    )
    B.save(
        H.BATCH / "continuation-registration.json",
        {
            "reason": "First live call correctly writes two runtime-owned mutable output indexes; first driver misclassified them as protected inputs.",
            "evidence": ".local-agents/reviewer-runtime.py finalize writes state.json and current-task.json; same pinned code in isolated roots.",
            "remaining": [r["id"] for r in rows[1:]],
            "first_cell_not_replayed": True,
            "first_failure_retained_in_original_denominator": True,
            "excluded_output_paths": sorted(OUTPUTS),
            "candidate_model_budget_contract_tests_unchanged": True,
            "pins": {
                str(p): B.sha(p)
                for p in (
                    Path(__file__),
                    B.KIT / "tests/test_terms_continuation.py",
                    H.BATCH / "continuation-controls-v2.xml",
                    H.BATCH / "cells/cell-01/result.json",
                    H.BATCH / "cells/cell-01/reviewer.json",
                )
            },
        },
    )


def run(name, used):
    assert 0 <= used < 45
    rows = audit()
    continuation = B.read(H.BATCH / "continuation-registration.json")
    for path, sha in continuation["pins"].items():
        assert B.sha(Path(path)) == sha
    assert name in continuation["remaining"]
    row = next(r for r in rows if r["id"] == name)
    for previous in rows[: rows.index(row)]:
        result = B.read(Path(previous["root"]).parent / "result.json")
        assert not result["infra_failure"]
        assert not (set(result["protected_drift"]) - OUTPUTS)
    root = Path(row["root"])
    cell = root.parent
    B.save(
        cell / "started.json",
        {
            "at": time.time(),
            "weekly_used": used,
            "no_retry": True,
            "continuation": True,
        },
    )
    argv = [
        sys.executable,
        "-B",
        str(H.PREV.ADAPTER),
        "--runtime-dir",
        str(root / ".local-agents"),
        "--request",
        str(root / ".agent/experiment-request.json"),
        "--config",
        str(root / ".agent/experiment-config.json"),
        "--report",
        str(cell / "reviewer.json"),
    ]
    start = time.monotonic()
    proc = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(B.KIT / "benchmarks/r3_capture"),
            "R3_WIRE_DIR": str(cell / "wire"),
        },
    )
    B.save(
        cell / "entry-result.json",
        {
            "argv": argv,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": time.monotonic() - start,
        },
    )
    report = B.read(cell / "reviewer.json")
    result = {
        "id": name,
        "observed": report.get("decision"),
        "expected": row["expected_decision"],
        "failure_reason": report.get("failure_reason"),
        "infra_failure": report.get("infra_failure"),
        "protected_drift": [
            p for p, sha in protected(row["files"]).items() if B.sha(root / p) != sha
        ],
        "mutable_outputs_changed": [
            p for p in OUTPUTS if B.sha(root / p) != row["files"][p]
        ],
        "seconds": time.monotonic() - start,
        "primary_adjudication": "pending",
    }
    B.save(cell / "result.json", result)
    print(result, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["freeze", "run"])
    p.add_argument("--case")
    p.add_argument("--used", type=int)
    args = p.parse_args()
    freeze() if args.action == "freeze" else run(args.case, args.used)
