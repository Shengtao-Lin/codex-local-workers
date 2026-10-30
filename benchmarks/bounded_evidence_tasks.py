"""Prepare three upstream-derived slices AFTER protocol freeze; never call models."""

import argparse
import ast
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import bounded_evidence_support as S
import capture_fixture_support as F

UPSTREAM = Path("F:/ChatGPT/agent-runtime-kit")
WORK = S.BATCH
SUFFIX = ""
SEED = (
    S.KIT
    / "benchmarks/work/harness-convergence/unified-transfer-20261018-1/cases/messages_output-candidate-1/isolated"
)
ORDER = [
    "T1-A1",
    "T1-B1",
    "T2-B1",
    "T2-A1",
    "T3-A1",
    "T3-B1",
    "T1-B2",
    "T1-A2",
    "T2-A2",
    "T2-B2",
    "T3-B2",
    "T3-A2",
]
TASKS = {
    "T1": {
        "upstream": "src/agent_runtime/service/app.py",
        "symbol": "_sse",
        "contract": "Encode SSE with the existing signature. Preserve exact output for single-line data, including empty and Unicode strings. Normalize CRLF and bare CR in data to LF and prefix EVERY resulting line, including trailing empty lines, with 'data: '. Finish exactly one event frame with a blank line. Reject any event name containing CR or LF with ValueError before producing a frame; other event names retain existing behavior. Do not mutate inputs or change other code.",
        "kind": "ordinary local implementation",
        "interactions": [
            "newline normalization",
            "empty/trailing data lines",
            "event framing and name rejection",
        ],
        "header": "from __future__ import annotations\n\n",
        "reference": """def _sse(event: str, data: str) -> str:
    if "\\r" in event or "\\n" in event:
        raise ValueError("event name must be one line")
    lines = data.replace("\\r\\n", "\\n").replace("\\r", "\\n").split("\\n")
    return f"event: {event}\\n" + "".join(f"data: {line}\\n" for line in lines) + "\\n"
""",
        "public": """import pytest
from product.code import _sse

@pytest.mark.parametrize(("data", "expected"), [("hello", "event: text\\ndata: hello\\n\\n"), ("", "event: text\\ndata: \\n\\n"), ("a\\nb", "event: text\\ndata: a\\ndata: b\\n\\n"), ("a\\r\\nb\\r", "event: text\\ndata: a\\ndata: b\\ndata: \\n\\n")])
def test_data(data: str, expected: str) -> None:
    assert _sse("text", data) == expected

def test_event() -> None:
    with pytest.raises(ValueError):
        _sse("bad\\nname", "x")
""",
        "private": """import pytest
from product.code import _sse

@pytest.mark.parametrize("data", ["雪", "\\n", "\\r", "\\r\\n", "a\\n\\n", "a\\rb\\r\\nc\\n", "data: x\\nevent: y", "\\t "])
def test_frame(data: str) -> None:
    normalized = data.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    expected = "event: delta\\n" + "\\n".join("data: " + x for x in normalized.split("\\n")) + "\\n\\n"
    assert _sse("delta", data) == expected

@pytest.mark.parametrize("event", ["\\r", "a\\rb", "a\\r\\nb"])
def test_bad_event(event: str) -> None:
    with pytest.raises(ValueError):
        _sse(event, "ok")
""",
        "cases": [
            {"args": ["text", s], "kwargs": {}} for s in ("x", "", "a\nb", "a\r\nb\r")
        ],
    },
    "T2": {
        "upstream": "src/agent_runtime/models_clients/openai_compatible.py",
        "symbol": "_sequence",
        "contract": "Extend the copied provider _sequence helper to accept finite Iterator objects, consuming each exactly once and returning a nonempty Sequence in iteration order. Preserve existing nonempty Sequence identity and contents. Empty sequences/iterators raise ValueError with the existing label-aware empty-array message. Reject str, bytes AND bytearray, mappings, sets and other non-sequence/non-iterator values with the existing label-aware TypeError. Propagate an iterator's own non-StopIteration exception unchanged. No mutation of existing sequences, no other code/signature changes.",
        "kind": "repair/extension preserving existing behavior",
        "interactions": [
            "sequence identity",
            "iterator consumption/order and empty detection",
            "excluded scalar/container types",
            "iterator exception propagation",
        ],
        "header": "from __future__ import annotations\n\nfrom collections.abc import Iterator, Sequence\nfrom typing import cast\n\n",
        "reference": """def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, Iterator):
        value = list(cast(Iterator[object], value))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"Provider {label} must be an array")
    if not value:
        raise ValueError(f"Provider {label} must not be empty")
    return cast(Sequence[object], value)
""",
        "public": """import pytest
from product.code import _sequence

def test_identity() -> None:
    value = [0, False, None]
    assert _sequence(value, "choices") is value

def test_iterator() -> None:
    value = iter([3, 1, 3])
    assert list(_sequence(value, "choices")) == [3, 1, 3]
    assert list(value) == []

def test_empty() -> None:
    with pytest.raises(ValueError, match="Provider choices must not be empty"):
        _sequence(iter([]), "choices")

@pytest.mark.parametrize("value", ["abc", b"abc", bytearray(b"abc"), {}, {1}, None])
def test_reject(value: object) -> None:
    with pytest.raises(TypeError, match="Provider choices must be an array"):
        _sequence(value, "choices")
""",
        "private": """from collections.abc import Iterator
import pytest
from product.code import _sequence

def test_tuple() -> None:
    value = ("x", "y")
    assert _sequence(value, "body") is value

@pytest.mark.parametrize("value", [[], (), iter(()), (x for x in [])])
def test_empty(value: object) -> None:
    with pytest.raises(ValueError, match="Provider body must not be empty"):
        _sequence(value, "body")

def test_failing_iterator() -> None:
    failure = RuntimeError("original")
    def values() -> Iterator[object]:
        yield 1
        raise failure
    with pytest.raises(RuntimeError) as caught:
        _sequence(values(), "body")
    assert caught.value is failure

def test_generator_falsy() -> None:
    assert list(_sequence((x for x in [None, 0, False, ""]), "body")) == [None, 0, False, ""]
""",
        "cases": [
            {"args": [v, "choices"], "kwargs": {}} for v in ([1, 2], [], "abc", None)
        ],
    },
    "T3": {
        "upstream": "src/agent_runtime/models_clients/gemini.py",
        "symbol": "_usage",
        "contract": "For this local slice, extend _usage to include thoughtsTokenCount in output_tokens in addition to candidatesTokenCount; cachedContentTokenCount must not reduce input_tokens. Preserve None for absent/non-Mapping usageMetadata, zero defaults for absent counters, acceptance of integers and integer strings via the existing conversion, and the real Usage return type. Reject any negative prompt/candidates/thoughts counter with ValueError even when sums would be nonnegative; preserve rejection of invalid integer text. Unknown metadata fields stay ignored. Keep the signature, do not mutate the input, do not change the real dependency model or code outside the function.",
        "kind": "local implementation using real dependency model",
        "interactions": [
            "three counter fields and addition",
            "per-counter validation vs total",
            "real Pydantic Usage constraints",
            "legacy absent/invalid behavior",
        ],
        "header": "from __future__ import annotations\n\nfrom collections.abc import Mapping\nfrom typing import cast\n\nfrom product.models import Usage\n\n",
        "reference": """def _usage(body: Mapping[str, object]) -> Usage | None:
    raw = body.get("usageMetadata")
    if not isinstance(raw, Mapping):
        return None
    usage = cast(Mapping[str, object], raw)
    prompt = int(str(usage.get("promptTokenCount", 0)))
    candidates = int(str(usage.get("candidatesTokenCount", 0)))
    thoughts = int(str(usage.get("thoughtsTokenCount", 0)))
    if min(prompt, candidates, thoughts) < 0:
        raise ValueError("token counts must be nonnegative")
    return Usage(input_tokens=prompt, output_tokens=candidates + thoughts)
""",
        "public": """import pytest
from product.code import _usage
from product.models import Usage

def test_counts() -> None:
    result = _usage({"usageMetadata": {"promptTokenCount": "7", "candidatesTokenCount": 2, "thoughtsTokenCount": 3, "cachedContentTokenCount": 5}})
    assert isinstance(result, Usage)
    assert result.model_dump() == {"input_tokens": 7, "output_tokens": 5}

def test_missing() -> None:
    assert _usage({}) is None
    assert _usage({"usageMetadata": None}) is None
    result = _usage({"usageMetadata": {}})
    assert result is not None and result.input_tokens == result.output_tokens == 0

def test_negative() -> None:
    with pytest.raises(ValueError):
        _usage({"usageMetadata": {"candidatesTokenCount": -1, "thoughtsTokenCount": 2}})
""",
        "private": """from collections import UserDict
import copy
import pytest
from product.code import _usage
from product.models import Usage

@pytest.mark.parametrize("key", ["promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount"])
def test_negative(key: str) -> None:
    with pytest.raises(ValueError):
        _usage({"usageMetadata": {key: "-2", "candidatesTokenCount": 10, "thoughtsTokenCount": 10, **{key: "-2"}}})

@pytest.mark.parametrize("raw", [None, [], "text", 0])
def test_nonmapping(raw: object) -> None:
    assert _usage({"usageMetadata": raw}) is None

def test_immutable_real_model() -> None:
    raw = UserDict({"promptTokenCount": "0", "candidatesTokenCount": "4", "thoughtsTokenCount": "5", "ignored": 99})
    before = copy.deepcopy(raw)
    result = _usage({"usageMetadata": raw})
    assert isinstance(result, Usage)
    assert result.model_dump() == {"input_tokens": 0, "output_tokens": 9}
    assert raw == before

@pytest.mark.parametrize("text", ["bad", "1.5", ""])
def test_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        _usage({"usageMetadata": {"thoughtsTokenCount": text}})
""",
        "cases": [
            {"args": [v], "kwargs": {}}
            for v in (
                {},
                {"usageMetadata": {}},
                {
                    "usageMetadata": {
                        "promptTokenCount": "7",
                        "candidatesTokenCount": 2,
                        "thoughtsTokenCount": 3,
                    }
                },
            )
        ],
    },
}

