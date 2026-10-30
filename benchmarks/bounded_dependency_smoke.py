"""One exposed two-unit snapshot smoke; explicit bridge, no global Coordinator."""

import argparse
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import installed_brief_trial as P
import installed_scope_trial as I
import limited_family_trial as L
from test_installable_bounded import INSTALL

BATCH = I.BASE / "bounded-dependency-smoke-20261021-4"
BRIDGE = F.load(S.KIT / ".local-agents/coordinator-bounded.py", "smoke_bounded_bridge")
SPECS = {
    "encode": {
        "path": "src/product/dependencies.py",
        "symbol": "encode_segment",
        "module": "product.dependencies",
        "contract": "encode_segment(segment: object) -> str rejects every non-str with TypeError and the empty string with ValueError; returns quote(segment, safe='') for every nonempty string, with no normalization or input mutation. Preserve signature and UTF-8 percent encoding, including literal percent, slash, whitespace, Unicode and query delimiters.",
        "header": "from urllib.parse import quote\n",
        "reference": L.TASKS["route"]["dependency"],
        "start": "from urllib.parse import quote\n\ndef encode_segment(segment: object) -> str:\n    return quote(str(segment), safe='')\n",
        "cases": [
            {"args": ["a/b"], "kwargs": {}},
            {"args": [None], "kwargs": {}},
            {"args": [""], "kwargs": {}},
        ],
    },
    "append": {
        "path": "src/product/code.py",
        "symbol": "append_segment",
        "module": "product.code",
        "contract": L.TASKS["route"]["contract"],
        "header": L.TASKS["route"]["header"],
        "reference": L.TASKS["route"]["header"] + "\n" + L.TASKS["route"]["reference"],
        "start": L.TASKS["route"]["header"]
        + "\n"
        + "def append_segment(base: str, segment: str) -> str:\n    return base + '/' + encode_segment(segment)\n",
        "cases": L.TASKS["route"]["cases"],
    },
}
ENCODER_TEST = """import pytest
from product.dependencies import encode_segment

def test_encode():
    assert encode_segment("a/b") == "a%2Fb"
    assert encode_segment("雪") == "%E9%9B%AA"
    with pytest.raises(ValueError):
        encode_segment("")
    for value in [None, False, 0, [], {}]:
        with pytest.raises(TypeError):
            encode_segment(value)
"""
PRIVATE = """import pytest
from urllib.parse import quote
from product.dependencies import encode_segment

def test_exact_preservation():
    for value in [" ", "%2F", "/", "?a#b", "雪/雨"]:
        assert encode_segment(value) == quote(value, safe="")
    for value in [True, 0.0, {"x": 1}]:
        with pytest.raises(TypeError):
            encode_segment(value)
"""


def fresh(used, observed):
    assert 0 <= used < 50 and observed and 0 <= time.time() - observed <= 120
    reg = S.read(BATCH / "registration.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    clock = BATCH / "start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time(), "weekly_used": used})
    assert time.time() - S.read(clock)["epoch"] < 7200


