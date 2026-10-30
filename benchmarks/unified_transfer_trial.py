"""Independent normal-implementation transfer; never reopens earlier scores."""

import argparse
import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

import capture_transfer_matrix as M
import unified_preparation_trial as U

T, KIT, PYTHON = M.T, M.KIT, M.PYTHON
OLD = M.BATCH
BATCH = KIT / "benchmarks/work/harness-convergence/unified-transfer-20261018-1"
ASSETS = KIT / "benchmarks/fixtures/capture-transfer-v2"
TOPICS = ("request_keys", "single_content", "messages_output")
ORDER = [
    f"{t}-{a}-{n}"
    for n in (1, 2)
    for t in TOPICS
    for a in (("baseline", "candidate") if n == 1 else ("candidate", "baseline"))
]
CONTRACT = (
    "Extend messages_output so that a mapping's exact messages field may contain one "
    "real Message or one Mapping describing a canonical message, equivalent to a "
    "singleton sequence. Preserve all existing list/tuple sequence behavior, order, "
    "direct InvocationOutput identity and direct Message handling. Use the unchanged "
    "real Message/InvocationOutput validation, including role/content, unknown-field "
    "and nonempty restrictions. Preserve metadata mapping conversion (stringify keys), "
    "values including falsy/null/nested data and bounded metadata validation on both "
    "old and new paths. Missing messages or unsupported scalar/string/bytes messages "
    "remain TypeError; invalid canonical messages remain rejected. Never mutate input "
    "or request. Keep signature and all source outside messages_output unchanged."
)


def activate():
    M.BATCH, M.TOPICS, M.ORDER = BATCH, TOPICS, ORDER


