"""Explicit Coordinator snapshot chain on two evidenced package functions.

Reuse the tested bridge/runner. Its internal encode/append aliases mean
sample-identity producer / request-digest consumer here, not URL operations.
"""

import argparse
import time
from pathlib import Path

import bounded_dependency_close as CLOSE
import bounded_dependency_smoke as D
import project_caller_tasks as TASKS
import project_caller_trial as PROJECT
import stable_execution_tasks as KNOWN

S, T = D.S, D.T
BATCH = D.I.BASE / "project-identity-chain-20261022-1"
PRODUCER = "src/evaluation_harness/canonical/fingerprint.py"
CONSUMER = "src/evaluation_harness/jobs/queue.py"
ORIGINAL_REFRESH, ORIGINAL_COMMAND = D.I.refresh_material, D.I.command

ROUNDTRIP = """
from evaluation_harness.canonical.fingerprint import make_sample_id

def identity_payload(revision, trace_id, request_id):
    sample_id = make_sample_id(application_id="app", environment="qa", source_trace_id=trace_id,
        source_revision=revision, row_mode="turn", turn_index=0, adapter_name="adapter", adapter_version="1")
    return {"sample_id": sample_id, "request_id": request_id, "traceparent": "transport-only"}

def test_producer_identity_and_consumer_digest_roundtrip():
    a = identity_payload("", "trace", "old")
    b = identity_payload(None, "trace", "new")
    assert a["sample_id"] == b["sample_id"]
    assert request_hash(a) == request_hash(b)
    assert request_hash(a) != request_hash(identity_payload("v2", "trace", "old"))
    assert request_hash(a) != request_hash(identity_payload("", "other-trace", "old"))
    assert request_hash(a) != request_hash(identity_payload(" ", "trace", "old"))
    assert a["request_id"] == "old" and b["request_id"] == "new"
"""


def specs():
    producer = KNOWN.tasks(T.extract)["hash"]
    consumer = TASKS.tasks()["hash"]
    canonical = PROJECT.function_source(TASKS.SNAPSHOT / PRODUCER, "canonical_json")
    return {
        "encode": {
            "path": PRODUCER,
            "module": "evaluation_harness.canonical.fingerprint",
            "symbol": "make_sample_id",
            "contract": producer["contract"],
            "header": canonical,
            "cases": producer["cases"],
            "reference": producer["reference"],
            "public": producer["public"].replace(
                "from product.code", "from evaluation_harness.canonical.fingerprint"
            ),
            "private": producer["private"]
            .replace(
                "from product.code", "from evaluation_harness.canonical.fingerprint"
            )
            .replace(
                "from product.dependencies",
                "from evaluation_harness.canonical.fingerprint",
            ),
            "qualification": "project-live-20261022-2/decision.json: exact source_revision-empty normalization 2/2 complete package accepts, 151 tests each",
        },
        "append": {
            "path": CONSUMER,
            "module": "evaluation_harness.jobs.queue",
            "symbol": "request_hash",
            "contract": consumer["contract"],
            "header": canonical,
            "cases": consumer["cases"],
            "reference": consumer["reference"],
            "public": TASKS.join_test_sources(consumer["public"], ROUNDTRIP),
            "private": consumer["private"],
            "qualification": "project-callers-20261022-2: hash-1 and hash-2 accepted, each165 complete package tests; clarified items() contract, zero-ID failure excluded",
        },
    }


def refresh(root, config):
    import shutil

    for folder in ("examples", "scripts"):
        if not (root / folder).exists():
            shutil.copytree(BATCH / "template" / folder, root / folder)
    ORIGINAL_REFRESH(root, config)
    config.update(
        bounded_compatibility_profile="flat-v1", model_load_ack_policy="api_verified"
    )
    for check in config["validation_profiles"]["real-trace-strict"]["commands"]:
        if check["id"] in {"ruff-format", "ruff-check"}:
            check["argv"].extend(["examples", "scripts"])


def command(root, mode="unit", replay=None):
    result = ORIGINAL_COMMAND(root, mode=mode, replay=replay)
    if mode == "unit":
        result.append("--compact-output")
    return result


def run_check(argv, root, timeout=120):
    args = [str(a) for a in argv]
    if "pytest" in args and "tests/test_encode.py" in args:
        args[args.index("tests/test_encode.py")] = "tests"
        args.extend(["--ignore=tests/test_append.py"])
    return PROJECT.run_check(args, root, timeout)


def fresh(used, observed):
    assert 0 <= used <= 100 and 0 <= time.time() - observed <= 120
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == sha for p, sha in reg["pins"].items()), "candidate drift"
    clock = BATCH / "start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time(), "weekly_used": used})
    assert time.time() - S.read(clock)["epoch"] < 7200


