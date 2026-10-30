"""No-model prototype: data-only observations from two approved immutable fixtures.

Not installed in Reviewer; no model API is called. The target, interpreter and
source snapshots are selected by Primary, never by the JSON request.
"""

import argparse
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import harness_semantic_policy as H

B = H.B
BATCH = H.BATCH.parent / "r4-probe-design-20261017-1"
TARGET = "src/evaluation_harness/adapters/common.py"
PYTHON = Path("F:/ChatGPT/agent-evaluation-harness/.venv/Scripts/python.exe")
FIXTURES = {"sample-17-candidate", "sample-18-candidate"}
MAX_INPUT = 8192
MAX_OUTPUT = 16384


def validate_request(request):
    def visit(value, depth=0):
        if depth > 8:
            raise ValueError("probe JSON nesting exceeds eight levels")
        if value is None or type(value) is bool:
            return
        if type(value) in {int, float}:
            if abs(value) > 1_000_000 or (
                type(value) is float and not math.isfinite(value)
            ):
                raise ValueError("probe number outside approved bounds")
            return
        if isinstance(value, str):
            if len(value) > 2048:
                raise ValueError("probe string too long")
            return
        if isinstance(value, (list, dict)) and len(value) <= 32:
            items = value.items() if isinstance(value, dict) else enumerate(value)
            for key, child in items:
                if isinstance(value, dict) and (
                    not isinstance(key, str) or len(key) > 128
                ):
                    raise ValueError("invalid probe JSON key")
                visit(child, depth + 1)
            return
        raise ValueError("probe accepts bounded JSON data only")

    visit(request)
    if not isinstance(request, dict) or set(request) != {"cases"}:
        raise ValueError("probe request accepts only cases; no paths/code/commands")
    cases = request["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 8:
        raise ValueError("probe requires one to eight cases")
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"parts"}:
            raise ValueError("each case contains only parts")
        parts = case["parts"]
        if not isinstance(parts, list) or not 1 <= len(parts) <= 16:
            raise ValueError("each case requires one to sixteen parts")
        for part in parts:
            if not isinstance(part, dict):
                raise TypeError("part must be an object")
            kind = part.get("type")
            keys = (
                {"type", "call_id", "name", "arguments"}
                if kind == "tool_call"
                else {"type", "call_id", "result"}
            )
            if kind not in {"tool_call", "tool_result"} or set(part) != keys:
                raise ValueError(
                    "only approved tool_call/tool_result data fields are accepted"
                )
            if (
                not isinstance(part["call_id"], str)
                or not 1 <= len(part["call_id"]) <= 128
            ):
                raise ValueError("call_id must be a bounded nonempty string")
            if kind == "tool_call" and (
                not isinstance(part["name"], str)
                or not isinstance(part["arguments"], dict)
            ):
                raise ValueError("tool call needs string name and object arguments")
    if (
        len(json.dumps(request, ensure_ascii=False, allow_nan=False).encode())
        > MAX_INPUT
    ):
        raise ValueError("probe request exceeds eight KiB")
    return request


def fixture(name):
    if name not in FIXTURES:
        raise ValueError("fixture is not approved for this offline prototype")
    H.audit()
    row = next(
        r for r in B.read(H.BATCH / "registration.json")["cells"] if r["id"] == name
    )
    root = Path(row["root"])
    if not root.resolve().is_relative_to((B.KIT / "benchmarks/work").resolve()):
        raise ValueError("fixture escapes kit work directory")
    H.R.assert_files(root, row["files"])
    return row


