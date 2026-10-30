"""Matched failure-context diagnostic, no formal unit or fresh-task credit."""

import argparse
import ast
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import repair_representation_diagnostic as D
import unified_transfer_trial as N

T, KIT, M = N.T, N.KIT, N.M
BATCH = KIT / "benchmarks/work/harness-convergence/exception-context-20261018-1"
ORDER = [
    f"{arm}-{n}"
    for n in (1, 2, 3)
    for arm in (("full", "lean") if n != 2 else ("lean", "full"))
]
ORIGIN = N.BATCH / "cases/messages_output-candidate-2/isolated"
RUN = (
    ORIGIN
    / ".agent/tasks/fresh-messages_output/runs/unified-transfer-20261018-messages_output-candidate-2"
)


def pruned_dependencies(module_source, roots):
    tree = ast.parse(module_source)
    nodes = {}
    for n in tree.body:
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes[n.name] = n
        elif isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name):
                    nodes[target.id] = n
    required, pending = set(), list(roots)
    while pending:
        name = pending.pop()
        if name in required or name not in nodes:
            continue
        required.add(name)
        pending.extend(
            n.id
            for n in ast.walk(nodes[name])
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        )
    selected = [
        n
        for n in tree.body
        if isinstance(n, (ast.Import, ast.ImportFrom))
        or any(nodes.get(k) is n for k in required)
    ]
    lines = module_source.splitlines()
    text = "\n\n".join("\n".join(lines[n.lineno - 1 : n.end_lineno]) for n in selected)
    return text, sorted(required), sorted(set(nodes) - required)


