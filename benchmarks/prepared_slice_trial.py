"""Two fixed integration units through the new create-only preparation entry."""

import argparse
import os
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import installed_scope_trial as I
import limited_family_trial as L
import normal_task_trial as N
from test_installable_bounded import INSTALL

BATCH = I.BASE / "prepared-slice-live-20261022-1"
OFFLINE = I.BASE / "preparation-entry-20261022-1"
SEED = I.BASE / "packaged-profile-live-20261022-1/cells/binding-1/isolated"
ORIGIN = Path(
    "F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness/adapters/common.py"
)
ORDER = ["message-id-1", "message-id-2"]
SYMBOL = "stable_message_id"
TARGET = "src/product/code.py"
HEADER = "import hashlib\nimport json\nfrom typing import Any\n"
CONTRACT = (
    "Extend stable_message_id so a supplied built-in integer zero is a valid ID, returning '0'. "
    "Prefer a usable id over message_id; a zero id must not lose to a nonempty message_id. "
    "A message_id of integer zero is used when id is absent or unusable. All existing truthy "
    "ID values remain usable with exactly their str conversion and existing priority. False, "
    "floating-point 0.0, None, empty strings and empty containers retain their previous absence "
    "behavior; do not conflate them with integer zero. If neither candidate is usable, preserve "
    "the exact existing msg_{source_trace_id}_{index}_{16hex} fallback computed from the full "
    "original message using existing sorted JSON/default=str/separators and SHA256 semantics. "
    "Preserve signature/imports, all original message keys and nested values, no input mutation "
    "or external effects. Other functions/tests/configuration are protected."
)
REFERENCE = """def stable_message_id(source_trace_id: str, index: int, message: dict[str, Any]) -> str:
    for key in ("id", "message_id"):
        value = message.get(key)
        if value or (type(value) is int and value == 0):
            return str(value)
    digest = hashlib.sha256(
        json.dumps(message, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return f"msg_{source_trace_id}_{index}_{digest}"
"""
PUBLIC = """import hashlib
import json
import pytest
from product.code import stable_message_id

@pytest.mark.parametrize(("message", "expected"), [({"id": 0, "message_id": "later"}, "0"), ({"id": "", "message_id": 0}, "0"), ({"id": "preferred", "message_id": 0}, "preferred"), ({"id": False, "message_id": "fallback"}, "fallback")])
def test_supplied_identifiers(message, expected):
    assert stable_message_id("t", 3, message) == expected

@pytest.mark.parametrize("value", [False, 0.0, None, "", [], {}])
def test_falsey_non_integer_retains_digest(value):
    message = {"id": value, "content": "body"}
    digest = hashlib.sha256(json.dumps(message, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]
    assert stable_message_id("trace", -1, message) == f"msg_trace_-1_{digest}"
"""
PRIVATE = """import copy
import hashlib
import json
from datetime import date
from product.code import stable_message_id

def test_priority_type_cross_product_and_preservation():
    usable = [(0, "0"), (True, "True"), (-2, "-2"), (" ", " "), (["x"], "['x']"), ({"x": 1}, "{'x': 1}")]
    absent = [False, 0.0, None, "", [], {}]
    for value, expected in usable:
        for second, _ in usable:
            message = {"id": value, "message_id": second, "nested": {"kept": [0, False]}}
            before = copy.deepcopy(message)
            nested = message["nested"]
            assert stable_message_id("雪/%", 0, message) == expected
            assert message == before and message["nested"] is nested
        for first in absent:
            assert stable_message_id("t", 1, {"id": first, "message_id": value}) == expected

def test_exact_fallback_with_unsupported_json_value():
    for first in [False, 0.0, None, "", [], {}]:
        message = {"message_id": first, "created": date(2026, 10, 22), "雪": [False, 0, None]}
        expected = hashlib.sha256(json.dumps(message, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]
        assert stable_message_id("雪/%", -4, message) == f"msg_雪/%_-4_{expected}"
"""


