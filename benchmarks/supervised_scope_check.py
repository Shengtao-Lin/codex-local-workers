"""Frozen real E/C/R probe in the currently evidenced supervised scope."""

import argparse
import copy
import json
import subprocess
import sys
import time
from pathlib import Path

import adapter_transfer_cases
import layer_isolation_cases
import typed_feedback_comparison as TYPED
from capability_fit import KIT, WORK, freeze, load_worker, write
from inherited_context_recovery import digest, read

BASE = WORK / "supervised-scope-1"
SNAPSHOT = WORK / "supervised-scope-baseline-1"
FA = TYPED.PRIOR.FA


def prepare():
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    template = read(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    transfer, refs = adapter_transfer_cases.cases(template)
    layer, _ = layer_isolation_cases.corpus(template)
    stop = next(c for c in transfer["cases"] if c["case_id"] == "async-stop")
    stop["files"]["src/product/entry.py"] = (
        "from product.target import collect_until\n\nasync def read_batch(fetch, keys):\n    return await collect_until(fetch, keys)\n"
    )
    stop["files"]["src/product/legacy.py"] = (
        "def read_all(values):\n    return [v for v in values if v]\n"
    )
    totals = next(c for c in layer["cases"] if c["case_id"] == "success-totals")
    data = {"cases": [stop, totals]}
    write(BASE / "corpus.json", data)
    FA.MIXED.CORPUS, FA.MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    cells = []
    for repetition in (1, 2):
        for case in data["cases"]:
            root = Path(
                FA.MIXED.prepare(
                    case["case_id"],
                    repetition,
                    SNAPSHOT / ".local-agents/config.json",
                    "scope",
                )["root"]
            )
            paths = [
                *case["files"],
                "pyproject.toml",
                ".agent/config.json",
                ".agent/qual-unit-reference.json",
            ]
            cells.append(
                {
                    "id": f"{case['case_id']}-r{repetition}",
                    "case": case["case_id"],
                    "repetition": repetition,
                    "root": str(root),
                    "hashes": {p: digest(root / p) for p in paths},
                }
            )
    # Reviewer controls: same contract, deliberately incomplete passing tests.
    controls = []
    control = copy.deepcopy(stop)
    control["files"] = {
        "src/product/__init__.py": "",
        "src/product/target.py": "async def collect_until(fetch, keys):\n    raise RuntimeError('initial')\n",
        "tests/test_target.py": "import asyncio\nfrom product.target import collect_until\ndef test_normal():\n    async def fetch(key):\n        return {1:7,2:None,3:9}[key]\n    assert asyncio.run(collect_until(fetch,[1,2,3]))==[7]\n    assert asyncio.run(collect_until(fetch,[]))==[]\n",
    }
    control["case_id"] = "sentinel-control"
    write(BASE / "controls-corpus.json", {"cases": [control]})
    FA.MIXED.CORPUS, FA.MIXED.WORK = BASE / "controls-corpus.json", BASE / "controls"
    for repetition in (1, 2):
        for opaque, defect in (("a", False), ("b", True)):
            root = Path(
                FA.MIXED.prepare(
                    control["case_id"],
                    repetition,
                    SNAPSHOT / ".local-agents/config.json",
                    "control-" + opaque,
                )["root"]
            )
            source = refs["async-stop"]["src/product/target.py"]
            if defect:
                source = source.replace("value is None", "not value")
            controls.append(
                {
                    "id": f"control-{opaque}-r{repetition}",
                    "root": str(root),
                    "source": source,
                    "has_defect_primary_only": defect,
                    "expected_defect": "Drops 0, False and empty string instead of stopping only at None"
                    if defect
                    else None,
                }
            )
    drivers = [
        Path(__file__).resolve(),
        Path(adapter_transfer_cases.__file__),
        Path(layer_isolation_cases.__file__),
    ]
    write(
        BASE / "manifest.json",
        {
            "feature_id": "supervised-scope-real-harness",
            "feature_risk": "medium",
            "unit_risk": "medium",
            "integration_risk": "medium",
            "contracts": [
                "protected-tests",
                "independent-review",
                "independent-explorer-score",
                "no-coordinator",
                "single-residency",
            ],
            "cells": cells,
            "controls": controls,
            "drivers": {str(p): digest(p) for p in drivers},
            "qualification_credit": False,
            "weekly_used_ceiling": 60,
            "decision": "Run 4 real units and 4 hidden/clean Reviewer controls. No same-signature blind rework. Primary adjudicates actual diffs and evidence; failures restrict scope. Explorer is independent diagnostic, no claimed savings from known synthetic fixtures.",
            "primary_active_time": None,
            "cloud_tokens": None,
        },
    )
    print("prepared 4 real units, 2 Explorer probes, 4 Reviewer controls", flush=True)


def invoke(root, name, argv):
    started = time.monotonic()
    process = subprocess.run(
        argv,
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1500,
        check=False,
    )
    result = {
        "exit": process.returncode,
        "seconds": time.monotonic() - started,
        "output": process.stdout + process.stderr,
    }
    write(root / f".agent/{name}-invocation.json", result)
    return result


def verify():
    manifest = read(BASE / "manifest.json")
    for p, sha in manifest["drivers"].items():
        if digest(Path(p)) != sha:
            raise ValueError("driver drift")
    FA.LAYER.verify_hashes(SNAPSHOT, read(SNAPSHOT / "freeze.json")["files"])
    return manifest


def unit(identity):
    manifest = verify()
    cell = next(c for c in manifest["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    FA.LAYER.verify_hashes(root, cell["hashes"])
    packet = read(root / ".agent/qual-unit-reference.json")
    if cell["case"] == "async-stop":
        question = "In src/product, which public async entry point delegates to the helper that must stop only at None while retaining other false-valued results? Trace the call to its implementation and cite the protected test asserting False is retained. Investigate this one call path, not legacy filtering. Read and cite actual files/lines."
        invoke(
            root,
            "explorer",
            [
                sys.executable,
                str(SNAPSHOT / ".local-agents/local-explore.py"),
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
        )
        report = read(root / ".agent/explorer.json")
        citations = []
        for ref in report.get("source_refs", []):
            path = ref.get("path")
            if path not in cell["hashes"]:
                citations.append(False)
                continue
            lines = (root / path).read_text(encoding="utf-8").splitlines()
            start, end = ref.get("start_line", 0), ref.get("end_line", 0)
            citations.append(
                1 <= start <= end <= len(lines)
                and ref.get("quote") == "\n".join(lines[start - 1 : end])
            )
        write(
            root / ".agent/explorer-primary-evidence.json",
            {
                "status": report.get("status"),
                "citation_checks": citations,
                "success": report.get("status") == "success"
                and bool(citations)
                and all(citations),
                "semantic_adjudication_pending": True,
            },
        )
    invoke(
        root,
        "unit",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/qual-unit-reference.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ],
    )
    independent = FA.LAYER.check(root, "primary")
    FA.LAYER.verify_hashes(
        root,
        {
            p: sha
            for p, sha in cell["hashes"].items()
            if p not in packet["scope"]["modify"]
        },
    )
    write(root / ".agent/primary-checks.json", independent)
    coder = read(root / ".agent/coder.json")
    reviewer = (
        read(root / ".agent/reviewer.json")
        if (root / ".agent/reviewer.json").exists()
        else {}
    )
    write(
        BASE / f"{identity}-result.json",
        {
            "coder_status": coder.get("status"),
            "coder_failure": coder.get("failure_reason"),
            "reviewer_decision": reviewer.get("decision"),
            "independent_all_checks": independent["all_checks_pass"],
            "primary_decision_pending": True,
        },
    )
    print(json.dumps(read(BASE / f"{identity}-result.json")), flush=True)


def control(identity):
    manifest = verify()
    cell = next(c for c in manifest["controls"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / ".agent/qual-unit-reference.json")
    config = read(root / ".agent/config.json")
    worker = load_worker(SNAPSHOT)
    runtime = worker.WorkerRuntime(root, packet, config, None)
    try:
        runtime.write_lock.acquire()
        runtime._prepare_run_archive()
        source = root / packet["scope"]["modify"][0]
        formatted = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--isolated",
                "--line-length",
                "100",
                "--stdin-filename",
                "target.py",
                "-",
            ],
            input=cell["source"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
        observed = runtime.read_file({"path": packet["scope"]["modify"][0]})
        runtime.safe_replace(
            {
                "path": packet["scope"]["modify"][0],
                "expected_sha256": observed["sha256"],
                "find": source.read_text(encoding="utf-8"),
                "replace": formatted,
            }
        )
        validation = runtime.validate(
            {"phase": "final", "contract_check": runtime.contract_check_template()}
        )
        if validation["status"] != "passed":
            raise ValueError("synthetic control preflight failed")
        _, report = runtime.execute(
            {
                "action": "FINISH_SUCCESS",
                "arguments": {
                    "summary": ["Primary-authored synthetic Reviewer control"]
                },
            }
        )
        report["synthetic_benchmark_archive"] = True
        runtime._complete_run(report)
    finally:
        runtime.close()
    request = {
        "schema_version": 1,
        "task_id": packet["task_id"],
        "unit_id": packet["unit_id"],
        "run_id": packet["run_id"],
        "review_id": "control-1",
    }
    write(root / ".agent/review-request.json", request)
    invoke(
        root,
        "reviewer",
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-review.py"),
            "--request",
            str(root / ".agent/review-request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ],
    )
    report = read(root / ".agent/reviewer.json")
    write(
        BASE / f"{identity}-result.json",
        {
            "decision": report.get("decision"),
            "findings": report.get("findings"),
            "expected_defect_primary_only": cell["expected_defect"],
            "primary_adjudication_pending": True,
        },
    )
    print(json.dumps(read(BASE / f"{identity}-result.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "unit", "control"))
    parser.add_argument("identity", nargs="?")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "unit":
        unit(args.identity)
    else:
        control(args.identity)
