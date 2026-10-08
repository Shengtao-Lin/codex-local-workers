"""Serial diagnostic continuation, preserving failed qualification and no acceptance."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import WORK, write


def run(case, repetition, cohort="roleq-six-1"):
    if cohort not in {
        "roleq-six-1",
        "roleq-binding-comparison-1",
        "roleq-boundary-comparison-1",
        "roleq-temperature-comparison-1",
        "roleq-plain-json-comparison-1",
        "roleq-vocabulary-comparison-1",
        "roleq-vocabulary-comparison-2",
        "roleq-formal-transfer-1",
        "roleq-semantic-examples-1",
        "roleq-retention-transfer-1",
        "roleq-protocol-transfer-1",
    }:
        raise ValueError("unknown registered cohort")
    base = WORK / cohort
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    cell = next(
        c
        for c in manifest["cells"]
        if c["case"] == case and c["repetition"] == repetition
    )
    root = Path(cell["workspace"])
    for field, relative in (
        ("packet_sha256", ".agent/qual-unit-reference.json"),
        ("config_sha256", ".agent/config.json"),
    ):
        if (
            field in cell
            and hashlib.sha256((root / relative).read_bytes()).hexdigest()
            != cell[field]
        ):
            raise ValueError("frozen packet/config drift")
    if (root / ".agent/coder.json").exists():
        raise ValueError("cell already executed; preserve it")
    for relative, digest in cell["initial_hashes"].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("initial source drift")
    snapshot = Path(manifest["runtime_snapshot"])
    freeze = json.loads((snapshot / "freeze.json").read_text(encoding="utf-8"))
    for relative, digest in freeze["files"].items():
        if hashlib.sha256((snapshot / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("runtime freeze drift")
    started = time.monotonic()
    explorer = None
    if case in manifest["explorer_cases"]:
        packet = json.loads(
            (root / ".agent/qual-unit-reference.json").read_text(encoding="utf-8")
        )
        question = cell.get("explorer_task") or (
            manifest["explorer_question"]
            + " Search within src/product and tests/test_target.py. "
            + packet["goal"]
        )
        exploration = subprocess.run(
            [
                sys.executable,
                str(snapshot / ".local-agents/local-explore.py"),
                "--task",
                question,
                "--task-id",
                packet["task_id"],
                "--config",
                str(root / ".agent/config.json"),
                "--report",
                str(root / ".agent/explorer.json"),
                "--full-report",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=900,
        )
        explorer = json.loads(
            (root / ".agent/explorer.json").read_text(encoding="utf-8")
        )
        verified = []
        for ref in explorer.get("source_refs", []):
            path = ref.get("path")
            if path not in cell["initial_hashes"]:
                raise ValueError("Explorer citation outside fixture")
            text = (root / path).read_text(encoding="utf-8")
            quote = ref.get("quote")
            verified.append(bool(quote and quote in text))
        write(
            root / ".agent/explorer-primary-evidence.json",
            {
                "exit": exploration.returncode,
                "status": explorer.get("status"),
                "actual_quote_checks": verified,
                "independent_success": explorer.get("status") == "success"
                and bool(verified)
                and all(verified),
                "not_overridden_by_coder": True,
            },
        )
    result = subprocess.run(
        [
            sys.executable,
            str(snapshot / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/qual-unit-reference.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=1200,
    )
    coder = json.loads((root / ".agent/coder.json").read_text(encoding="utf-8"))
    summary = {
        "classification": "supplementary capability diagnostic; original qualification remains failed",
        "case": case,
        "repetition": repetition,
        "exit": result.returncode,
        "status": coder.get("status"),
        "reason": coder.get("failure_reason"),
        "seconds": round(time.monotonic() - started, 2),
        "output": result.stdout + result.stderr,
        "primary_accepted": False,
        "explorer_status": explorer.get("status") if explorer else None,
    }
    write(root / "diagnostic-result.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--repetition", type=int, choices=(1, 2), required=True)
    parser.add_argument(
        "--cohort",
        choices=(
            "roleq-six-1",
            "roleq-binding-comparison-1",
            "roleq-boundary-comparison-1",
            "roleq-temperature-comparison-1",
            "roleq-plain-json-comparison-1",
            "roleq-vocabulary-comparison-1",
            "roleq-vocabulary-comparison-2",
            "roleq-formal-transfer-1",
            "roleq-semantic-examples-1",
            "roleq-retention-transfer-1",
            "roleq-protocol-transfer-1",
        ),
        default="roleq-six-1",
    )
    args = parser.parse_args()
    run(args.case, args.repetition, args.cohort)
