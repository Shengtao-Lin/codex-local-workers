"""Fixed new-task qualification; reuse existing controller, checks and archives."""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import normal_task_trial as N
import reasoning_wire_candidate as W
import supervised_repair_phase as P

BATCH = S.KIT / "benchmarks/work/harness-convergence/limited-family-20261020-2"
SEED = (
    S.KIT
    / "benchmarks/work/harness-convergence/supervised-static-release-20261020-1/cells/ids-1/isolated"
)
ORDER = ["labels-1", "unique-1", "route-1", "route-2", "unique-2", "labels-2"]
TASKS = {
    "labels": {
        "symbol": "merge_labels",
        "header": "from __future__ import annotations\n",
        "contract": "merge_labels(defaults: dict[str, str], overrides: dict[str, str | None]) returns a new dictionary. Keep defaults unless overridden; None in overrides removes that key even if absent; any other override, including empty string, is retained. Preserve default key insertion order for surviving keys, append genuinely new keys in override order, do not mutate either input. Missing deletions are harmless. No normalization of strings or keys.",
        "start": "def merge_labels(defaults: dict[str, str], overrides: dict[str, str | None]) -> dict[str, str]:\n    return dict(defaults)\n",
        "reference": "def merge_labels(defaults: dict[str, str], overrides: dict[str, str | None]) -> dict[str, str]:\n    result = dict(defaults)\n    for key, value in overrides.items():\n        if value is None:\n            result.pop(key, None)\n        else:\n            result[key] = value\n    return result\n",
        "public": """from product.code import merge_labels

def test_merge():
    defaults = {"a": "one", "b": "two"}
    overrides = {"b": "", "c": "three", "absent": None}
    assert merge_labels(defaults, overrides) == {"a": "one", "b": "", "c": "three"}
    assert defaults == {"a": "one", "b": "two"}
    assert overrides == {"b": "", "c": "three", "absent": None}

def test_delete_and_empty():
    assert merge_labels({"a": "x"}, {"a": None}) == {}
    defaults = {"a": "x"}
    assert merge_labels(defaults, {}) is not defaults
    assert merge_labels({}, {"a": ""}) == {"a": ""}
""",
        "private": """from product.code import merge_labels

def test_order_and_strings():
    defaults = {"a": "old", "b": "x", "c": "y"}
    overrides = {"b": None, "a": "new", "d": "雪", "e": " "}
    result = merge_labels(defaults, overrides)
    assert list(result.items()) == [("a", "new"), ("c", "y"), ("d", "雪"), ("e", " ")]
    assert list(defaults) == ["a", "b", "c"]
    assert merge_labels({}, {"missing": None}) == {}
""",
        "cases": [{"args": [{"a": "x"}, {"a": None, "b": ""}], "kwargs": {}}],
    },
    "unique": {
        "symbol": "unique_records",
        "header": "from __future__ import annotations\n",
        "contract": "unique_records(records: list[dict[str, str]], key: str) returns a new list keeping the FIRST record for each distinct record[key], in original first-occurrence order. Retain the actual original record objects, including nested or additional fields, and do not mutate the list or any record. Empty string is a real key value, not missing. If any visited record lacks key, propagate KeyError even if earlier records were valid. Empty input returns an empty new list. No sorting, last-wins replacement or string coercion.",
        "start": "def unique_records(records: list[dict[str, str]], key: str) -> list[dict[str, str]]:\n    return records\n",
        "reference": "def unique_records(records: list[dict[str, str]], key: str) -> list[dict[str, str]]:\n    result = []\n    seen = set()\n    for record in records:\n        value = record[key]\n        if value not in seen:\n            seen.add(value)\n            result.append(record)\n    return result\n",
        "public": """import pytest
from product.code import unique_records

def test_first_and_order():
    records = [{"id": "b", "text": "first"}, {"id": "a"}, {"id": "b", "text": "last"}]
    result = unique_records(records, "id")
    assert result == records[:2]
    assert result[0] is records[0] and result[1] is records[1]
    assert len(records) == 3 and result is not records

def test_empty_and_missing():
    records = []
    assert unique_records(records, "id") == []
    assert unique_records(records, "id") is not records
    with pytest.raises(KeyError):
        unique_records([{"id": "x"}, {}], "id")
""",
        "private": """import copy
import pytest
from product.code import unique_records

def test_falsy_and_requested_field():
    records = [{"name": "", "id": "z"}, {"name": "", "id": "y"}, {"name": "x", "id": "z"}]
    before = copy.deepcopy(records)
    result = unique_records(records, "name")
    assert [id(r) for r in result] == [id(records[0]), id(records[2])]
    assert records == before
    with pytest.raises(KeyError):
        unique_records([{"name": ""}, {"other": ""}], "name")
""",
        "cases": [
            {"args": [[{"id": "b"}, {"id": "a"}, {"id": "b"}], "id"], "kwargs": {}}
        ],
    },
    "route": {
        "symbol": "append_segment",
        "header": "from __future__ import annotations\nfrom product.dependencies import encode_segment\n",
        "contract": "append_segment(base: str, segment: str) returns base with trailing slash characters removed, followed by exactly one slash and one encoded segment. The approved product.dependencies.encode_segment defines segment validity and exact encoding; preserve that dependency's ValueError and TypeError rather than inventing fallback. Slash, percent, spaces and non-ASCII within a segment are encoded, never interpreted as extra path components. Leave all other base content unchanged. Do not modify dependency, signature or read-only tests. No URL joining that discards the base path.",
        "start": "def append_segment(base: str, segment: str) -> str:\n    return base + '/' + segment\n",
        "reference": "def append_segment(base: str, segment: str) -> str:\n    return base.rstrip('/') + '/' + encode_segment(segment)\n",
        "dependency": "from urllib.parse import quote\n\ndef encode_segment(segment: object) -> str:\n    if not isinstance(segment, str):\n        raise TypeError('segment must be str')\n    if not segment:\n        raise ValueError('segment is empty')\n    return quote(segment, safe='')\n",
        "public": """import pytest
from product.code import append_segment

def test_route():
    assert append_segment("https://host/api///", "a/b") == "https://host/api/a%2Fb"
    assert append_segment("root", "a b") == "root/a%20b"
    assert append_segment("", "雪") == "/%E9%9B%AA"

def test_dependency_errors():
    with pytest.raises(ValueError):
        append_segment("base", "")
    with pytest.raises(TypeError):
        append_segment("base", None)
""",
        "private": """from product.code import append_segment
from product.dependencies import encode_segment

def test_dependency_parity():
    for base in ["root/path", "root/", "/", "https://host/a"]:
        for segment in ["%2F", "/root", "a?b#c", " ", "雪/雨"]:
            assert append_segment(base, segment) == base.rstrip("/") + "/" + encode_segment(segment)
""",
        "cases": [{"args": ["https://host/api/", "a/b"], "kwargs": {}}],
    },
}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def command(root, mode="unit", replay=None):
    return P.command(root, mode, replay) + [
        "--static-focus",
        "--reviewer-forward-reasoning",
    ]