def prepare(used):
    assert 0 <= used < 15
    assert T.read(U.BATCH / "decision.json")["conditional_migration_allowed"]
    assert all(
        T.sha(p) == sha for p, sha in T.read(U.BATCH / "freeze.json")["pins"].items()
    )
    BATCH.mkdir(exist_ok=False)
    paths = set(
        T.git("ls-files", "-m", "-o", "--exclude-standard", "-z").split("\0")
    ) - {""}
    T.save(
        BATCH / "baseline.json",
        {
            "head": T.git("rev-parse", "HEAD").strip(),
            "files": {p: T.sha(KIT / p) for p in paths if (KIT / p).is_file()},
        },
    )
    T.save(
        BATCH / "registration.json",
        {
            "authorization": "Approved formal candidate/conditional migration and same-boundary autonomous decisions",
            "feature_id": "unified-normal-transfer",
            "feature_risk": "high",
            "unit_risk": {t: "high" for t in TOPICS},
            "integration_risk": "high",
            "risk_rationale": "Public identity/parser/runtime model compatibility boundaries remain high risk",
            "owned_contract_ids": list(TOPICS),
            "dependencies": ["unified-preparation-20261018-1"],
            "contracts": {
                **{t: M.CONTRACTS[t] for t in TOPICS[:2]},
                "messages_output": CONTRACT,
            },
            "order": ORDER,
            "registered_units": 12,
            "criterion": "Candidate6/6 Primary-accepted complete chains, each task2/2, not below paired baseline; same protected/private tests and strict checks, no safety failure or Primary semantic implementation takeover. First unreachable candidate closes batch; no replacement/retry.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
            },
            "single_residency": True,
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "budget": {
                "coder_requests": 6,
                "validations": 3,
                "model_edits": 3,
                "formatter_commands": 1,
                "coder_seconds": 900,
                "reviewer_requests": 16,
                "reviewer_errors": 4,
                "reviewer_seconds": 600,
                "reviewer_output_tokens": 4096,
            },
            "baseline": "Original R0 Coder bytes/config in .baseline-agents, same qualified Reviewer/capture; not previous exposed static-repair comparator",
            "candidate": "Exact frozen unified candidate, schema/one trusted formatter preparation/location-bound static span; no new runtime logic",
            "freshness": "request_keys/single_content are previously frozen but NOT_RUN contracts: Primary preparation known, no worker calls or candidate development from their outputs. messages_output is a new contract from sibling runtime; no live calls located for this contract. This is narrow task-level transfer, not unseen repository or universal coding proof.",
            "primary_classification": True,
            "coordinator_enabled": False,
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    old_rows = T.read(OLD / "prepared-cells-v3.json")
    for topic in TOPICS[:2]:
        for arm in ("baseline", "candidate"):
            row = old_rows[f"{topic}-{arm}-1"]
            assert not (Path(row["root"]).parent / "started.json").exists()
            assert all(
                T.sha(Path(row["root"]) / p) == sha for p, sha in row["files"].items()
            )
        shutil.copytree(OLD / "fixtures" / topic, BATCH / "fixtures" / topic)
        shutil.copytree(OLD / "private" / topic, BATCH / "private" / topic)
        T.save(
            BATCH / "fixtures" / (topic + ".json"),
            T.read(OLD / "fixtures" / (topic + ".json")),
        )
    runtime = KIT.parent / "agent-runtime-kit"
    origin_paths = [
        "src/agent_runtime/adapters/mapping.py",
        "src/agent_runtime/models.py",
    ]
    T.save(
        BATCH / "origins.json",
        {
            "repo": str(runtime),
            "head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=runtime, text=True
            ).strip(),
            "status": subprocess.check_output(
                ["git", "status", "--short"], cwd=runtime, text=True
            ),
            "files": {p: T.sha(runtime / p) for p in origin_paths},
            "isolation": "Exact modules; empty package initializers avoid unrelated optional adapter imports. No dependency stubs.",
        },
    )
    root = BATCH / "fixtures/messages_output"
    root.mkdir(parents=True)
    for p in origin_paths:
        M.write(root, p, (runtime / p).read_text(encoding="utf-8-sig"))
    for p in (
        "src/agent_runtime/__init__.py",
        "src/agent_runtime/adapters/__init__.py",
    ):
        M.write(root, p, "")
    (root / "tests").mkdir()
    shutil.copyfile(
        ASSETS / "test_messages_output.py", root / "tests/test_messages_output.py"
    )
    shutil.copyfile(
        OLD / "fixtures/request_keys/pyproject.toml", root / "pyproject.toml"
    )
    path = origin_paths[0]
    original = (root / path).read_text(encoding="utf-8")
    reference = original.replace(
        '    raw_messages = output_mapping.get("messages")\n',
        '    raw_messages = output_mapping.get("messages")\n    if isinstance(raw_messages, (Message, Mapping)):\n        raw_messages = [raw_messages]\n',
        1,
    )
    assert reference != original
    M.write(BATCH, "private/messages_output/reference.py", reference)
    M.write(
        BATCH,
        "private/messages_output/mutant.py",
        reference.replace(
            "messages=messages, metadata=metadata", "messages=messages, metadata={}", 1
        ),
    )
    shutil.copyfile(
        ASSETS / "private_messages_output.py",
        BATCH / "private/messages_output/test_private_messages_output.py",
    )
    message = {
        "id": "00000000-0000-0000-0000-000000000001",
        "role": "assistant",
        "content": [{"type": "text", "text": "hello"}],
    }
    values = [
        {"messages": message, "metadata": {"nil": None, "zero": 0}},
        {"messages": [message]},
        {"messages": []},
        {"messages": "bad"},
        {"messages": {**message, "role": "unknown"}},
    ]
    T.save(
        BATCH / "fixtures/messages_output.json",
        {
            "path": path,
            "symbol": "messages_output",
            "module": "agent_runtime.adapters.mapping",
            "contract": CONTRACT,
            "cases": [{"args": [value, None], "kwargs": {}} for value in values],
        },
    )
    print("Registered twelve units, no live calls")


