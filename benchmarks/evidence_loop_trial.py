"""New isolated sibling slices: fixed A/B evidence-access diagnosis, not release."""

import argparse
import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import normal_task_trial as N
import supervised_feedback_trial as OLD
import supervised_repair_phase as P

BATCH = S.KIT / "benchmarks/work/harness-convergence/evidence-loop-20261020-5"
UP = Path("F:/ChatGPT/agent-runtime-kit/src/agent_runtime")
ORDER = [
    "final-A-1",
    "final-B-1",
    "payload-B-1",
    "payload-A-1",
    "sequence-A-1",
    "sequence-B-1",
    "final-B-2",
    "final-A-2",
    "payload-A-2",
    "payload-B-2",
    "sequence-B-2",
    "sequence-A-2",
]
SPECS = {
    "final": {
        "origin": "runtime.py",
        "symbol": "_final_assistant",
        "header": "from __future__ import annotations\nfrom product.dependencies import Message\n",
        "contract": "Select the last assistant Message containing at least one text content part, ignoring tool-call-only assistant messages and other roles. Return the exact original Message object, not a copy. Whitespace text counts as text; do not strip or rewrite content. If none qualifies, retain ValueError and original error message. Preserve input order and objects, signature and all other code.",
        "public": """import pytest
from product.code import _final_assistant
from product.dependencies import Message

def message(role, content):
    return Message(role=role, content=content)

def test_skip_tool_only_and_other_roles():
    text = message("assistant", [{"type": "text", "text": "answer"}])
    tool = message("assistant", [{"type": "tool_call", "tool_call": {"id": "c", "name": "run", "arguments": {}}}])
    user = message("user", [{"type": "text", "text": "later"}])
    data = [text, tool, user]
    before = [m.model_dump() for m in data]
    assert _final_assistant(data) is text
    assert [m.model_dump() for m in data] == before

def test_absent():
    with pytest.raises(ValueError, match="Agent output must contain an assistant message"):
        _final_assistant([message("user", [{"type": "text", "text": "question"}])])
""",
        "private": """import pytest
from product.code import _final_assistant
from product.dependencies import Message

def test_latest_mixed_and_whitespace_identity():
    first = Message(role="assistant", content=[{"type": "text", "text": "first"}])
    last = Message(role="assistant", content=[{"type": "tool_call", "tool_call": {"id": "c", "name": "x", "arguments": {}}}, {"type": "text", "text": " "}])
    assert _final_assistant([first, last]) is last

def test_empty_and_tool_only():
    with pytest.raises(ValueError):
        _final_assistant([])
    only = Message(role="assistant", content=[{"type": "tool_call", "tool_call": {"id": "c", "name": "x"}}])
    with pytest.raises(ValueError):
        _final_assistant([only])
""",
    },
    "payload": {
        "origin": "models_clients/openai_compatible.py",
        "symbol": "_message_payload",
        "header": "from __future__ import annotations\nimport json\nfrom product.dependencies import Message, TextContent\n",
        "contract": "Preserve _message_payload's existing provider payload shape, roles, text joining, missing-text None, tool call ordering, IDs/names and JSON values. Change embedded JSON serialization of tool arguments and tool results to preserve Unicode characters instead of ASCII escapes. Do not mutate Message or nested objects, and preserve falsy/null values and signature/imports/other functions.",
        "public": """import json
from product.code import _message_payload
from product.dependencies import Message

def test_tool_arguments_unicode():
    m = Message(role="assistant", content=[{"type": "tool_call", "tool_call": {"id": "c", "name": "run", "arguments": {"city": "雪"}}}])
    before = m.model_dump()
    out = _message_payload(m)
    encoded = out["tool_calls"][0]["function"]["arguments"]
    assert "雪" in encoded and json.loads(encoded) == {"city": "雪"}
    assert out["content"] is None and m.model_dump() == before

def test_result_unicode():
    m = Message(role="tool", content=[{"type": "tool_result", "tool_call_id": "c", "result": {"label": "雪"}}])
    out = _message_payload(m)
    assert "雪" in out["content"] and json.loads(out["content"]) == {"label": "雪"}
    assert out["role"] == "tool" and out["tool_call_id"] == "c"
""",
        "private": """import json
import pytest
from product.code import _message_payload
from product.dependencies import Message

@pytest.mark.parametrize("value", [None, False, 0, ["雪", {"x": False}]])
def test_result_values_and_no_mutation(value):
    m = Message(role="tool", content=[{"type": "tool_result", "tool_call_id": "r", "result": value}])
    before = m.model_dump()
    assert json.loads(_message_payload(m)["content"]) == value
    assert m.model_dump() == before

def test_text_and_call_order():
    m = Message(role="assistant", content=[{"type": "text", "text": "a"}, {"type": "tool_call", "tool_call": {"id": "2", "name": "run", "arguments": {}}}, {"type": "text", "text": "b"}, {"type": "tool_call", "tool_call": {"id": "1", "name": "run", "arguments": {"x": 0}}}])
    out = _message_payload(m)
    assert out["content"] == "a\\nb"
    assert [c["id"] for c in out["tool_calls"]] == ["2", "1"]
""",
    },
    "sequence": {
        "origin": "models_clients/openai_compatible.py",
        "symbol": "_sequence",
        "header": "from __future__ import annotations\nfrom collections.abc import Sequence\nfrom typing import cast\n",
        "contract": "Extend _sequence's rejection of string/bytes scalars to bytearray and memoryview, including empty values, as TypeError with the original label-specific array message. Continue accepting other nonempty Sequence inputs with exact object identity, and reject empty valid Sequences as ValueError with original not-empty message. Retain the validation ordering, signature and other code.",
        "public": """import pytest
from product.code import _sequence

@pytest.mark.parametrize("value", [bytearray(b"abc"), memoryview(b"abc")])
def test_binary_scalars(value):
    with pytest.raises(TypeError, match="Provider choices must be an array"):
        _sequence(value, "choices")

def test_identity_and_empty():
    value = [False, 0, None]
    assert _sequence(value, "choices") is value
    with pytest.raises(ValueError, match="Provider choices must not be empty"):
        _sequence([], "choices")
""",
        "private": """import pytest
from product.code import _sequence

@pytest.mark.parametrize("value", [bytearray(), memoryview(b""), "", b"", {}, None])
def test_type_precedes_empty(value):
    with pytest.raises(TypeError, match="Provider delta must be an array"):
        _sequence(value, "delta")

def test_other_sequences_keep_identity():
    for value in [(1, 2), range(3)]:
        assert _sequence(value, "data") is value
    for value in [(), range(0)]:
        with pytest.raises(ValueError):
            _sequence(value, "data")
""",
    },
}


