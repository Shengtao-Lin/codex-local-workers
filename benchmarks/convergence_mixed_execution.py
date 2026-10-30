"""M1: frozen capability routing around existing trusted approvals and workers."""

import argparse
import copy
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import convergence_execution as core
import convergence_execution_results as results
from convergence_coder import KIT, save
from convergence_protocol_audit import preservation
from system_convergence import junit_counts, read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/mixed-execution-20261011-2"
OLD = KIT / "benchmarks/work/system-convergence/execution-20261011-2"
C3 = KIT / "benchmarks/work/system-convergence/c3-transport-20261011-1"
RUNTIME = C3 / "candidate-kit/.local-agents"
CLASSIFICATION = "src/evaluation_harness/telemetry/classification.py"


def route_plan(plan, catalog):
    """Primary's frozen catalog, not model-supplied family labels, grants eligibility."""
    expected = {c["id"] for c in plan["contracts"]}
    if not isinstance(catalog, dict) or set(catalog) != expected:
        raise ValueError("complete Primary capability catalog required")
    for unit in plan["units"]:
        entries = [catalog[c] for c in unit["owned_contract_ids"]]
        owners = {e["owner"] for e in entries}
        if owners != {unit["owner"]} or unit["owner"] not in {"primary", "local-coder"}:
            raise ValueError("capability owner mismatch or mixed-owner atomic unit")
        for entry in entries:
            if not entry.get("evidence") or entry.get("route") != (
                "direct_local" if unit["owner"] == "local-coder" else "primary_owned"
            ):
                raise ValueError("unqualified or unsupported capability route")
        scope = unit["scope_authority"]
        if (
            set(scope["modify"]) != {p for e in entries for p in e["modify"]}
            or scope["create"]
        ):
            raise ValueError("unit write scope does not match capability catalog")
    return plan


def accepted_state(api, root, plan, initial_hashes, refs):
    accepted = api.CONTRACT.accepted_units_from_archives(plan, root, refs)
    expected = dict(initial_hashes)
    units = {u["unit_id"]: u for u in plan["units"]}
    for unit_id, run_ref in refs.items():
        if units[unit_id]["owner"] == "primary":
            record = read_object(
                root
                / ".agent/primary-reviews"
                / plan["feature_id"]
                / (unit_id + ".json")
            )
            changes = record["post_source_hashes"]
            if set(changes) != set(record["changed_files"]) or not set(changes) <= set(
                units[unit_id]["scope_authority"]["modify"]
            ):
                raise ValueError("invalid Primary post-source attribution")
            if record.get("primary_authorized") is not True:
                raise ValueError("Primary record lacks explicit authority")
            prefix = ".agent/" + unit_id + "-primary"
            required_checks = [
                prefix + "-" + s + ".json" for s in ("tests", "lint", "format")
            ]
            if (
                record.get("check_records") != required_checks
                or record.get("junit") != prefix + ".xml"
            ):
                raise ValueError("Primary required checks omitted")
            if {i["path"] for i in record["evidence"]} != {
                *required_checks,
                prefix + ".xml",
            }:
                raise ValueError("Primary validation evidence incomplete")
            for item in record["evidence"]:
                path = root / item["path"]
                if (
                    not path.resolve().is_relative_to((root / ".agent").resolve())
                    or sha256(path) != item["sha256"]
                ):
                    raise ValueError("Primary evidence drift or escape")
            for name in record["check_records"]:
                if read_object(root / name)["exit"] != 0:
                    raise ValueError("Primary check did not pass")
            counts = junit_counts(root / record["junit"])
            if (
                not counts["executed"]
                or counts["failures"]
                or counts["errors"]
                or counts["skipped"]
            ):
                raise ValueError("Primary tests missing, failing or skipped")
            expected.update(changes)
        else:
            archive = (
                root / ".agent/tasks" / run_ref["task_id"] / "runs" / run_ref["run_id"]
            )
            handoff = read_object(archive / "handoff.json")
            expected.update(
                {c["path"]: c["final_sha256"] for c in handoff["changed_files"]}
            )
    api.assert_sources_current({"source_hashes": expected}, root)
    return accepted


