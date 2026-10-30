"""New contracts on read-only sibling source slices; references never enter Worker roots."""

import argparse
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import function_repeat_trial as OLD
from supervised_release_checkpoint import BATCH

UP = Path("F:/ChatGPT/agent-evaluation-harness/src/evaluation_harness")
ORDER = ["ids-1", "json-1", "raw-1", "raw-2", "json-2", "ids-2"]
TASKS = {
    "ids": {
        "origin": "adapters/common.py",
        "symbol": "stable_message_id",
        "header": "from __future__ import annotations\nimport hashlib\nimport json\nfrom typing import Any\n",
        "contract": "Preserve the existing stable_message_id signature and fallback hash exactly. Explicit id takes precedence over message_id. Treat only None and the empty string as absent: 0 and False are valid explicit identifiers, returned through str. If id is absent use message_id under the same rule, otherwise use the existing fallback, calculated from the ORIGINAL complete message. Do not mutate input. All existing nonempty identifiers and hash canonicalization retain behavior.",
        "reference": """def stable_message_id(source_trace_id: str, index: int, message: dict[str, Any]) -> str:
    for key in ("id", "message_id"):
        value = message.get(key)
        if value is not None and value != "":
            return str(value)
    digest = hashlib.sha256(json.dumps(message, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:16]
    return f"msg_{source_trace_id}_{index}_{digest}"
""",
        "public": """import copy
import hashlib
import json
import pytest
from product.code import stable_message_id

@pytest.mark.parametrize(("payload", "expected"), [({"id": 0, "message_id": "other"}, "0"), ({"id": False}, "False"), ({"id": None, "message_id": "m"}, "m"), ({"id": "", "message_id": 0}, "0"), ({"id": "a", "message_id": "b"}, "a")])
def test_explicit(payload, expected):
    before = copy.deepcopy(payload)
    assert stable_message_id("trace", 2, payload) == expected
    assert payload == before

def test_fallback():
    payload = {"id": None, "message_id": "", "body": {"雪": [0, False]}}
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    assert stable_message_id("trace", 2, payload) == "msg_trace_2_" + hashlib.sha256(encoded).hexdigest()[:16]
""",
        "private": """import pytest
from product.code import stable_message_id

@pytest.mark.parametrize(("payload", "expected"), [({"id": " ", "message_id": "b"}, " "), ({"message_id": False}, "False"), ({"id": None, "message_id": False}, "False"), ({"id": 0.0}, "0.0"), ({"id": -2}, "-2")])
def test_independent_precedence(payload, expected):
    assert stable_message_id("trace", 0, payload) == expected
""",
        "cases": [
            {"args": ["t", 1, v], "kwargs": {}}
            for v in ({"id": 0}, {"message_id": False}, {"id": "x"}, {})
        ],
    },
    "json": {
        "origin": "canonical/fingerprint.py",
        "symbol": "canonical_json",
        "header": "from __future__ import annotations\nimport json\nfrom typing import Any\n",
        "contract": "Keep canonical_json returning deterministic UTF-8 bytes with non-ASCII characters unescaped, sorted keys and compact separators. Retain default=str for unsupported objects and all existing finite JSON behavior. Reject nonfinite float values (NaN, positive/negative infinity) with ValueError wherever the JSON encoder encounters them, including nested arrays/objects and numeric keys. Do not mutate data or alter signature. Do not reject a string merely because it spells NaN/Infinity, or require unsupported objects to become JSON-native.",
        "reference": """def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")
""",
        "public": """from datetime import date
import pytest
from product.code import canonical_json

def test_encoding():
    assert canonical_json({"b": [False, 0, None], "a": "雪"}) == '{"a":"雪","b":[false,0,null]}'.encode()
    assert canonical_json(date(2026, 1, 2)) == b'"2026-01-02"'

@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), {"x": [float("nan")]}])
def test_nonfinite(value):
    with pytest.raises(ValueError):
        canonical_json(value)

def test_strings():
    assert canonical_json(["NaN", "Infinity"]) == b'["NaN","Infinity"]'
""",
        "private": """import pytest
from product.code import canonical_json

@pytest.mark.parametrize("value", [{float("nan"): 1}, [1, {"x": float("-inf")}], {"x": (float("inf"),)}])
def test_independent_nonfinite(value):
    with pytest.raises(ValueError):
        canonical_json(value)

def test_finite_nonmutation():
    value = {"negative": -0.0, "tiny": 1e-200}
    assert canonical_json(value) == b'{"negative":-0.0,"tiny":1e-200}'
    assert value == {"negative": -0.0, "tiny": 1e-200}
""",
        "cases": [
            {"args": [v], "kwargs": {}} for v in ({"a": "雪"}, [False, None, 0], "NaN")
        ],
    },
    "raw": {
        "origin": "adapters/common.py",
        "symbol": "mapping_raw",
        "header": "from __future__ import annotations\nimport json\nfrom typing import Any, cast\nfrom product.dependencies import AdapterError, SourceTrace\n",
        "contract": "Extend mapping_raw to accept bytes and bytearray containing STRICT UTF-8 JSON objects, alongside existing dictionary and JSON-string inputs. UTF-8 decoding failure or invalid JSON must raise the real AdapterError with reason invalid_json, chaining the original cause. Valid JSON with non-object root remains unsupported_shape. Existing dictionary inputs must retain object identity; preserve the existing string path and rejection reasons. Never mutate trace.raw or bytearray data. Signature and dependencies remain unchanged. UTF-16/32 are not permitted byte encodings.",
        "reference": """def mapping_raw(trace: SourceTrace) -> dict[str, Any]:
    raw = trace.raw
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AdapterError("invalid_json", "trace payload is not valid JSON") from exc
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdapterError("invalid_json", "trace payload is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise AdapterError("unsupported_shape", "trace payload must be an object")
    return cast(dict[str, Any], raw)
""",
        "public": """from datetime import UTC, datetime
import pytest
from product.code import mapping_raw
from product.dependencies import AdapterError, SourceTrace

def trace(raw):
    return SourceTrace(source_trace_id="t", observed_at=datetime(2026, 1, 1, tzinfo=UTC), raw=raw)

@pytest.mark.parametrize("raw", [b'{"x":0}', bytearray(b'{"x":0}'), '{"x":0}'])
def test_object(raw):
    t = trace(raw)
    assert mapping_raw(t) == {"x": 0}
    assert t.raw == raw

def test_identity():
    t = trace({"x": []})
    assert mapping_raw(t) is t.raw

@pytest.mark.parametrize(("raw", "reason"), [(b"\\xff", "invalid_json"), (b"{", "invalid_json"), (b"[]", "unsupported_shape"), (None, "unsupported_shape")])
def test_error(raw, reason):
    with pytest.raises(AdapterError) as err:
        mapping_raw(trace(raw))
    assert err.value.reason == reason
    if reason == "invalid_json":
        assert err.value.__cause__ is not None
""",
        "private": """from datetime import UTC, datetime
import pytest
from product.code import mapping_raw
from product.dependencies import AdapterError, SourceTrace

def trace(raw):
    return SourceTrace(source_trace_id="t", observed_at=datetime(2026, 1, 1, tzinfo=UTC), raw=raw)

def test_unicode_and_no_mutation():
    raw = bytearray('{"雪":false}'.encode())
    before = bytes(raw)
    assert mapping_raw(trace(raw)) == {"雪": False}
    assert bytes(raw) == before

@pytest.mark.parametrize("raw", ['{"x":0}'.encode("utf-16"), b'"text"', b"null", b"0"])
def test_invalid_encoding_or_shape(raw):
    with pytest.raises(AdapterError):
        mapping_raw(trace(raw))
""",
        "cases": [{"args": [v], "kwargs": {}} for v in ('{"x":0}', "[]", "{")],
    },
}