def observe_child(name, request):
    validate_request(request)
    row = fixture(name)
    root = Path(row["root"])
    sys.path.insert(0, str(root / "src"))
    module = importlib.import_module("evaluation_harness.adapters.common")
    if Path(module.__file__).resolve() != (root / TARGET).resolve():
        raise ValueError("probe imported source from a different snapshot")
    observations = []
    for case in request["cases"]:
        parts = []
        for part in case["parts"]:
            data = {key: value for key, value in part.items() if key != "type"}
            cls = (
                module.ToolCallPart
                if part["type"] == "tool_call"
                else module.ToolResultPart
            )
            parts.append(cls(**data))
        messages = [
            module.CanonicalMessage(
                message_id="observation", role="assistant", content=parts
            )
        ]
        before = [m.model_dump(mode="json") for m in messages]
        try:
            returned = module.collect_tools(messages)
            projected = [
                {
                    key: item.model_dump(mode="json")[key]
                    for key in ("call_id", "name", "arguments", "result", "status")
                }
                for item in returned
            ]
            outcome = {"kind": "returned", "value": projected}
        except (
            TypeError,
            ValueError,
            AttributeError,
            KeyError,
            IndexError,
            RuntimeError,
        ) as exc:
            outcome = {
                "kind": "raised",
                "type": type(exc).__name__,
                "message": str(exc)[:1000],
            }
        observations.append(
            {
                "input_before": before,
                "input_after": [m.model_dump(mode="json") for m in messages],
                "outcome": outcome,
            }
        )
    H.R.assert_files(root, row["files"])
    result = {
        "execution_completed": True,
        "profile_id": "collect-tools-json-observation-v1",
        "source": {"path": TARGET, "sha256": B.sha(root / TARGET)},
        "projection": ["call_id", "name", "arguments", "result", "status"],
        "observations": observations,
        "semantic_verdict": None,
    }
    text = json.dumps(result, ensure_ascii=False, allow_nan=False)
    if len(text.encode()) > MAX_OUTPUT:
        return {
            "execution_completed": False,
            "reason": "observation_output_too_large",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "bytes": len(text.encode()),
        }
    return result


def execute(name, request, archive):
    # Validate before launching any process or creating request/output artifacts.
    validate_request(request)
    row = fixture(name)
    archive = Path(archive)
    if not archive.resolve().is_relative_to(BATCH.resolve()):
        raise ValueError(
            "offline observation archive must stay in its own design batch"
        )
    B.save(archive / "request.json", request)
    argv = [
        str(PYTHON),
        "-B",
        str(Path(__file__).resolve()),
        "child",
        "--fixture",
        name,
        "--request",
        str((archive / "request.json").resolve()),
    ]
    proc = subprocess.run(
        argv,
        cwd=row["root"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(Path(row["root"]) / "src"),
        },
    )
    B.save(
        archive / "execution.json",
        {
            "argv": argv,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timeout_seconds": 30,
        },
    )
    if proc.returncode != 0:
        raise ValueError("approved observation child failed; inspect execution.json")
    result = json.loads(proc.stdout)
    H.R.assert_files(Path(row["root"]), row["files"])
    B.save(archive / "observation.json", result)
    return result


def boundary_request():
    return {
        "cases": [
            {
                "parts": [
                    {
                        "type": "tool_call",
                        "call_id": "a",
                        "name": "tool",
                        "arguments": {},
                    },
                    {"type": "tool_result", "call_id": "a", "result": value},
                ]
            }
            for value in (None, False, 0, "", [], {})
        ]
    }


def prepare(used):
    assert 0 <= used < 50
    H.audit()
    BATCH.mkdir(exist_ok=False)
    B.save(
        BATCH / "registration.json",
        {
            "feature_id": "reviewer-data-only-observation-design",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "rationale": "New model-proposed input surface would need explicit execution authority; this stage is offline-only.",
            "owned_contract_ids": [
                "fixed-target-binding",
                "data-only-input",
                "immutable-source",
                "no-semantic-oracle",
            ],
            "dependencies": {
                str(H.BATCH / "decision.json"): B.sha(H.BATCH / "decision.json")
            },
            "weekly_used_start": used,
            "usage_ceiling": 50,
            "model_calls": 0,
            "live_authorized": False,
            "approved_offline_fixtures": {
                name: fixture(name)["files"][TARGET] for name in sorted(FIXTURES)
            },
            "limits": {
                "cases": 8,
                "parts_per_case": 16,
                "input_bytes": MAX_INPUT,
                "output_bytes": MAX_OUTPUT,
                "child_timeout_seconds": 30,
            },
            "criterion": "Offline source-bound observations match actual None versus other falsy behavior, reject code/path/root injection and bounds violations before process launch. No Reviewer/R4 capability credit.",
            "production_installed": False,
            "new_reviewer_live_started": False,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "demonstrate", "child"])
    parser.add_argument("--used", type=int)
    parser.add_argument("--fixture")
    parser.add_argument("--request")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.used)
    elif args.action == "child":
        print(
            json.dumps(
                observe_child(args.fixture, B.read(Path(args.request))),
                ensure_ascii=False,
            )
        )
    else:
        for name in sorted(FIXTURES):
            result = execute(name, boundary_request(), BATCH / name)
            print(
                {
                    "fixture": name,
                    "execution_completed": result["execution_completed"],
                    "statuses": [
                        o["outcome"]["value"][0]["status"]
                        for o in result["observations"]
                    ],
                }
            )
