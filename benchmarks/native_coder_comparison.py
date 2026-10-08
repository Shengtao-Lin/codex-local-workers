"""Four bounded fresh cells: current JSON envelope versus typed native tools."""

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import mixed_feature_benchmark as MIXED
from capability_fit import KIT, WORK, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-native-coder-1"
SNAPSHOT = WORK / "roleq-final-channel-candidate-1"
ADAPTER = KIT / "benchmarks/native_coder_adapter.py"
ORDER = (
    "window-groups-envelope",
    "window-groups-native",
    "timeout-roundtrip-native",
    "timeout-roundtrip-envelope",
)


def prepare():
    BASE.mkdir(exist_ok=False)
    corpus = read(WORK / "roleq-boundary-comparison-1/corpus.json")
    write(BASE / "corpus.json", corpus)
    MIXED.CORPUS, MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    worker = load_worker(SNAPSHOT)
    cells = []
    for label in ORDER:
        case, arm = label.rsplit("-", 1)
        root = Path(
            MIXED.prepare(case, 1, SNAPSHOT / ".local-agents/config.json", "nt1" + arm)[
                "root"
            ]
        )
        packet = read(root / ".agent/qual-unit-reference.json")
        worker.validate_packet(packet)
        files = next(c for c in corpus["cases"] if c["case_id"] == case)["files"]
        cells.append(
            {
                "label": label,
                "root": str(root),
                "arm": arm,
                "hashes": {
                    p: digest(root / p)
                    for p in [
                        *files,
                        "pyproject.toml",
                        ".agent/config.json",
                        ".agent/qual-unit-reference.json",
                    ]
                },
            }
        )
    write(
        BASE / "manifest.json",
        {
            "classification": "Known development families, not unseen qualification; no Primary semantic hints",
            "feature_id": "typed-native-coder-diagnostic",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Adapter must preserve current action gates and canonical acceptance authority",
            "contracts": [
                "unchanged-contract-and-scope",
                "typed-protocol-only",
                "independent-acceptance",
            ],
            "axis": "Native named tools with typed parameter schemas plus necessary protocol-header adaptation; not a pure sampling or semantic-prompt comparison",
            "fixed": "Same model/quantization, sampling, context, budgeted retention, runtime guards, protected tests, contracts and limits; no production configuration promotion",
            "cells": cells,
            "order": ORDER,
            "coder_calls_max": 4,
            "retries": 0,
            "stop": "One call per cell; both native failures close the route. Successful cells require verified handoff, Reviewer and Primary; no repeat-until-success.",
            "reviewer_policy": "Only after actual Coder validation/handoff; failures never count as pass",
            "explorer": "N/A: locations known, this tests Coder protocol not localization",
            "coordinator_started": False,
            "weekly_used_ceiling": 60,
            "snapshot": str(SNAPSHOT),
            "drivers": {
                str(p): digest(p)
                for p in (
                    Path(__file__),
                    ADAPTER,
                    KIT / "benchmarks/mixed_feature_benchmark.py",
                )
            },
        },
    )


def run(label):
    manifest = read(BASE / "manifest.json")
    for path, sha in manifest["drivers"].items():
        if digest(Path(path)) != sha:
            raise ValueError("driver drift")
    for relative, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / relative) != sha:
            raise ValueError("runtime drift")
    cell = next(c for c in manifest["cells"] if c["label"] == label)
    root = Path(cell["root"])
    for relative, sha in cell["hashes"].items():
        if digest(root / relative) != sha:
            raise ValueError("input drift: " + relative)
    write(BASE / f"{label}-started.json", {"at": time.time()})
    prefix = (
        [str(ADAPTER), "--snapshot", str(SNAPSHOT)]
        if cell["arm"] == "native"
        else [str(SNAPSHOT / ".local-agents/local-code.py")]
    )
    started = time.monotonic()
    coder = subprocess.run(
        [
            sys.executable,
            *prefix,
            "--packet",
            str(root / ".agent/qual-unit-reference.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/coder.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    report = read(root / ".agent/coder.json")
    result = {
        "coder_exit": coder.returncode,
        "coder_status": report.get("status"),
        "coder_seconds": time.monotonic() - started,
        "coder_output": coder.stdout + coder.stderr,
        "reviewer": None,
        "primary_accepted": False,
    }
    write(BASE / f"{label}-coder-result.json", result)
    if coder.returncode == 0 and report.get("status") == "ready_for_review":
        spec = importlib.util.spec_from_file_location(
            "native_handoff", SNAPSHOT / ".local-agents/local-unit.py"
        )
        unit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unit)
        identity = unit.verify_handoff(root, report)
        request = root / ".agent/native-comparison-review-request.json"
        write(
            request,
            {"schema_version": 1, **identity, "review_id": "native-comparison-1"},
        )
        reviewed = subprocess.run(
            [
                sys.executable,
                str(SNAPSHOT / ".local-agents/local-review.py"),
                "--request",
                str(request),
                "--config",
                str(root / ".agent/config.json"),
                "--report",
                str(root / ".agent/reviewer.json"),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        result["reviewer"] = {
            "exit": reviewed.returncode,
            "report": read(root / ".agent/reviewer.json"),
            "output": reviewed.stdout + reviewed.stderr,
        }
    result["total_seconds"] = time.monotonic() - started
    write(BASE / f"{label}-result.json", result)
    print(
        json.dumps(
            {
                "label": label,
                "coder": result["coder_status"],
                "reviewer": result["reviewer"]["report"].get("decision")
                if result["reviewer"]
                else None,
                "seconds": result["total_seconds"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", *ORDER))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(args.action)