def command(root, mode="coder", replay=None):
    argv = P.command(root, mode, replay) + ["--static-focus"]
    if "-B-" in root.parent.name:
        argv.append("--evidence-loop")
    if mode == "coder":
        argv[argv.index("--report") + 1] = str(root / ".agent/unit-report.json")
        argv += ["--summary", str(root / ".agent/unit-summary.json")]
    return argv


def prepare():
    import approved_read_tasks

    SPECS = approved_read_tasks.SPECS
    ORDER = [
        cell.replace("final", "parse").replace("payload", "mapping")
        for cell in globals()["ORDER"]
    ]
    controls = list(ET.parse(BATCH / "offline-controls-v2.xml").iter("testcase"))
    if len(controls) != 33 or any(
        c.find(tag) is not None
        for c in controls
        for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("All33 offline controls required")
    paths = [
        S.KIT / "benchmarks" / n
        for n in (
            "consolidated_harness.py",
            "consolidated_entry.py",
            "approved_evidence.py",
            "evidence_loop_rules.py",
            "bounded_evidence_candidate.py",
            "static_focus_rules.py",
            "repair_phase_rules.py",
            "bounded_source_rules.py",
            "normal_task_trial.py",
            "capture_fixture_support.py",
            "capture_validation_facts.py",
            "reviewer_canonical_capture.py",
            "reviewer_capture_entry.py",
            "literal_check_feedback.py",
            "supervised_repair_phase.py",
            "supervised_bounded_trial.py",
            "function_repeat_trial.py",
            "evidence_loop_trial.py",
            "approved_read_tasks.py",
        )
    ]
    # Candidate pinned before generating new task fixtures; no tuning on outcomes.
    S.save(BATCH / "candidate-freeze.json", {"pins": {str(p): S.sha(p) for p in paths}})
    seed = Path(S.read(OLD.OLD / "cells.json")["raw-1"]["root"])
    rows = {}
    for topic, spec in SPECS.items():
        template = BATCH / "templates" / topic
        symbol = spec["symbol"].lstrip("_")
        original = T.extract(UP / spec["origin"], spec["symbol"]).replace(
            "def " + spec["symbol"] + "(", "def " + symbol + "(", 1
        )
        target = "src/product/code.py"
        T.write(template / target, spec["header"] + "\n\n" + original)
        T.write(template / "src/product/__init__.py", "")
        T.write(
            template / "tests/test_contract.py",
            re.sub(r"\b" + re.escape(spec["symbol"]) + r"\b", symbol, spec["public"]),
        )
        if topic == "parse":
            dependency = Path(spec["dependency_source"]).read_text(encoding="utf-8")
            dependency += "\n\n" + T.extract(
                Path(spec["origin"]).with_name("base.py"), "AdapterError"
            )
            dependency = dependency.replace(
                "import json\n", "import hashlib\nimport json\n", 1
            )
            dependency += "\n\n" + T.extract(Path(spec["origin"]), "stable_message_id")
            T.write(template / "src/product/dependencies.py", dependency)
        elif topic in {"final", "payload"}:
            shutil.copyfile(UP / "models.py", template / "src/product/dependencies.py")
            wrapper = f"""from typing import Any
from product.code import {symbol}
from product.dependencies import Message

def observe(payload: Any) -> Any:
    value = {symbol}({"[Message.model_validate(m) for m in payload]" if topic == "final" else "Message.model_validate(payload)"})
    return {'value.model_dump(mode="json")' if topic == "final" else "value"}
"""
            T.write(template / "src/product/probe.py", wrapper)
        shutil.copyfile(seed / "pyproject.toml", template / "pyproject.toml")
        private = BATCH / "private" / topic / "test_independent.py"
        T.write(
            private,
            re.sub(r"\b" + re.escape(spec["symbol"]) + r"\b", symbol, spec["private"]),
        )
        for argv in (
            [
                S.PYTHON,
                "-B",
                "-m",
                "ruff",
                "check",
                "--select",
                "I",
                "--fix",
                "src",
                "tests",
            ],
            [S.PYTHON, "-B", "-m", "ruff", "format", "src", "tests"],
        ):
            if T.run(argv, template)["exit_code"]:
                raise ValueError("Fixture formatting failed")
        baseline = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], template)
        proof = BATCH / "reference-checks" / topic
        shutil.copytree(template, proof)
        if topic == "parse":
            reference = original.replace(
                'parts.append(TextPart(text=str(part.get("text", ""))))',
                'text = part.get("text")\n                if not isinstance(text, str) or text == "":\n                    raise AdapterError("invalid_content", f"message {index} content is invalid")\n                parts.append(TextPart(text=text))',
            )
        elif topic == "mapping":
            reference = spec["reference"]
        elif topic == "final":
            reference = original.replace(
                'if message.role == "assistant":',
                'if message.role == "assistant" and any(part.type == "text" for part in message.content):',
            )
        elif topic == "payload":
            reference = original.replace("ensure_ascii=True", "ensure_ascii=False")
        else:
            reference = original.replace(
                "(str, bytes)", "(str, bytes, bytearray, memoryview)"
            )
        (proof / target).write_text(
            spec["header"] + "\n\n" + reference, encoding="utf-8"
        )
        T.run(
            [S.PYTHON, "-B", "-m", "ruff", "check", "--select", "I", "--fix", "src"],
            proof,
        )
        T.run([S.PYTHON, "-B", "-m", "ruff", "format", "src"], proof)
        checks = [
            T.run(argv, proof)
            for argv in (
                [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", private],
                [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
                [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
                [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
            )
        ]
        S.save(
            BATCH / "task-controls" / (topic + ".json"),
            {
                "baseline": baseline,
                "reference": checks,
                "upstream": str(UP / spec["origin"]),
                "upstream_sha256": S.sha(UP / spec["origin"]),
                "extraction": "Original method body extracted as standalone function, removing leading underscore to avoid artificial private cross-module use; parameter/return signature retained; imports relocated to copied real model types. No sibling modification.",
                "behavior_requirements": spec["contract"],
            },
        )
        if baseline["exit_code"] != 1 or any(c["exit_code"] for c in checks):
            raise ValueError("Task control failed: " + topic)
        for cell in [c for c in ORDER if c.startswith(topic + "-")]:
            root = BATCH / "cells" / cell / "isolated"
            shutil.copytree(
                template,
                root,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".pytest_cache", "__pycache__"
                ),
            )
            shutil.copytree(seed / ".local-agents", root / ".local-agents")
            identity = {
                k: BATCH.name + "-" + cell for k in ("task_id", "unit_id", "run_id")
            }
            packet = S.read(seed / ".agent/packet.json")
            packet.update(identity)
            packet.update(
                feature_id="evidence-" + topic,
                goal=spec["contract"],
                primary_plan_sha256=S.sha(BATCH / "candidate-freeze.json"),
            )
            source_paths = [
                p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file()
                and (
                    p.relative_to(root).parts[0] in {"src", "tests"}
                    or p.name == "pyproject.toml"
                )
            ]
            packet["scope"]["readonly"] = [p for p in source_paths if p != target] + [
                F.POLICY_PATH,
                F.PRODUCER,
                F.HELPER,
            ]
            packet["edit_targets"] = [{"path": target, "anchor": "def " + symbol + "("}]
            packet["owned_contract_ids"] = [topic]
            packet["required_behavior"] = [
                {
                    "id": topic,
                    "text": spec["contract"],
                    "risk_floor": "high",
                    "implementation_ref": {"path": target, "symbol": symbol},
                }
            ]
            packet["acceptance_criteria"] = [
                {
                    "id": topic,
                    "text": "All original behavior requirements and trusted full checks; no protected modifications",
                }
            ]
            config = S.read(seed / ".agent/config.json")
            config["coder_single_function"] = {
                "path": target,
                "symbol": symbol,
                "dependencies": spec["header"],
            }
            config["experimental_evidence_files"] = [
                p for p in source_paths if p.startswith(("src/", "tests/"))
            ]
            cases = [{"args": [[1, 2], "choices"], "kwargs": {}}]
            capture_target = {
                "path": target,
                "module": "product.code",
                "symbol": symbol,
            }
            if topic == "parse":
                cases = spec["cases"]
            elif topic in {"final", "payload"}:
                capture_target = {
                    "path": "src/product/probe.py",
                    "module": "product.probe",
                    "symbol": "observe",
                }
                message = {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "雪"}],
                }
                cases = [
                    {"args": [[message] if topic == "final" else message], "kwargs": {}}
                ]
            _, digest = F.install_material(
                root,
                identity,
                source_paths=source_paths,
                target=capture_target,
                family="json-call-model-dump-v1",
                cases=cases,
                writable=[target],
                python=S.PYTHON,
            )
            config["experimental_capture_policy_sha256"] = digest
            S.save(root / ".agent/packet.json", packet)
            S.save(root / ".agent/config.json", config)
            if cell.endswith("-1"):
                offline = BATCH / "offline" / cell / "isolated"
                shutil.copytree(root, offline)
                replay = offline.parent / "replay.json"
                S.save(replay, [{"replacement": T.extract(proof / target, symbol)}])
                result = T.run(command(offline, "unit", replay), offline, timeout=180)
                S.save(offline.parent / "process.json", result)
                if result["exit_code"]:
                    raise ValueError("No-model complete-chain failed: " + cell)
            rows[cell] = {
                "root": str(root),
                "topic": topic,
                "identity": identity,
                "target": target,
                "private_tests": str(private),
                "files": {
                    p.relative_to(root).as_posix(): S.sha(p)
                    for p in root.rglob("*")
                    if p.is_file()
                    and not any(
                        part in {".ruff_cache", ".pytest_cache", "__pycache__"}
                        for part in p.relative_to(root).parts
                    )
                },
            }
    S.save(BATCH / "cells.json", rows)
    pins = S.read(BATCH / "candidate-freeze.json")["pins"]
    pins[str(BATCH / "cells.json")] = S.sha(BATCH / "cells.json")
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "pins": pins,
            "registered": 12,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "A": "Static-focused current source/contract/check loop; no memory",
            "B": "A plus existing bounded read/search protocol on same exact approved source/test files; max4 evidence actions count in12 requests",
            "budget": {
                "requests": 12,
                "edits": 3,
                "post_edit_checks": 3,
                "initial_checks": 1,
                "seconds": 900,
                "output_tokens": 4096,
            },
            "gate": "Evidence effect unexercised if B makes no read/search requests. Support only if B improves independent completion without family regression; otherwise no adoption claim. Reviewer/final acceptance NOT_RUN_DIAGNOSTIC; no release credit.",
            "continue_rule": "Complete ordinary outcomes; no retries/resampling/hidden feedback. Stop safety/infrastructure/drift, deadline or weekly50.",
            "primary": "Once-only three slice contracts/public+private tests/ref proofs/capture setup. No new semantics or implementation guidance during live. Costs unknown, not a savings claim.",
            "exposure": "New to this candidate; real sibling method extracts with explicit new bounded behavior; not public benchmark or unseen-pretraining claim.",
        },
    )
    print("12 evidence-access cells frozen after task/reference/whole-chain controls")


def run(cell, used, observed):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    N.run(
        cell,
        used,
        observed,
        batch=BATCH,
        order=S.read(BATCH / "registration.json")["order"],
        build_command=command,
        usage_limit=50,
        batch_seconds=10800,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare"])
    p.parse_args()
    prepare()
