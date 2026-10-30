"""Create-only real installed generic-profile recovery control; zero model calls."""

import os
import shutil
import sys

import bounded_evidence_support as S
import project_caller_trial as J
from strata_native_trial import command

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-generic-evidence-20261023-1"
ORIGIN = BATCH.parent / "strata-complex-20261023-2"


def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    S.save(
        BATCH / "registration.json",
        {
            "candidate": "default-off pytest-source-v1, no specialized typed observation producer",
            "feature_id": "strata-generic-source-evidence",
            "risk": "high: authenticated validation inputs and handoff compatibility",
            "owned_contract_ids": [
                "source-version-binding",
                "complete-checks",
                "default-unchanged",
                "no-false-accept",
            ],
            "live_registered": 0,
            "model_calls": 0,
            "controls": "fresh installed preparation preview/apply, offline real failed draft->repair->full checks, canonical gate, protected drift denial",
            "no_changes": "no production defaults, existing capture profile remains; direct-Primary experiment only, no Reviewer qualification",
            "weekly_stop": 50,
        },
    )
    root = BATCH / "isolated"
    J.copy_project(ORIGIN / "templates/raw", root)
    shutil.copytree(
        S.KIT / ".local-agents",
        root / ".local-agents",
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache"
        ),
    )
    seed = ORIGIN / "cells/raw-1/isolated"
    packet = S.read(seed / ".agent/packet.json")
    packet.update({k: BATCH.name for k in ("task_id", "unit_id", "run_id")})
    config = S.read(seed / ".agent/config.json")
    config.update(
        bounded_evidence_profile="pytest-source-v1", experimental_strata_subagent=True
    )
    config.pop("experimental_capture_policy_sha256", None)
    profile = config["validation_profiles"][packet["validation_profile"]]
    profile["commands"] = [
        c for c in profile["commands"] if c["id"] != "actual-observations"
    ]
    spec = S.read(seed / ".agent/capture-spec.json")
    spec.update(family="pytest-source-v1", cases=[])
    for name, value in (("packet", packet), ("config", config), ("spec", spec)):
        S.save(root / f".agent/{name}.json", value)
    args = [
        S.PYTHON,
        "-B",
        root / ".local-agents/local-bounded-prepare.py",
        "--packet",
        ".agent/packet.json",
        "--config",
        ".agent/config.json",
        "--capture-spec",
        ".agent/spec.json",
    ]
    before = {
        p.relative_to(root).as_posix(): S.sha(p) for p in root.rglob("*") if p.is_file()
    }
    preview = command(args, root)
    S.save(BATCH / "preview.json", preview)
    assert preview["exit_code"] == 0, preview
    assert before == {
        p.relative_to(root).as_posix(): S.sha(p) for p in root.rglob("*") if p.is_file()
    }
    apply = command([*args, "--apply"], root)
    S.save(BATCH / "apply.json", apply)
    assert apply["exit_code"] == 0, apply
    assert not (root / "acceptance/capture-policy.json").exists()
    assert not (root / "acceptance/capture_validation_facts.py").exists()
    prepared = root / ".agent/prepared" / packet["run_id"]
    entry = [
        S.PYTHON,
        "-B",
        root / ".local-agents/local-bounded-unit.py",
        "--packet",
        prepared / "packet.json",
        "--config",
        prepared / "config.json",
    ]
    preflight = command(
        [*entry, "--mode", "preflight", "--report", ".agent/preflight.json"], root
    )
    S.save(BATCH / "preflight-process.json", preflight)
    assert preflight["exit_code"] == 0, preflight
    target = packet["scope"]["modify"][0]
    good = J.function_source(ORIGIN / "references/raw" / target, "mapping_raw")
    bad = good.replace('decode("utf-8"', 'decode("latin-1"')
    assert bad != good
    S.save(
        root / ".agent/replay.json",
        [
            {"kind": "replacement", "content": bad},
            {"kind": "replacement", "content": good},
        ],
    )
    replay = command(
        [
            *entry,
            "--mode",
            "coder",
            "--replay",
            ".agent/replay.json",
            "--report",
            ".agent/offline-report.json",
        ],
        root,
        timeout=180,
    )
    S.save(BATCH / "replay-process.json", replay)
    assert replay["exit_code"] == 0, replay
    report = S.read(root / ".agent/offline-report.json")
    assert report["status"] == "validation_passed_pending_review"
    actual = report["consolidated_harness"]["actual"]
    assert actual["edits"] == 2 and actual["post_edit_checks"] == 2, actual
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F

    gate = F.load(root / ".local-agents/local-unit.py", "generic_gate_control")
    cfg = S.read(prepared / "config.json")
    gate.verify_handoff(root, report, config=cfg)
    # Preserve the successful exact protected bytes before a deliberate drift.
    test = root / packet["focused_tests"][0]
    preimage = BATCH / "protected-test-preimage"
    preimage.write_bytes(test.read_bytes())
    test.write_bytes(
        test.read_bytes() + b"\n# deliberate postvalidation drift control\n"
    )
    try:
        gate.verify_handoff(root, report, config=cfg)
    except gate.HandoffError as exc:
        denied = {"denied": True, "reason": str(exc), "type": type(exc).__name__}
    else:
        raise AssertionError("Protected drift was accepted")
    S.save(BATCH / "protected-drift.json", denied)
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_OFFLINE_ONLY",
            "model_calls": 0,
            "actual": actual,
            "live_qualified": False,
            "production_acceptance": False,
            "protected_drift": denied,
            "warning": "Workspace intentionally stale after positive archival; not a current acceptable task",
        },
    )
    print(
        "PASS generic preparation+real failed draft/repair/checks+canonical gate+protected drift;0 model"
    )


if __name__ == "__main__":
    main()