def command(root, mode="unit", replay=None):
    args = I.command(root, mode=mode, replay=replay)
    packet = S.read(root / ".agent/packet.json")
    prepared = root / ".agent/prepared" / packet["run_id"]
    for flag, name in (("--packet", "packet.json"), ("--config", "config.json")):
        args[args.index(flag) + 1] = str(prepared / name)
    return args


def prepare(used):
    started = time.monotonic()
    suites = ET.parse(OFFLINE / "full-regression.xml").getroot().findall("testsuite")
    assert suites and all(
        int(s.get("failures", 0))
        == int(s.get("errors", 0))
        == int(s.get("skipped", 0))
        == 0
        for s in suites
    )
    origin_hash = S.sha(ORIGIN)
    start = T.extract(ORIGIN, SYMBOL)
    assert S.sha(ORIGIN) == origin_hash
    T.write(BATCH / "origin/source.py", ORIGIN.read_text(encoding="utf-8"))
    template = BATCH / "template"
    T.write(template / TARGET, HEADER + "\n\n" + start)
    T.write(template / "src/product/__init__.py", "")
    T.write(template / "tests/test_contract.py", PUBLIC)
    shutil.copyfile(SEED / "pyproject.toml", template / "pyproject.toml")
    private = BATCH / "private/test_independent.py"
    T.write(private, PRIVATE)
    reference = BATCH / "reference-checks"
    shutil.copytree(template, reference)
    (reference / TARGET).write_text(HEADER + "\n\n" + REFERENCE, encoding="utf-8")
    for root in (template, reference):
        for sub in (("check", "--select", "I", "--fix"), ("format",)):
            assert (
                T.run([S.PYTHON, "-B", "-m", "ruff", *sub, "src", "tests"], root)[
                    "exit_code"
                ]
                == 0
            )
    old = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], template)
    checks = L.checks(reference, private)
    S.save(BATCH / "task-controls.json", {"baseline": old, "reference": checks})
    assert old["exit_code"] == 1 and "2 failed" in old["stdout"]
    assert all(c["exit_code"] == 0 for c in checks)
    rows = {}
    for cell in ORDER:
        with tempfile.TemporaryDirectory(prefix="prepared-slice-install-") as directory:
            installed = Path(directory)
            INSTALL.install(S.KIT, installed, apply=True)
            root = BATCH / "cells" / cell / "isolated"
            shutil.copytree(installed, root)
        for name in ("src", "tests"):
            shutil.copytree(template / name, root / name)
        shutil.copyfile(template / "pyproject.toml", root / "pyproject.toml")
        packet = S.read(SEED / ".agent/packet.json")
        identity = {
            k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
        }
        packet.update(
            identity,
            feature_id="supplied-zero-message-id",
            goal=CONTRACT,
            primary_plan_sha256=S.sha(__file__),
        )
        packet["risk"]["reasons"] = [
            "Public identifier/fallback compatibility; preserve all legacy values except specified built-in integer zero."
        ]
        packet["owned_contract_ids"] = ["message-id"]
        packet["required_behavior"] = [
            {
                "id": "message-id",
                "text": CONTRACT,
                "risk_floor": "high",
                "implementation_ref": {"path": TARGET, "symbol": SYMBOL},
            }
        ]
        packet["acceptance_criteria"] = [
            {
                "id": "message-id",
                "text": "Exact zero priority, legacy type/fallback semantics, no mutation, complete strict profile",
            }
        ]
        packet["acceptance_scenarios"] = [
            {
                "id": "normal",
                "text": "Truthy supplied ID conversion and precedence stay unchanged",
            },
            {
                "id": "boundary",
                "text": "Built-in integer zero is usable in either slot, without treating False or 0.0 as that ID",
            },
            {
                "id": "fallback",
                "text": "Absent IDs preserve exact sorted-JSON/default=str hash of original data and no mutation",
            },
        ]
        packet["edit_targets"] = [{"path": TARGET, "anchor": "def " + SYMBOL + "("}]
        config = S.read(SEED / ".agent/config.json")
        config["coder_single_function"] = {
            "path": TARGET,
            "symbol": SYMBOL,
            "dependencies": HEADER,
        }
        spec = {
            "schema_version": 1,
            "target": {"path": TARGET, "module": "product.code", "symbol": SYMBOL},
            "source_paths": [
                TARGET,
                "src/product/__init__.py",
                "tests/test_contract.py",
                "pyproject.toml",
            ],
            "family": "json-call-model-dump-v1",
            "cases": [
                {"args": ["trace", 1, m], "kwargs": {}}
                for m in (
                    {"id": 0, "message_id": "fallback"},
                    {"id": False},
                    {"message_id": 0},
                    {"id": 0.0},
                )
            ],
        }
        for name, value in (
            ("packet", packet),
            ("config", config),
            ("capture-spec", spec),
        ):
            S.save(root / f".agent/{name}.json", value)
        prep_argv = [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-prepare.py",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--capture-spec",
            ".agent/capture-spec.json",
        ]
        for label, suffix in (("preview", []), ("apply", ["--apply"])):
            result = T.run([*prep_argv, *suffix], root)
            S.save(BATCH / "preparation" / f"{cell}-{label}.json", result)
            assert result["exit_code"] == 0
        argv = command(root, "preflight")
        argv[argv.index("--report") + 1] = str(root / ".agent/preflight.json")
        result = T.run(argv, root)
        S.save(BATCH / "preparation" / f"{cell}-preflight.json", result)
        assert result["exit_code"] == 0
        if cell == ORDER[0]:
            proof = BATCH / "full-chain-replay/isolated"
            shutil.copytree(root, proof)
            replay = proof.parent / "reference.json"
            S.save(
                replay,
                [
                    {
                        "kind": "replacement",
                        "content": T.extract(reference / TARGET, SYMBOL),
                    }
                ],
            )
            result = T.run(command(proof, replay=replay), proof, timeout=180)
            S.save(proof.parent / "process.json", result)
            assert result["exit_code"] == 0
        rows[cell] = {
            "root": str(root),
            "identity": identity,
            "target": TARGET,
            "private_tests": str(private),
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
                and not any(
                    v in p.parts
                    for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
                )
            },
        }
    S.save(BATCH / "cells.json", rows)
    pins = [
        Path(__file__),
        Path(I.__file__),
        Path(N.__file__),
        BATCH / "cells.json",
        private,
        OFFLINE / "full-regression.xml",
    ]
    pins += [
        p
        for p in (S.KIT / ".local-agents").rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".json", ".md"}
        and "__pycache__" not in p.parts
    ]
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "prepared-real-slice-integration",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "candidate": "Unchanged bounded-v1/flat-v1 execution and Reviewer; new create-only preparation entry only",
            "order": ORDER,
            "registered": 2,
            "weekly_stop": None,
            "weekly_used_start": used,
            "batch_seconds": 5400,
            "unit_seconds": 2220,
            "pins": {str(p): S.sha(p) for p in pins},
            "origin": {"path": str(ORIGIN), "sha256": origin_hash},
            "exposure": "One new requested behavior on a frozen real sibling function; two repeats, not two tasks. Detailed Primary contract/public tests are intentionally available; private tests/reference outside readable workspace.",
            "qualification_fit": "Existing local identifier-normalization family. Not broadening to cross-file changes or general algorithms.",
            "gate": "2/2 fresh Reviewer plus independent checks AND Primary full-diff acceptance; no assistance, protected drift or unsafe behavior",
            "continue_rule": "Ordinary failure is HOLD; finish remaining registered diagnostic cell. Infrastructure, protected drift, safety or fixed deadline stops, no replacement or extra attempts.",
            "roles": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context": 24576,
                "single_residency": True,
                "Explorer": "NOT_RUN: target already located",
                "Coordinator": "NOT_RUN: one cohesive unit",
            },
            "budget": {
                "coder_requests": 12,
                "effective_edits": 3,
                "post_edit_checks": 3,
                "initial_checks": 1,
                "coder_seconds": 900,
                "reviewer_requests": 16,
                "reviewer_errors": 4,
                "reviewer_seconds": 600,
                "output_tokens_per_request": 4096,
            },
            "Primary": "Prepared contract/public-private tests/reference and selected existing config; no repair/algorithm hints in live. Final source and evidence reviewed independently. Precise active time/cloud tokens unknown; no cost-saving claim.",
            "offline_preparation_seconds": time.monotonic() - started,
            "not_claimed": [
                "general production readiness",
                "unknown Reviewer defect detection",
                "cloud savings",
                "Coordinator decomposition improvement",
            ],
        },
    )
    print(
        "Prepared two fixed real-slice units; offline replay passed, zero live so far"
    )