def prepare(used):
    assert 0 <= used < 15 and not T.read(N.BATCH / "decision.json")["r4_matrix_passed"]
    pins = T.read(N.BATCH / "live-freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    BATCH.mkdir(exist_ok=False)
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Human delegated same-boundary mechanical decisions; fixed model/context representation diagnosis, not a new semantic implementation or changed gate",
            "feature_id": "exception-repair-context",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "owned_contract_ids": ["messages_output"],
            "dependencies": ["closed-unified-transfer"],
            "risk_rationale": "Exception compatibility plus exact source/hash edit binding",
            "order": ORDER,
            "registered": 6,
            "fresh_holdout": False,
            "change": "Only target.dependencies: full real models module versus literal AST-name transitive closure rooted in InvocationInput/InvocationOutput/Message; all imports, required nodes and exact source retained",
            "unchanged": "System/schema/sampling, contract, actual failure including pytest.raises(ValueError), source/hash, tests, output4096 and single residency",
            "budget": {
                "proposals_per_cell": 1,
                "total_chat_requests": 6,
                "extra_probes": 0,
                "repairs": 0,
                "formatter_commands": 0,
            },
            "models": {"coder": "qwen/qwen3-coder-30b", "reviewer": "NOT_CALLED"},
            "criteria": "Lean3/3 applied, original25 behavior tests and strict static checks, no protected drift. Compare paired full3; if both pass cannot claim pruning required. No complete-chain, accepted-unit or fresh transfer credit. Close after fixed6 or infra/drift/budget stop; no sample replacement.",
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    request = T.read(RUN / "proposal-request-2.json")
    facts = D.INTERFACE.restore_literal(request["messages"][1]["content"])
    assert "with pytest.raises(ValueError):" in json.dumps(facts)
    binding = request["binding"]
    model_source = (ORIGIN / "src/agent_runtime/models.py").read_text(encoding="utf-8")
    dependencies = facts["target"]["dependencies"]
    assert dependencies.endswith(model_source)
    closure, included, excluded = pruned_dependencies(
        model_source, {"InvocationInput", "InvocationOutput", "Message"}
    )
    lean = copy.deepcopy(facts)
    lean["target"]["dependencies"] = dependencies[: -len(model_source)] + closure
    entry = next(
        p for p in T.read(RUN / "preimages.json") if p["path"] == binding["path"]
    )
    source = (ORIGIN / entry["archive_path"]).read_text(encoding="utf-8")
    previous_function = D.BOUNDARY.target(source, binding["symbol"])[3]
    source = source.replace(previous_function, binding["source"], 1)
    versions = [source.encode(), source.replace("\n", "\r\n").encode()]
    snapshot = next(
        v for v in versions if D.EDITOR.sha256_bytes(v) == binding["sha256"]
    )
    fixture = {
        "binding": binding,
        "span": {},
        "facts": facts,
        "user_message": D.INTERFACE.literal_input(facts),
        "lean_user_message": D.INTERFACE.literal_input(lean),
        "system_message": request["messages"][0]["content"],
        "included_names": included,
        "excluded_names": excluded,
        "origin_request": str(RUN / "proposal-request-2.json"),
        "origin_request_sha256": T.sha(RUN / "proposal-request-2.json"),
    }
    assert fixture["system_message"] == D.PROMPTS["whole"]
    T.save(BATCH / "fixture.json", fixture)
    (BATCH / "snapshot.py").write_bytes(snapshot)
    seed = T.read(N.BATCH / "cells.json")["messages_output-candidate-2"]
    rows = {}
    for name in ORDER:
        root = BATCH / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for relative in seed["files"]:
            if relative.startswith(("src/", "tests/")) or relative == "pyproject.toml":
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ORIGIN / relative, target)
        (root / binding["path"]).write_bytes(snapshot)
        rows[name] = {"root": str(root), "files": M.source_map(root)}
    T.save(BATCH / "cells.json", rows)
    T.save(
        BATCH / "failure-audit.json",
        {
            "model_calls": 0,
            "expected_value_error_assertion_displayed": True,
            "actual_type_error_displayed": True,
            "current_source_hash_bound": True,
            "initial_proposals": 2,
            "validations": 3,
            "semantic_progress": "First proposal resolves8 baseline failures but leaves3 invalid-canonical error-type failures; second broadens exception catch rather than preserving validation errors",
            "not_caused_by": [
                "invalid JSON",
                "rejected patch",
                "missing expected assertion",
                "HTTP400",
                "context/output exhaustion",
                "Reviewer startup",
            ],
            "capacity_inference": "A real applied semantic repair failure under this budget, not proof the model can never implement this task: separate first repetition passed25 and complete chain",
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "controls-v1.xml")
    assert len(tree.findall(".//testcase")) == 4
    assert not any(tree.findall(".//" + k) for k in ("failure", "error", "skipped"))
    pins = T.read(N.BATCH / "live-freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    files = [
        Path(__file__),
        KIT / "tests/test_exception_context.py",
        *[
            BATCH / n
            for n in (
                "registration.json",
                "fixture.json",
                "snapshot.py",
                "cells.json",
                "failure-audit.json",
                "controls-v1.xml",
            )
        ],
    ]
    T.save(
        BATCH / "freeze.json", {"pins": {**pins, **{str(p): T.sha(p) for p in files}}}
    )


def sample(name, used):
    original_read, original_apply, original_command = T.read, D.apply, M.command
    fixture_path = BATCH / "fixture.json"

    def read(path):
        value = original_read(path)
        if Path(path) == fixture_path and name.startswith("lean-"):
            value["user_message"] = value["lean_user_message"]
        return value

    def command(argv, root, env=None):
        argv = [str(x) for x in argv]
        for i, arg in enumerate(argv):
            if arg == "tests/test_metadata.py":
                argv[i] = "tests/test_messages_output.py"
            elif arg.endswith(
                "private/metadata/test_private_metadata.py"
            ) or arg.endswith("private\\metadata\\test_private_metadata.py"):
                argv[i] = str(
                    N.BATCH / "private/messages_output/test_private_messages_output.py"
                )
        return original_command(argv, root, env)

    # Exact original current Qwen inference settings. Diagnostic does not use
    # the old runtime or modify any source/config under either origin.
    current = original_read(ORIGIN / ".agent/config.json")
    legacy = original_read(
        Path(original_read(D.S.BATCH / "cells.json")["new-1"]["root"])
        / ".agent/config.json"
    )
    for key in (
        "lmstudio_base_url",
        "coder_model",
        "coder_max_tokens",
        "coder_temperature",
        "coder_top_p",
        "coder_top_k",
        "coder_min_p",
        "coder_repeat_penalty",
        "coder_context_length",
        "model_context_safety_margin",
    ):
        assert current[key] == legacy[key]
    D.BATCH, D.ORDER = BATCH, ORDER
    D.PROMPTS.update(full=D.PROMPTS["whole"], lean=D.PROMPTS["whole"])
    T.read = read
    D.apply = lambda root, raw, arm, fixture: original_apply(
        root, raw, "whole", fixture
    )
    M.command = command
    try:
        D.run(name, used)
    finally:
        T.read, D.apply, M.command = original_read, original_apply, original_command


def run_all(used):
    assert 0 <= used < 15
    for name in ORDER:
        cell = BATCH / "cases" / name
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(KIT / "benchmarks/r3_capture"),
            "R3_WIRE_DIR": str(cell / "wire"),
        }
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__)),
                "sample",
                "--case",
                name,
                "--used",
                str(used),
            ],
            env=env,
            cwd=KIT,
            check=False,
        )
        assert result.returncode == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "sample", "run-all"])
    parser.add_argument("--used", type=int, required=True)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "freeze": freeze,
        "sample": lambda: sample(args.case, args.used),
        "run-all": lambda: run_all(args.used),
    }[args.action]()