PROJECT = """[project]
name = "bounded-evidence-slice"
version = "0.0.0"
requires-python = ">=3.11"
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-p no:cacheprovider"
[tool.ruff]
line-length = 100
target-version = "py311"
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "ASYNC", "RUF"]
[tool.pyright]
include = ["src"]
pythonVersion = "3.11"
typeCheckingMode = "strict"
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def extract(path, name):
    text = path.read_text(encoding="utf-8")
    nodes = [
        n
        for n in ast.walk(ast.parse(text))
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name
    ]
    if len(nodes) != 1:
        raise ValueError("Upstream symbol not unique")
    node = nodes[0]
    return (
        textwrap.dedent("\n".join(text.splitlines()[node.lineno - 1 : node.end_lineno]))
        + "\n"
    )


def run(argv, root, timeout=120):
    result = subprocess.run(
        [str(x) for x in argv],
        cwd=root,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(root / "src"),
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    return {
        "argv": [str(x) for x in argv],
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def prepare():
    frozen = S.read(S.BATCH / "candidate-freeze.json")
    if any(S.sha(p) != digest for p, digest in frozen["pins"].items()):
        raise ValueError("Candidate changed after freeze")
    rows, controls = {}, {}
    for name, task in TASKS.items():
        root = WORK / "templates" / name
        origin = UPSTREAM / task["upstream"]
        original = extract(origin, task["symbol"])
        adapted = original
        if name == "T3":
            adapted = adapted.replace("def _usage(cls, body:", "def _usage(body:")
        write(root / "src/product/__init__.py", "")
        export = "__all__ = [" + repr(task["symbol"]) + "]\n\n"
        write(root / "src/product/code.py", task["header"] + export + adapted)
        if name == "T3":
            models = UPSTREAM / "src/agent_runtime/models.py"
            model_text = (
                "from pydantic import BaseModel, ConfigDict, Field\n\n\n"
                + extract(models, "StrictModel")
                + "\n\n"
                + extract(models, "Usage")
            )
            write(root / "src/product/models.py", model_text)
        write(root / "tests/test_contract.py", task["public"])
        private = WORK / "private" / name / "test_independent.py"
        write(private, task["private"])
        write(root / "pyproject.toml", PROJECT)
        reference = WORK / "private" / name / "reference.py"
        write(reference, task["header"] + export + task["reference"])
        run(
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
            root,
        )
        formatted = run([S.PYTHON, "-B", "-m", "ruff", "format", "src", "tests"], root)
        if formatted["exit_code"]:
            raise ValueError(formatted)
        # References and private tests remain outside every Worker root.
        run([S.PYTHON, "-B", "-m", "ruff", "format", reference, private], root)
        baseline = run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], root)
        proof = WORK / "reference-checks" / name
        shutil.copytree(root, proof)
        shutil.copyfile(reference, proof / "src/product/code.py")
        commands = [
            [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", private],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        ]
        checks = [run(cmd, proof) for cmd in commands]
        controls[name] = {"baseline": baseline, "reference": checks}
        S.save(WORK / "task-controls" / (name + ".json"), controls[name])
        if baseline["exit_code"] != 1 or any(c["exit_code"] for c in checks):
            raise ValueError("Task control failed; retained detailed record: " + name)
        inputs = {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
            and (
                p.relative_to(root).parts[0] in {"src", "tests"}
                or p.name == "pyproject.toml"
            )
        }
        rows[name] = {
            "task": name,
            "symbol": task["symbol"],
            "contract": task["contract"],
            "kind": task["kind"],
            "interactions": task["interactions"],
            "root": str(root),
            "inputs": inputs,
            "origin": {
                "path": str(origin),
                "sha256": S.sha(origin),
                "block_sha256": __import__("hashlib")
                .sha256(original.encode())
                .hexdigest(),
            },
            "adaptations": "Extract upstream function into isolated product.code; omit method decorator; T3 drops unused cls and relocates actual StrictModel/Usage; T2 adds approved Iterator import. No upstream logic changes at start.",
            "reference_sha256": S.sha(reference),
            "private_test_sha256": S.sha(private),
            "exposure": "New task to current Worker; Primary authored and reviewed tests/reference; not blind to preparer; unrelated historical exposure cannot be fully excluded without archive scan",
        }
    S.save(
        S.BATCH / ("task-freeze" + SUFFIX + ".json"),
        {
            "candidate_freeze_sha256": S.sha(S.BATCH / "candidate-freeze.json"),
            "tasks": rows,
        },
    )
    prepare_cells(rows)


def prepare_cells(tasks):
    rows = {}
    for cell in ORDER:
        topic, arm_repeat = cell.split("-")
        arm = arm_repeat[0]
        task, info = TASKS[topic], tasks[topic]
        root = WORK / "cases" / cell / "isolated"
        shutil.copytree(
            Path(info["root"]),
            root,
            ignore=shutil.ignore_patterns(
                ".ruff_cache", "__pycache__", ".pytest_cache"
            ),
        )
        shutil.copytree(
            SEED / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "*.pyc", "config.json"
            ),
        )
        config = S.read(SEED / ".agent/config.json")
        packet = S.read(SEED / ".agent/packet.json")
        identity = {
            "task_id": "evidence-" + topic,
            "unit_id": "evidence-" + topic,
            "run_id": "bounded-20261018-" + cell,
        }
        inputs = sorted(info["inputs"])
        _policy, policy_sha = F.install_material(
            root,
            identity,
            source_paths=inputs,
            target={
                "path": "src/product/code.py",
                "module": "product.code",
                "symbol": task["symbol"],
            },
            family="json-call-model-dump-v1",
            cases=task["cases"],
            writable=["src/product/code.py"],
            python=S.PYTHON,
        )
        protected = [p for p in inputs if p != "src/product/code.py"] + [
            F.POLICY_PATH,
            F.PRODUCER,
            F.HELPER,
        ]
        contract = {
            "id": topic,
            "text": task["contract"],
            "risk_floor": "high",
            "implementation_ref": {
                "path": "src/product/code.py",
                "symbol": task["symbol"],
            },
        }
        packet.update(
            **identity,
            feature_id="evidence-" + topic,
            goal=task["contract"],
            primary_plan_sha256=S.sha(S.BATCH / "candidate-freeze.json"),
            packet_revision=1,
            plan_revision=1,
            attempt=1,
            risk={
                "feature": "high",
                "unit": "high",
                "integration": "high",
                "reasons": [
                    "Copied public provider/framing compatibility boundary; no reduced risk floor"
                ],
            },
            dependencies=[],
            owned_contract_ids=[topic],
            required_behavior=[contract],
            review_feedback=[],
            implementation_guidance=[],
            scope={
                "read": [
                    "src",
                    "tests",
                    "pyproject.toml",
                    F.POLICY_PATH,
                    F.PRODUCER,
                    F.HELPER,
                ],
                "readonly": protected,
                "modify": ["src/product/code.py"],
                "create": [],
                "forbidden": [
                    ".agent",
                    ".git",
                    ".local-agents",
                    "private",
                    "AGENTS.md",
                ],
            },
            edit_targets=[
                {"path": "src/product/code.py", "anchor": "def " + task["symbol"] + "("}
            ],
            focused_tests=["tests/test_contract.py"],
            supplemental_tests=[],
            acceptance_criteria=[
                {
                    "id": topic,
                    "text": "Full hard contract, project checks, independent Reviewer and Primary acceptance",
                }
            ],
            acceptance_scenarios=[
                {"id": "normal", "text": "Required normal behavior"},
                {"id": "boundary", "text": "Preserve specified interacting boundaries"},
                {
                    "id": "error",
                    "text": "Specified rejection/propagation without input mutation",
                },
            ],
            limits={
                "max_model_turns": 12,
                "hard_max_model_turns": 12,
                "max_validation_runs": 4,
                "max_local_repairs": 2,
                "repair_turn_reserve": 0,
                "prevalidation_edit_turn_reserve": 0,
            },
        )
        dependencies = task["header"]
        if topic == "T3":
            dependencies += (
                "\n# Actual dependency, also readable in src/product/models.py\n"
                + (root / "src/product/models.py").read_text()
            )
        config.update(
            max_model_turns=12,
            hard_max_model_turns=12,
            max_validation_runs=4,
            experimental_bounded_evidence=arm,
            experimental_evidence_files=[
                p for p in inputs if p.startswith(("src/", "tests/"))
            ],
            experimental_unified_preparation=True,
            experimental_static_span_repair=True,
            experimental_prevalidation_format=True,
            experimental_output_channel="schema",
            coder_single_function={
                "path": "src/product/code.py",
                "symbol": task["symbol"],
                "dependencies": dependencies,
            },
        )
        S.save(root / ".agent/config.json", config)
        S.save(root / ".agent/packet.json", packet)
        rows[cell] = {
            "root": str(root),
            "arm": arm,
            "task": topic,
            "capture_policy_sha256": policy_sha,
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
            "status": "NOT_RUN",
            "private_tests": str(WORK / "private" / topic / "test_independent.py"),
        }
    S.save(S.BATCH / ("cells" + SUFFIX + ".json"), rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, required=True)
    args = parser.parse_args()
    WORK = S.BATCH / ("task-preparation-v" + str(args.generation))
    SUFFIX = "-v" + str(args.generation)
    prepare()