def prepare(used):
    assert 0 <= used < 50
    gate = S.read(I.BASE / "coordinator-bounded-bridge-20261021-1/gate.json")
    assert gate["status"] == "PASS_OFFLINE_BRIDGE" and all(
        S.sha(S.KIT / p) == h for p, h in gate["pins"].items()
    )
    root = BATCH / "template"
    texts = {
        "src/product/__init__.py": "",
        "tests/test_encode.py": ENCODER_TEST,
        "tests/test_append.py": L.TASKS["route"]["public"],
    }
    texts.update({s["path"]: s["start"] for s in SPECS.values()})
    for path, value in texts.items():
        L.write(root / path, value)
    shutil.copyfile(L.SEED / "pyproject.toml", root / "pyproject.toml")
    for args in (("check", "--select", "I", "--fix"), ("format",)):
        assert (
            T.run([S.PYTHON, "-B", "-m", "ruff", *args, "src", "tests"], root)[
                "exit_code"
            ]
            == 0
        )
    L.write(BATCH / "private/test_private_encode.py", PRIVATE)
    L.write(BATCH / "private/test_private_append.py", L.TASKS["route"]["private"])
    proof = BATCH / "reference"
    shutil.copytree(root, proof)
    for spec in SPECS.values():
        (proof / spec["path"]).write_text(spec["reference"], encoding="utf-8")
    for args in (("check", "--select", "I", "--fix"), ("format",)):
        assert (
            T.run([S.PYTHON, "-B", "-m", "ruff", *args, "src", "tests"], proof)[
                "exit_code"
            ]
            == 0
        )
    checks = L.checks(proof, BATCH / "private")
    baseline = T.run([S.PYTHON, "-B", "-m", "pytest", "-q", "tests"], root)
    S.save(
        BATCH / "reference-controls.json", {"reference": checks, "baseline": baseline}
    )
    assert all(c["exit_code"] == 0 for c in checks) and baseline["exit_code"] == 1
    files = {
        p.relative_to(root).as_posix(): S.sha(p)
        for p in root.rglob("*")
        if p.is_file()
        and not any(
            x in p.parts for x in ("__pycache__", ".pytest_cache", ".ruff_cache")
        )
    }
    brief = {
        "schema_version": 1,
        "revision": 1,
        "feature_id": "bounded-route-chain",
        "task_id": "bounded-route-chain",
        "goal": "Implement the approved URL segment compatibility feature in cohesive qualified units. Producer output is consumed by append_segment; preserve actual dependency and error propagation. Propose tasks, not implementation algorithms.",
        "risk_rationale": "Primary: public encoding/compatibility and exact cross-unit error behavior impose high risk",
        "feature_risk": "high",
        "integration_risk": "high",
        "authority": {
            "read_roots": ["src", "tests", "pyproject.toml", "acceptance"],
            "modify": [s["path"] for s in SPECS.values()],
            "create": [],
            "readonly": [
                p for p in files if p not in {s["path"] for s in SPECS.values()}
            ],
            "forbidden": [".agent", ".git", ".local-agents", "AGENTS.md"],
        },
        "max_units": 2,
        "contracts": [
            {
                "id": k,
                "text": s["contract"],
                "risk_floor": "high",
                "implementation_ref": {"path": s["path"], "symbol": s["symbol"]},
            }
            for k, s in SPECS.items()
        ],
        "contract_edges": [["encode", "append"]],
        "atomic_contract_groups": [],
        "source_hashes": files,
        "integration_tests": ["tests/test_encode.py", "tests/test_append.py"],
        "validation_profile": "real-trace-strict",
        "acceptance_catalog": {
            k: {
                "acceptance_criteria": [{"id": k, "text": s["contract"]}],
                "acceptance_scenarios": [
                    {
                        "id": k + "-compatibility",
                        "text": "Normal/error/exact boundary behavior",
                        "observables": {"contract": s["contract"]},
                    }
                ],
                "required_order": [],
                "forbidden_orderings": [],
                "required_focused_tests": ["tests/test_" + k + ".py"],
            }
            for k, s in SPECS.items()
        },
    }
    context = {
        "files": {p: (root / p).read_text("utf-8") for p in files},
        "qualified_capability": "One existing function/file per local-coder unit; no edits to tests, imports, permission/classification or architecture. Separate immutable execution snapshots preserve producer evidence. Primary provides classification and final acceptance.",
    }
    P.C.validate_brief(brief)
    S.save(BATCH / "input.json", {"brief": brief, "context": context})
    S.save(
        BATCH / "catalog.json",
        {
            k: {
                "family": BRIDGE.FAMILY,
                "path": s["path"],
                "symbol": s["symbol"],
                "qualification_evidence": "Qualified bounded local transformation family; this exposed producer/consumer composition is a new smoke, not independently promoted production capability",
            }
            for k, s in SPECS.items()
        },
    )
    offline_proposal = {
        "status": "proposed",
        "questions": [],
        "rationale": "Offline control only, excluded from model input",
        "units": [
            {
                "id": k,
                "goal": s["contract"],
                "owner": "local-coder",
                "risk": "high",
                "contracts": [k],
                "dependencies": ["encode"] if k == "append" else [],
                "modify": [s["path"]],
                "create": [],
            }
            for k, s in SPECS.items()
        ],
    }
    offline_plan = P.C.proposal_plan(brief, offline_proposal)
    for topic, spec in SPECS.items():
        data = materialize(topic, offline_plan=offline_plan)
        control_root = Path(data["root"])
        replay = control_root.parent / "scripted-reference.json"
        S.save(
            replay, [{"replacement": T.extract(proof / spec["path"], spec["symbol"])}]
        )
        full = T.run(I.command(control_root, replay=replay), control_root, timeout=180)
        S.save(control_root.parent / "full-chain.json", full)
        assert full["exit_code"] == 0, full["stderr"][-1500:]
        assert (
            S.read(control_root / ".agent/unit-summary.json")["reviewer_started"]
            is False
        )
    paths = [
        Path(__file__),
        BATCH / "input.json",
        BATCH / "catalog.json",
        *list((BATCH / "private").glob("*.py")),
        *list((S.KIT / ".local-agents").rglob("*.py")),
    ]
    S.save(
        BATCH / "registration.json",
        {
            "pins": {str(p): S.sha(p) for p in paths if "__pycache__" not in p.parts},
            "weekly_used_start": used,
            "weekly_stop": 50,
            "batch_seconds": 7200,
            "registered": "1 Coordinator proposal (max2 requests) +2 ordered Coder/fresh Reviewer units + independent integration",
            "budgets": "Unchanged bounded-v1: C12/3 edits/1+3 checks/900s; R16/4 errors/600s/4096 output; each unit2220s; single residency; Coordinator Muse24576 low4096 max2 requests",
            "gate": "Both units independently accepted, exact immutable producer transfer, full integration tests and static checks pass; no runtime semantic hints/takeover/safety drift",
            "continue_rule": "Any failed proposal/unsupported route/unaccepted producer stops dependent dispatch; no resampling/replacements or budget increases. Ordinary failures retained; downstream NOT_RUN. Infrastructure/time/weekly50 stop.",
            "exposure": "Existing exposed route behavior and its previously read-only encoder, not holdout or real upstream deployment",
            "Primary_cost": "Primary supplied complete contracts, known paths, tests/reference and classification; no runtime algorithm hints; cloud tokens/active time unknown",
            "scope": "Primary-supervised snapshot chain, not same-worktree automatic coordinator enablement or general R4/R5 release",
        },
    )
    print("One two-unit exposed chain registered; reference/static profile pass")


