"""D2 thin experiment adapter: proposals never dispatch or accept by themselves."""

import argparse
import ast
import os
import shutil
import subprocess
import time
from pathlib import Path

import qualification_matrix_cases as CASES
from convergence_coder import KIT, PYTHON, save
from convergence_decomposition import load
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/execution-20261011-1"
TARGET = BASE / "candidate-kit"
RUNTIME = TARGET / ".local-agents"
R_SOURCE = KIT / "benchmarks/work/system-convergence/assessment-20261011-1/reviewer-kit"
E_SOURCE = (
    KIT
    / "benchmarks/work/system-convergence/protocol-20261011-1/explorer/candidate-kit"
)
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def module():
    return load("d2_brief", RUNTIME / "coordinator-brief.py")


def command(root, argv, output):
    if output.exists():
        raise FileExistsError(str(output))
    start = time.perf_counter()
    result = subprocess.run(
        [str(PYTHON), "-B", *map(str, argv)],
        cwd=root,
        env=ENV,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    save(
        output,
        {
            "exit": result.returncode,
            "command_wall_seconds": time.perf_counter() - start,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    print(
        output.name,
        result.returncode,
        result.stdout[-700:],
        result.stderr[-300:],
        flush=True,
    )
    return result.returncode


def fixtures():
    data, oracles = CASES.corpus(
        read_object(KIT / "benchmarks/fixtures/mixed-features-v1.json")["cases"][0]
    )
    selected = []
    for ident in ("async-first-present", "async-receipt"):
        case = next(c for c in data["cases"] if c["case_id"] == ident)
        selected.append(
            {
                "id": ident,
                "goal": case["goal"],
                "files": case["files"],
                "contracts": [
                    {"id": u["unit_id"], "text": u["contract"], "risk_floor": "medium"}
                    for u in case["units"]
                ],
                "selectors": {u["unit_id"]: u["tests"] for u in case["units"]},
                "edges": [["collect-unit", "qual-unit"]]
                if ident == "async-receipt"
                else [],
                "reference": oracles[ident]["reference"],
                "mutants": oracles[ident]["mutants"],
                "origin": "Previously qualified synthetic executable business fixture; not a real-project copy",
                "expected_units": 2 if ident == "async-receipt" else 1,
            }
        )
    real_path = "src/evaluation_harness/telemetry/classification.py"
    sibling = KIT.parent / "agent-evaluation-harness" / real_path
    original = sibling.read_text(encoding="utf-8")
    behavior = (
        "is_internal_trace returns False without raising for non-dict raw or truthy non-dict attributes, metadata or resource. "
        "Preserve existing valid dictionary semantics: attributes-or-metadata fallback, evaluator internal/source markers, default/custom service names, precedence, and no input mutation. "
        "An invalid selected nested container is external even if another container carries an internal marker. No new API, dependency or changes to protected tests."
    )
    reference = original.replace(
        '    resource = raw.get("resource") or {}',
        '    resource = raw.get("resource") or {}\n    if not isinstance(attributes, dict) or not isinstance(resource, dict):\n        return False',
    )
    tests = (
        KIT
        / "benchmarks/fixtures/convergence-decomposition/tests/test_classification_shapes.py"
    ).read_text()
    tests += """\n\ndef test_fallback_precedence_and_shape_boundaries():
    classify = runpy.run_path("src/evaluation_harness/telemetry/classification.py")["is_internal_trace"]
    raw = {"attributes": {}, "metadata": {"evaluation.source": "worker"}}
    assert classify(raw) is True
    assert raw == {"attributes": {}, "metadata": {"evaluation.source": "worker"}}
    assert classify({"attributes": {"other": 1}, "metadata": {"evaluation.internal": True}}) is False
    for key in ("attributes", "metadata", "resource"):
        for bad in ([1], "bad", 1, True):
            assert classify({key: bad}) is False
    assert classify({"attributes": [1], "resource": {"service.name": "evaluation-api"}}) is False
    assert classify({"attributes": {"evaluation.internal": True}, "resource": "bad"}) is False
    for marker in ("evaluator", "worker", "api"):
        assert classify({"attributes": {"evaluation.source": marker}}) is True
    assert classify({"attributes": {"evaluation.internal": 1}}) is False
    for service in ("evaluation-api", "evaluation-worker"):
        assert classify({"resource": {"service.name": service}}) is True
    assert classify({"resource": {"service.name": "custom"}}, service_names={"custom"}) is True
    assert classify({"resource": {"service.name": "evaluation-api"}}, service_names={"custom"}) is False
    assert classify({"resource": {"service.name": "outside"}, "attributes": {"service.name": "evaluation-api"}}) is False
"""
    selected.append(
        {
            "id": "classification-shapes",
            "goal": behavior,
            "files": {
                real_path: original,
                "tests/test_classification_shapes.py": tests,
            },
            "contracts": [
                {
                    "id": "classification-shapes",
                    "text": behavior,
                    "risk_floor": "medium",
                }
            ],
            "selectors": {
                "classification-shapes": ["tests/test_classification_shapes.py"]
            },
            "edges": [],
            "reference": {real_path: reference},
            "mutants": [
                {real_path: original},
                {
                    real_path: reference.replace(
                        'attributes = raw.get("attributes") or raw.get("metadata") or {}',
                        'attributes = raw.get("attributes") or {}',
                    )
                },
            ],
            "origin": {
                "kind": "real-readonly-copy",
                "source": str(sibling),
                "sha256": sha256(sibling),
                "novelty": "Not previously implemented by Coder; Coordinator saw original D1 brief/source. Not blind.",
                "family": "Bounded type/error branch preservation; transfer within supervised branch family",
            },
            "expected_units": 1,
        }
    )
    return selected


def prepare():
    BASE.mkdir(parents=True, exist_ok=False)
    assert (
        read_object(R_SOURCE.parent / "reviewer/stage-decision-1.json")["correct"] == 16
    )
    assert (
        read_object(E_SOURCE.parent / "stage-decision-1.json")[
            "question_complete_and_truthful"
        ]
        == 6
    )
    shutil.copytree(
        R_SOURCE,
        TARGET,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    for path in (
        ".local-agents/explorer-runtime.py",
        ".local-agents/tests/test_explorer_answers.py",
    ):
        shutil.copyfile(E_SOURCE / path, TARGET / path)
    shutil.copyfile(
        KIT / "tests/test_convergence_execution.py",
        TARGET / "tests/test_convergence_execution.py",
    )
    for filename in (
        "convergence_execution.py",
        "convergence_decomposition.py",
        "convergence_coder.py",
    ):
        shutil.copyfile(KIT / "benchmarks" / filename, TARGET / "benchmarks" / filename)
    config = read_object(
        KIT
        / "benchmarks/work/system-convergence/c1-20261010-1/cells/async-baseline/.agent/config.json"
    )
    config.update(
        explorer_answer_protocol=True,
        reviewer_evidence_ids=True,
        reviewer_assessment_protocol=True,
        coordinator_enabled=True,
    )
    assert config["single_model_residency"] is True
    save(BASE / "config.json", config)
    features = []
    for index, case in enumerate(fixtures()):
        arms = []
        for arm in ("A", "B"):
            root = BASE / "features" / case["id"] / arm
            root.mkdir(parents=True)
            paths = {
                **case["files"],
                "pyproject.toml": (
                    KIT / "benchmarks/fixtures/convergence-decomposition/pyproject.toml"
                ).read_text(),
            }
            for name, text in paths.items():
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(text, encoding="utf-8")
            # Format only before input registration, preserving source semantics.
            subprocess.run(
                [str(PYTHON), "-B", "-m", "ruff", "format", "src", "tests"],
                cwd=root,
                env=ENV,
                check=True,
                capture_output=True,
            )
            sources = {p: sha256(root / p) for p in paths}
            writes = list(case["reference"])
            readonly = [p for p in paths if p not in writes]
            brief = {
                "schema_version": 1,
                "revision": 1,
                "feature_id": "d2-" + case["id"] + "-" + arm.lower(),
                "task_id": "d2-" + case["id"] + "-" + arm.lower(),
                "goal": case["goal"],
                "feature_risk": "medium",
                "integration_risk": "medium",
                "risk_rationale": "Bounded business behavior, public input/exception compatibility; no security or transaction authority delegated",
                "contracts": case["contracts"],
                "authority": {
                    "read_roots": ["src", "tests", "pyproject.toml"],
                    "modify": writes,
                    "create": [],
                    "readonly": readonly,
                    "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
                },
                "max_units": 3,
                "atomic_contract_groups": [],
                "contract_edges": case["edges"],
                "integration_tests": [p for p in paths if p.startswith("tests/")],
                "source_hashes": sources,
                "validation_profile": "mixed-strict",
                "unknowns": [],
                "capability_route": {
                    "route": "direct_local",
                    "authority": "Primary",
                    "family": "Qualified bounded async/presence or type-error branch preservation",
                    "evidence": "qualification-matrix-6 and C1 four paired normal/branch units",
                    "not_permission_to_take_over": True,
                },
                "sequencing_requirement": "Collector independently accepted before receipt implementation; separate release units required"
                if case["edges"]
                else "One cohesive behavior, no artificial splitting",
            }
            catalog = {}
            for contract in case["contracts"]:
                selectors = case["selectors"][contract["id"]]
                scenarios = []
                for selector in selectors:
                    path, _, name = selector.partition("::")
                    source = (root / path).read_text()
                    for node in ast.parse(source).body:
                        if (
                            isinstance(node, ast.FunctionDef)
                            and node.name.startswith("test_")
                            and (not name or name == node.name)
                        ):
                            scenarios.append(
                                {
                                    "id": contract["id"]
                                    + "-"
                                    + node.name.replace("_", "-"),
                                    "text": ast.get_source_segment(source, node),
                                    "observables": {
                                        "protected_test": path + "::" + node.name,
                                        "expected": "Original assertions pass",
                                    },
                                }
                            )
                catalog[contract["id"]] = {
                    "acceptance_criteria": [
                        {"id": contract["id"], "text": contract["text"]}
                    ],
                    "acceptance_scenarios": scenarios,
                    "required_order": [],
                    "forbidden_orderings": [],
                    "validation_profile": "mixed-strict",
                    "required_focused_tests": selectors,
                }
            brief["acceptance_catalog"] = catalog
            module().validate_brief(brief)
            save(root / ".agent/brief.json", brief)
            save(
                root / ".agent/context.json", {p: (root / p).read_text() for p in paths}
            )
            save(
                root / ".agent/config.json",
                {**config, "coordinator_enabled": arm == "B"},
            )
            arms.append(
                {
                    "arm": arm,
                    "root": str(root),
                    "inputs": sources,
                    "brief": ref(root, ".agent/brief.json"),
                    "context": ref(root, ".agent/context.json"),
                    "config": ref(root, ".agent/config.json"),
                }
            )
        assert arms[0]["inputs"] == arms[1]["inputs"]
        features.append(
            {
                "id": case["id"],
                "origin": case["origin"],
                "arms": arms,
                "expected_units": case["expected_units"],
                "order": ["A", "B"] if index % 2 == 0 else ["B", "A"],
                "wall_ceiling_seconds": 5400,
                "reason": "Single-residency loading plus at most three bounded 900-second units and review; no timeout increase",
                "external_substantive_rework_max": 1,
                "oracle": case["reference"],
                "mutants": case["mutants"],
            }
        )
    save(
        BASE / "preparation.json",
        {
            "features": features,
            "once_only_infrastructure_cost": "Unknown, separate from both task arms",
            "common_fixture_and_tests_cost": "Primary authored/reviewed; shared both arms, tokens/active time unknown",
        },
    )


def entry(identity, arm="B"):
    feature = next(
        f
        for f in read_object(BASE / "preparation.json")["features"]
        if f["id"] == identity
    )
    return feature, next(a for a in feature["arms"] if a["arm"] == arm)


def verify_frozen():
    registration = read_object(BASE / "registration.json")
    for item in registration["runtime"]:
        if sha256(RUNTIME / item["path"]) != item["sha256"]:
            raise ValueError("runtime drift")
    if sha256(Path(__file__)) != registration["driver"]["sha256"]:
        raise ValueError("driver drift")
    if sha256(BASE / "preparation.json") != registration["preparation"]["sha256"]:
        raise ValueError("preparation drift")
    for feature in read_object(BASE / "preparation.json")["features"]:
        for cell in feature["arms"]:
            for key in ("brief", "context", "config"):
                item = cell[key]
                if sha256(Path(cell["root"]) / item["path"]) != item["sha256"]:
                    raise ValueError("frozen contract/context/config drift")
    return registration


def probe(identity):
    verify_frozen()
    _, cell = entry(identity)
    root = Path(cell["root"])
    brief = read_object(root / ".agent/brief.json")
    api = module()
    api.assert_sources_current(brief, root)
    worker, residency = (
        api.load("d2_worker", "worker-runtime.py"),
        api.load("d2_residency", "model_residency.py"),
    )
    config = read_object(root / ".agent/config.json")
    target = root / ".agent/proposal-result.json"
    if target.exists():
        raise FileExistsError("already attempted")
    client = worker.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        context_length=config["coordinator_context_length"],
        max_tokens=config["coordinator_max_tokens"],
        timeout=config["coordinator_request_timeout_seconds"],
        structured_output=False,
    )
    start = time.perf_counter()
    try:
        with residency.role_model_lease(client, config):
            result = api.probe(
                brief,
                read_object(root / ".agent/context.json"),
                client,
                reasoning_strength=config.get("coordinator_reasoning_strength"),
            )
    except (
        OSError,
        ValueError,
        worker.WorkerError,
        residency.ModelResidencyError,
    ) as exc:
        result = {
            "status": "infrastructure_or_request_failure",
            "reason": str(exc),
            "request_stats": client.last_request_stats,
            "dispatch_allowed": False,
        }
    save(
        target,
        {
            **result,
            "command_wall_seconds": time.perf_counter() - start,
            "cloud_tokens": None,
        },
    )
    api.assert_sources_current(brief, root)
    print(identity, result["status"], result.get("proposal"), flush=True)


def dispatch_guard(
    api, root, plan, initial_hashes, accepted_refs, unit_id, *, primary_authorized
):
    """Explicit Primary invocation; trusted canonical accepts account for legitimate writes."""
    if primary_authorized is not True:
        raise ValueError("explicit Primary step authorization required")
    accepted = api.CONTRACT.accepted_units_from_archives(plan, root, accepted_refs)
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    if unit_id in accepted or not set(unit["dependencies"]) <= accepted:
        raise ValueError("already accepted or dependencies not accepted")
    expected = dict(initial_hashes)
    for ref_ in accepted_refs.values():
        archive = root / ".agent/tasks" / ref_["task_id"] / "runs" / ref_["run_id"]
        handoff = read_object(archive / "handoff.json")
        # Reviewer/Primary archive acceptance alone does not prove current file bytes.
        for change in handoff["changed_files"]:
            expected[change["path"]] = change["final_sha256"]
    api.assert_sources_current({"source_hashes": expected}, root)
    return unit


def run(identity, unit_id):
    verify_frozen()
    _, cell = entry(identity)
    root = Path(cell["root"])
    api = module()
    brief = read_object(root / ".agent/brief.json")
    approved = read_object(root / ".agent/approval.json")
    transfer = read_object(root / ".agent/primary-execution-transfer.json")
    proposal = read_object(root / ".agent/proposal-result.json")["proposal"]
    plan = api.proposal_plan(brief, proposal)
    if (
        plan != approved["approved_plan"]
        or approved["approval_authority"] != "trusted_primary_api"
        or any(sha256(root / p) != h for p, h in transfer["authority_hashes"].items())
    ):
        raise ValueError("approved authority drift")
    refs = {
        p.stem: read_object(p) for p in (root / ".agent/accepted-refs").glob("*.json")
    }
    unit = dispatch_guard(
        api, root, plan, brief["source_hashes"], refs, unit_id, primary_authorized=True
    )
    run_id = brief["task_id"] + "-" + unit_id + "-a1"
    authorized = root / (".agent/" + unit_id + "-authorization.json")
    if authorized.exists():
        raise FileExistsError("duplicate dispatch")
    targets = []
    for path in unit["scope_authority"]["modify"]:
        source = (root / path).read_text()
        function = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        targets.append(
            {"path": path, "anchor": function.name, "line_hint": function.lineno}
        )
    packet = api.CONTRACT.materialize_bounded_packet(
        plan,
        {
            "unit_id": unit_id,
            "run_id": run_id,
            "attempt": 1,
            "packet_revision": 1,
            "goal": next(
                u["goal"]
                for u in proposal["units"]
                if u["contracts"] == unit["owned_contract_ids"]
            ),
            "scope": {
                "read": unit["scope_authority"]["read_roots"],
                "modify": unit["scope_authority"]["modify"],
                "create": unit["scope_authority"]["create"],
            },
            "edit_targets": targets,
            "focused_tests": unit["packet_contract"]["required_focused_tests"],
            "supplemental_tests": [],
            "implementation_guidance": [],
        },
    )
    save(root / (".agent/" + unit_id + "-packet.json"), packet)
    save(
        authorized,
        {
            "primary_authorized": True,
            "explicit_step": unit_id,
            "run_id": run_id,
            "approved_plan_sha256": api.digest(plan),
            "accepted_refs": refs,
            "current_input_hashes": {
                p: sha256(root / p) for p in brief["source_hashes"]
            },
            "no_unattended_loop": True,
            "primary_acceptance_not_inferred": True,
        },
    )
    command(
        root,
        [
            RUNTIME / "local-unit.py",
            "--packet",
            root / (".agent/" + unit_id + "-packet.json"),
            "--config",
            root / ".agent/config.json",
            "--coder-report",
            root / (".agent/" + unit_id + "-coder.json"),
            "--review-report",
            root / (".agent/" + unit_id + "-reviewer.json"),
        ],
        root / (".agent/" + unit_id + "-invocation.json"),
    )


def approve(identity, note):
    verify_frozen()
    feature, cell = entry(identity)
    root = Path(cell["root"])
    api = module()
    brief = read_object(root / ".agent/brief.json")
    proposal = read_object(root / ".agent/proposal-result.json")["proposal"]
    plan = api.proposal_plan(brief, proposal)
    if (
        not plan
        or len(plan["units"]) != feature["expected_units"]
        or any(u["owner"] != "local-coder" for u in plan["units"])
    ):
        raise ValueError(
            "Proposal does not satisfy registered local execution graph; Primary must adjudicate, not silently rewrite"
        )
    api.approve(
        brief, proposal, root, root / ".agent/approval.json", primary_review_note=note
    )
    plan = api.approved_plan(brief, proposal, root, root / ".agent/approval.json")
    save(
        root / ".agent/primary-execution-transfer.json",
        {
            "primary_review_note": note,
            "initial_source_current_checked": True,
            "authority_hashes": {
                p: sha256(root / p)
                for p in (
                    ".agent/brief.json",
                    ".agent/proposal-result.json",
                    ".agent/approval.json",
                )
            },
            "legitimate_writes_only_from_independently_accepted_canonical_runs": True,
            "explicit_separate_primary_step_required": True,
            "approved_plan_sha256": api.digest(plan),
        },
    )
    print(
        identity,
        [
            (u["unit_id"], u["owned_contract_ids"], u["dependencies"])
            for u in plan["units"]
        ],
    )


def preflight():
    for feature in read_object(BASE / "preparation.json")["features"]:
        cell = feature["arms"][0]
        source = Path(cell["root"])
        for name, changes in [
            ("reference", feature["oracle"]),
            *[("mutant-" + str(i), m) for i, m in enumerate(feature["mutants"])],
        ]:
            root = BASE / "controls" / feature["id"] / name
            shutil.copytree(source, root)
            for path, text in changes.items():
                (root / path).write_text(text, encoding="utf-8")
            subprocess.run(
                [str(PYTHON), "-B", "-m", "ruff", "format", "src", "tests"],
                cwd=root,
                env=ENV,
                check=True,
                capture_output=True,
            )
            code = command(
                root,
                [
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--junitxml",
                    root / ".agent/tests.xml",
                ],
                root / ".agent/invocation.json",
            )
            if (name == "reference") != (code == 0):
                raise ValueError("Acceptance discriminator failure")
    save(
        BASE / "preflight.json",
        {
            "all_reference_pass_and_mutants_fail": True,
            "denominator": 9,
            "model_calls": 0,
        },
    )


def register():
    import xml.etree.ElementTree as ET

    cases = list(ET.parse(BASE / "full-regression-2.xml").iter("testcase"))
    if any(c.find("failure") is not None or c.find("error") is not None for c in cases):
        raise ValueError("combined regression failure")
    skipped = [c.get("name") for c in cases if c.find("skipped") is not None]
    if skipped != ["test_symlink_path_is_rejected"]:
        raise ValueError("unexpected skips")
    assert read_object(BASE / "preflight.json")["all_reference_pass_and_mutants_fail"]
    save(
        BASE / "registration.json",
        {
            "stage": "D2",
            "candidate": "combined-typed-roles-approved-proposal-1",
            "driver": ref(KIT, "benchmarks/convergence_execution.py"),
            "preparation": ref(BASE, "preparation.json"),
            "runtime": [
                ref(RUNTIME, p.relative_to(RUNTIME).as_posix())
                for p in RUNTIME.rglob("*.py")
            ],
            "combined_full_regression": ref(BASE, "full-regression-2.xml"),
            "host_skip": skipped,
            "registered_feature_pairs": 3,
            "registered_chains": 6,
            "units_per_feature_max": 3,
            "quality_gate": "All three B features original validation, real independent Reviewer, explicit Primary accepts, accepted dependencies and integration, within one external substantive rework, no Primary implementation in B",
            "economic_gate": "Attributable cloud tokens reduce >=20% aggregate with two improved pairs and no extra Primary active work; unknown measurements remain UNMEASURED",
            "same_primary_learning_confound": True,
            "solutions_not_forwarded_between_arms": True,
            "weekly_used_start": 2,
            "weekly_used_ceiling": 15,
            "cloud_tokens": None,
            "primary_active_seconds": None,
            "global_coordinator_enabled": False,
            "production_promoted": False,
            "commit_push": False,
            "initial_test_environment_failure_retained": ref(
                BASE, "full-regression-1.xml"
            ),
            "explorer": {
                "feature": "async-receipt",
                "maximum_calls": 2,
                "question": "Which protected test exercises public run_receipt for retained falsy values, and which awaited caller path reaches collect_values? Cite actual read caller source and test assertions.",
            },
        },
    )


def regression():
    import sys
    import tempfile

    temp = BASE / "regression-temp-2"
    temp.mkdir(exist_ok=False)
    tempfile.tempdir = str(temp)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["R1_RUNTIME_ROOT"] = str(RUNTIME)
    os.chdir(TARGET)
    sys.path[:0] = [str(TARGET / "benchmarks"), str(TARGET)]
    import tool_reviewer_protocol_reference_trial as legacy_reference
    import tool_reviewer_test_consistency_trial as legacy_consistency

    legacy_reference.PYTHON = legacy_consistency.PYTHON = PYTHON
    import pytest

    raise SystemExit(
        pytest.main(
            [
                ".local-agents/tests",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(temp / "pytest"),
                "--junitxml=" + str(BASE / "full-regression-2.xml"),
            ]
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "preflight",
            "regression",
            "register",
            "probe",
            "approve",
            "run",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("unit", nargs="?")
    parser.add_argument("--note")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "preflight":
        preflight()
    elif args.action == "regression":
        regression()
    elif args.action == "register":
        register()
    elif args.action == "probe":
        probe(args.identity)
    elif args.action == "approve":
        approve(args.identity, args.note)
    else:
        run(args.identity, args.unit)
