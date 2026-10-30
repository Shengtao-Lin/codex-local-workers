"""Register/close offline scheduling controls; deliberately no live command."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import output_channel_trial as O

T = O.T
BATCH = (
    T.KIT
    / "benchmarks/work/harness-convergence/prevalidation-format-offline-20261018-1"
)


def prepare():
    BATCH.mkdir(exist_ok=False)
    old_pins = T.read(O.BATCH / "freeze.json")["pins"]
    assert all(T.sha(p) == sha for p, sha in old_pins.items())
    files = set(
        T.git("ls-files", "-m", "-o", "--exclude-standard", "-z").split("\0")
    ) - {""}
    T.save(
        BATCH / "baseline.json",
        {
            "head": T.git("rev-parse", "HEAD").strip(),
            "files": {
                p: T.sha(T.KIT / p) for p in sorted(files) if (T.KIT / p).is_file()
            },
        },
    )
    T.save(
        BATCH / "registration.json",
        {
            "scope": "Offline scheduling implementation/replay only; no new live authorization inferred",
            "feature_id": "prevalidation-format-scheduling",
            "risk": "high",
            "risk_rationale": "Validation epoch, acceptance and execution budget are trust boundaries",
            "owned_contract_ids": [
                "validation-currentness",
                "scope-preservation",
                "bounded-execution",
            ],
            "dependencies": ["frozen-constrained-whole-function-output"],
            "models": "unchanged, none called",
            "weekly_used_start": 2,
            "weekly_used_ceiling": 15,
            "budget": {
                "requests": 6,
                "counted_validation_attempts": 3,
                "model_edits": 3,
                "formatter_commands": 1,
                "seconds": 900,
            },
            "change": "Move existing eligible whitespace formatting before counted post-edit validation. Preserve failed drafts in proposal/archive plus a separate preparation receipt. No counter refunds, no suppressed validation, no relaxed acceptance.",
            "criterion": "Frozen old loop reproduces failure. New scripted loop exposes the exact type failure before a second scripted proposal and accepts only after fresh full validation and original canonical gate. Reject changed source/protected input, semantic formatter changes, stale hash and signature changes. Enforce same caps.",
            "production_changes": False,
            "live_calls": 0,
            "interpretation": "More useful checks within the same ceiling is not proof of fewer actual subprocesses than the previous failed run; compare actual costs explicitly. Scripted gold repair proves scheduling only, not model capability.",
        },
    )


def close():
    tree = ET.parse(BATCH / "controls-v2.xml")
    tests = tree.findall(".//testcase")
    assert tests and not any(
        tree.findall(".//" + k) for k in ("failure", "error", "skipped")
    )
    semantic = ET.parse(BATCH / "format-semantic-negative.xml")
    assert len(semantic.findall(".//testcase")) == 1
    assert not any(semantic.findall(".//" + k) for k in ("failure", "error", "skipped"))
    baseline = T.read(BATCH / "baseline.json")
    permitted = {
        "benchmarks/prevalidation_format_audit.py",
        "benchmarks/coder_prevalidation_format.py",
        "tests/test_prevalidation_format.py",
        "docs/local-model-harness-convergence-plan.md",
    }
    drift = [
        p
        for p, sha in baseline["files"].items()
        if p not in permitted and T.sha(T.KIT / p) != sha
    ]
    old_pins = T.read(O.BATCH / "freeze.json")["pins"]
    assert not drift
    assert all(T.sha(p) == sha for p, sha in old_pins.items())
    extra = [
        Path(__file__),
        T.KIT / "benchmarks/coder_prevalidation_format.py",
        T.KIT / "tests/test_prevalidation_format.py",
        BATCH / "registration.json",
        BATCH / "controls-v2.xml",
        BATCH / "format-semantic-negative.xml",
    ]
    T.save(
        BATCH / "freeze.json",
        {"pins": {**old_pins, **{str(p): T.sha(p) for p in extra}}},
    )
    T.save(
        BATCH / "preservation.json",
        {
            "inherited_drift": drift,
            "old_pins_unchanged": True,
            "production_changes": False,
            "siblings": "read-only",
            "live_calls": 0,
        },
    )
    T.save(
        BATCH / "decision.json",
        {
            "status": "PASS_OFFLINE_SCHEDULING_ONLY",
            "tests": len(tests) + 1,
            "live_calls": 0,
            "model_repair_capability": "unmeasured",
            "product_release": False,
            "goal_complete": False,
            "live_requires_separate_registration": True,
            "next_action": "Use only schema arm in a separately authorized/frozen scheduling comparison; retain all prior failures and original budgets. No fresh-transfer credit for exposed metadata.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "close"])
    {"prepare": prepare, "close": close}[parser.parse_args().action]()
