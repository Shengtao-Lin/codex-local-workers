"""Independent one-attempt repair experiment; old evidence is never rewritten."""

import json
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import capture_fixture_support as F
import reasoning_wire_candidate as W
import reviewer_rework_permit as P
import supervised_repair_phase as OLD

BATCH = S.KIT / "benchmarks/work/harness-convergence/reviewer-bounded-rework-20261020-2"
ORDER = ["defect-1", "false-positive-1", "false-positive-2", "defect-2"]
NORMAL = S.KIT / "benchmarks/work/harness-convergence/function-normal-repeat-20261019-1"


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def command(root, *, replay=None, permit=True, mode="unit"):
    args = [
        S.PYTHON,
        "-B",
        S.KIT / "benchmarks/consolidated_entry.py",
        "--mode",
        mode,
        "--runtime-dir",
        root / ".local-agents",
        "--packet",
        root / ".agent/child.json",
        "--config",
        root / ".agent/config.json",
        "--report",
        root / ".agent/child-report.json",
        "--review-report",
        root / ".agent/child-reviewer.json",
        "--summary",
        root / ".agent/child-summary.json",
        "--bounded-source-output",
        "--focused-repair",
        "--static-focus",
        "--reviewer-forward-reasoning",
    ]
    if permit:
        path = root / ".agent/rework-permit.json"
        args += [
            "--experimental-rework-permit",
            path,
            "--experimental-rework-permit-sha256",
            S.sha(path),
        ]
    if replay:
        args += ["--replay", replay]
    return args


def source(cell):
    batch = OLD.BATCH if cell.startswith("defect") else NORMAL
    name = "json-2" if cell.startswith("defect") else "single_content-1"
    return S.read(batch / "cells.json")[name]


