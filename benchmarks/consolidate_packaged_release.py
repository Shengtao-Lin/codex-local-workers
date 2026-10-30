"""Finite scoped release decision; do not add overlapping experiment denominators."""

import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import installed_scope_trial as I

BATCH = I.BASE / "packaged-release-20261022-1"


def main(used):
    evidence = {
        "installed_coder_reviewer": ("packaged-profile-live-20261022-1", "PASS_FIXED_INSTALLED_PROFILE_MATRIX"),
        "full_project": ("project-live-20261022-2", "PASS_FIXED_FULL_PACKAGE_PAIR"),
        "reviewer_positive_negative": ("reviewer-profile-screen-20261022-3", "PASS_FIXED_REVIEWER_SCREEN"),
        "explorer_locator": ("explorer-locator-profile-20261022-1", "PASS_SCOPED_INSTALLED_LOCATOR_SCREEN"),
        "snapshot_coordinator": ("packaged-chain-profile-20261022-1", "PASS_PACKAGED_SNAPSHOT_CHAIN"),
    }
    links = {}
    for label, (name, status) in evidence.items():
        path = I.BASE / name / "decision.json"
        assert S.read(path)["status"] == status
        links[label] = {"decision": str(path), "sha256": S.sha(path)}
    original = S.read(I.BASE / "packaged-flat-profile-20261022-1/baseline.json")
    for relative in (".local-agents/config.json", ".local-agents/config.example.json"):
        assert S.sha(S.KIT / relative) == original["preimages"][relative]
    old = ET.parse(I.BASE / "packaged-chain-profile-20261022-1/runtime-regression.xml")
    new = ET.parse(I.BASE / "packaged-chain-profile-20261022-1/fixture-recheck.xml")
    key = lambda c: (c.get("classname"), c.get("name"))
    errors = {key(c) for c in old.iter("testcase") if c.find("error") is not None}
    passed = {key(c) for c in new.iter("testcase") if all(c.find(t) is None for t in ("failure", "error", "skipped"))}
    assert len(errors) == 18 and errors <= passed
    S.save(BATCH / "offline-evidence.json", {
        "whole_runtime_first_attempt": "663 passed,18 setup errors; XML retained",
        "fixture_recheck": "78 passed with existing fixture plugin explicitly preloaded; includes all18 formerly errored cases and60 overlaps. No assertions or source changed.",
        "fixed_setup_errors_verified": len(errors),
        "current_profile_bridge_controls": "57 passed; overlaps other suites, not summed",
        "explorer_and_profile_controls": "104 passed; overlaps other suites, not summed",
        "initial_profile_controls": "44 passed; separate installed-version evidence, not model success",
    })
    production = {str(p.relative_to(S.KIT)): S.sha(p) for p in (S.KIT / ".local-agents").rglob("*.py") if "__pycache__" not in p.parts}
    S.save(BATCH / "candidate.json", {"profile": "Explicit bounded-v1 + flat-v1; API-verified CLI-timeout completion",
           "models": {"Explorer": "openai/gpt-oss-20b", "Coder": "qwen/qwen3-coder-30b", "Reviewer": "meta/muse-glimmer", "Coordinator": "meta/muse-glimmer"},
           "contexts": {"Explorer": 32768, "Coder": 24576, "Reviewer": 24576, "Coordinator": 24576},
           "single_model_residency": True, "default_configs_unchanged": True, "source_sha256": production})
    S.save(BATCH / "decision.json", {
        "status": "PASS_SCOPED_SUPERVISED_TRIAL",
        "general_production": "HOLD",
        "weekly_used_observed": used, "weekly_stop": 60,
        "stop_reason": "Registered scoped product migration and role/integration controls complete. Not budget exhaustion; no open live batch or implicit new benchmark extension.",
        "scope": {"Explorer": "Known paths/symbol anchors, read source-range retrieval only; Primary owns causal judgment",
                  "Coder": "Previously qualified localized single-function transformations with trusted full profile and bounded host repair",
                  "Reviewer": "Fresh source/contract review, same checked acceptance/disposition rules; two explicit defect controls passed, unknown-boundary detection not established",
                  "Coordinator": "Approved known-family plans -> two cohesive dependency units, explicit Primary approval and immutable snapshot transfer only"},
        "not_admitted": ["Arbitrary repository/feature delegation", "Narrative Explorer causal conclusions as trusted evidence", "Unconfirmed automatic Reviewer semantic rework", "Known difficult ASCII semantic repair as qualified family", "Default Coordinator or same-worktree autonomous dependency execution"],
        "evidence": links,
        "failures_preserved": ["Old schema array failures", "ASCII semantic recovery failures", "Reviewer load timeout", "Full-project manifest preparation failure", "Two Reviewer-screen preparation faults", "All failed Explorer narrative investigations and incorrect citation diagnostic"],
        "economic_benefit": "UNKNOWN; Primary still supplied contracts/tests/location/risk, approved decomposition and performed final full reviews; no Primary-only or precise cloud-token comparison",
    })
    print("Scoped supervised trial decision saved; general production remains HOLD")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--weekly-used", type=int, required=True)
    main(p.parse_args().weekly_used)
