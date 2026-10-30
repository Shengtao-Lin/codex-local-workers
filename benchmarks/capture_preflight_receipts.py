"""Register the narrow early capture-binding guard, separate from closed batches."""

import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/capture-preflight-20261022-1"
FILES = [
    ".local-agents/local-bounded-unit.py",
    ".local-agents/bounded/capture_fixture_support.py",
    ".local-agents/README.md",
]


def main():
    pins = {}
    for name in FILES:
        target = BATCH / "preimages" / name
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(S.KIT / name, target)
        pins[name] = S.sha(target)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "early-capture-compatibility",
            "feature_risk": "high",
            "integration_risk": "high",
            "unit_id": "reuse-authentication-before-model-load",
            "unit_risk": "high",
            "owned_contract_ids": [
                "same-policy-guard",
                "reject-before-model",
                "no-acceptance-credit",
            ],
            "dependencies": ["host-preflight-20261022-1"],
            "rationale": "Preflight must reuse final canonical policy checks without allowing new sources, edits or acceptance.",
            "hypothesis": "Known invalid target/protection/interpreter/policy material currently survives preflight and can waste model work before final rejection.",
            "candidate": "Reuse installed reviewer_canonical_capture.policy_material via read-only Worker view before any role lease; retain final checks unchanged.",
            "checks": [
                "Five malformed-material controls plus unchanged valid control through installed CLI",
                "Scripted HTTP trap confirms invalid live invocation makes no readiness/model request",
                "Existing installed full chains and current complete runtime controls",
            ],
            "preimages": pins,
            "prior_baseline": "../host-preflight-20261022-1/baseline.json",
            "live_registered": 0,
            "unchanged": [
                "models",
                "default configs",
                "Worker budgets",
                "scope",
                "semantic rules",
                "final handoff",
                "old outcomes",
            ],
            "weekly_stop": None,
            "stop": "Deterministic controls and independent diff review; no new task-family qualification",
            "sibling_repositories": "read-only",
            "commit_push": False,
        },
    )
    print("Capture preflight follow-up registered; zero live units")


def close():
    previous = BATCH.parent / "host-preflight-20261022-1"
    original = S.read(previous / "baseline.json")
    registration = S.read(BATCH / "registration.json")
    allowed = set(FILES) | {
        ".local-agents/local-bounded-review.py",
        ".local-agents/tests/test_coordinator_supervised.py",
    }
    changed = {p for p, sha in original["preimages"].items() if S.sha(S.KIT / p) != sha}
    caches = {p for p in changed if "/.ruff_cache/" in p}
    assert changed - caches <= allowed, changed - caches - allowed
    assert all(
        S.sha(previous / "preimages" / p) == sha
        for p, sha in original["preimages"].items()
    )
    assert all(
        S.sha(BATCH / "preimages" / p) == sha
        for p, sha in registration["preimages"].items()
    )
    head = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
        .decode()
        .strip()
    )
    assert head == original["head"]
    checks = {}
    for name in ("red.xml", "green.xml", "full-regression.xml"):
        suites = ET.parse(BATCH / name).getroot().findall("testsuite")
        checks[name] = {
            key: sum(int(s.get(key, "0")) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        checks[name]["seconds"] = sum(float(s.get("time", "0")) for s in suites)
    for name in ("green.xml", "full-regression.xml"):
        assert checks[name]["tests"] > 0
        assert not any(checks[name][key] for key in ("failures", "errors", "skipped"))
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_EARLY_CAPTURE_COMPATIBILITY",
            "checks": checks,
            "red_interpretation": "Five previously accepted incompatible policies; one premature residency GET; valid control lacked newly specified diagnostic field. Seven red assertions, not seven runtime/model failures.",
            "green_interpretation": "Five invalid materials rejected without model work; valid packet remains accepted. Final suite also tests both coder and unit entry and no Reviewer dispatch.",
            "overlap": "Focused green and full regression overlap; do not add denominators.",
            "live_registered": 0,
            "live_model_calls": 0,
            "boundary": "No policy weakening, prompt/schema/model/repair-budget change; no new task-family or general production qualification.",
            "limitations": [
                "Static preflight validates declared material; transitive import completeness and executable checks still require offline replay.",
                "Existing constructor errors can still fail closed before this structured preflight branch.",
                "Model semantic recovery and Reviewer unknown defect detection remain independent unresolved limits.",
            ],
            "weekly_used_observed": 38,
            "weekly_stop": None,
        },
    )
    S.save(
        BATCH / "preservation.json",
        {
            "head_unchanged": head,
            "both_stage_preimages_intact": True,
            "changed_current_files": {
                p: S.sha(S.KIT / p) for p in sorted(changed - caches)
            },
            "tool_cache_changes": {p: S.sha(S.KIT / p) for p in sorted(caches)},
            "default_configs_unchanged": True,
            "other_preexisting_runtime_files_unchanged": True,
            "test_sources": {
                name: S.sha(S.KIT / name)
                for name in (
                    "tests/test_bounded_capture_preflight.py",
                    "tests/test_bounded_review_inspection.py",
                )
            },
            "sibling_repositories": "read-only; no writes issued",
            "commit_push": False,
        },
    )
    print(checks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("freeze", "close"), nargs="?", default="freeze"
    )
    (main if parser.parse_args().mode == "freeze" else close)()