def dispatch_guard(
    api, root, plan, initial_hashes, refs, unit_id, *, primary_authorized
):
    if primary_authorized is not True:
        raise ValueError("explicit Primary step required")
    catalog = read_object(root / ".agent/brief.json")["capability_catalog"]
    route_plan(plan, catalog)
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    if unit["owner"] != "local-coder":
        raise ValueError("Primary-owned unit cannot enter a local worker")
    accepted = accepted_state(api, root, plan, initial_hashes, refs)
    if unit_id in accepted or not set(unit["dependencies"]) <= accepted:
        raise ValueError("duplicate or unaccepted dependency")
    return unit


def bind():
    core.BASE, core.TARGET, core.RUNTIME = BASE, RUNTIME.parent, RUNTIME
    core.dispatch_guard = dispatch_guard
    results.fixture.bind = bind


def prepare():
    BASE.mkdir(parents=True, exist_ok=False)
    save(
        BASE / "authorization.json",
        {
            "user_authorized": True,
            "user_message": "批准建立新的受限混合执行门槛：Coordinator只向已合格任务族派工，classification交给Primary，旧D2失败记录不变。",
            "weekly_used_start": 4,
            "weekly_used_ceiling": 15,
            "production_promoted": False,
            "commit_push": False,
            "preservation": preservation(),
        },
    )
    prior = read_object(OLD / "preparation.json")["features"]
    by_id = {f["id"]: f for f in prior}
    cases = []
    for identity, members in (
        ("mixed-independent", ("async-first-present", "classification-shapes")),
        ("async-receipt", ("async-receipt",)),
    ):
        root = BASE / "features" / identity / "B"
        root.mkdir(parents=True)
        briefs, origins, oracle, mutants = [], [], {}, []
        for member in members:
            old_cell = next(c for c in by_id[member]["arms"] if c["arm"] == "B")
            old_root = Path(old_cell["root"])
            brief = read_object(old_root / ".agent/brief.json")
            briefs.append(brief)
            for path, digest in old_cell["inputs"].items():
                source = old_root / path
                if path in brief["authority"]["modify"]:
                    images = list(
                        (old_root / ".agent/tasks" / brief["task_id"] / "runs").glob(
                            "*/preimages.json"
                        )
                    )
                    found = []
                    for image in images:
                        for item in json.loads(image.read_text()):
                            if (
                                item["path"] == path
                                and sha256(old_root / item["archive_path"]) == digest
                            ):
                                found.append(old_root / item["archive_path"])
                    if not found:
                        raise ValueError("missing original preimage")
                    source = found[0]
                if sha256(source) != digest:
                    raise ValueError("origin changed")
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and sha256(target) != digest:
                    raise ValueError("fixture collision")
                shutil.copyfile(source, target)
            origins.append(
                {
                    "member": member,
                    "inputs": old_cell["inputs"],
                    "brief": ref(old_root, ".agent/brief.json"),
                }
            )
            oracle.update(by_id[member]["oracle"])
            mutants.extend(by_id[member]["mutants"])
        # New fixture version adds the pre-registered C4 counterexample; old tests remain unchanged.
        if identity == "mixed-independent":
            path = root / "tests/test_classification_shapes.py"
            path.write_text(
                path.read_text()
                + '\n\ndef test_attribute_service_name_fallback():\n    classify = runpy.run_path("src/evaluation_harness/telemetry/classification.py")["is_internal_trace"]\n    for service in ("evaluation-api", "evaluation-worker"):\n        raw = {"attributes": {"service.name": service}}\n        assert classify(raw) is True\n        assert raw == {"attributes": {"service.name": service}}\n    assert classify({"attributes": {"service.name": "custom"}}, service_names={"custom"}) is True\n    assert classify({"resource": {}, "attributes": {"service.name": "evaluation-api"}}) is True\n',
                encoding="utf-8",
            )
            mutants.append(
                {
                    CLASSIFICATION: oracle[CLASSIFICATION].replace(
                        'resource.get("service.name") or attributes.get("service.name")',
                        'resource.get("service.name")',
                    )
                }
            )
        assert (
            core.command(
                root,
                ["-m", "ruff", "format", "src", "tests"],
                root / ".agent/preparation-format.json",
            )
            == 0
        )
        paths = [
            p.relative_to(root).as_posix()
            for folder in ("src", "tests")
            for p in (root / folder).rglob("*.py")
        ] + ["pyproject.toml"]
        writes = [p for b in briefs for p in b["authority"]["modify"]]
        brief = copy.deepcopy(briefs[0])
        brief.update(
            feature_id="m1-" + identity,
            task_id="m1-" + identity,
            goal="Implement both independent outcomes without coupling them: "
            + " | ".join(b["goal"] for b in briefs)
            if len(briefs) == 2
            else brief["goal"],
            contracts=[c for b in briefs for c in b["contracts"]],
            source_hashes={p: sha256(root / p) for p in paths},
            integration_tests=[p for p in paths if p.startswith("tests/")],
            contract_edges=[e for b in briefs for e in b["contract_edges"]],
            capability_route={
                "authority": "Primary",
                "route": "catalog_only",
                "unknown_family": "reject local dispatch; Primary decision required",
            },
        )
        brief["authority"]["modify"] = writes
        brief["authority"]["readonly"] = [p for p in paths if p not in writes]
        brief["acceptance_catalog"] = {
            k: v for b in briefs for k, v in b["acceptance_catalog"].items()
        }
        catalog = {}
        for b in briefs:
            for c in b["contracts"]:
                primary = c["id"] == "classification-shapes"
                modify = (
                    [CLASSIFICATION]
                    if primary
                    else (
                        ["src/product/collector.py"]
                        if c["id"] == "collect-unit"
                        else ["src/product/target.py"]
                    )
                )
                catalog[c["id"]] = {
                    "owner": "primary" if primary else "local-coder",
                    "route": "primary_owned" if primary else "direct_local",
                    "modify": modify,
                    "evidence": str(
                        KIT
                        / (
                            "benchmarks/work/system-convergence/c4-assisted-20261011-1/stage-decision-1.json"
                            if primary
                            else "benchmarks/work/system-convergence/execution-20261011-2/stage-decision-1.json"
                        )
                    ),
                    "qualification": "Named exposed task/contract only; not general branch or asynchronous algorithm ability",
                }
        brief["capability_catalog"] = catalog
        core.module().validate_brief(brief)
        config = read_object(C3 / "cells/normal-candidate/.agent/config.json")
        config["coordinator_enabled"] = True
        save(root / ".agent/brief.json", brief)
        save(root / ".agent/context.json", {p: (root / p).read_text() for p in paths})
        save(root / ".agent/config.json", config)
        cases.append(
            {
                "id": identity,
                "arms": [
                    {
                        "arm": "B",
                        "root": str(root),
                        "inputs": brief["source_hashes"],
                        **{
                            k: ref(root, ".agent/" + k + ".json")
                            for k in ("brief", "context", "config")
                        },
                    }
                ],
                "expected_units": 2,
                "origin": origins,
                "oracle": oracle,
                "mutants": mutants,
                "external_substantive_rework_max": 1,
                "wall_ceiling_seconds": 5400,
            }
        )
    save(
        BASE / "preparation.json",
        {
            "features": cases,
            "common_tests_cost": "UNMEASURED",
            "infrastructure_cost": "UNMEASURED",
        },
    )


