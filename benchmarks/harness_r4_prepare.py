"""R4 preflight from previously frozen holdouts, without production or history edits."""

import argparse
import ast
import hashlib
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_r3_readiness as S

B, P, R = S.B, S.P, S.R
BATCH = B.KIT / "benchmarks/work/harness-convergence/r4-transfer-20261016-1"
TOPICS = ("message_id", "datetime", "collect_tools")
ORDER = [
    f"{topic}-{arm}-{repeat}"
    for repeat in (1, 2)
    for topic in TOPICS
    for arm in (("baseline", "candidate") if repeat == 1 else ("candidate", "baseline"))
]
REVIEWER_REGISTRATION = (
    B.KIT / "benchmarks/work/system-convergence/r1-20261010-1/registration.json"
)


def confirm_controls():
    observed = B.read(BATCH / "corrected-preflight-decision.json")["results"]
    expected = {
        "message_id": [0, 1, 1, 0],
        "datetime": [1, 0, 1, 1],
        "collect_tools": [1, 0, 0, 0],
    }
    for topic in TOPICS:
        assert observed[topic]["private-reference"] == [0, 0, 0, 0]
        assert observed[topic]["visible"] == expected[topic]
        for arm in ("private-reference", "visible"):
            root = BATCH / "prepared-fixtures" / topic / arm
            R.assert_files(
                root, B.read(BATCH / "prepared-fixtures-freeze.json")[topic][arm]
            )
            proof = B.read(
                BATCH
                / "corrected-controls"
                / topic
                / arm
                / "mechanical-test-normalization.json"
            )
            assert proof["test_ast_equal"]
    rows = B.read(BATCH / "corrected-controls/datetime/visible/results.json")
    assert (
        "F401" in rows[2]["stdout"]
        and "`datetime.UTC` imported but unused" in rows[2]["stdout"]
    )
    assert 'Import "UTC" is not accessed' in rows[3]["stdout"]
    B.save(
        BATCH / "controls-approved.json",
        {
            "ready": True,
            "expected_visible_exits": expected,
            "correction": "Initial predicate omitted the frozen datetime stub's unused UTC import. Both lint and type failures are genuine task errors, not test failures; source is untouched.",
            "reference_all_checks_passed": True,
            "test_ast_equal": True,
            "live_calls": 0,
        },
    )


