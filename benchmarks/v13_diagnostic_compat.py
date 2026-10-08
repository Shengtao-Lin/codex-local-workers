"""Create-only stage A compatibility fixtures and explicitly synthetic runtime audit.

Not a capability cohort or release qualification. Uses unchanged frozen models.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
WORK = KIT / "benchmarks/work/capability-fit"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("v1", "v2", "audit"))
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--trial", default="1")
    args = parser.parse_args()
    if any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-"
        for c in args.snapshot + args.trial
    ):
        raise ValueError("invalid identity")
    snapshot = WORK / args.snapshot
    manifest = json.loads((snapshot / "freeze.json").read_text(encoding="utf-8"))
    for relative, digest in manifest["files"].items():
        if hashlib.sha256((snapshot / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("snapshot drift: " + relative)
    root = WORK / f"v13-compat-{args.mode}-{args.trial}"
    root.mkdir(exist_ok=False)
    shutil.copytree(snapshot / ".local-agents", root / ".local-agents")
    (root / "src").mkdir()
    (root / "tests").mkdir()
    config = json.loads((snapshot / ".local-agents/config.json").read_text())
    config["python"] = sys.executable
    config["validation_profiles"] = {
        "v13-strict": {
            "python": sys.executable,
            "compile": True,
            "pytest_argv": ["-B", "-m", "pytest"],
            "commands": [
                {
                    "id": "ruff-check",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "check",
                        "--config",
                        "ruff.toml",
                        "src",
                        "tests",
                    ],
                },
                {
                    "id": "ruff-format",
                    "argv": [
                        "{python}",
                        "-m",
                        "ruff",
                        "format",
                        "--check",
                        "--config",
                        "ruff.toml",
                        "src",
                        "tests",
                    ],
                },
            ],
        }
    }
    shutil.copyfile(snapshot / ".local-agents/ruff.toml", root / "ruff.toml")
    source = "VALUE = 1\n"
    (root / "src/value.py").write_text(source, encoding="utf-8")
    (root / "tests/test_value.py").write_text(
        "from src.value import VALUE\n\n\ndef test_value():\n    assert VALUE == 2\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["."]\n', encoding="utf-8"
    )
    identity = f"v13-{args.mode}-{args.trial}"
    contracts = [
        {"id": "value-two", "text": "VALUE equals 2; protected test remains unchanged."}
    ]
    writable = ["src/value.py"]
    tests = ["tests/test_value.py"]
    anchors = ["VALUE"]
    if args.mode == "audit":
        shutil.copytree(snapshot / ".local-agents", root / "src", dirs_exist_ok=True)
        writable = ["src/worker-runtime.py", "src/local-unit.py"]
        tests = ["src/tests/test_worker_runtime.py", "src/tests/test_local_unit.py"]
        anchors = ["_is_repair_edit", "verify_handoff"]
        contracts = [
            {
                "id": "repair-budget-accounting",
                "text": "Fresh failed baseline does not spend the initial implementation's repair budget; inherited calls remain bounded repairs and never reuse parent validation.",
            },
            {
                "id": "diagnostic-not-acceptance",
                "text": "Check accepts boolean false/null ordering acknowledgements without converting them to proof; final/finish requires complete current acknowledgements. Green fresh unedited baseline is not submission.",
            },
            {
                "id": "fresh-validation-handoff",
                "text": "Handoff independently rejects diagnostic-only acknowledgement and preserves nonzero JUnit, freshness, identity, protected inputs and scope attribution gates.",
            },
        ]
        for relative in writable:
            shutil.copyfile(
                WORK / "v13-a-before-1" / ".local-agents" / Path(relative).name,
                root / relative,
            )
    packet = {
        "schema_version": 2,
        "task_id": identity,
        "feature_id": identity,
        "unit_id": "implementation",
        "run_id": identity + "-a1",
        "plan_revision": 1,
        "packet_revision": 1,
        "goal": "Review the actual stage A runtime delta independently; examine both submission paths and tests."
        if args.mode == "audit"
        else "Change VALUE from 1 to 2. Run a diagnostic check before editing, using false or null acknowledgements for unmet/unknown ordering, then submit only after current verification.",
        "scope": {
            "read": ["src", "tests"],
            "modify": writable,
            "create": [],
            "readonly": tests,
            "forbidden": [".git", ".agent", ".local-agents"],
        },
        "edit_targets": [{"path": p, "anchor": a} for p, a in zip(writable, anchors)],
        "required_behavior": contracts,
        "owned_contract_ids": [item["id"] for item in contracts],
        "risk": {
            "feature": "high" if args.mode == "audit" else "medium",
            "unit": "high" if args.mode == "audit" else "medium",
            "integration": "high" if args.mode == "audit" else "medium",
            "reasons": [
                "State/submission audit"
                if args.mode == "audit"
                else "Frozen protocol compatibility, not capability qualification"
            ],
        },
        "dependencies": [],
        "focused_tests": tests,
        "validation_profile": "v13-strict",
        "contract_check_required": True,
        "required_order": []
        if args.mode == "audit"
        else ["Implement VALUE = 2 before claiming the target behavior is verified."],
        "forbidden_orderings": []
        if args.mode == "audit"
        else ["Never submit the initial VALUE = 1 as completed implementation."],
        "acceptance_criteria": [
            {
                "id": "protected",
                "text": "Protected tests, Ruff check and format check pass.",
            }
        ],
        "acceptance_scenarios": [
            {
                "id": "normal",
                "text": "Current implementation satisfies protected checks.",
            }
        ],
    }
    if args.mode == "v1":
        packet["schema_version"] = 1
        packet["required_behavior"] = [item["text"] for item in contracts]
        packet["acceptance_criteria"] = ["Protected tests and Ruff pass."]
        del packet["owned_contract_ids"]
    if args.mode == "audit":
        navigation = []
        for filename, symbols in {
            "worker-runtime.py": [
                "resolve_inherited_packet",
                "_is_repair_edit",
                "_record_edit",
                "_assert_submission_contract",
                "_contract_check",
                "validate",
            ],
            "local-unit.py": ["verify_handoff"],
        }.items():
            lines = (
                (snapshot / ".local-agents" / filename)
                .read_text(encoding="utf-8")
                .splitlines()
            )
            for symbol in symbols:
                line = next(
                    i for i, text in enumerate(lines, 1) if f"def {symbol}(" in text
                )
                navigation.append(f"src/{filename}:{line} {symbol}")
        packet["goal"] += (
            " Review the stage A changed methods, not every unrelated runtime subsystem. Navigation hints (read current source; these are not proof): "
            + "; ".join(navigation)
            + ". The passing full focused suite is execution evidence, not semantic proof. Read the new v13 tests at the start of both focused files, inspect submission and handoff independently, then REPORT concrete defects or a source-backed decision."
        )
        # Goal is not part of Reviewer input. Navigation is advisory, not proof.
        packet["review_feedback"] = [
            {"text": packet["goal"], "verify_in_review": False}
        ]
    write(root / ".agent/packet.json", packet)
    write(root / ".agent/config.json", config)
    write(
        root / "experiment.json",
        {
            "snapshot": args.snapshot,
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "mode": args.mode,
            "synthetic_archive": args.mode == "audit",
            "capability_score": None,
            "cloud_tokens": None,
            "coordinator_invoked": False,
            "explorer_invoked": False,
        },
    )
    started = time.monotonic()
    if args.mode == "audit":
        spec = importlib.util.spec_from_file_location(
            "v13_audit_worker", root / ".local-agents/worker-runtime.py"
        )
        worker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = worker
        spec.loader.exec_module(worker)
        runtime = worker.WorkerRuntime(root, packet, config, None)
        runtime.write_lock.acquire()
        try:
            runtime._prepare_run_archive()
            for relative in writable:
                observed = runtime.read_file({"path": relative})
                replacement = (
                    snapshot / ".local-agents" / Path(relative).name
                ).read_text(encoding="utf-8")
                runtime.safe_replace(
                    {
                        "path": relative,
                        "expected_sha256": observed["sha256"],
                        "find": (root / relative).read_text(encoding="utf-8"),
                        "replace": replacement,
                    }
                )
            result = runtime.validate(
                {"phase": "final", "contract_check": runtime.contract_check_template()}
            )
            if result["status"] != "passed":
                raise ValueError(
                    "Synthetic audit validation failed: " + json.dumps(result)
                )
            if {item["id"] for item in runtime.validation.configured_checks} != {
                "ruff-check",
                "ruff-format",
            }:
                raise ValueError(
                    "Synthetic audit did not execute registered static checks"
                )
            _, report = runtime.execute(
                {
                    "action": "FINISH_SUCCESS",
                    "arguments": {
                        "summary": [
                            "Primary-authored stage A delta; synthetic archive, NOT Coder performance."
                        ]
                    },
                }
            )
            report["synthetic_benchmark_archive"] = True
            runtime._complete_run(report)
        finally:
            runtime.close()
        request = {
            "schema_version": 1,
            "task_id": identity,
            "unit_id": "implementation",
            "run_id": identity + "-a1",
            "review_id": "independent-audit-1",
        }
        write(root / ".agent/review-request.json", request)
        argv = [
            sys.executable,
            str(root / ".local-agents/local-review.py"),
            "--request",
            str(root / ".agent/review-request.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--report",
            str(root / ".agent/reviewer.json"),
        ]
    else:
        argv = [
            sys.executable,
            str(root / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/packet.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ]
    completed = subprocess.run(
        argv,
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    write(
        root / "process-result.json",
        {
            "exit_code": completed.returncode,
            "seconds": time.monotonic() - started,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )
    print(
        json.dumps(
            {
                "root": str(root),
                "exit_code": completed.returncode,
                "seconds": time.monotonic() - started,
            }
        )
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