def controls():
    # Fixed project formatter, before freezing. No source semantics changed.
    before = {
        str(p): ast.dump(
            ast.parse(p.read_text(encoding="utf-8")), include_attributes=False
        )
        for p in (BATCH / "fixtures").rglob("*.py")
    }
    formatting = M.command(
        [PYTHON, "-B", "-m", "ruff", "format", BATCH / "fixtures"], KIT
    )
    T.save(BATCH / "fixture-formatting.json", formatting)
    assert formatting["exit_code"] == 0
    assert all(
        ast.dump(
            ast.parse(Path(p).read_text(encoding="utf-8")), include_attributes=False
        )
        == tree
        for p, tree in before.items()
    )
    results = {}
    for topic in TOPICS:
        info = T.read(BATCH / "fixtures" / (topic + ".json"))
        for mode in ("baseline", "reference", "mutant"):
            root = BATCH / "controls" / topic / mode
            shutil.copytree(BATCH / "fixtures" / topic, root)
            if mode != "baseline":
                shutil.copyfile(
                    BATCH / "private" / topic / (mode + ".py"), root / info["path"]
                )
            formatting = M.command(
                [PYTHON, "-B", "-m", "ruff", "format", "src", "tests"], root
            )
            env = {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(root / "src"),
            }
            checks = [
                M.command(
                    [
                        PYTHON,
                        "-B",
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        test,
                        "--junitxml=" + str(root / f"junit-{i}.xml"),
                    ],
                    root,
                    env,
                )
                for i, test in enumerate(
                    [
                        "tests/test_" + topic + ".py",
                        str(
                            BATCH
                            / "private"
                            / topic
                            / ("test_private_" + topic + ".py")
                        ),
                    ]
                )
            ]
            checks += [
                M.command(
                    [PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
                    root,
                ),
                M.command([PYTHON, "-B", "-m", "ruff", "check", "src", "tests"], root),
                M.command(
                    [PYTHON, "-B", "-m", "pyright", "--pythonpath", PYTHON], root
                ),
            ]
            T.save(root / "results.json", {"format": formatting, "checks": checks})
            results[f"{topic}-{mode}"] = [c["exit_code"] for c in checks]
    T.save(BATCH / "fixture-controls.json", results)
    assert all(results[t + "-reference"] == [0] * 5 for t in TOPICS), results
    assert all(results[t + "-baseline"][0] != 0 for t in TOPICS), results
    assert all(results[t + "-mutant"][:2] == [0, 1] for t in TOPICS), results
    T.save(BATCH / "fixture-controls-approved.json", {"passed": True, "model_calls": 0})


def cells():
    activate()
    M.prepare_cells()
    rows = T.read(BATCH / "prepared-cells.json")
    template = T.read(
        Path(T.read(U.BATCH / "cells.json")["new-1"]["root"]) / ".agent/config.json"
    )
    for name, row in rows.items():
        root = Path(row["root"])
        packet = T.read(root / ".agent/packet.json")
        policy = T.read(root / M.F.POLICY_PATH)
        packet["run_id"] = "unified-transfer-20261018-" + name
        policy["identity"] = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
        for relative, data in (
            (".agent/packet.json", packet),
            (M.F.POLICY_PATH, policy),
        ):
            (root / relative).write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
        row["policy_sha256"] = T.sha(root / M.F.POLICY_PATH)
        config = T.read(root / ".agent/config.json")
        if "-candidate-" in name:
            for key in (
                "coder_structured_output",
                "experimental_output_channel",
                "experimental_prevalidation_format",
                "experimental_static_span_repair",
                "experimental_unified_preparation",
            ):
                config[key] = template[key]
        if name.startswith("messages_output-"):
            config["coder_single_function"]["dependencies"] += "\n\n" + (
                root / "src/agent_runtime/models.py"
            ).read_text(encoding="utf-8")
        # New local inputs only, before freeze.
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
        row["files"] = M.source_map(root)
    T.save(BATCH / "cells.json", rows)


def entries():
    outcomes = []
    rows = T.read(BATCH / "cells.json")
    for name, row in rows.items():
        root = Path(row["root"])
        if "-candidate-" in name:
            check = M.command(
                [
                    PYTHON,
                    "-B",
                    KIT / "benchmarks/unified_coder_entry.py",
                    "--preflight-only",
                    "--runtime-dir",
                    row["coder_runtime_dir"],
                    "--capture-policy",
                    M.F.POLICY_PATH,
                    "--capture-policy-sha256",
                    row["policy_sha256"],
                    "--packet",
                    root / ".agent/packet.json",
                    "--config",
                    root / ".agent/config.json",
                ],
                root,
            )
            assert check["exit_code"] == 0, check
        else:
            worker = M.F.load(
                Path(row["coder_runtime_dir"]) / "worker-runtime.py",
                "unified_transfer_baseline_" + name,
            )
            cls = M.CODER.install(worker, M.F.POLICY_PATH, row["policy_sha256"])
            config = T.read(root / ".agent/config.json")
            client = type(
                "NoModel",
                (),
                {
                    "timeout": 180,
                    "structured_output": config["coder_structured_output"],
                    "native_tools": None,
                    "typed_action_arguments": config["coder_typed_action_arguments"],
                },
            )()
            runtime = cls(root, T.read(root / ".agent/packet.json"), config, client)
            try:
                check = runtime.preflight()
                assert runtime.max_turns == runtime.hard_max_turns == 6
            finally:
                runtime.close()
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
        capture = M.command(
            [PYTHON, "-B", root / M.F.PRODUCER, "--policy", M.F.POLICY_PATH],
            root,
            {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert capture["exit_code"] == 0, capture
        assert json.loads(capture["stdout"])["observations"]
        assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
        outcomes.append({"case": name, "preflight": check, "actual_capture": capture})
    paired = []
    for topic in TOPICS:
        for repeat in (1, 2):
            left, right = [
                Path(rows[f"{topic}-{a}-{repeat}"]["root"])
                for a in ("baseline", "candidate")
            ]
            a, b = [T.read(p / ".agent/packet.json") for p in (left, right)]
            a.pop("run_id"), b.pop("run_id")
            assert a == b
            for p in rows[f"{topic}-baseline-{repeat}"]["files"]:
                if p.startswith(("src/", "tests/", ".local-agents/")) or p in {
                    "pyproject.toml",
                    M.F.PRODUCER,
                    M.F.HELPER,
                }:
                    assert T.sha(left / p) == T.sha(right / p)
            a, b = [T.read(p / ".agent/config.json") for p in (left, right)]
            differences = {
                k: [a.get(k), b.get(k)] for k in set(a) | set(b) if a.get(k) != b.get(k)
            }
            paired.append(
                {"topic": topic, "repeat": repeat, "config_differences": differences}
            )
    T.save(
        BATCH / "entry-controls-v2.json",
        {
            "model_calls": 0,
            "outcomes": outcomes,
            "paired": paired,
            "same_qualified_reviewer": True,
            "paired_contract_source_tests_equal": True,
        },
    )


def freeze():
    import xml.etree.ElementTree as ET

    tree = ET.parse(BATCH / "registration-controls-v2.xml")
    assert len(tree.findall(".//testcase")) == 4
    assert not any(tree.findall(".//" + k) for k in ("failure", "error", "skipped"))
    assert len(T.read(BATCH / "entry-controls-v2.json")["outcomes"]) == 12
    pins = T.read(U.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in pins.items())
    paths = [
        Path(__file__),
        BATCH / "registration.json",
        BATCH / "cells.json",
        BATCH / "entry-controls-v2.json",
        BATCH / "fixture-controls.json",
        BATCH / "fixture-controls-approved.json",
        BATCH / "origins.json",
        BATCH / "registration-controls-v1.xml",
        BATCH / "registration-controls-v2.xml",
        KIT / "tests/test_unified_transfer_registration.py",
    ]
    paths += [
        p
        for base in (ASSETS, BATCH / "private", BATCH / "fixtures")
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    T.save(
        BATCH / "live-freeze.json",
        {
            "pins": {**pins, **{str(p): T.sha(p) for p in paths}},
            "cells": T.read(BATCH / "cells.json"),
            "no_live_changes": True,
        },
    )


def run(name, used):
    activate()
    original = subprocess.run

    def dispatch(argv, *args, **kwargs):
        argv = [str(x) for x in argv]
        old = str(KIT / "benchmarks/capture_unit_entry.py")
        if "-candidate-" in name and old in argv:
            argv[argv.index(old)] = str(KIT / "benchmarks/unified_unit_entry.py")
        return original(argv, *args, **kwargs)

    subprocess.run = dispatch
    try:
        M.run(name, used)
    finally:
        subprocess.run = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["prepare", "controls", "cells", "entries", "freeze", "run"]
    )
    parser.add_argument("--used", required=True, type=int)
    parser.add_argument("--case")
    args = parser.parse_args()
    {
        "prepare": lambda: prepare(args.used),
        "controls": controls,
        "cells": cells,
        "entries": entries,
        "freeze": freeze,
        "run": lambda: run(args.case, args.used),
    }[args.action]()