def preflight():
    for feature in read_object(BASE / "preparation.json")["features"]:
        source = Path(feature["arms"][0]["root"])
        for name, changes in [
            ("reference", {}),
            *[("mutant-" + str(i), m) for i, m in enumerate(feature["mutants"])],
        ]:
            root = BASE / "controls-authorized" / feature["id"] / name
            shutil.copytree(source, root)
            for path, text in {**feature["oracle"], **changes}.items():
                (root / path).write_text(text, encoding="utf-8")
            assert (
                core.command(
                    root,
                    ["-m", "ruff", "format", "src", "tests"],
                    root / ".agent/control-format.json",
                )
                == 0
            )
            code = core.command(
                root,
                [
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--junitxml=" + str(root / ".agent/control.xml"),
                ],
                root / ".agent/control-tests.json",
            )
            if (name == "reference") != (code == 0):
                raise ValueError("acceptance discriminator failed")
    save(
        BASE / "preflight.json",
        {
            "reference_pass_mutants_fail": True,
            "model_calls": 0,
            "historical_tests_unmodified": True,
        },
    )


def register():
    assert read_object(BASE / "preflight.json")["reference_pass_mutants_fail"]
    for f in read_object(BASE / "preparation.json")["features"]:
        root = Path(f["arms"][0]["root"])
        core.module().assert_sources_current(
            read_object(root / ".agent/brief.json"), root
        )
        for name, argv in (
            ("initial-lint", ["-m", "ruff", "check", "src", "tests"]),
            ("initial-format", ["-m", "ruff", "format", "--check", "src", "tests"]),
        ):
            output = root / (".agent/" + name + ".json")
            assert (
                read_object(output)["exit"]
                if output.exists()
                else core.command(root, argv, output)
            ) == 0
    controls = junit_counts(BASE / "guard-controls-freeze.xml")
    assert controls["executed"] and not (
        controls["failures"] or controls["errors"] or controls["skipped"]
    )
    full = list(ET.parse(BASE / "combined-regression-3.xml").iter("testcase"))
    assert full and all(
        c.find("failure") is None and c.find("error") is None for c in full
    )
    assert [c.get("name") for c in full if c.find("skipped") is not None] == [
        "test_symlink_path_is_rejected"
    ]
    save(
        BASE / "registration.json",
        {
            "stage": "M1",
            "candidate": "primary-catalog-mixed-owners-1",
            "driver": ref(KIT, "benchmarks/convergence_execution.py"),
            "wrapper": ref(KIT, "benchmarks/convergence_mixed_execution.py"),
            "adapter_tests": ref(KIT, "tests/test_convergence_mixed_execution.py"),
            "preparation": ref(BASE, "preparation.json"),
            "runtime": read_object(C3 / "registration.json")["runtime"]["candidate"],
            "reused_full_regression": ref(C3, "full-regression-2.xml"),
            "guard_controls": ref(BASE, "guard-controls-freeze.xml"),
            "current_full_regression": ref(BASE, "combined-regression-3.xml"),
            "initial_joint_collection_failure_retained": ref(
                BASE, "combined-regression.xml"
            ),
            "preflight": ref(BASE, "preflight.json"),
            "prior_preparation_failure": ref(
                BASE.parent / "mixed-execution-20261011-1", "preparation-failure-1.json"
            ),
            "experiment_integration_risk": "high: routing and acceptance evidence; business unit floors unchanged",
            "unchanged_runtime_no_new_regression_claim": True,
            "catalog_scope": "Only these exact exposed contracts and paths; unknown family fails closed",
            "registered_features": 2,
            "registered_units": {"local-coder": 3, "primary": 1},
            "maximum_calls": {
                "coordinator": 2,
                "explorer": 1,
                "coder": 5,
                "reviewer": 5,
            },
            "quality_gate": "Both original outcomes plus new protected fallback test pass. Two fresh proposals match catalog without owner rewriting. Three actual local units pass current tests/static checks, fresh Reviewer and independent Primary acceptance; one explicit Primary unit passes full independent protected checks. Dependencies and feature integration pass. No local edits to classification or protected tests.",
            "interventions": "One inherited rework maximum per feature; no local feature takeover credited as pass. Primary classification implementation is planned ownership, not local success or fallback.",
            "stop": "Safety/authority failure immediately; two consecutive identical no-progress semantic failures; weekly used 15; or a fixed stage decision. No resampling or changed candidate after live.",
            "explorer": "One focused caller/test question for async-receipt, independently adjudicated; no repeated identical investigation",
            "single_model_residency": True,
            "weekly_used_start": 4,
            "weekly_used_ceiling": 15,
            "old_D2": ref(OLD, "stage-decision-1.json"),
            "old_D2_status": "HOLD 2/3 unchanged",
            "qualification_sources": [
                ref(KIT, p.relative_to(KIT).as_posix())
                for p in (
                    C3 / "stage-decision-1.json",
                    BASE.parent / "c4-assisted-20261011-1/stage-decision-1.json",
                    BASE.parent
                    / "assessment-20261011-1/reviewer/stage-decision-1.json",
                    BASE.parent / "protocol-20261011-1/explorer/stage-decision-1.json",
                )
            ],
            "product_boundary_user_approved": True,
            "I1_general": "NOT_RELEASED",
            "economics": "UNMEASURED; not a new paired cost benchmark",
            "production_promoted": False,
            "global_coordinator_enabled_changed": False,
            "commit_push": False,
        },
    )