def prepare(used):
    assert not BATCH.exists()
    assert S.read(D.I.BASE / "project-live-20261022-2/decision.json")["accepted"] == 2
    prior = S.read(D.I.BASE / "project-callers-20261022-2/metrics.json")
    assert all(prior["cells"][f"hash-{i}"]["accepted"] for i in (1, 2))
    S.save(
        BATCH / "preparation.json",
        {
            "authority": "Current autonomous isolated experimentation; no weekly cap",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "goal": "Use real Coordinator decomposition then two qualified installed units and exact snapshot transfer, not automatic acceptance",
            "qualified_contracts": {k: v["qualification"] for k, v in D.SPECS.items()},
            "excluded": "Failed integer-zero stable_message_id task; no broader source-family inference",
        },
    )
    root = BATCH / "template"
    PROJECT.copy_project(TASKS.SNAPSHOT, root)
    for topic, spec in D.SPECS.items():
        T.write(root / ("tests/test_" + topic + ".py"), spec["public"])
        T.write(BATCH / ("private/test_private_" + topic + ".py"), spec["private"])
    for sub in (("check", "--select", "I", "--fix"), ("format",)):
        result = T.run(
            [
                S.PYTHON,
                "-B",
                "-m",
                "ruff",
                *sub,
                "tests/test_encode.py",
                "tests/test_append.py",
            ],
            root,
        )
        assert result["exit_code"] == 0, result
    proof = BATCH / "reference"
    PROJECT.copy_project(root, proof)
    for spec in D.SPECS.values():
        target = proof / spec["path"]
        source = target.read_text("utf-8")
        old = PROJECT.function_source(target, spec["symbol"])
        assert source.count(old) == 1
        target.write_text(source.replace(old, spec["reference"], 1), encoding="utf-8")
    assert (
        T.run([S.PYTHON, "-B", "-m", "ruff", "format", PRODUCER, CONSUMER], proof)[
            "exit_code"
        ]
        == 0
    )
    controls = {
        "reference": D.L.checks(proof, BATCH / "private"),
        "baseline": D.L.checks(root, BATCH / "private"),
    }
    S.save(BATCH / "reference-controls.json", controls)
    assert all(c["exit_code"] == 0 for c in controls["reference"]), controls
    assert controls["baseline"][0]["exit_code"] == 1 and all(
        c["exit_code"] == 0 for c in controls["baseline"][1:]
    )
    paths = [p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py")]
    paths += [
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_encode.py",
        "tests/test_append.py",
        "pyproject.toml",
    ]
    files = {p: S.sha(root / p) for p in paths}
    brief = {
        "schema_version": 1,
        "revision": 1,
        "feature_id": "project-identity-stability",
        "task_id": "project-identity-stability",
        "goal": "Propose cohesive units for stable identity propagation: empty/None source revision produces the same sample ID, and that sample ID becomes a job payload whose top-level transport-only fields do not affect request digest. Preserve exact meaningful identity boundaries. Propose responsibilities and dependencies, not algorithm/code. Primary-reviewed contracts and risk are fixed.",
        "risk_rationale": "Public identities/idempotency compatibility, high risk; isolated snapshot only, no live data or migration",
        "feature_risk": "high",
        "integration_risk": "high",
        "max_units": 2,
        "authority": {
            "read_roots": ["src", "tests", "pyproject.toml", "acceptance"],
            "modify": [PRODUCER, CONSUMER],
            "create": [],
            "readonly": [p for p in paths if p not in {PRODUCER, CONSUMER}],
            "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
        },
        "contracts": [
            {
                "id": k,
                "text": v["contract"],
                "risk_floor": "high",
                "implementation_ref": {"path": v["path"], "symbol": v["symbol"]},
            }
            for k, v in D.SPECS.items()
        ],
        "contract_edges": [["encode", "append"]],
        "atomic_contract_groups": [],
        "source_hashes": files,
        "integration_tests": ["tests/test_encode.py", "tests/test_append.py"],
        "validation_profile": "real-trace-strict",
        "acceptance_catalog": {
            k: {
                "acceptance_criteria": [{"id": k, "text": v["contract"]}],
                "acceptance_scenarios": [
                    {
                        "id": k + "-compatibility",
                        "text": "Normal, meaningful boundaries and real producer/consumer round-trip",
                        "observables": {"contract": v["contract"]},
                    }
                ],
                "required_order": [],
                "forbidden_orderings": [],
                "required_focused_tests": ["tests/test_" + k + ".py"],
            }
            for k, v in D.SPECS.items()
        },
    }
    context = {
        "current_functions": {
            k: PROJECT.function_source(root / v["path"], v["symbol"])
            for k, v in D.SPECS.items()
        },
        "protected_tests": {
            p: (root / p).read_text("utf-8") for p in brief["integration_tests"]
        },
        "qualified_capability": "One existing function/file per local unit; exact supplied contracts only, Primary classifies/approves. Separate snapshots; consumer reads exact accepted producer bytes. No zero-ID task or database/migration work.",
    }
    D.P.C.validate_brief(brief)
    S.save(BATCH / "input.json", {"brief": brief, "context": context})
    S.save(
        BATCH / "catalog.json",
        {
            k: {
                "family": D.BRIDGE.FAMILY,
                "path": v["path"],
                "symbol": v["symbol"],
                "qualification_evidence": v["qualification"],
            }
            for k, v in D.SPECS.items()
        },
    )
    proposal = {
        "status": "proposed",
        "questions": [],
        "rationale": "Offline construction only, not a model answer",
        "units": [
            {
                "id": k,
                "goal": v["contract"],
                "owner": "local-coder",
                "risk": "high",
                "contracts": [k],
                "dependencies": ["encode"] if k == "append" else [],
                "modify": [v["path"]],
                "create": [],
            }
            for k, v in D.SPECS.items()
        ],
    }
    plan = D.P.C.proposal_plan(brief, proposal)
    for topic, spec in D.SPECS.items():
        material = D.materialize(topic, offline_plan=plan)
        unit_root = Path(material["root"])
        replay = unit_root.parent / "scripted-reference.json"
        S.save(
            replay,
            [
                {
                    "kind": "replacement",
                    "content": PROJECT.function_source(
                        proof / spec["path"], spec["symbol"]
                    ),
                }
            ],
        )
        result = T.run(command(unit_root, replay=replay), unit_root, timeout=240)
        S.save(unit_root.parent / "full-chain.json", result)
        assert result["exit_code"] == 0, result
    pins = [
        Path(__file__),
        Path(TASKS.__file__),
        Path(PROJECT.__file__),
        Path(D.__file__),
        Path(CLOSE.__file__),
        BATCH / "input.json",
        BATCH / "catalog.json",
        *list((BATCH / "private").glob("*.py")),
        *list((S.KIT / ".local-agents").rglob("*.py")),
    ]
    S.save(
        BATCH / "registration.json",
        {
            "pins": {str(p): S.sha(p) for p in pins if "__pycache__" not in p.parts},
            "weekly_used_start": used,
            "weekly_stop": None,
            "batch_seconds": 7200,
            "registered": "1 Coordinator max2requests; 2 dependent units; full project/cross-boundary final integration",
            "budgets": "C12requests/3edits/1initial+3postchecks/900s/4096out; R16requests/4errors/600s/4096out; unit2220s; Muse Coordinator24576 low4096 max2requests; unchanged single residency",
            "gate": "Valid scoped Coordinator decomposition reviewed by Primary, both units independently accepted, exact accepted producer transfer, complete package/cross-unit tests and strict checks, no assistance/takeover/drift",
            "continue_rule": "Unaccepted producer prevents consumer; no semantic reroll. Infrastructure/drift/unsafe behavior/time/user stop halts. Failed dependent counts NOT_RUN. Ordinary failure remains HOLD.",
            "exposure": "Known exact qualified task contracts in an untested real-package snapshot composition; no novel semantic task or unknown-plan autonomy claim",
            "Primary_cost": "Primary chose contracts, tested family evidence, paths, risk, public/private tests/reference and explicit contract edge. Coordinator must package valid units; Primary reviews proposal and complete diffs. Preparation cost substantial, active time/cloud tokens unknown.",
            "scope": "One supervised immutable snapshot composition. No DB migration/concurrency or external MLflow, no default enablement or same-workspace autonomous scheduler.",
        },
    )
    print(
        "One real-package dependency chain frozen; offline controls passed", flush=True
    )


def configure():
    D.BATCH = BATCH
    D.SPECS = specs()
    D.fresh = fresh
    D.I.refresh_material = refresh
    D.I.command = command
    T.run = run_check


def close(used, reason):
    original = S.save

    def current_budget(path, value):
        if Path(path) == BATCH / "metrics.json":
            value = {**value, "weekly_stop": None}
        original(path, value)

    S.save = current_budget
    try:
        CLOSE.close(used, reason)
    finally:
        S.save = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=["prepare", "plan", "approve", "execute", "accept", "close"]
    )
    parser.add_argument("--topic", choices=["encode", "append"])
    parser.add_argument("--weekly-used", type=int, required=True)
    parser.add_argument("--reason")
    args = parser.parse_args()
    configure()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    elif args.mode == "plan":
        D.plan(args.weekly_used, time.time())
    elif args.mode == "approve":
        fresh(args.weekly_used, time.time())
        D.approve(args.reason)
    elif args.mode == "execute":
        D.execute(args.topic, args.weekly_used, time.time())
    elif args.mode == "accept":
        fresh(args.weekly_used, time.time())
        D.accept(args.topic, args.reason)
    else:
        fresh(args.weekly_used, time.time())
        close(args.weekly_used, args.reason)
