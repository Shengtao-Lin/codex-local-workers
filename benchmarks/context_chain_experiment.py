"""Frozen long-chain Reviewer pairs and Coder visibility measurement."""

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time

from capability_fit import KIT, WORK, load_worker, write
from context_chain_case import BOUNDARY_TEST, CONTRACT, FILES, HIDDEN, PUBLIC_TESTS

BASE = WORK / "roleq-context-chain-1"
SNAPSHOT = WORK / "roleq-context-candidate-1"
TEMPLATE = WORK / "roleq-six-1/runs/v1/roleq1/timeout-roundtrip-round-1/.agent"
BASELINE = "def quote(cart, discount_percent=0, destination='home'):\n    raise RuntimeError('not implemented')\n"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    BASE.mkdir(exist_ok=False)
    cells = [
        "reviewer-hidden-off",
        "reviewer-hidden-on",
        "reviewer-clean-on",
        "reviewer-clean-off",
        "coder-recent",
        "coder-budgeted",
    ]
    write(
        BASE / "plan.json",
        {
            "feature_id": "long-investigation-context",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "contracts": [
                "immutable-history",
                "independent-source-evidence",
                "no-qualification-credit-for-scripted-reads",
            ],
            "risk_rationale": "Admission evidence and instrumentation must not substitute scripted work for autonomous agent results.",
            "functional_unit_risk": "medium; isolated Decimal quote calculations, no persistent transactions or public migration",
            "cells": cells,
            "runtime": str(SNAPSHOT),
            "weekly_ceiling": 40,
            "reviewer_axis": "same candidate runtime; context recovery on/off; hidden/clean fresh contexts",
            "coder_axis": "recent/budgeted context retention only; other protocols unchanged; focused full acceptance tests",
            "criterion": "Actual visibility/eviction and restoration plus independently adjudicated semantic results; no restoration means no efficacy inference",
            "conditional_followup": "If natural review does not restore context, at most one hidden off/on scripted-prefix diagnostic, explicitly not autonomous qualification",
            "model_calls_max": "4 review + 2 coder + automatic review for successful coders; conditional diagnostic at most 2 review",
            "coordinator_started": False,
            "explorer": "N/A: fixture paths supplied; no discovery score claimed",
            "private_boundary": BOUNDARY_TEST,
        },
    )
    driver_hashes = {
        name: digest(KIT / "benchmarks" / name)
        for name in [
            "context_chain_case.py",
            "context_chain_experiment.py",
            "context_request_observer.py",
        ]
    }
    manifest = {"drivers": driver_hashes, "cells": {}}
    worker = load_worker(SNAPSHOT)
    for label in cells:
        root = BASE / label
        root.mkdir()
        coder = label.startswith("coder")
        sources = copy.deepcopy(FILES)
        sources["src/shop/quote.py"] = HIDDEN if coder else BASELINE
        sources["tests/test_quote.py"] = PUBLIC_TESTS + (
            "\n" + BOUNDARY_TEST.replace("from shop.quote import quote\n", "")
            if coder
            else ""
        )
        for relative, text in sources.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        (root / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\npythonpath=["src"]\n[tool.ruff.lint]\nselect=["E4","E7","E9","F"]\n',
            encoding="utf-8",
        )
        config = read(TEMPLATE / "config.json")
        config["reviewer_context_recovery"] = (
            label.endswith("on") if not coder else False
        )
        if coder:
            config["coder_context_retention"] = label.split("-", 1)[1]
        packet = read(TEMPLATE / "qual-unit-reference.json")
        identity = "context-chain-" + label
        packet.update(
            task_id=identity,
            feature_id=identity,
            run_id=identity + "-a1",
            goal=CONTRACT,
        )
        packet["scope"].update(
            modify=["src/shop/quote.py"],
            readonly=[p for p in sources if p != "src/shop/quote.py"],
        )
        packet["edit_targets"] = [{"path": "src/shop/quote.py", "anchor": "def quote"}]
        packet["focused_tests"] = ["tests/test_quote.py"]
        packet["required_behavior"] = [
            {"id": "qual-unit", "risk_floor": "medium", "text": CONTRACT}
        ]
        packet["acceptance_scenarios"] = [
            {"id": k, "text": t, "observables": {k: True}}
            for k, t in [
                (
                    "normal",
                    "Catalog, shipping and tax are applied without input mutation",
                ),
                ("error", "Unknown SKU and invalid quantity are rejected"),
                (
                    "boundary",
                    "Fractional-cent total is rounded once after all operations",
                ),
            ]
        ]
        worker.validate_packet(packet)
        write(root / ".agent/config.json", config)
        write(root / ".agent/packet.json", packet)
        subprocess.run(
            [sys.executable, "-m", "ruff", "format", "src", "tests"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        if not coder:
            final = HIDDEN if "hidden" in label else FILES["src/shop/quote.py"]
            temporary = root / "reference.py"
            temporary.write_text(final, encoding="utf-8")
            subprocess.run(
                [sys.executable, "-m", "ruff", "format", str(temporary)],
                check=True,
                capture_output=True,
            )
            runtime = worker.WorkerRuntime(root, packet, config, None)
            runtime.write_lock.acquire()
            try:
                runtime._prepare_run_archive()
                observed = runtime.read_file({"path": "src/shop/quote.py"})
                runtime.safe_replace(
                    {
                        "path": "src/shop/quote.py",
                        "expected_sha256": observed["sha256"],
                        "find": (root / "src/shop/quote.py").read_text(
                            encoding="utf-8"
                        ),
                        "replace": temporary.read_text(encoding="utf-8"),
                    }
                )
                assert (
                    runtime.validate(
                        {
                            "phase": "final",
                            "contract_check": runtime.contract_check_template(),
                        }
                    )["status"]
                    == "passed"
                )
                _, report = runtime.execute(
                    {
                        "action": "FINISH_SUCCESS",
                        "arguments": {
                            "summary": [
                                "Primary synthetic reviewer control; Coder not invoked"
                            ]
                        },
                    }
                )
                report["synthetic_benchmark_archive"] = True
                runtime._complete_run(report)
            finally:
                runtime.close()
            write(
                root / ".agent/request.json",
                {
                    "schema_version": 1,
                    "task_id": identity,
                    "unit_id": "qual-unit",
                    "run_id": packet["run_id"],
                    "review_id": "chain-1",
                },
            )
        manifest["cells"][label] = {
            "files": {
                p: digest(root / p)
                for p in [
                    *sources,
                    "pyproject.toml",
                    ".agent/config.json",
                    ".agent/packet.json",
                ]
            }
        }
    write(BASE / "manifest.json", manifest)
    print(str(BASE), flush=True)


def run(label):
    manifest = read(BASE / "manifest.json")
    root = BASE / label
    for name, sha in manifest["drivers"].items():
        if digest(KIT / "benchmarks" / name) != sha:
            raise ValueError("driver drift: " + name)
    for path, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / path) != sha:
            raise ValueError("runtime drift")
    for path, sha in manifest["cells"][label]["files"].items():
        if digest(root / path) != sha:
            raise ValueError("cell drift: " + path)
    if (root / "result.json").exists() or (root / "requests.jsonl").exists():
        raise ValueError("cell already started")
    role = "coder" if label.startswith("coder") else "reviewer"
    argument = "--packet" if role == "coder" else "--request"
    source = ".agent/packet.json" if role == "coder" else ".agent/request.json"
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            str(KIT / "benchmarks/context_request_observer.py"),
            "--snapshot",
            str(SNAPSHOT),
            "--role",
            role,
            "--trace",
            str(root / "requests.jsonl"),
            argument,
            str(root / source),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/report.json"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=1200,
    )
    record = {
        "label": label,
        "seconds": round(time.monotonic() - started, 2),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "primary_accepted": False,
    }
    write(root / "result.json", record)
    print(
        json.dumps({k: v for k, v in record.items() if k not in {"stdout", "stderr"}}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument(
        "--run",
        choices=(
            "reviewer-hidden-off",
            "reviewer-hidden-on",
            "reviewer-clean-on",
            "reviewer-clean-off",
            "coder-recent",
            "coder-budgeted",
        ),
    )
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        run(args.run)
    else:
        parser.error("choose prepare or run")