def prepare_cases():
    assert B.read(BATCH / "controls-approved.json")["ready"]
    frozen = B.read(P.BATCH / "holdouts-freeze.json")
    snapshots = B.read(BATCH / "prepared-fixtures-freeze.json")
    cases = {}
    for name in ORDER:
        topic, arm, _ = name.split("-")
        info = frozen["cases"][topic]
        source = BATCH / "prepared-fixtures" / topic / "visible"
        R.assert_files(source, snapshots[topic]["visible"])
        root = BATCH / "cases" / name / "isolated"
        P.copy_inputs(source, root)
        previous = S.BATCH / "cases" / f"presence-{arm}-1" / "isolated"
        shutil.copytree(
            previous / ".local-agents",
            root / ".local-agents",
            ignore=shutil.ignore_patterns(
                "tests", "__pycache__", "*.pyc", "config.json"
            ),
        )
        packet = B.read(previous / ".agent/packet.json")
        config = B.read(previous / ".agent/config.json")
        # Source-backed declarations only, never the private reference function.
        module = ast.parse((source / info["path"]).read_text(encoding="utf-8"))
        declarations = [
            ast.unparse(node)
            for node in module.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        if topic == "collect_tools":
            model_source = source / "src/evaluation_harness/canonical/models.py"
            declarations += [
                ast.unparse(node)
                for node in ast.parse(model_source.read_text(encoding="utf-8")).body
                if isinstance(node, ast.ClassDef)
                and node.name
                in {
                    "CanonicalMessage",
                    "CanonicalToolCall",
                    "ToolCallPart",
                    "ToolResultPart",
                }
            ]
        config["coder_single_function"] = {
            "path": info["path"],
            "symbol": info["symbol"],
            "dependencies": "\n\n".join(declarations),
        }
        task_id = "r4-" + topic
        contract = {
            "id": task_id,
            "text": info["goal"]
            + " Preserve the signature and all code outside this function; all fixed tests and checks must pass.",
            "risk_floor": "high",
            "implementation_ref": {"path": info["path"], "symbol": info["symbol"]},
        }
        readonly = [p for p in snapshots[topic]["visible"] if p != info["path"]]
        packet.update(
            task_id=task_id,
            feature_id="host-proposal-transfer-v1",
            unit_id=task_id,
            run_id="r4-20261016-" + name,
            primary_plan_sha256=B.sha(BATCH / "registration.json"),
            goal=info["goal"],
            owned_contract_ids=[task_id],
            required_behavior=[contract],
            acceptance_criteria=[{"id": task_id, "text": contract["text"]}],
            scope={
                "read": ["src", "tests", "pyproject.toml"],
                "modify": [info["path"]],
                "create": [],
                "readonly": readonly,
                "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
            },
            edit_targets=[
                {"path": info["path"], "anchor": "def " + info["symbol"] + "("}
            ],
            focused_tests=[info["visible_test_file"]],
            supplemental_tests=[],
            implementation_guidance=[],
            acceptance_scenarios=[
                {
                    "id": "normal",
                    "text": "Satisfy the normal behavior in the frozen function contract and tests.",
                },
                {
                    "id": "boundary",
                    "text": "Preserve empty/falsy/identity/order cases specified by the contract and frozen tests.",
                },
                {
                    "id": "error",
                    "text": "Preserve the specified error or unmatched-input behavior; no silent fallback beyond the contract.",
                },
            ],
            dependencies=[],
            review_feedback=[],
        )
        B.save(root / ".agent/packet.json", packet)
        B.save(root / ".agent/config.json", config)
        for p, digest in snapshots[topic]["visible"].items():
            assert B.sha(root / p) == digest
        cases[name] = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
    B.save(BATCH / "prepared-cases.json", cases)
    print("Twelve R4 cells prepared from identical frozen paired inputs", flush=True)


def entry_preflight():
    cases = B.read(BATCH / "prepared-cases.json")
    outcomes = {}
    for name, files in cases.items():
        topic, arm, _ = name.split("-")
        root = BATCH / "cases" / name / "isolated"
        R.assert_files(root, files)
        worker = R.load(
            root / ".local-agents/worker-runtime.py", "r4_preflight_" + name
        )
        packet, config = (
            B.read(root / ".agent/packet.json"),
            B.read(root / ".agent/config.json"),
        )
        client = type(
            "NoModel",
            (),
            {
                "timeout": 180,
                "structured_output": config.get("coder_structured_output", True),
                "native_tools": None,
                "typed_action_arguments": False,
            },
        )()
        cls = worker.WorkerRuntime
        if arm == "candidate":
            cls = R.load(
                root / ".local-agents/host-proposal.py", "r4_host_" + name
            ).make_runtime_class(worker)
        runtime = cls(root, packet, config, client)
        runtime.preflight()
        assert runtime.max_turns == runtime.hard_max_turns == 6
        runtime.close()
        observed = checks(root, BATCH / "entry-controls" / name)
        exits = [row["exit_code"] for row in observed]
        assert (
            exits
            == B.read(BATCH / "controls-approved.json")["expected_visible_exits"][topic]
        )
        R.assert_files(root, files)
        outcomes[name] = exits
        print(name, "entry and starting predicate PASS", flush=True)
    for topic in TOPICS:
        for repeat in (1, 2):
            a = B.read(
                BATCH
                / "cases"
                / f"{topic}-baseline-{repeat}"
                / "isolated/.agent/packet.json"
            )
            b = B.read(
                BATCH
                / "cases"
                / f"{topic}-candidate-{repeat}"
                / "isolated/.agent/packet.json"
            )
            a.pop("run_id")
            b.pop("run_id")
            assert a == b
    B.save(BATCH / "entry-controls-approved.json", outcomes)


def freeze():
    assert len(B.read(BATCH / "entry-controls-approved.json")) == 12
    tree = ET.parse(BATCH / "driver-controls.xml")
    assert tree.findall(".//testcase") and not any(
        tree.findall(".//" + kind) for kind in ("failure", "error", "skipped")
    )
    original = B.read(S.BATCH / "live-freeze-approved.json")
    R.assert_files(B.KIT, original["candidate_and_driver"])
    B.save(
        BATCH / "live-freeze-approved.json",
        {
            **original,
            "candidate_and_driver": {
                **original["candidate_and_driver"],
                "benchmarks/harness_r4_prepare.py": B.sha(Path(__file__)),
                "tests/test_harness_r4_registration.py": B.sha(
                    B.KIT / "tests/test_harness_r4_registration.py"
                ),
            },
            "registration": B.sha(BATCH / "registration.json"),
            "prepared_cases": B.sha(BATCH / "prepared-cases.json"),
            "fixture_controls": B.sha(BATCH / "controls-approved.json"),
            "entry_controls": B.sha(BATCH / "entry-controls-approved.json"),
            "fixture_correction_registration": B.sha(
                BATCH / "fixture-correction-registration.json"
            ),
        },
    )


def run(name, used):
    assert name in ORDER
    for previous in ORDER[: ORDER.index(name)]:
        if "-candidate-" in previous:
            assert (
                B.read(BATCH / "cases" / previous / "primary-decision.json")["decision"]
                == "accept"
            )
    frozen = B.read(BATCH / "live-freeze-approved.json")
    assert B.sha(BATCH / "controls-approved.json") == frozen["fixture_controls"]
    assert B.sha(BATCH / "entry-controls-approved.json") == frozen["entry_controls"]
    R.BATCH = BATCH
    R.run(name, used)


def checks(root, output):
    output.mkdir(parents=True)
    commands = [
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
            "--junitxml=" + str(output / "pytest.xml"),
        ],
        ["-m", "ruff", "format", "--check", "src", "tests"],
        ["-m", "ruff", "check", "src", "tests"],
        ["-m", "pyright", "--pythonpath", str(P.PYTHON)],
    ]
    result = [B.command([str(P.PYTHON), "-B", *args], cwd=root) for args in commands]
    B.save(output / "results.json", result)
    return result


