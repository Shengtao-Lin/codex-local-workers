"""Fresh fixed transfer matrix; immutable preparation, no live retry or reselection."""

import argparse
import ast
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import capture_coder_entry as CODER
import capture_fixture_support as F
import harness_capture_transport as T

KIT = F.KIT
BATCH = KIT / "benchmarks/work/harness-convergence/capture-transfer-20261017-1"
SEED = KIT / "benchmarks/work/harness-convergence/r4-transfer-20261016-1/cases"
FIXTURES = KIT / "benchmarks/fixtures/capture-transfer-v1"
PYTHON = Path("F:/ChatGPT/agent-evaluation-harness/.venv/Scripts/python.exe")
TOPICS = ("metadata", "request_keys", "single_content")
ORDER = [
    f"{topic}-{arm}-{repeat}"
    for repeat in (1, 2)
    for topic in TOPICS
    for arm in (("baseline", "candidate") if repeat == 1 else ("candidate", "baseline"))
]
CONTRACTS = {
    "metadata": "Make validate_metadata reject non-finite floats at any nested JSON depth with ValueError, in addition to its existing non-JSON rejection. Preserve the existing 64-key, 1..128-character string-key, and 16384 UTF-8 encoded-byte bounds (limits inclusive). Preserve all valid JSON values including falsy/null/nested data, return the original mapping object and never mutate it, including on rejection. Keep the signature, constants and all code outside this function unchanged.",
    "request_keys": "Compute request_hash as a lowercase 64-hex SHA256 of canonical_json applied to the payload without ONLY its exact top-level request_id and submitted_at keys. Ignore these keys regardless of their values. Nested occurrences, case-distinct keys, all other keys/values, falsy/null values and canonical ordering must remain significant. Never mutate the caller payload, including nested data. Use the unchanged existing encoding helper and preserve signature and all other code.",
    "single_content": "Extend parse_message to accept one typed content dictionary as the same decoded content as a singleton list. Preserve all existing string/list behavior, valid roles, content-kind validation, structured AdapterError rejections and real CanonicalMessage/part types. Preserve explicit IDs/name/tool_call_id; fallback message IDs must still be computed from the original unmodified input message. Preserve tool result values exactly, including None/False/0/empty collections, and nested tool_call arguments. Never mutate input. Unknown kinds/roles and unsupported scalar content must remain rejected; signature and all code outside parse_message unchanged.",
}


def write(root, path, text):
    target = Path(root) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def function(path, symbol):
    text = Path(path).read_text(encoding="utf-8-sig")
    node = next(
        n
        for n in ast.parse(text).body
        if isinstance(n, ast.FunctionDef) and n.name == symbol
    )
    return "\n".join(text.splitlines()[node.lineno - 1 : node.end_lineno]) + "\n"