def frozen():
    bind()
    record = core.verify_frozen()
    for key in ("wrapper", "adapter_tests", "old_D2"):
        item = record[key]
        origin = OLD if key == "old_D2" else KIT
        if sha256(origin / item["path"]) != item["sha256"]:
            raise ValueError("frozen authority or adapter drift")
    for item in record["qualification_sources"]:
        if sha256(KIT / item["path"]) != item["sha256"]:
            raise ValueError("qualification evidence drift")
    for key, origin in (
        ("guard_controls", BASE),
        ("preflight", BASE),
        ("current_full_regression", BASE),
        ("reused_full_regression", C3),
    ):
        item = record[key]
        if sha256(origin / item["path"]) != item["sha256"]:
            raise ValueError("frozen verification evidence drift")
    return record


def approve(identity, note):
    frozen()
    feature, cell = core.entry(identity)
    root = Path(cell["root"])
    api = core.module()
    brief = read_object(root / ".agent/brief.json")
    proposal = read_object(root / ".agent/proposal-result.json")["proposal"]
    plan = api.proposal_plan(brief, proposal)
    if plan is None or len(plan["units"]) != feature["expected_units"]:
        raise ValueError("unresolved or wrong decomposition")
    route_plan(plan, brief["capability_catalog"])
    api.approve(
        brief, proposal, root, root / ".agent/approval.json", primary_review_note=note
    )
    api.approved_plan(brief, proposal, root, root / ".agent/approval.json")
    save(
        root / ".agent/primary-execution-transfer.json",
        {
            "primary_review_note": note,
            "approved_plan_sha256": api.digest(plan),
            "authority_hashes": {
                p: sha256(root / p)
                for p in (
                    ".agent/brief.json",
                    ".agent/proposal-result.json",
                    ".agent/approval.json",
                )
            },
            "explicit_separate_primary_step_required": True,
            "capability_routes_checked": True,
        },
    )
    print(
        [
            (u["unit_id"], u["owner"], u["owned_contract_ids"], u["dependencies"])
            for u in plan["units"]
        ]
    )