def register(used):
    assert 0 <= used < 30
    assert B.read(S.BATCH / "decision.json")["r4_admitted"] is True
    candidate = B.read(S.BATCH / "live-freeze-approved.json")
    R.assert_files(B.KIT, candidate["candidate_and_driver"])
    frozen = B.read(P.BATCH / "holdouts-freeze.json")
    for name, row in frozen["cases"].items():
        R.assert_files(P.BATCH / "holdouts-v2" / name, row["files"])
    BATCH.mkdir(exist_ok=False)
    paths = {Path(p) for p in B.read(S.BATCH / "baseline.json")}
    paths.update(B.files(S.BATCH))
    B.save(
        BATCH / "baseline.json",
        {str(p): B.sha(p) for p in sorted(paths) if p.is_file()},
    )
    B.save(
        BATCH / "registration.json",
        {
            "stage": "R4",
            "feature_id": "host-proposal-transfer-v1",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "rationale": "Frozen isolated transfer tests of the versioned acceptance boundary, not deployment",
            "dependencies": [str(S.BATCH / "decision.json")],
            "owned_contract_ids": [
                "scope-preservation",
                "current-validation",
                "independent-review",
                "immutable-history",
            ],
            "order": ORDER,
            "registered": 12,
            "candidate_denominator": 6,
            "gate": "candidate 6/6 complete chains and every topic 2/2; no safety failure or semantic rescue; not worse than baseline",
            "reviewer_gate": "Original 16 controls with unchanged semantic adjudication; separate from clean transfer chains",
            "reviewer_registration": str(REVIEWER_REGISTRATION),
            "reviewer_registration_sha256": B.sha(REVIEWER_REGISTRATION),
            "holdouts_sha256": B.sha(P.BATCH / "holdouts-freeze.json"),
            "candidate_and_driver": candidate["candidate_and_driver"],
            "models": B.read(S.BATCH / "registration.json")["models"],
            "budgets": B.read(S.BATCH / "registration.json")["budgets"],
            "single_model_residency": True,
            "usage_start": used,
            "usage_ceiling": 30,
            "stop": "Failed preflight means zero live; candidate quality failure closes transfer gate; no resampling",
            "no_production_runtime_changes": True,
        },
    )
    print("R4 registered; no model calls", flush=True)


def preflight():
    registration = B.read(BATCH / "registration.json")
    assert B.sha(P.BATCH / "holdouts-freeze.json") == registration["holdouts_sha256"]
    frozen = B.read(P.BATCH / "holdouts-freeze.json")
    results = {}
    for topic in TOPICS:
        original = P.BATCH / "holdouts-v2" / topic
        R.assert_files(original, frozen["cases"][topic]["files"])
        results[topic] = {}
        for arm in ("private-reference", "visible"):
            root = BATCH / "preflight" / topic / arm
            P.copy_inputs(original / arm, root)
            for p in B.files(original / arm):
                assert B.sha(p) == B.sha(root / p.relative_to(original / arm))
            observations = checks(root, BATCH / "preflight-results" / topic / arm)
            exits = [row["exit_code"] for row in observations]
            results[topic][arm] = exits
            print(topic, arm, exits, flush=True)
    ready = all(results[topic]["private-reference"] == [0, 0, 0, 0] for topic in TOPICS)
    ready = ready and results["message_id"]["visible"] == [0, 0, 1, 0]
    ready = ready and all(
        results[topic]["visible"][0] != 0 for topic in ("datetime", "collect_tools")
    )
    B.save(
        BATCH / "preflight-decision.json",
        {"ready": ready, "results": results, "live_calls": 0},
    )
    print({"ready_for_live_preparation": ready}, flush=True)