def prepare(
    *,
    batch=BATCH,
    used=4,
    feedback_mode="raw",
    controls_path=None,
    expected_controls=12,
    extra_pins=(),
):
    BATCH = Path(batch)
    control_source = (
        Path(controls_path)
        if controls_path
        else (
            BATCH.with_name("reviewer-bounded-rework-20261020-1")
            / "offline-controls-v2.xml"
        )
    )
    controls = list(ET.parse(control_source).iter("testcase"))
    assert len(controls) == expected_controls and not any(
        c.find(tag) is not None
        for c in controls
        for tag in ("failure", "error", "skipped")
    )
    baseline = {
        "weekly_used": used,
        "weekly_stop": 50,
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=S.KIT, text=True
        ).strip(),
        "status": subprocess.check_output(
            ["git", "status", "--short"], cwd=S.KIT, text=True
        ),
        "production_files": {
            str(p.relative_to(S.KIT)): S.sha(p)
            for p in [*(S.KIT / ".local-agents").glob("*.py"), S.KIT / "AGENTS.md"]
        },
    }
    S.save(BATCH / "baseline.json", baseline)
    rows = {}
    for cell in ORDER:
        old = source(cell)
        origin, identity = Path(old["root"]), old["identity"]
        parent_run = (
            Path(".agent/tasks") / identity["task_id"] / "runs" / identity["run_id"]
        )
        post = S.read(origin / parent_run / "post-state.json")["validation_inputs"]
        parent = S.read(origin / ".agent/unit-report.json")
        credits = P.credits(parent)
        root = BATCH / "cells" / cell / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            expected = post[name]["sha256"] if name == old["target"] else digest
            assert S.sha(origin / name) == expected, name
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin / name, dest)
        shutil.copytree(origin / parent_run, root / parent_run)
        review_dir = (
            Path(".agent/tasks")
            / identity["task_id"]
            / "reviews"
            / ("auto-" + identity["run_id"])
        )
        shutil.copytree(origin / review_dir, root / review_dir)
        report_path = root / review_dir / "handoff.json"
        report = S.read(report_path)
        packet = S.read(root / parent_run / "packet.json")
        gate = F.load(root / ".local-agents/local-unit.py", "bounded_parent_gate")
        # Historical absolute commands bind ORIGIN, not the cloned directory.
        gate.verify_handoff(
            origin, parent, config=S.read(origin / ".agent/config.json")
        )
        S.save(
            root / ".agent/origin-validation.json",
            {
                "origin": str(origin),
                "parent_handoff_sha256": S.sha(origin / parent_run / "handoff.json"),
                "verified_at_original_root": True,
                "clone_reexecution_claimed": False,
            },
        )
        feedback = P.eligibility(
            root, packet, report, S.read(root / review_dir / "completed.json")
        )
        before_parent = {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in [*(root / parent_run).rglob("*"), *(root / review_dir).rglob("*")]
            if p.is_file()
        }
        child = {
            "schema_version": 2,
            "task_id": identity["task_id"],
            "unit_id": identity["unit_id"],
            "run_id": identity["run_id"] + "-bounded",
            "parent_run_id": identity["run_id"],
            "packet_revision": packet.get("packet_revision", 1) + 1,
            "preserve_contract": True,
            "review_feedback": feedback,
        }
        S.save(root / ".agent/child.json", child)
        S.save(
            root / ".agent/original-controls.json",
            {
                "policy": S.read(root / F.POLICY_PATH),
                "config": S.read(root / ".agent/config.json"),
            },
        )
        policy = S.read(root / F.POLICY_PATH)
        policy["identity"] = {k: child[k] for k in ("task_id", "unit_id", "run_id")}
        write(root / F.POLICY_PATH, policy)
        config = S.read(root / ".agent/config.json")
        config["experimental_capture_policy_sha256"] = S.sha(root / F.POLICY_PATH)
        config["experimental_recovery_credits"] = credits
        if feedback_mode == "location-only":
            config["experimental_rework_feedback_projection"] = feedback_mode
        write(root / ".agent/config.json", config)
        transport = W.patch_client(root / ".local-agents/worker-runtime.py")
        hook = P.install_hook(root / ".local-agents/worker-runtime.py", root)
        files = {
            p.relative_to(root).as_posix(): S.sha(p)
            for p in root.rglob("*")
            if p.is_file()
        }
        permit = {
            "coder_feedback_mode": feedback_mode,
            "authority": P.AUTHORITY,
            "max_child_attempts": 1,
            "automatic_acceptance": False,
            "child_run_id": child["run_id"],
            "identity": report["identity"],
            "report_sha256": S.sha(report_path),
            "bindings": files,
            "semantic_defect_confirmed": False,
            "user_authorization": "2026-10-20 independent bounded Reviewer-to-Coder experiment",
        }
        S.save(root / ".agent/rework-permit.json", permit)
        # No-network proof: default gate still rejects, permitted child retains hard contract.
        offline = BATCH / "offline" / cell / "isolated"
        shutil.copytree(root, offline)
        denied = T.run(
            command(offline, permit=False, mode="preflight"), offline, timeout=120
        )
        S.save(offline.parent / "default-gate.json", denied)
        assert denied["exit_code"] and "Primary" in denied["stderr"], denied
        if cell == "defect-1":
            good = S.read(OLD.BATCH / "cells.json")["json-1"]
            reference = T.extract(Path(good["root"]) / good["target"], "canonical_json")
            responses = [{"replacement": reference}]
        else:
            responses = [
                {"blocked_reason": "Offline inherited-feedback transport control"}
            ]
        replay = offline.parent / "replay.json"
        S.save(replay, responses)
        proof = T.run(command(offline, replay=replay), offline, timeout=180)
        S.save(offline.parent / "permitted-entry.json", proof)
        assert proof["exit_code"] == (0 if cell == "defect-1" else 2), proof
        if cell == "defect-1":
            private_proof = T.run(
                [
                    S.PYTHON,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "tests",
                    old["private_tests"],
                    BATCH / "private/test_json_fidelity.py",
                ],
                offline,
                timeout=120,
            )
            S.save(offline.parent / "independent-reference.json", private_proof)
            assert private_proof["exit_code"] == 0, private_proof
        archive = (
            offline / ".agent/tasks" / identity["task_id"] / "runs" / child["run_id"]
        )
        resolved = S.read(archive / "packet.json")
        assert all(
            resolved[k] == packet[k]
            for k in (
                "required_behavior",
                "scope",
                "focused_tests",
                "risk",
                "validation_profile",
            )
        )
        assert resolved["_experimental_reviewer_recovery"]["confirmed_defect"] is False
        assert resolved["review_feedback"] == feedback
        if feedback_mode == "location-only":
            import literal_check_feedback as L

            request = S.read(archive / "proposal-request-1.json")
            facts = L.restore(request["messages"][1]["content"].split("\n", 1)[1])
            assert facts["review_feedback"] == P.locator_feedback(report)
            assert facts["review_feedback"] != feedback
        assert all(S.sha(offline / p) == h for p, h in before_parent.items())
        rows[cell] = {
            "root": str(root),
            "identity": {k: child[k] for k in ("task_id", "unit_id", "run_id")},
            "parent_identity": identity,
            "parent": parent,
            "target": old["target"],
            "private_tests": old["private_tests"],
            "files": files,
            "permit_sha256": S.sha(root / ".agent/rework-permit.json"),
            "parent_files": before_parent,
            "hook": hook,
            "transport": transport,
        }
    S.save(BATCH / "cells.json", rows)
    names = [
        "consolidated_entry.py",
        "consolidated_harness.py",
        "reviewer_rework_permit.py",
        "reviewer_bounded_trial.py",
        "reviewer_contract_first.py",
        "reviewer_capture_entry.py",
        "static_focus_rules.py",
        "repair_phase_rules.py",
        "bounded_source_rules.py",
        "literal_check_feedback.py",
        "function_proposal_rules.py",
        "preserved_import_guard.py",
    ]
    S.save(
        BATCH / "registration.json",
        {
            "registered": 4,
            "order": ORDER,
            "weekly_stop": 50,
            "batch_seconds": 10800,
            "pins": {
                **{str(Path(p).resolve()): S.sha(p) for p in extra_pins},
                str(control_source): S.sha(control_source),
                str(BATCH / "private/test_json_fidelity.py"): S.sha(
                    BATCH / "private/test_json_fidelity.py"
                ),
                **{
                    str(S.KIT / "benchmarks" / n): S.sha(S.KIT / "benchmarks" / n)
                    for n in names
                },
            },
            "exposure": "Two exposed task families: real Coder JSON defect and known false-positive parse_message recommendation. Each reused frozen parent twice; historical failure retained, not new holdout or initial Reviewer qualification.",
            "authority": "Independent default-off experiment explicitly user approved; no fabricated Primary disposition, no production gate/default changes.",
            "candidate": f"One eligible recommendation triggers ONE inherited Coder call; Coder feedback mode={feedback_mode}. Raw canonical packet remains unchanged for Reviewer. No contract/scope/test/format/Reviewer/budget change; no Primary semantic filtering.",
            "budget": "Parent+child Coder12 requests/3 edits/3 postchecks/12 format preparations/2 protocol recoveries/900s combined, deduct parent actual use. Separate initial check per invocation (max2), supplemental cap16 each. Initial historical and fresh Reviewer each16 requests/600s/4096 output. No Explorer/Coordinator, no same-code review resampling.",
            "gate": "Defect pair2/2 independent final acceptance, false-positive pair0/2 semantic regressions. Safe abstention/blocked false-positive is no acceptance and no Coder defect-fix credit. Gate never grants R4/production automatically.",
            "continue_rule": "Complete all four ordinary outcomes, keep every failed child. Safety/protected drift/infra/budget stop; no second repair attempt or semantic prompt adjustment.",
            "primary_cost": "One-time policy/fixture preparation distinct from runtime; no per-child semantic curation or implementation edits. Final full source plus parent/child diff and checks still Primary.",
        },
    )
    print("Four cells frozen; default-denial and permitted child controls passed")