def plan(used, observed):
    fresh(used, observed)
    data = S.read(BATCH / "input.json")
    config = S.read(L.SEED / ".agent/config.json")
    client = P.W.LMStudioClient(
        config["lmstudio_base_url"],
        config["coordinator_model"],
        timeout=360,
        max_tokens=4096,
        temperature=0.1,
        structured_output=False,
        context_length=24576,
    )
    client.reasoning_effort = "low"
    S.save(BATCH / "plan-start.json", {"weekly_used": used, "epoch": time.time()})
    with P.W.MODEL_RESIDENCY.role_model_lease(client, config):
        client.preflight()
        result = P.C.probe(
            data["brief"], data["context"], client, reasoning_strength="low"
        )
    S.save(BATCH / "proposal.json", result)
    print(result["status"], "Primary proposal review required")


def approve(reason):
    data, result = S.read(BATCH / "input.json"), S.read(BATCH / "proposal.json")
    assert result["status"] == "proposal_valid"
    plan = result["untrusted_plan"]
    assert len(plan["units"]) == 2
    for unit in plan["units"]:
        assert unit["owner"] == "local-coder" and len(unit["owned_contract_ids"]) == 1
        topic = unit["owned_contract_ids"][0]
        assert (
            unit["scope_authority"]["modify"] == [SPECS[topic]["path"]]
            and not unit["scope_authority"]["create"]
        )
    record = P.C.approve(
        data["brief"],
        result["proposal"],
        BATCH / "template",
        BATCH / "template/.agent/approval.json",
        primary_review_note=reason,
    )
    S.save(BATCH / "approved-plan.json", record["approved_plan"])
    print("Primary-approved decomposition; execution still explicit")