def explore():
    frozen()
    _, cell = core.entry("async-receipt")
    root = Path(cell["root"])
    brief = read_object(root / ".agent/brief.json")
    core.module().assert_sources_current(brief, root)
    core.command(
        root,
        [
            RUNTIME / "local-explore.py",
            "--task-id",
            brief["task_id"],
            "--task",
            "Which protected test exercises public run_receipt for retained falsy values, and which awaited caller path reaches collect_values? Cite actual read caller source and test assertions.",
            "--config",
            root / ".agent/config.json",
            "--report",
            root / ".agent/explorer.json",
            "--full-report",
        ],
        root / ".agent/explorer-invocation.json",
    )


def primary_begin(identity, unit_id, note):
    frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    api = core.module()
    brief = read_object(root / ".agent/brief.json")
    proposal = read_object(root / ".agent/proposal-result.json")["proposal"]
    plan = api.approved_plan(brief, proposal, root, root / ".agent/approval.json")
    route_plan(plan, brief["capability_catalog"])
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    if unit["owner"] != "primary" or unit["dependencies"]:
        raise ValueError("only registered independent Primary unit here")
    save(
        root / (".agent/" + unit_id + "-primary-authorization.json"),
        {
            "primary_authorized": True,
            "unit_id": unit_id,
            "primary_plan_sha256": api.CONTRACT.authority_fingerprint(plan),
            "pre_source_hashes": brief["source_hashes"],
            "note": note,
            "planned_primary_implementation_not_worker_credit": True,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )


def primary_accept(identity, unit_id, note):
    frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    api = core.module()
    brief = read_object(root / ".agent/brief.json")
    plan = read_object(root / ".agent/approval.json")["approved_plan"]
    route_plan(plan, brief["capability_catalog"])
    authorization = read_object(
        root / (".agent/" + unit_id + "-primary-authorization.json")
    )
    if (
        authorization["primary_plan_sha256"] != api.CONTRACT.authority_fingerprint(plan)
        or authorization["primary_authorized"] is not True
    ):
        raise ValueError("stale Primary authorization")
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    if unit["owner"] != "primary":
        raise ValueError("not Primary owned")
    writes = unit["scope_authority"]["modify"]
    api.assert_sources_current(
        {
            "source_hashes": {
                p: h for p, h in brief["source_hashes"].items() if p not in writes
            }
        },
        root,
    )
    prefix = ".agent/" + unit_id + "-primary"
    validation_inputs = {p: sha256(root / p) for p in brief["source_hashes"]}
    records = []
    for suffix, argv in (
        (
            "tests",
            [
                "-m",
                "pytest",
                "tests/test_classification_shapes.py",
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=" + str(root / (prefix + ".xml")),
            ],
        ),
        ("lint", ["-m", "ruff", "check", "src", "tests"]),
        ("format", ["-m", "ruff", "format", "--check", "src", "tests"]),
    ):
        path = prefix + "-" + suffix + ".json"
        assert core.command(root, argv, root / path) == 0
        records.append(path)
    counts = junit_counts(root / (prefix + ".xml"))
    assert counts["executed"] == 4 and not (
        counts["failures"] or counts["errors"] or counts["skipped"]
    )
    api.assert_sources_current({"source_hashes": validation_inputs}, root)
    api.assert_sources_current(
        {
            "source_hashes": {
                p: h for p, h in brief["source_hashes"].items() if p not in writes
            }
        },
        root,
    )
    save(
        root / ".agent/primary-reviews" / plan["feature_id"] / (unit_id + ".json"),
        {
            "schema_version": 1,
            "feature_id": plan["feature_id"],
            "unit_id": unit_id,
            "plan_revision": plan["plan_revision"],
            "primary_plan_sha256": api.CONTRACT.authority_fingerprint(plan),
            "primary_authorized": True,
            "decision": "accept",
            "summary": note,
            "changed_files": writes,
            "post_source_hashes": {p: sha256(root / p) for p in writes},
            "evidence": [ref(root, p) for p in [*records, prefix + ".xml"]],
            "check_records": records,
            "junit": prefix + ".xml",
            "local_worker_credit": False,
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    refs = {**results.accepted_refs(root), unit_id: {}}
    accepted_state(api, root, plan, brief["source_hashes"], refs)
    save(root / ".agent/accepted-refs" / (unit_id + ".json"), {})


def finish(identity, note):
    frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    plan = read_object(root / ".agent/approval.json")["approved_plan"]
    brief = read_object(root / ".agent/brief.json")
    accepted = accepted_state(
        core.module(), root, plan, brief["source_hashes"], results.accepted_refs(root)
    )
    if accepted != {u["unit_id"] for u in plan["units"]}:
        raise ValueError("all owners must be explicitly accepted")
    results.integration(identity)
    counts = junit_counts(root / ".agent/integration.xml")
    if (
        not counts["executed"]
        or counts["failures"]
        or counts["errors"]
        or counts["skipped"]
    ):
        raise ValueError("integration not complete")
    accepted_state(
        core.module(), root, plan, brief["source_hashes"], results.accepted_refs(root)
    )
    save(
        root / ".agent/primary-feature-decision.json",
        {
            "decision": "accept",
            "summary": note,
            "integration": counts,
            "local_units": sum(u["owner"] == "local-coder" for u in plan["units"]),
            "primary_units": sum(u["owner"] == "primary" for u in plan["units"]),
            "all_units_accepted": sorted(accepted),
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )


def rework_prepare(identity, unit_id, note):
    frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    marker = root / ".agent/external-rework-1.json"
    if marker.exists():
        raise FileExistsError("registered external feature recovery exhausted")
    parent = read_object(root / (".agent/" + unit_id + "-packet.json"))
    coder = read_object(root / (".agent/" + unit_id + "-coder.json"))
    plan = read_object(root / ".agent/approval.json")["approved_plan"]
    brief = read_object(root / ".agent/brief.json")
    route_plan(plan, brief["capability_catalog"])
    unit = next(u for u in plan["units"] if u["unit_id"] == unit_id)
    if unit["owner"] != "local-coder" or coder["status"] != "failed":
        raise ValueError("only diagnosed failed local call may use this recovery entry")
    expected = dict(cell["inputs"])
    for change in coder["changed_files"]:
        if change["path"] not in parent["scope"]["modify"]:
            raise ValueError("scope failure requires immediate HOLD")
        expected[change["path"]] = change["final_sha256"]
    accepted = accepted_state(
        core.module(), root, plan, expected, results.accepted_refs(root)
    )
    if not set(unit["dependencies"]) <= accepted or unit_id in accepted:
        raise ValueError("unaccepted dependency or duplicate")
    assert (
        core.command(
            root,
            [
                RUNTIME / "record-review.py",
                "--task-id",
                parent["task_id"],
                "--run-id",
                parent["run_id"],
                "--decision",
                "rework",
                "--summary",
                note,
                "--repo",
                root,
            ],
            root / (".agent/" + unit_id + "-failed-primary-record.json"),
        )
        == 0
    )
    child = {
        k: parent[k] for k in ("schema_version", "task_id", "unit_id", "plan_revision")
    }
    child.update(
        run_id=parent["run_id"].removesuffix("a1") + "a2",
        attempt=2,
        packet_revision=2,
        parent_run_id=parent["run_id"],
        preserve_contract=True,
        review_feedback=[note],
    )
    path = root / (".agent/" + unit_id + "-rework-packet.json")
    save(path, child)
    worker = core.module().load("m1_inherited_shape", "worker-runtime.py")
    resolved = worker.resolve_inherited_packet(root, child)
    core.module().CONTRACT.validate_unit_packet(plan, resolved)
    save(
        marker,
        {
            "unit_id": unit_id,
            "parent_run_id": parent["run_id"],
            "run_id": child["run_id"],
            "packet_sha256": sha256(path),
            "current_inputs": {p: sha256(root / p) for p in expected},
            "primary_feedback": note,
            "count": 1,
            "scope_contract_and_budgets_unchanged": True,
        },
    )


def rework_run(identity):
    frozen()
    _, cell = core.entry(identity)
    root = Path(cell["root"])
    marker = read_object(root / ".agent/external-rework-1.json")
    unit_id = marker["unit_id"]
    packet = root / (".agent/" + unit_id + "-rework-packet.json")
    if sha256(packet) != marker["packet_sha256"]:
        raise ValueError("recovery packet changed")
    core.module().assert_sources_current(
        {"source_hashes": marker["current_inputs"]}, root
    )
    core.command(
        root,
        [
            RUNTIME / "local-unit.py",
            "--packet",
            packet,
            "--config",
            root / ".agent/config.json",
            "--coder-report",
            root / (".agent/" + unit_id + "-rework-coder.json"),
            "--review-report",
            root / (".agent/" + unit_id + "-rework-reviewer.json"),
        ],
        root / (".agent/" + unit_id + "-rework-invocation.json"),
    )


def collect(latest_used):
    record = frozen()
    rows, coder_calls, reviewer_calls, proposals = [], [], [], []
    for feature in read_object(BASE / "preparation.json")["features"]:
        cell = feature["arms"][0]
        root = Path(cell["root"])
        brief = read_object(root / ".agent/brief.json")
        core.module().assert_sources_current(
            {
                "source_hashes": {
                    p: h
                    for p, h in cell["inputs"].items()
                    if p not in brief["authority"]["modify"]
                }
            },
            root,
        )
        proposal_path = root / ".agent/proposal-result.json"
        if proposal_path.exists():
            value = read_object(proposal_path)
            proposals.append(
                {
                    "feature": feature["id"],
                    "status": value["status"],
                    "attempts": len(value.get("attempts", [])),
                    "dispatch_allowed": value["dispatch_allowed"],
                    "command_wall_seconds": value.get("command_wall_seconds"),
                }
            )
        for archive in (root / ".agent/tasks" / brief["task_id"] / "runs").glob("*"):
            if not (archive / "handoff.json").exists():
                continue
            handoff = read_object(archive / "handoff.json")
            review_path = archive / "review.json"
            coder_calls.append(
                {
                    "feature": feature["id"],
                    "identity": handoff["identity"],
                    "status": handoff["status"],
                    "failure": handoff.get("failure_reason"),
                    "current_validation": handoff.get("validation"),
                    "protocol_errors": handoff.get("protocol_error_count"),
                    "primary": read_object(review_path)["decision"]
                    if review_path.exists()
                    else "not_recorded",
                    "handoff": ref(
                        root, archive.relative_to(root).as_posix() + "/handoff.json"
                    ),
                }
            )
        for archive in (root / ".agent/tasks" / brief["task_id"] / "reviews").glob("*"):
            report_path = archive / "handoff.json"
            if report_path.exists():
                report = read_object(report_path)
                reviewer_calls.append(
                    {
                        "feature": feature["id"],
                        "identity": report["identity"],
                        "decision": report["decision"],
                        "protocol_errors": report.get("runtime_facts", {}).get(
                            "protocol_error_count"
                        ),
                        "report": ref(root, report_path.relative_to(root).as_posix()),
                    }
                )
        decision_path = root / ".agent/primary-feature-decision.json"
        decision = (
            read_object(decision_path)
            if decision_path.exists()
            else {"decision": "not_completed"}
        )
        if decision["decision"] == "accept":
            plan = read_object(root / ".agent/approval.json")["approved_plan"]
            route_plan(plan, brief["capability_catalog"])
            accepted_state(
                core.module(),
                root,
                plan,
                brief["source_hashes"],
                results.accepted_refs(root),
            )
            for path in ("integration.json", "ruff-check.json", "ruff-format.json"):
                if read_object(root / ".agent" / path)["exit"] != 0:
                    raise ValueError("accepted feature validation failed")
        rows.append(
            {
                "feature": feature["id"],
                "decision": decision,
                "external_rework": (root / ".agent/external-rework-1.json").exists(),
                "protected_inputs_unchanged": True,
            }
        )
    explorer_path = BASE / "explorer-adjudication.json"
    explorer_ok = (
        explorer_path.exists()
        and read_object(explorer_path).get("question_complete_and_truthful") is True
    )
    passed = all(r["decision"]["decision"] == "accept" for r in rows) and explorer_ok
    if passed and (
        len(proposals) != 2
        or any(
            p["status"] != "proposal_valid" or p["dispatch_allowed"] is not False
            for p in proposals
        )
    ):
        raise ValueError("fresh proposal denominator or authority changed")
    local_accepts = sum(r["decision"].get("local_units", 0) for r in rows)
    primary_accepts = sum(r["decision"].get("primary_units", 0) for r in rows)
    if passed and (local_accepts != 3 or primary_accepts != 1):
        raise ValueError("registered owner denominator changed")
    save(
        BASE / "stage-decision-1.json",
        {
            "stage": "M1",
            "decision": "LIMITED_MIXED_EXECUTION_QUALITY_PASS"
            if passed
            else "INCOMPLETE_BUDGET"
            if latest_used >= 15
            else "HOLD_MIXED_EXECUTION",
            "registered_features": 2,
            "accepted_features": sum(
                r["decision"]["decision"] == "accept" for r in rows
            ),
            "features": rows,
            "local_accepted_units": local_accepts,
            "planned_primary_accepted_units": primary_accepts,
            "coder_calls": coder_calls,
            "reviewer_calls": reviewer_calls,
            "coordinator_calls": proposals,
            "explorer": ref(BASE, "explorer-adjudication.json")
            if (BASE / "explorer-adjudication.json").exists()
            else "not_completed",
            "registration": ref(BASE, "registration.json"),
            "old_D2": record["old_D2"],
            "old_D2_status": "HOLD 2/3 unchanged",
            "I1_general": "NOT_RELEASED",
            "economics": "UNMEASURED; planned Primary implementation explicitly charged to mixed workflow, not local success",
            "weekly_used_start": 4,
            "weekly_used_end": latest_used,
            "weekly_used_ceiling": 15,
            "preservation": preservation(),
            "production_promoted": False,
            "commit_push": False,
            "next": "If M1 passes, separately register limited-scope integration/delivery checks; no automatic global enable or v2.1 release",
        },
    )
    print(
        "M1",
        "PASS" if passed else "HOLD",
        local_accepts,
        "local accepts",
        primary_accepts,
        "planned Primary accept",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "prepare",
            "preflight",
            "register",
            "probe",
            "explore",
            "approve",
            "run",
            "accept",
            "integration",
            "primary-begin",
            "primary-accept",
            "rework-prepare",
            "rework-run",
            "finish",
            "collect",
        ),
    )
    parser.add_argument("identity", nargs="?")
    parser.add_argument("unit", nargs="?")
    parser.add_argument("--note")
    parser.add_argument("--latest-used", type=int)
    args = parser.parse_args()
    bind()
    if args.action in {"prepare", "preflight", "register"}:
        globals()[args.action]()
    else:
        frozen()
        if args.action == "probe":
            core.probe(args.identity)
        elif args.action == "explore":
            explore()
        elif args.action == "approve":
            approve(args.identity, args.note)
        elif args.action == "run":
            core.run(args.identity, args.unit)
        elif args.action == "accept":
            results.accept(args.identity, args.unit, args.note)
        elif args.action == "integration":
            results.integration(args.identity)
        elif args.action == "primary-begin":
            primary_begin(args.identity, args.unit, args.note)
        elif args.action == "finish":
            finish(args.identity, args.note)
        elif args.action == "collect":
            collect(args.latest_used)
        elif args.action == "rework-prepare":
            rework_prepare(args.identity, args.unit, args.note)
        elif args.action == "rework-run":
            rework_run(args.identity)
        else:
            primary_accept(args.identity, args.unit, args.note)