def run(cell, used, observed, *, batch=BATCH):
    BATCH = Path(batch)
    assert 0 <= used < 50 and 0 <= time.time() - observed <= 120
    reg, rows = S.read(BATCH / "registration.json"), S.read(BATCH / "cells.json")
    assert all(S.sha(p) == h for p, h in reg["pins"].items())
    for previous in ORDER[: ORDER.index(cell)]:
        assert not S.read(BATCH / "results" / previous / "result.json")["stop_batch"]
    clock = BATCH / "batch-start.json"
    if not clock.exists():
        S.save(clock, {"epoch": time.time()})
    remaining = 10800 - (time.time() - S.read(clock)["epoch"])
    assert remaining > 0
    row = rows[cell]
    root = Path(row["root"])
    assert all(S.sha(root / p) == h for p, h in row["files"].items())
    assert S.sha(root / ".agent/rework-permit.json") == row["permit_sha256"]
    S.save(
        BATCH / "results" / cell / "start.json",
        {"weekly_used": used, "observed_at": observed},
    )
    started = time.monotonic()
    process = T.run(command(root), root, timeout=min(2220, remaining))
    report = S.read(root / ".agent/child-report.json")
    summary = S.read(root / ".agent/child-summary.json")
    drift = [
        p
        for p, h in row["files"].items()
        if p != row["target"] and S.sha(root / p) != h
    ]
    private = [row["private_tests"]]
    if cell.startswith("defect"):
        private.append(BATCH / "private/test_json_fidelity.py")
    checks = [
        T.run(cmd, root, timeout=120)
        for cmd in [
            [S.PYTHON, "-B", "-m", "pytest", "-q", "tests", *private],
            [S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON],
        ]
    ]
    result = {
        "identity": row["identity"],
        "process": process,
        "coder_status": report["status"],
        "reviewer_decision": summary["reviewer_decision"],
        "protected_drift": drift,
        "parent": row["parent"]["consolidated_harness"],
        "child": report["consolidated_harness"],
        "checks": checks,
        "all_checks_pass": all(c["exit_code"] == 0 for c in checks),
        "stop_batch": bool(
            drift
            or report.get("infra_failure")
            or report["status"] == "policy_violation"
        ),
        "seconds": time.monotonic() - started,
        "primary_final": "PENDING",
    }
    S.save(BATCH / "results" / cell / "result.json", result)
    print(
        cell,
        result["coder_status"],
        result["reviewer_decision"],
        "independent checks",
        result["all_checks_pass"],
    )