def materialize(topic, *, offline_plan=None):
    plan = (
        offline_plan
        if offline_plan is not None
        else S.read(BATCH / "approved-plan.json")
    )
    unit = next(u for u in plan["units"] if u["owned_contract_ids"] == [topic])
    spec = SPECS[topic]
    root = (
        BATCH
        / ("offline" if offline_plan is not None else "units")
        / topic
        / "isolated"
    )
    with tempfile.TemporaryDirectory(prefix="bounded-chain-install-") as directory:
        staging = Path(directory)
        INSTALL.install(S.KIT, staging, apply=True)
        shutil.copytree(staging, root)
    for name in ("src", "tests"):
        shutil.copytree(BATCH / "template" / name, root / name)
    shutil.copyfile(BATCH / "template/pyproject.toml", root / "pyproject.toml")
    if topic == "append":
        if offline_plan is not None:
            producer_root = BATCH / "reference"
        else:
            producer = S.read(BATCH / "units/encode/binding.json")
            assert (
                S.read(BATCH / "units/encode/acceptance.json")["automatic_acceptance"]
                is False
            )
            producer_root = Path(producer["root"])
        shutil.copyfile(
            producer_root / SPECS["encode"]["path"], root / SPECS["encode"]["path"]
        )
    proposal = {
        "unit_id": unit["unit_id"],
        "run_id": "chain-" + topic,
        "attempt": 1,
        "packet_revision": 1,
        "goal": spec["contract"],
        "scope": {
            "read": unit["scope_authority"]["read_roots"],
            "modify": [spec["path"]],
            "create": [],
        },
        "edit_targets": [
            {"path": spec["path"], "anchor": "def " + spec["symbol"] + "("}
        ],
        "focused_tests": ["tests/test_" + topic + ".py"],
        "supplemental_tests": [],
        "implementation_guidance": [],
    }
    packet = BRIDGE.CONTRACT.materialize_bounded_packet(plan, proposal)
    sources = list(S.read(BATCH / "input.json")["brief"]["source_hashes"])
    packet["scope"]["readonly"] = list(
        dict.fromkeys(
            [p for p in sources if p != spec["path"]]
            + [F.POLICY_PATH, F.PRODUCER, F.HELPER]
        )
    )
    config = S.read(L.SEED / ".agent/config.json")
    config["bounded_execution_profile"] = "bounded-v1"
    dependencies = spec["header"]
    if topic == "append":
        dependencies += "\nRead-only accepted dependency:\n" + (
            root / SPECS["encode"]["path"]
        ).read_text("utf-8")
    config["coder_single_function"] = {
        "path": spec["path"],
        "symbol": spec["symbol"],
        "dependencies": dependencies,
    }
    identity = {k: packet[k] for k in ("task_id", "unit_id", "run_id")}
    _, digest = F.install_material(
        root,
        identity,
        source_paths=sources,
        target={
            "path": spec["path"],
            "symbol": spec["symbol"],
            "module": spec["module"],
        },
        family="json-call-model-dump-v1",
        cases=spec["cases"],
        writable=[spec["path"]],
        python=S.PYTHON,
    )
    config["experimental_capture_policy_sha256"] = digest
    I.refresh_material(root, config)
    BRIDGE.eligible_packet(
        plan,
        packet,
        config,
        S.read(BATCH / "catalog.json"),
        bridge_profile="bounded-v1",
    )
    S.save(root / ".agent/packet.json", packet)
    S.save(root / ".agent/config.json", config)
    preflight = I.command(root, "preflight")
    preflight[preflight.index("--report") + 1] = str(root / ".agent/preflight.json")
    control = T.run(preflight, root)
    S.save(root.parent / "preflight.json", control)
    assert control["exit_code"] == 0
    binding = {
        "root": str(root),
        "packet": packet,
        "config": config,
        "protected": {
            p: S.sha(root / p)
            for p in sources + [F.POLICY_PATH, F.PRODUCER, F.HELPER]
            if p != spec["path"]
        },
    }
    S.save(root.parent / "binding.json", binding)
    return binding


