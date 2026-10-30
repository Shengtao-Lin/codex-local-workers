"""Finish pending offline gate controls; do not rerun successful host cases."""

import copy
import shutil
import sys
from pathlib import Path

import bounded_evidence_support as S
import project_caller_trial as J

BATCH = S.KIT / "benchmarks/work/harness-convergence/strata-bridge-gates-20261023-1"
PRIOR = BATCH.parent / "strata-bridge-host-20261023-2"


def main():
    assert not BATCH.exists(), "Create-only continuation"
    root = PRIOR / "read-edit-check/isolated"
    previous = S.read(PRIOR / "independent-checks.json")
    assert all(c["exit_code"] == 0 for c in previous[:3])
    assert previous[3]["exit_code"] != 0 and "--pythonpath" not in previous[3]["argv"]
    S.save(
        BATCH / "registration.json",
        {
            "type": "offline_pending_controls_only",
            "provider_calls": 0,
            "weekly_used_start": 34,
            "weekly_cap": 40,
            "reuse": "Prior same-version pytest164/Ruff format/lint and4 native-host cases; original Pyright invocation failure remains",
            "checks": [
                "Pyright with trusted interpreter",
                "canonical checks missing",
                "zero tests",
                "protected drift",
            ],
            "explicit_mutation": "Append diagnostic comment to prior isolated positive workspace public test ONLY after final checks, retaining original bytes and all canonical reports; deliberately makes live workspace stale",
        },
    )
    # Preserve current preparation/bridge source versions, not just their hashes.
    for name in [
        "strata_bridge_gate_controls.py",
        "strata_bridge_host.py",
        "strata_bridge_host_controls.py",
        "strata_native_replay.mjs",
        "strata_kit_tool_bridge.mjs",
    ]:
        output = BATCH / "candidate-source" / name
        output.parent.mkdir(parents=True, exist_ok=True)
        assert not output.exists()
        shutil.copyfile(Path(__file__).with_name(name), output)
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F

    gate = F.load(root / ".local-agents/local-unit.py", "bridge_tail_gate")
    report = S.read(root / ".agent/native-host-report.json")
    config = S.read(root / ".agent/prepared" / report["run_id"] / "config.json")
    gate.verify_handoff(root, report, config=config)
    result = J.run_check(
        [S.PYTHON, "-B", "-m", "pyright", "--pythonpath", S.PYTHON], root
    )
    S.save(BATCH / "pyright-corrected.json", result)
    assert result["exit_code"] == 0, result
    gate.verify_handoff(root, report, config=config)
    summary = copy.deepcopy(report)
    summary["validation"]["configured_checks"] = []
    gate.verify_handoff(root, summary, config=config)
    S.save(
        BATCH / "convenience-control.json",
        {
            "status": "PASS",
            "meaning": "Ignored changed summary; acceptance still bound to valid unchanged canonical facts",
        },
    )
    archive = root / ".agent/tasks" / report["task_id"] / "runs" / report["run_id"]
    packet = S.read(archive / "packet.json")
    handoff = S.read(archive / "handoff.json")
    validation = S.read(archive / "validation.json")
    negatives = []
    for case in ("missing_configured_checks", "zero_tests"):
        bad = copy.deepcopy(validation)
        if case == "missing_configured_checks":
            bad["configured_checks"] = []
        else:
            bad["focused_tests"]["junit"]["executed"] = 0
        try:
            gate.HOST.verify(root, archive, packet, handoff, bad, config)
        except (ValueError, RuntimeError) as exc:
            negatives.append(
                {
                    "case": case,
                    "reason": str(exc),
                    "kind": "direct canonical verifier argument negative, archive NOT changed",
                }
            )
        assert len(negatives) == (1 if case == "missing_configured_checks" else 2)
    protected = root / "tests/unit/test_local_worker_raw.py"
    shutil.copyfile(protected, BATCH / "protected-test-preimage.py")
    before_sha = S.sha(protected)
    with protected.open("a", encoding="utf-8") as stream:
        stream.write("\n# Offline post-validation drift negative control\n")
    try:
        gate.verify_handoff(root, report, config=config)
    except (ValueError, RuntimeError) as exc:
        negatives.append(
            {
                "case": "real_post_validation_drift",
                "reason": str(exc),
                "preimage_sha256": before_sha,
                "current_sha256": S.sha(protected),
            }
        )
    assert len(negatives) == 3
    S.save(BATCH / "gate-negatives.json", negatives)
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_OFFLINE_REAL_HOST_BRIDGE_AND_GATES",
            "native_host_cases_reused": 4,
            "canonical_negatives": 3,
            "same_version_full_project_tests": "164 passed, previous independent-checks.json",
            "static_checks": "Ruff format/lint reused; corrected Pyright0 errors",
            "provider_calls": 0,
            "production_acceptance": False,
            "protected_drift": "Intentional only after valid checks in prior isolated control workspace; canonical and independent evidence preserved, CURRENT workspace is now stale and may NOT be accepted",
            "prior_failures": "Control specification and independent Pyright invocation errors remain in prior batches; no reruns overwrite results",
            "pending": "No native Agent/SDK/model route, generic profile, multi-file/test authoring, skills/Web or cross-attempt budget qualification",
        },
    )
    print("PASS real host bridge + canonical controls; zero provider calls")


if __name__ == "__main__":
    main()