def freeze(batch=BATCH):
    BATCH = batch
    paths = [
        S.KIT / "benchmarks" / name
        for name in (
            "consolidated_harness.py",
            "consolidated_entry.py",
            "function_proposal_rules.py",
            "preserved_import_guard.py",
            "harness_protocol.py",
            "supervised_acceptance.py",
            "capture_fixture_support.py",
            "capture_validation_facts.py",
            "reviewer_capture_entry.py",
            "reviewer_canonical_capture.py",
        )
    ]
    S.save(
        BATCH / "candidate-freeze.json",
        {
            "pins": {str(p): S.sha(p) for p in paths},
            "controls": "controls.xml:25 passed",
            "weekly_stop": 40,
        },
    )


def prepare(batch=BATCH, typed_capture=False):
    BATCH = batch
    frozen = S.read(BATCH / "candidate-freeze.json")
    if any(S.sha(p) != digest for p, digest in frozen["pins"].items()):
        raise ValueError("Candidate drift")
    seed = OLD.BATCH / "cells/request_keys-1/isolated"
    rows = {}
    for topic, spec in TASKS.items():
        root = BATCH / "templates" / topic
        text = T.extract(UP / spec["origin"], spec["symbol"])
        T.write(root / "src/product/__init__.py", "")
        T.write(root / "src/product/code.py", spec["header"] + "\n\n" + text)
        if topic == "raw":
            deps = "from datetime import datetime\nfrom typing import Any\nfrom pydantic import BaseModel, ConfigDict\n\n"
            for path, symbol in (
                ("trace_sources/base.py", "StrictModel"),
                ("trace_sources/base.py", "SourceTrace"),
                ("adapters/base.py", "AdapterError"),
            ):
                deps += T.extract(UP / path, symbol) + "\n\n"
            T.write(root / "src/product/dependencies.py", deps)
            T.write(
                root / "src/product/probe.py",
                """from datetime import UTC, datetime
from typing import Any
from product.code import mapping_raw
from product.dependencies import SourceTrace

def observe(text: str) -> dict[str, Any]:
    return mapping_raw(SourceTrace(source_trace_id="probe", observed_at=datetime(2026, 1, 1, tzinfo=UTC), raw=text.encode("utf-8")))
""",
            )
        T.write(root / "tests/test_contract.py", spec["public"])
        private = BATCH / "private" / topic / "test_independent.py"
        T.write(private, spec["private"])
        shutil.copyfile(seed / "pyproject.toml", root / "pyproject.toml")
        for cmd in (
            [S.PYTHON, "-m", "ruff", "check", "--select", "I", "--fix", "src", "tests"],
            [S.PYTHON, "-m", "ruff", "format", "src", "tests"],
        ):
            result = T.run(cmd, root)
            if result["exit_code"]:
                raise ValueError(result)
        baseline = T.run(
            [S.PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
            root,
        )
        proof = BATCH / "reference-checks" / topic
        shutil.copytree(root, proof)
        # Reference only in a separate proof directory, never copied into live cells.
        (proof / "src/product/code.py").write_text(
            spec["header"] + "\n\n" + spec["reference"], encoding="utf-8"
        )
        T.run([S.PYTHON, "-m", "ruff", "check", "--select", "I", "--fix", "src"], proof)
        T.run([S.PYTHON, "-m", "ruff", "format", "src"], proof)
        checks = [
            T.run(cmd, proof)
            for cmd in (
                [
                    S.PYTHON,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "tests",
                    private,
                ],
                [S.PYTHON, "-m", "ruff", "format", "--check", "src", "tests"],
                [S.PYTHON, "-m", "ruff", "check", "src", "tests"],
                [S.PYTHON, "-m", "pyright", "--pythonpath", S.PYTHON],
            )
        ]
        S.save(
            BATCH / "task-controls" / (topic + ".json"),
            {
                "baseline": baseline,
                "reference": checks,
                "origin": str(UP / spec["origin"]),
                "origin_sha256": S.sha(UP / spec["origin"]),
            },
        )
        if baseline["exit_code"] != 1 or any(c["exit_code"] for c in checks):
            raise ValueError("Task controls failed: " + topic)
        for cell in [c for c in ORDER if c.startswith(topic + "-")]:
            target_root = BATCH / "cells" / cell / "isolated"
            shutil.copytree(root, target_root)
            shutil.copytree(seed / ".local-agents", target_root / ".local-agents")
            identity = {
                k: "supervised-" + cell for k in ("task_id", "unit_id", "run_id")
            }
            packet = S.read(seed / ".agent/packet.json")
            packet.update(identity)
            packet.update(
                feature_id="supervised-" + topic,
                goal=spec["contract"],
                primary_plan_sha256=S.sha(S.KIT / "docs/supervised-release-stage.md"),
            )
            source_paths = [
                p.relative_to(target_root).as_posix()
                for p in target_root.rglob("*")
                if p.is_file()
                and (
                    p.relative_to(target_root).parts[0] in {"src", "tests"}
                    or p.name == "pyproject.toml"
                )
            ]
            target = "src/product/code.py"
            packet["scope"]["modify"] = [target]
            packet["scope"]["readonly"] = [p for p in source_paths if p != target] + [
                F.POLICY_PATH,
                F.PRODUCER,
                F.HELPER,
            ]
            packet["focused_tests"] = ["tests/test_contract.py"]
            packet["edit_targets"] = [
                {"path": target, "anchor": "def " + spec["symbol"] + "("}
            ]
            packet["owned_contract_ids"] = [topic]
            packet["required_behavior"] = [
                {
                    "id": topic,
                    "text": spec["contract"],
                    "risk_floor": "high",
                    "implementation_ref": {"path": target, "symbol": spec["symbol"]},
                }
            ]
            packet["acceptance_criteria"] = [
                {
                    "id": topic,
                    "text": "Full contract and all configured checks; no source/test mutation outside scope",
                }
            ]
            config = S.read(seed / ".agent/config.json")
            config["coder_single_function"] = {
                "path": target,
                "symbol": spec["symbol"],
                "dependencies": spec["header"],
            }
            capture_target = (
                {"path": target, "module": "product.code", "symbol": spec["symbol"]}
                if topic != "raw"
                else {
                    "path": "src/product/probe.py",
                    "module": "product.probe",
                    "symbol": "observe",
                }
            )
            family = "json-call-model-dump-v1"
            cases = spec["cases"]
            if typed_capture:
                capture_target = {
                    "path": target,
                    "module": "product.code",
                    "symbol": spec["symbol"],
                }
                if topic == "json":
                    family = "canonical-json-bytes-v1"
                elif topic == "raw":
                    family = "mapping-raw-utf8-v1"
                    cases = [
                        {"text": text, "kind": kind}
                        for text, kind in (
                            ('{"x":0}', "bytes"),
                            ("[]", "bytearray"),
                            ("{", "str"),
                        )
                    ]
            _, digest = F.install_material(
                target_root,
                identity,
                source_paths=source_paths,
                target=capture_target,
                family=family,
                cases=cases,
                writable=[target],
                python=S.PYTHON,
            )
            config["experimental_capture_policy_sha256"] = digest
            S.save(target_root / ".agent/packet.json", packet)
            S.save(target_root / ".agent/config.json", config)
            preflight = T.run(OLD.command(target_root, "preflight"), target_root)
            S.save(BATCH / "preflight" / (cell + ".json"), preflight)
            if preflight["exit_code"]:
                raise ValueError(preflight)
            if typed_capture and cell.endswith("-1"):
                control = BATCH / "full-chain-replay" / topic / "isolated"
                shutil.copytree(target_root, control)
                replay = control.parent / "scripted-reference.json"
                S.save(replay, [{"replacement": spec["reference"]}])
                replay_result = T.run(
                    OLD.command(control, replay=replay), control, timeout=180
                )
                S.save(control.parent / "process.json", replay_result)
                if replay_result["exit_code"]:
                    raise ValueError("Full no-model chain replay failed: " + topic)
                summary = S.read(control / ".agent/unit-summary.json")
                ledger = S.read(control / ".agent/unit-report.json")[
                    "consolidated_harness"
                ]["actual"]
                if (
                    not summary["reviewer_input_authenticated"]
                    or summary["reviewer_started"]
                    or ledger["model_requests"]
                ):
                    raise ValueError("Replay did not prove no-model complete handoff")
            rows[cell] = {
                "root": str(target_root),
                "topic": topic,
                "identity": identity,
                "target": target,
                "private_tests": str(private),
                "files": {
                    p.relative_to(target_root).as_posix(): S.sha(p)
                    for p in target_root.rglob("*")
                    if p.is_file()
                },
            }
    S.save(BATCH / "cells.json", rows)
    pins = {
        **frozen["pins"],
        str(Path(__file__).resolve()): S.sha(__file__),
        str(BATCH / "cells.json"): S.sha(BATCH / "cells.json"),
    }
    for p in (BATCH / "private").rglob("*.py"):
        pins[str(p)] = S.sha(p)
    S.save(
        BATCH / "registration.json",
        {
            "pins": pins,
            "order": ORDER,
            "registered": 6,
            "weekly_stop": 40,
            "batch_seconds": 14400,
            "candidate": "frozen function output + independent supervised acceptance",
            "gate": "6/6 supervised accepted, each task2/2; no assistance/safety drift; report strict separately",
            "continue_rule": "ordinary failure HOLD but complete remaining cells; no resampling; infra/safety/budget stop",
            "exposure": "New contract batch"
            if not typed_capture
            else "Previously exposed tasks from stopped preparation-fault batch; fresh repeat evidence only, not holdout",
            "roles": "Coder Qwen, fresh Reviewer Muse; Explorer separately qualified before any combined release",
            "primary_preparation": "Explicit behavior boundaries/public and private tests/reference proof; no algorithm hints given to Worker",
        },
    )
    print("Six cells frozen after baseline-fail/reference-pass and entry preflight")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["freeze", "prepare"])
    p.add_argument("--batch", type=Path, default=BATCH)
    p.add_argument("--typed-capture", action="store_true")
    args = p.parse_args()
    freeze(args.batch) if args.mode == "freeze" else prepare(
        args.batch, args.typed_capture
    )