def execute(topic, used, observed):
    fresh(used, observed)
    data = materialize(topic)
    root, packet, config = Path(data["root"]), data["packet"], data["config"]
    if topic == "append":
        producer = S.read(BATCH / "units/encode/binding.json")
        uid = producer["packet"]["unit_id"]
        receipt = BRIDGE.dependency_readiness(
            S.read(BATCH / "approved-plan.json"),
            root,
            packet,
            config,
            S.read(BATCH / "catalog.json"),
            {uid: {k: producer["packet"][k] for k in ("task_id", "run_id")}},
            {uid: producer["config"]},
            bridge_profile="bounded-v1",
            dependency_roots={uid: producer["root"]},
            evidence_root=BATCH,
            transfer_paths={
                uid: {
                    "source": SPECS["encode"]["path"],
                    "destination": SPECS["encode"]["path"],
                }
            },
        )
        S.save(root.parent / "dependency-gate.json", receipt)
    dest = root.parent
    S.save(dest / "start.json", {"weekly_used": used, "epoch": time.time()})
    started = time.monotonic()
    with (
        (dest / "stdout.log").open("x", encoding="utf-8") as out,
        (dest / "stderr.log").open("x", encoding="utf-8") as err,
    ):
        child = subprocess.Popen(
            I.command(root),
            cwd=root,
            stdout=out,
            stderr=err,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        S.save(dest / "process.json", {"pid": child.pid})
        try:
            child.wait(
                timeout=min(
                    2220, 7200 - (time.time() - S.read(BATCH / "start.json")["epoch"])
                )
            )
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
            child.wait(timeout=30)
            S.save(dest / "result.json", {"status": "TIMEOUT", "stop": True})
            return
    test = "tests/test_encode.py" if topic == "encode" else "tests"
    private = (
        BATCH / "private/test_private_encode.py"
        if topic == "encode"
        else BATCH / "private"
    )
    checks = [
        T.run(cmd, root, timeout=120)
        for cmd in (
            [S.PYTHON, "-B", "-m", "pytest", "-q", test, private],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        )
    ]
    drift = [p for p, h in data["protected"].items() if S.sha(root / p) != h]
    summary = (
        S.read(root / ".agent/unit-summary.json")
        if (root / ".agent/unit-summary.json").exists()
        else {}
    )
    S.save(
        dest / "result.json",
        {
            "exit_code": child.returncode,
            "seconds": time.monotonic() - started,
            "summary": summary,
            "independent_checks": checks,
            "protected_drift": drift,
            "all_checks_pass": all(c["exit_code"] == 0 for c in checks),
            "Primary_decision": "PENDING",
        },
    )
    print(topic, summary, "Primary full review required")


def accept(topic, reason):
    data = S.read(BATCH / "units" / topic / "binding.json")
    root, packet = Path(data["root"]), data["packet"]
    result = S.read(root.parent / "result.json")
    assert (
        result["all_checks_pass"]
        and not result["protected_drift"]
        and result["summary"].get("reviewer_decision") == "pass_to_primary"
    )
    review_id = "auto-" + packet["run_id"]
    report_path = (
        root
        / ".agent/tasks"
        / packet["task_id"]
        / "reviews"
        / review_id
        / "handoff.json"
    )
    report = S.read(report_path)
    assert not report["findings"]
    disposition = {
        "schema_version": 1,
        "authority": "primary",
        "identity": report["identity"],
        "report_sha256": S.sha(report_path),
        "resolution": "cleared",
        "evidence": [reason],
        "findings": [],
    }
    S.save(root.parent / "disposition.json", disposition)
    command = [
        S.PYTHON,
        "-B",
        root / ".local-agents/record-review.py",
        "--repo",
        root,
        "--task-id",
        packet["task_id"],
        "--run-id",
        packet["run_id"],
        "--decision",
        "accept",
        "--summary",
        reason,
        "--config",
        root / ".agent/config.json",
        "--disposition",
        root.parent / "disposition.json",
    ]
    done = T.run(command, root)
    S.save(root.parent / "record-process.json", done)
    assert done["exit_code"] == 0
    receipt = BRIDGE.verify_accepted_unit(
        S.read(BATCH / "approved-plan.json"),
        root,
        packet["unit_id"],
        {k: packet[k] for k in ("task_id", "run_id")},
        data["config"],
        S.read(BATCH / "catalog.json"),
        bridge_profile="bounded-v1",
    )
    S.save(root.parent / "acceptance.json", receipt)
    print(topic, "Primary accepted; explicit bridge verified current evidence")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("prepare", "plan", "approve", "execute", "accept"))
    p.add_argument("--topic", choices=SPECS)
    p.add_argument("--weekly-used", type=int)
    p.add_argument("--observed-at", type=float)
    p.add_argument("--reason")
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    elif args.mode == "plan":
        plan(args.weekly_used, args.observed_at)
    elif args.mode == "approve":
        approve(args.reason)
    elif args.mode == "execute":
        execute(args.topic, args.weekly_used, args.observed_at)
    else:
        accept(args.topic, args.reason)