def run(cell, used):
    registration = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == sha for p, sha in registration["pins"].items()), (
        "candidate drift"
    )
    for previous in ORDER[: ORDER.index(cell)]:
        assert not S.read(BATCH / "live-results" / previous / "result.json")[
            "stop_batch"
        ]
    row = S.read(BATCH / "cells.json")[cell]
    root = Path(row["root"])
    assert all(S.sha(root / p) == sha for p, sha in row["files"].items()), "used input"
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = 5400 - (time.time() - S.read(clock)["epoch"])
    assert remaining > 0
    record = BATCH / "live-results" / cell
    argv = command(root)
    S.save(
        record / "start.json",
        {"weekly_used_observed": used, "epoch": time.time(), "argv": argv},
    )
    started = time.monotonic()
    interrupted = False
    with (
        (record / "stdout.log").open("x", encoding="utf-8") as out,
        (record / "stderr.log").open("x", encoding="utf-8") as err,
    ):
        child = subprocess.Popen(
            argv,
            cwd=root,
            stdout=out,
            stderr=err,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        S.save(record / "process.json", {"pid": child.pid})
        try:
            child.wait(timeout=min(2220, remaining))
        except subprocess.TimeoutExpired:
            interrupted = True
            subprocess.run(
                ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
            child.wait(timeout=30)
    checks = []
    if not interrupted:
        for check in (
            [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", row["private_tests"]],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        ):
            available = min(
                started + 2220 - time.monotonic(),
                S.read(clock)["epoch"] + 5400 - time.time(),
            )
            if available <= 0:
                interrupted = True
                break
            try:
                checks.append(T.run(check, root, timeout=min(120, available)))
            except subprocess.TimeoutExpired:
                interrupted = True
                break

    def optional(name):
        path = root / ".agent" / name
        return S.read(path) if path.exists() else {}

    report, summary, reviewer = (
        optional("unit-report.json"),
        optional("unit-summary.json"),
        optional("reviewer-report.json"),
    )
    drift = [
        p for p, sha in row["files"].items() if p != TARGET and S.sha(root / p) != sha
    ]
    S.save(
        record / "result.json",
        {
            "cell": cell,
            "seconds": time.monotonic() - started,
            "exit_code": child.returncode,
            "interrupted": interrupted,
            "summary": summary,
            "coder_status": report.get("status"),
            "ledger": report.get("consolidated_harness"),
            "independent_checks": checks,
            "all_independent_pass": len(checks) == 4
            and all(c["exit_code"] == 0 for c in checks),
            "protected_drift": drift,
            "final_source_sha256": S.sha(root / TARGET),
            "assisted": False,
            "Primary_decision": "PENDING",
            "stop_batch": interrupted
            or bool(drift)
            or not summary
            or N.reviewer_failed(summary, reviewer)
            or bool(report.get("infra_failure"))
            or report.get("status") in {"interrupted", "policy_violation"},
        },
    )
    print(cell, "complete; Primary independent review pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        run(args.cell, args.weekly_used)