def command(argv, root, env=None):
    started = time.monotonic()
    result = subprocess.run(
        [str(x) for x in argv],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    return {
        "argv": [str(x) for x in argv],
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "seconds": time.monotonic() - started,
    }


def source_map(root):
    return {
        p.relative_to(root).as_posix(): T.sha(p)
        for p in sorted(Path(root).rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def prepare(used):
    assert 0 <= used < 15
    assert (
        T.read(T.BATCH / "decision.json")["qualification"] == "PASS_OFFLINE_COMPONENT"
    )
    for path, sha in T.read(T.BATCH / "freeze.json")["pins"].items():
        assert T.sha(path) == sha, path
    BATCH.mkdir(exist_ok=False)
    T.save(
        BATCH / "registration.json",
        {
            "feature_id": "fresh-single-function-transfer",
            "feature_risk": "high",
            "integration_risk": "high",
            "unit_risk": {t: "high" for t in TOPICS},
            "risk_rationale": "Metadata validation, request identity and public canonical parsing are compatibility boundaries. Each atomic function owns its whole invariant; isolation does not lower semantic risk.",
            "owned_contract_ids": list(TOPICS),
            "dependencies": [],
            "contracts": CONTRACTS,
            "order": ORDER,
            "registered_units": 12,
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "criterion": "Candidate6/6 complete chains, every task2/2, not below baseline; no scope/safety failures or Primary semantic implementation takeover. Preserve all outcomes; stop when unreachable, no replacement tasks or live edits.",
            "coder_budget": {
                "requests": 6,
                "edits": 3,
                "validation_runs": 3,
                "invocation_seconds": 900,
            },
            "reviewer_budget": {
                "requests": 16,
                "errors": 4,
                "invocation_seconds": 600,
                "output_tokens": 4096,
            },
            "reviewer": "Same frozen qualified contract-first Reviewer for both arms, same capture preparation. Baseline Coder loop bytes retained in .baseline-agents, current qualified review/handoff modules in .local-agents for both arms.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
            },
            "single_residency": True,
            "primary_classification": True,
            "coordinator_enabled": False,
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
            "freshness": "These specific feature contracts/fixtures were not used to develop the frozen Coder/Reviewer candidate. Original collect_tools None regression stays exposed, never counted here. Primary creates references/negative controls; workers never read them.",
        },
    )
    origins = {}
    evaluation = KIT.parent / "agent-evaluation-harness"
    runtime = KIT.parent / "agent-runtime-kit"
    for repo in (evaluation, runtime):
        origins[str(repo)] = {
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip(),
            "status": subprocess.check_output(
                ["git", "status", "--short"], cwd=repo, text=True
            ),
            "files": {},
        }

    def read_origin(repo, path):
        origins[str(repo)]["files"][path] = T.sha(repo / path)
        return (repo / path).read_text(encoding="utf-8-sig")

    metadata_path = "src/agent_runtime/models.py"
    read_origin(runtime, metadata_path)
    metadata = function(runtime / metadata_path, "validate_metadata")
    queue_path = "src/evaluation_harness/jobs/queue.py"
    read_origin(evaluation, queue_path)
    request_hash = function(evaluation / queue_path, "request_hash")
    encoding_path = "src/evaluation_harness/canonical/fingerprint.py"
    read_origin(evaluation, encoding_path)
    encoding = function(evaluation / encoding_path, "canonical_json")
    seed_rows = T.read(
        KIT
        / "benchmarks/work/harness-convergence/r4-contract-first-20261017-1/registration.json"
    )["cells"]
    real_row = next(r for r in seed_rows if r["id"] == "sample-17-candidate")
    common_path = "src/evaluation_harness/adapters/common.py"
    for topic in TOPICS:
        root = BATCH / "fixtures" / topic
        root.mkdir(parents=True)
        if topic == "metadata":
            path, symbol, module = (
                "src/product/metadata.py",
                "validate_metadata",
                "product.metadata",
            )
            content = (
                "from __future__ import annotations\n\nimport json\nfrom typing import Any\n\nMAX_METADATA_KEYS = 64\nMAX_METADATA_BYTES = 16_384\n\n\n"
                + metadata
            )
            reference = content.replace(
                'separators=(",", ":")', 'separators=(",", ":"), allow_nan=False'
            )
            mutant = reference.replace(
                "len(encoded) > MAX_METADATA_BYTES",
                "len(encoded) >= MAX_METADATA_BYTES",
            )
            cases = [
                {"args": [v], "kwargs": {}}
                for v in (
                    {},
                    {"ok": [False, 0, None, ""]},
                    {"": 1},
                    {"x" * 129: 1},
                    {"unicode": "中文"},
                )
            ]
        elif topic == "request_keys":
            path, symbol, module = (
                "src/product/request_keys.py",
                "request_hash",
                "product.request_keys",
            )
            content = (
                "from __future__ import annotations\n\nimport hashlib\nfrom typing import Any\n\nfrom product.encoding import canonical_json\n\n\n"
                + request_hash
            )
            write(
                root,
                "src/product/encoding.py",
                "from __future__ import annotations\n\nimport json\nfrom typing import Any\n\n\n"
                + encoding,
            )
            reference = content.replace(
                "return hashlib.sha256(canonical_json(payload)).hexdigest()",
                'identity = {k: v for k, v in payload.items() if k not in {"request_id", "submitted_at"}}\n    return hashlib.sha256(canonical_json(identity)).hexdigest()',
            )
            mutant = reference.replace(
                '{"request_id", "submitted_at"}',
                '{"request_id", "submitted_at", "Request_id"}',
            )
            cases = [
                {"args": [v], "kwargs": {}}
                for v in (
                    {},
                    {"request_id": None, "submitted_at": False},
                    {"body": {"request_id": "nested"}, "request_id": "outer"},
                    {"x": False},
                    {"x": 0},
                    {"b": 2, "a": 1},
                )
            ]
        else:
            path, symbol, module = (
                common_path,
                "parse_message",
                "evaluation_harness.adapters.common",
            )
            for p in real_row["files"]:
                if p.startswith("src/") and p != path:
                    write(root, p, read_origin(evaluation, p))
            content = read_origin(evaluation, path)
            reference = content.replace(
                '    raw_content = value.get("content")\n',
                '    raw_content = value.get("content")\n    if isinstance(raw_content, dict):\n        raw_content = [raw_content]\n',
                1,
            )
            mutant = reference.replace('name=value.get("name"),', "name=None,", 1)
            values = [
                {"role": "assistant", "content": "hello"},
                {"role": "user", "content": [{"type": "text", "text": "hi"}]},
                {"role": "assistant", "content": {"type": "text", "text": "hi"}},
                {
                    "role": "tool",
                    "content": {"type": "tool_result", "call_id": "a", "result": None},
                },
                {
                    "role": "assistant",
                    "content": {
                        "type": "tool_call",
                        "tool_call": {"id": "a", "name": "x", "arguments": {"x": 0}},
                    },
                },
                {"role": "user", "content": {"type": "unknown"}},
            ]
            cases = [{"args": ["capture-trace", 0, v], "kwargs": {}} for v in values]
        assert reference != content and mutant != reference
        write(root, path, content)
        shutil.copyfile(
            FIXTURES / ("test_" + topic + ".py"), root / ("test_" + topic + ".py")
        )
        (root / "tests").mkdir()
        (root / ("test_" + topic + ".py")).rename(
            root / "tests" / ("test_" + topic + ".py")
        )
        shutil.copyfile(
            SEED / "message_id-candidate-1/isolated/pyproject.toml",
            root / "pyproject.toml",
        )
        write(BATCH, "private/" + topic + "/reference.py", reference)
        write(BATCH, "private/" + topic + "/mutant.py", mutant)
        shutil.copyfile(
            FIXTURES / ("private_" + topic + ".py"),
            BATCH / "private" / topic / ("test_private_" + topic + ".py"),
        )
        T.save(
            BATCH / "fixtures" / (topic + ".json"),
            {
                "path": path,
                "symbol": symbol,
                "module": module,
                "cases": cases,
                "contract": CONTRACTS[topic],
            },
        )
    T.save(BATCH / "origins.json", origins)
    print(
        "Registered three fixed feature contracts and isolated source slices; no model calls",
        flush=True,
    )


def fixture_controls():
    assert not (BATCH / "fixture-controls.json").exists()
    before = {
        str(p): ast.dump(
            ast.parse(p.read_text(encoding="utf-8")), include_attributes=False
        )
        for p in (BATCH / "fixtures").rglob("*.py")
    }
    formatted = command([PYTHON, "-B", "-m", "ruff", "format", BATCH / "fixtures"], KIT)
    T.save(BATCH / "fixture-formatting.json", formatted)
    assert formatted["exit_code"] == 0
    assert all(
        ast.dump(
            ast.parse(Path(p).read_text(encoding="utf-8")), include_attributes=False
        )
        == tree
        for p, tree in before.items()
    )
    outcomes = {}
    for topic in TOPICS:
        info = T.read(BATCH / "fixtures" / (topic + ".json"))
        for mode in ("baseline", "reference", "mutant"):
            root = BATCH / "controls" / topic / mode
            shutil.copytree(BATCH / "fixtures" / topic, root)
            if mode != "baseline":
                shutil.copyfile(
                    BATCH / "private" / topic / (mode + ".py"), root / info["path"]
                )
            formatting = command(
                [PYTHON, "-B", "-m", "ruff", "format", "src", "tests"], root
            )
            assert formatting["exit_code"] == 0
            env = {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(root / "src"),
            }
            tests = [
                "tests/test_" + topic + ".py",
                str(BATCH / "private" / topic / ("test_private_" + topic + ".py")),
            ]
            checks = [
                command(
                    [
                        PYTHON,
                        "-B",
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        target,
                        "--junitxml=" + str(root / ("junit-" + str(index) + ".xml")),
                    ],
                    root,
                    env,
                )
                for index, target in enumerate(tests)
            ]
            checks += [
                command(
                    [PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
                    root,
                ),
                command([PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root),
                command([PYTHON, "-B", "-m", "pyright", "--pythonpath", PYTHON], root),
            ]
            T.save(root / "results.json", checks)
            outcomes[topic + "-" + mode] = [r["exit_code"] for r in checks]
    T.save(BATCH / "fixture-controls.json", outcomes)
    assert all(outcomes[t + "-reference"] == [0, 0, 0, 0, 0] for t in TOPICS), outcomes
    assert all(outcomes[t + "-baseline"][0] != 0 for t in TOPICS), outcomes
    assert all(outcomes[t + "-mutant"][:2] == [0, 1] for t in TOPICS), outcomes
    T.save(
        BATCH / "fixture-controls-approved.json",
        BATCH / "preparation-v1-failure.json",
        BATCH / "preparation-v2-failure.json",
        KIT
        / "benchmarks/work/harness-convergence/r1-r2-20261013-2/cases/failed-draft-formal-1/isolated/.agent/config.json",
        {
            "passed": True,
            "results": outcomes,
            "model_calls": 0,
            "private_tests_add_detection": True,
            "formatting_ast_equal": True,
        },
    )


def prepare_cells(generation=1):
    assert T.read(BATCH / "fixture-controls-approved.json")["passed"]
    previous = SEED / "message_id-candidate-1/isolated"
    rows = {}
    for name in ORDER:
        topic, arm, _repeat = name.split("-")
        info = T.read(BATCH / "fixtures" / (topic + ".json"))
        directory = "cases" if generation == 1 else "cases-v" + str(generation)
        root = BATCH / directory / name / "isolated"
        shutil.copytree(BATCH / "fixtures" / topic, root)
        shutil.copytree(
            previous / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "*.pyc", "config.json"
            ),
        )
        # Both arms get the exact already-qualified review/handoff code. Only
        # baseline Coder runs its original frozen runtime in a separate folder.
        if arm == "baseline":
            shutil.copytree(
                SEED / "message_id-baseline-1/isolated/.local-agents",
                root / ".baseline-agents",
                ignore=shutil.ignore_patterns(
                    "tests", "__pycache__", "*.pyc", "config.json"
                ),
            )
        packet = T.read(previous / ".agent/packet.json")
        config = T.read(
            SEED / ("message_id-" + arm + "-1") / "isolated/.agent/config.json"
        )
        if arm == "baseline":
            original = T.read(
                KIT
                / "benchmarks/work/harness-convergence/r1-r2-20261013-2/cases/failed-draft-formal-1/isolated/.agent/config.json"
            )
            for key in ("coder_structured_output", "coder_typed_action_arguments"):
                config[key] = original[key]
        identity = {
            "task_id": "fresh-" + topic,
            "unit_id": "fresh-" + topic,
            "run_id": "fresh-20261017-" + name,
        }
        target = {k: info[k] for k in ("path", "module", "symbol")}
        inputs = [
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file()
            and (
                p.relative_to(root).parts[0] in {"src", "tests"}
                or p.name == "pyproject.toml"
            )
        ]
        capture_cases, omissions = [], []
        for index, case in enumerate(info["cases"]):
            try:
                F.P.bounded_json([case])
            except ValueError as exc:
                omissions.append(
                    {
                        "case_index": index,
                        "reason": str(exc),
                        "behavior_acceptance_still_required": True,
                    }
                )
            else:
                capture_cases.append(case)
        _policy, policy_sha = F.install_material(
            root,
            identity,
            source_paths=inputs,
            target=target,
            family="json-call-model-dump-v1",
            cases=capture_cases,
            writable=[info["path"]],
            python=PYTHON,
        )
        protected = [p for p in inputs if p != info["path"]] + [
            F.POLICY_PATH,
            F.PRODUCER,
            F.HELPER,
        ]
        contract = {
            "id": topic,
            "text": info["contract"],
            "risk_floor": "high",
            "implementation_ref": {"path": info["path"], "symbol": info["symbol"]},
        }
        packet.update(
            **identity,
            feature_id="fresh-" + topic,
            primary_plan_sha256=T.sha(BATCH / "registration.json"),
            goal=info["contract"],
            risk={
                "feature": "high",
                "unit": "high",
                "integration": "high",
                "reasons": [
                    "Primary: public validation/identity/parsing compatibility boundary; copied isolation does not lower the risk floor."
                ],
            },
            required_behavior=[contract],
            owned_contract_ids=[topic],
            acceptance_criteria=[
                {
                    "id": topic,
                    "text": "Satisfy all required behavior and the fixed project checks; tests alone do not establish untested branches.",
                }
            ],
            dependencies=[],
            implementation_guidance=[],
            review_feedback=[],
            scope={
                "read": ["src", "tests", "pyproject.toml", *protected[-3:]],
                "readonly": protected,
                "modify": [info["path"]],
                "create": [],
                "forbidden": [
                    ".agent",
                    ".git",
                    ".local-agents",
                    ".baseline-agents",
                    "AGENTS.md",
                ],
            },
            edit_targets=[
                {"path": info["path"], "anchor": "def " + info["symbol"] + "("}
            ],
            focused_tests=["tests/test_" + topic + ".py"],
            supplemental_tests=[],
            acceptance_scenarios=[
                {
                    "id": "normal",
                    "text": "Satisfy the specified normal behavior without changing caller inputs.",
                },
                {
                    "id": "boundary",
                    "text": "Preserve the explicitly specified falsy/null/order/size/type boundaries.",
                },
                {
                    "id": "error",
                    "text": "Reject invalid specified input without inventing fallback or mutating input.",
                },
            ],
        )
        source = ast.parse((root / info["path"]).read_text(encoding="utf-8"))
        declarations = [
            ast.unparse(n)
            for n in source.body
            if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign))
        ]
        if topic == "single_content":
            declarations += [
                ast.unparse(n)
                for n in ast.parse(
                    (root / "src/evaluation_harness/canonical/models.py").read_text(
                        encoding="utf-8"
                    )
                ).body
                if isinstance(n, ast.ClassDef)
                and n.name
                in {"CanonicalMessage", "TextPart", "ToolCallPart", "ToolResultPart"}
            ]
        config["coder_single_function"] = {
            "path": info["path"],
            "symbol": info["symbol"],
            "dependencies": "\n\n".join(declarations),
        }
        config["validation_profiles"]["real-trace-strict"]["commands"].append(
            F.command()
        )
        T.save(root / ".agent/packet.json", packet)
        T.save(root / ".agent/config.json", config)
        rows[name] = {
            "root": str(root),
            "policy_sha256": policy_sha,
            "files": source_map(root),
            "coder_runtime_dir": str(
                root / (".baseline-agents" if arm == "baseline" else ".local-agents")
            ),
            "observation_omissions": omissions,
        }
    manifest_name = (
        "prepared-cells.json"
        if generation == 1
        else "prepared-cells-v" + str(generation) + ".json"
    )
    T.save(BATCH / manifest_name, rows)
    print("Prepared twelve immutable paired inputs; no model calls", flush=True)


def entry_controls():
    rows = T.read(BATCH / "prepared-cells-v3.json")
    outcomes = {}
    for name, row in rows.items():
        root = Path(row["root"])
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
        worker = F.load(
            Path(row["coder_runtime_dir"]) / "worker-runtime.py",
            "fresh_preflight_" + name,
        )
        cls = CODER.install(worker, F.POLICY_PATH, row["policy_sha256"])
        packet, config = (
            T.read(root / ".agent/packet.json"),
            T.read(root / ".agent/config.json"),
        )
        if config.get("host_proposal_enabled") is True:
            host = F.load(
                root / ".local-agents/host-proposal.py", "fresh_host_preflight_" + name
            )
            cls = host.make_runtime_class(worker)
        client = type(
            "NoModel",
            (),
            {
                "timeout": 180,
                "structured_output": bool(config.get("coder_structured_output", True)),
                "native_tools": None,
                "typed_action_arguments": config.get(
                    "coder_typed_action_arguments", False
                ),
            },
        )()
        runtime = cls(root, packet, config, client)
        try:
            outcomes[name] = runtime.preflight()
            assert runtime.max_turns == runtime.hard_max_turns == 6
        finally:
            runtime.close()
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
    for topic in TOPICS:
        for repeat in (1, 2):
            left, right = (
                Path(rows[f"{topic}-{arm}-{repeat}"]["root"])
                for arm in ("baseline", "candidate")
            )
            a, b = (
                T.read(left / ".agent/packet.json"),
                T.read(right / ".agent/packet.json"),
            )
            a.pop("run_id"), b.pop("run_id")
            assert a == b
            ca, cb = (
                T.read(left / ".agent/config.json"),
                T.read(right / ".agent/config.json"),
            )
            differences = {k for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)}
            assert differences == {
                "host_proposal_enabled",
                "host_proposal_isolated_high_risk_fixture",
                "coder_single_function_patch_repair",
                "coder_structured_output",
                "coder_typed_action_arguments",
            }, differences
            for p in rows[f"{topic}-baseline-{repeat}"]["files"]:
                if p.startswith(("src/", "tests/", ".local-agents/")) or p in {
                    "pyproject.toml",
                    F.PRODUCER,
                    F.HELPER,
                }:
                    assert T.sha(left / p) == T.sha(right / p), p
    T.save(
        BATCH / "entry-controls.json",
        {
            "model_calls": 0,
            "paired_inputs_equal": True,
            "same_qualified_reviewer": True,
            "outcomes": outcomes,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "registration-controls-v1.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + k) for k in ("failure", "error", "skipped")
    )
    assert T.read(BATCH / "entry-controls.json")["paired_inputs_equal"]
    rows = T.read(BATCH / "prepared-cells-v3.json")
    pins = T.read(T.BATCH / "freeze.json")["pins"]
    for path, sha in pins.items():
        assert T.sha(path) == sha, path
    extra = [
        Path(__file__),
        KIT / "benchmarks/capture_coder_entry.py",
        KIT / "benchmarks/capture_unit_entry.py",
        KIT / "benchmarks/r3_capture/sitecustomize.py",
        BATCH / "registration.json",
        BATCH / "prepared-cells-v3.json",
        BATCH / "entry-controls.json",
        BATCH / "fixture-controls-approved.json",
        BATCH / "registration-controls-v1.xml",
        KIT / "tests/test_capture_transfer_registration.py",
    ]
    extra += list(FIXTURES.glob("*.py"))
    extra += [
        p
        for p in (BATCH / "private").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    T.save(
        BATCH / "live-freeze.json",
        {
            "pins": {**pins, **{str(p): T.sha(p) for p in extra}},
            "cells": rows,
            "models_unchanged": True,
            "semantic_candidate_unchanged": True,
            "registered_units": 12,
            "no_live_changes": True,
        },
    )


def run(name, used):
    assert 0 <= used < 15
    frozen = T.read(BATCH / "live-freeze.json")
    assert name in ORDER
    for previous in ORDER:
        if previous == name:
            break
        result = T.read(Path(frozen["cells"][previous]["root"]).parent / "result.json")
        if "-candidate-" in previous:
            primary = T.read(
                Path(frozen["cells"][previous]["root"]).parent / "primary-decision.json"
            )
            assert result["eligible_for_primary"] and primary["decision"] == "accept", (
                "Candidate gate unreachable; no further cells"
            )
    for path, sha in frozen["pins"].items():
        assert T.sha(path) == sha, path
    row = frozen["cells"][name]
    root = Path(row["root"])
    cell = root.parent
    assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
    T.save(
        cell / "started.json",
        {
            "case": name,
            "weekly_used": used,
            "started_at": time.time(),
            "no_retry": True,
        },
    )
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(KIT / "benchmarks/r3_capture"),
        "R3_WIRE_DIR": str(cell / "wire"),
    }
    argv = [
        PYTHON,
        "-B",
        KIT / "benchmarks/capture_unit_entry.py",
        "--coder-runtime-dir",
        row["coder_runtime_dir"],
        "--capture-policy-sha256",
        row["policy_sha256"],
        "--packet",
        root / ".agent/packet.json",
        "--config",
        root / ".agent/config.json",
        "--coder-report",
        cell / "coder.json",
        "--review-report",
        cell / "reviewer.json",
        "--summary",
        cell / "unit-summary.json",
    ]
    started = time.monotonic()
    process = subprocess.run(
        [str(x) for x in argv],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    T.save(
        cell / "entry-result.json",
        {
            "argv": [str(x) for x in argv],
            "exit_code": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "seconds": time.monotonic() - started,
        },
    )
    packet = T.read(root / ".agent/packet.json")
    topic = name.split("-")[0]
    (cell / "independent-checks").mkdir()
    independent_env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root / "src"),
    }
    checks = [
        command(
            [
                PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *packet["focused_tests"],
                BATCH / "private" / topic / ("test_private_" + topic + ".py"),
                "--junitxml=" + str(cell / "independent-checks/junit.xml"),
            ],
            root,
            independent_env,
        )
    ]
    checks += [
        command(
            [PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"], root
        ),
        command([PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root),
        command([PYTHON, "-B", "-m", "pyright", "--pythonpath", PYTHON], root),
    ]
    T.save(cell / "independent-checks/results.json", checks)
    coder = T.read(cell / "coder.json") if (cell / "coder.json").exists() else {}
    reviewer = (
        T.read(cell / "reviewer.json") if (cell / "reviewer.json").exists() else {}
    )
    drift = [
        p
        for p, sha in row["files"].items()
        if p not in packet["scope"]["modify"]
        and (not (root / p).is_file() or T.sha(root / p) != sha)
    ]
    eligible = (
        process.returncode == 0
        and coder.get("status")
        in {"ready_for_review", "validation_passed_pending_review"}
        and reviewer.get("decision") == "pass_to_primary"
        and not drift
        and all(c["exit_code"] == 0 for c in checks)
    )
    T.save(
        cell / "result.json",
        {
            "case": name,
            "eligible_for_primary": eligible,
            "coder_status": coder.get("status"),
            "reviewer_decision": reviewer.get("decision"),
            "checks": [c["exit_code"] for c in checks],
            "protected_drift": drift,
            "whole_seconds": time.monotonic() - started,
            "acceptance": "Primary review still required; this record never accepts a feature",
        },
    )
    print(json.dumps(T.read(cell / "result.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["prepare", "controls", "cells", "entry-controls", "freeze", "run"],
    )
    parser.add_argument("--used", required=True, type=int)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "controls": fixture_controls,
        "cells": lambda: prepare_cells(args.generation),
        "entry-controls": entry_controls,
        "freeze": freeze,
        "run": lambda: run(args.case, args.used),
    }[args.action]()