def checks(root, private):
    return [
        T.run(cmd, root, timeout=120)
        for cmd in (
            [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", private],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        )
    ]


def prepare(used):
    if not 0 <= used < 50:
        raise ValueError("Budget stop")
    S.save(
        BATCH / "baseline.json",
        {
            "weekly_used": used,
            "weekly_stop": 50,
            "git_status": subprocess.check_output(
                ["git", "status", "--short"], cwd=S.KIT
            ).decode(),
            "production": {
                p.relative_to(S.KIT).as_posix(): S.sha(p)
                for p in (S.KIT / ".local-agents").rglob("*")
                if p.is_file()
                and not any(
                    v.startswith(".") or v == "__pycache__"
                    for v in p.relative_to(S.KIT / ".local-agents").parts
                )
            },
        },
    )
    rows = {}
    for topic, spec in TASKS.items():
        template = BATCH / "templates" / topic
        write(template / "src/product/__init__.py", "")
        write(template / "src/product/code.py", spec["header"] + "\n\n" + spec["start"])
        if "dependency" in spec:
            write(template / "src/product/dependencies.py", spec["dependency"])
        write(template / "tests/test_contract.py", spec["public"])
        shutil.copy2(SEED / "pyproject.toml", template / "pyproject.toml")
        private = BATCH / "private" / topic / "test_independent.py"
        write(private, spec["private"])
        for argv in (
            [S.PYTHON, "-m", "ruff", "check", "--select", "I", "--fix", "src", "tests"],
            [S.PYTHON, "-m", "ruff", "format", "src", "tests"],
        ):
            if T.run(argv, template)["exit_code"]:
                raise ValueError("Preparation format failed")
        proof = BATCH / "reference-checks" / topic
        shutil.copytree(template, proof)
        (proof / "src/product/code.py").write_text(
            spec["header"] + "\n\n" + spec["reference"], encoding="utf-8"
        )
        for args in (("check", "--select", "I", "--fix"), ("format",)):
            if T.run([S.PYTHON, "-m", "ruff", *args, "src", "tests"], proof)[
                "exit_code"
            ]:
                raise ValueError("Reference preparation failed")
        observed = checks(proof, private)
        baseline = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], template)
        S.save(
            BATCH / "task-controls" / (topic + ".json"),
            {"reference": observed, "baseline": baseline},
        )
        if baseline["exit_code"] != 1 or any(r["exit_code"] for r in observed):
            raise ValueError("Task controls failed: " + topic)
        for cell in (v for v in ORDER if v.startswith(topic + "-")):
            root = BATCH / "cells" / cell / "isolated"
            shutil.copytree(template, root)
            shutil.copytree(
                S.KIT / ".local-agents",
                root / ".local-agents",
                ignore=shutil.ignore_patterns("tests", "__pycache__", ".ruff_cache"),
            )
            W.patch_client(root / ".local-agents/worker-runtime.py", root)
            identity = {
                k: "limited-20261020-1-" + cell
                for k in ("task_id", "unit_id", "run_id")
            }
            packet = S.read(SEED / ".agent/packet.json")
            packet.update(
                identity,
                feature_id="limited-" + topic,
                goal=spec["contract"],
                primary_plan_sha256=S.sha(__file__),
            )
            target = "src/product/code.py"
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
            packet["owned_contract_ids"] = [topic]
            packet["edit_targets"] = [
                {"path": target, "anchor": "def " + spec["symbol"] + "("}
            ]
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
                    "text": "Full contract, configured checks, protected scope",
                }
            ]
            packet["review_feedback"] = []
            config = S.read(SEED / ".agent/config.json")
            dependencies = spec["header"] + (
                "\nReadonly dependency source:\n" + spec["dependency"]
                if "dependency" in spec
                else ""
            )
            config["coder_single_function"] = {
                "path": target,
                "symbol": spec["symbol"],
                "dependencies": dependencies,
            }
            _, digest = F.install_material(
                root,
                identity,
                source_paths=source_paths,
                target={
                    "path": target,
                    "module": "product.code",
                    "symbol": spec["symbol"],
                },
                family="json-call-model-dump-v1",
                cases=spec["cases"],
                writable=[target],
                python=S.PYTHON,
            )
            config["experimental_capture_policy_sha256"] = digest
            S.save(root / ".agent/packet.json", packet)
            S.save(root / ".agent/config.json", config)
            preflight = T.run(command(root, "preflight"), root, timeout=120)
            S.save(BATCH / "preflight" / (cell + ".json"), preflight)
            if preflight["exit_code"]:
                raise ValueError("Preflight failed")
            if cell.endswith("-1"):
                replay_root = BATCH / "full-chain-replay" / topic / "isolated"
                shutil.copytree(root, replay_root)
                replay = replay_root.parent / "reference.json"
                S.save(
                    replay, [{"replacement": T.extract(proof / target, spec["symbol"])}]
                )
                result = T.run(
                    command(replay_root, replay=replay), replay_root, timeout=180
                )
                S.save(replay_root.parent / "process.json", result)
                if result["exit_code"]:
                    raise ValueError("No-model chain failed: " + topic)
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
                    and "__pycache__" not in p.parts
                    and ".pytest_cache" not in p.parts
                    and ".ruff_cache" not in p.parts
                },
            }
    S.save(BATCH / "cells.json", rows)
    pins = [Path(__file__), BATCH / "cells.json"]
    pins += [p for p in (S.KIT / "benchmarks").glob("*.py")]
    pins += list((BATCH / "private").rglob("*.py"))
    S.save(
        BATCH / "registration.json",
        {
            "order": ORDER,
            "registered": 6,
            "weekly_stop": 50,
            "batch_seconds": 14400,
            "pins": {str(p): S.sha(p) for p in pins},
            "candidate": "Existing bounded-source/focused-repair/static-focus + unchanged contract-first Reviewer; installed production base with explicit isolated reasoning wire patch",
            "feature_risk": "high",
            "integration_risk": "high",
            "units": {
                k: {
                    "risk": "high",
                    "owned_contract_ids": [k],
                    "dependencies": ["readonly encode_segment"] if k == "route" else [],
                    "rationale": "Compatibility and error propagation invariant; Primary keeps classification",
                }
                for k in TASKS
            },
            "budget": {
                "requests": 12,
                "edits": 3,
                "post_edit_checks": 3,
                "initial_checks": 1,
                "seconds": 900,
                "output_tokens": 4096,
            },
            "reviewer_budget": {
                "requests": 16,
                "errors": 4,
                "seconds": 600,
                "output_tokens": 4096,
            },
            "gate": "6/6 independent strict or explicitly adjudicated supervised accepts, each family2/2, no new hints/code rescue/safety drift. Old gates unchanged",
            "continue_rule": "Ordinary quality failure => HOLD but finish fixed order; infrastructure/safety/drift/time/weekly50 => stop, remaining NOT_RUN. No replacement.",
            "exposure": "New synthetic local task contracts; known semantic families, not a real-project or general capability proof",
            "roles": "Coder Qwen/Muse Reviewer; Explorer not needed for already-located single-function packets, assessed separately; Coordinator NOT_RUN",
            "Primary_work": "Contracts, public/private tests and reference controls prepared; no task algorithm hints or implementation rescue in live",
        },
    )
    print("Six cells frozen after three reference proofs and no-model chains")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "run"))
    p.add_argument("--cell", choices=ORDER)
    p.add_argument("--weekly-used", type=int, required=True)
    p.add_argument("--observed-at", type=float)
    args = p.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        N.run(
            args.cell,
            args.weekly_used,
            args.observed_at,
            batch=BATCH,
            order=ORDER,
            build_command=command,
            usage_limit=50,
            batch_seconds=14400,
        )