def normalize_fixture_tests():
    """Only mechanical test layout in new copies; original frozen inputs untouched."""
    assert B.read(BATCH / "preflight-decision.json")["ready"] is False
    frozen = B.read(P.BATCH / "holdouts-freeze.json")
    B.save(
        BATCH / "fixture-correction-registration.json",
        {
            "reason": "Frozen references fail whole-project checks in protected test layout; no live calls occurred",
            "authorized_changes": "Only Ruff I001/RUF100 and formatting in copied tests, AST including imports/order/assertions identical",
            "source_changes": "none, including original mutations and private reference implementations",
            "unchanged": "models, runtime, all assertions, behavior, budgets, gate, topic selection and original frozen files",
            "message_id_expected_exits_correction": [0, 1, 1, 0],
            "message_id_reason": "Original frozen mutation also contains a trailing docstring space; observed format failure is inside the target and must remain, not be repaired by Primary",
        },
    )
    results, snapshots = {}, {}
    for topic in TOPICS:
        origin = P.BATCH / "holdouts-v2" / topic
        R.assert_files(origin, frozen["cases"][topic]["files"])
        results[topic], snapshots[topic] = {}, {}
        for arm in ("private-reference", "visible"):
            root = BATCH / "prepared-fixtures" / topic / arm
            P.copy_inputs(origin / arm, root)
            before = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
            ast_before = {
                p.name: ast.dump(
                    ast.parse(p.read_text(encoding="utf-8")), include_attributes=False
                )
                for p in (root / "tests").glob("*.py")
            }
            formatting = [
                B.command(
                    [
                        str(P.PYTHON),
                        "-B",
                        "-m",
                        "ruff",
                        "check",
                        "--fix",
                        "--select",
                        "I001,RUF100",
                        "tests",
                    ],
                    cwd=root,
                ),
                B.command(
                    [str(P.PYTHON), "-B", "-m", "ruff", "format", "tests"], cwd=root
                ),
            ]
            assert all(row["exit_code"] == 0 for row in formatting)
            ast_after = {
                p.name: ast.dump(
                    ast.parse(p.read_text(encoding="utf-8")), include_attributes=False
                )
                for p in (root / "tests").glob("*.py")
            }
            assert ast_before == ast_after, (
                "Mechanical fixture repair changed test semantics"
            )
            after = {p.relative_to(root).as_posix(): B.sha(p) for p in B.files(root)}
            changed = [path for path in before if before[path] != after[path]]
            assert all(path.startswith("tests/") for path in changed)
            output = BATCH / "corrected-controls" / topic / arm
            observed = checks(root, output)
            B.save(
                output / "mechanical-test-normalization.json",
                {
                    "commands": formatting,
                    "changed_paths": changed,
                    "before": before,
                    "after": after,
                    "test_ast_equal": True,
                    "ast_sha256": {
                        name: hashlib.sha256(value.encode()).hexdigest()
                        for name, value in ast_before.items()
                    },
                },
            )
            results[topic][arm] = [row["exit_code"] for row in observed]
            snapshots[topic][arm] = after
            print(topic, arm, results[topic][arm], flush=True)
        left, right = snapshots[topic]["private-reference"], snapshots[topic]["visible"]
        assert all(right[p] == h for p, h in left.items() if p.startswith("tests/"))
    ready = all(results[t]["private-reference"] == [0, 0, 0, 0] for t in TOPICS)
    ready = ready and results["message_id"]["visible"] == [0, 1, 1, 0]
    ready = ready and results["datetime"]["visible"] == [1, 0, 0, 1]
    ready = ready and results["collect_tools"]["visible"] == [1, 0, 0, 0]
    B.save(BATCH / "prepared-fixtures-freeze.json", snapshots)
    B.save(
        BATCH / "corrected-preflight-decision.json",
        {"ready": ready, "results": results, "live_calls": 0},
    )
    print({"ready_for_live_preparation": ready}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "register",
            "preflight",
            "normalize_fixture_tests",
            "confirm_controls",
            "prepare_cases",
            "entry_preflight",
            "freeze",
            "run",
        ],
    )
    parser.add_argument("--used", type=int)
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.action == "register":
        register(args.used)
    elif args.action == "run":
        run(args.case, args.used)
    else:
        globals()[args.action]()
