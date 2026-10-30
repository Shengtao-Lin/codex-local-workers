"""One isolated additive feature on provenance-checked real adapter modules."""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import KIT, WORK, freeze, write
from inherited_context_recovery import digest, read

BASE = WORK / "reviewer-real-unit-1"
ROOT = BASE / "candidate"
SNAPSHOT = WORK / "reviewer-real-unit-runtime-1"
FROZEN = KIT / "benchmarks/fixtures/real-adapter-datetime-v3"
SOURCE = "src/evaluation_harness/adapters/common.py"
EXTRA = "tests/test_timestamp_whitespace_trial.py"
TASK = "reviewer-real-unit-1"


def invoke(name, argv):
    started = time.monotonic()
    p = subprocess.run(
        argv,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1500,
        check=False,
    )
    result = {
        "exit": p.returncode,
        "seconds": time.monotonic() - started,
        "output": p.stdout + p.stderr,
    }
    write(BASE / f"{name}.json", result)
    return result


def prepare():
    started = time.monotonic()
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    provenance = read(FROZEN / "provenance.json")
    paths = provenance["copied_original_files"].copy()
    paths[provenance["primary_added_test"]["path"]] = provenance["primary_added_test"][
        "sha256"
    ]
    for path, sha in paths.items():
        assert digest(FROZEN / path) == sha, path
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FROZEN / path, target)
    added = (
        KIT
        / "benchmarks/fixtures/real-adapter-datetime-extra/test_timestamp_whitespace_trial.py"
    )
    if TASK.endswith("-2"):
        added = added.with_name("test_timestamp_whitespace_trial_v2.py")
    shutil.copy2(added, ROOT / EXTRA)
    paths[EXTRA] = digest(added)
    config = read(
        WORK / "reviewer-live-rework-1/display-default-b-r1/.agent/config.json"
    )
    config["coordinator_enabled"] = False
    config["validation_profiles"]["mixed-strict"]["commands"].append(
        {
            "id": "pyright",
            "argv": ["{python}", "-m", "pyright", "--pythonpath", "{python}", "src"],
        }
    )
    write(ROOT / ".agent/config.json", config)
    packet = read(
        WORK / "real-adapter-live-2/candidate/.agent/normalize-unit-bound.json"
    )
    contract = (
        "Extend only private _datetime timestamp-string normalization to ignore leading and trailing "
        "Python whitespace before existing ISO parsing. Padded Z, naive and +05:30 strings must produce "
        "the same datetime as their unpadded form; preserve aware offset/wall time, parsed naive UTC, "
        "and existing datetime identity (including naive objects). Empty, whitespace-only, invalid and "
        "invalid-calendar strings still raise ValueError, never return default. Non-string/non-datetime "
        "inputs return default by identity. Do not remove internal characters or broaden accepted "
        "timestamp syntax beyond outer whitespace. GenericOtelAdapter trace/turn normalization of padded "
        "timestamps must match unpadded canonical samples including IDs, message/tool contents, runtime "
        "and JSON event_time roundtrip, without mutating input. No other semantic changes, dependency "
        "changes, adapter version changes or test edits."
    )
    if TASK.endswith("-2"):
        contract = (
            contract.replace(
                "timestamps must match unpadded canonical samples including IDs, message/tool contents, runtime ",
                "timestamps must match unpadded canonical samples except raw source_metadata.event_time, including IDs, message/tool contents, runtime ",
            )
            + " Preserve source_metadata.event_time as the exact original padded input string; other source_metadata entries remain equal. Primary explicitly revises erroneous whole-sample equality from experiment 1; do not normalize raw source evidence."
        )
    packet.update(
        schema_version=2,
        task_id=TASK,
        feature_id=TASK,
        unit_id="timestamp-unit",
        run_id=TASK + "-timestamp-unit-a1",
        attempt=1,
        plan_revision=1,
        packet_revision=1,
        goal=contract,
        dependencies=[],
        owned_contract_ids=["timestamp-unit"],
        risk={
            "feature": "high",
            "unit": "high",
            "integration": "high",
            "reasons": [
                "New accepted input form reaches public adapter normalization; preserve compatibility and sample identity."
            ],
        },
        required_behavior=[
            {"id": "timestamp-unit", "risk_floor": "high", "text": contract}
        ],
        scope={
            "read": ["src", "tests"],
            "modify": [SOURCE],
            "create": [],
            "readonly": [
                p for p in paths if p.startswith(("src/", "tests/")) and p != SOURCE
            ],
            "forbidden": [".git", ".agent", ".local-agents"],
        },
        edit_targets=[{"path": SOURCE, "anchor": "_datetime", "line_hint": 251}],
        focused_tests=[
            EXTRA,
            "tests/test_datetime_trial.py",
            "tests/unit/test_adapters.py",
        ],
        supplemental_tests=[],
        required_order=[],
        forbidden_orderings=[],
        implementation_guidance=[],
        review_feedback=[],
        acceptance_scenarios=[
            {
                "id": "normal",
                "text": "Padded ISO strings match unpadded; adapter trace/turn roundtrip preserves samples.",
                "observables": {"offset_minutes": 330, "input_unchanged": True},
            },
            {
                "id": "error",
                "text": "Invalid padded/calendar/whitespace-only strings raise ValueError, never default.",
                "observables": {"error": "ValueError"},
            },
            {
                "id": "boundary",
                "text": "Datetime and fallback identity remain unchanged; no internal character removal.",
                "observables": {"identity_preserved": True},
            },
        ],
    )
    write(ROOT / ".agent/packet.json", packet)
    write(
        BASE / "registration.json",
        {
            "feature_id": TASK,
            "risk": packet["risk"],
            "owned_contract_ids": ["timestamp-unit"],
            "dependencies": [],
            "root": str(ROOT),
            "fixture": str(FROZEN),
            "paths": paths,
            "config_sha256": digest(ROOT / ".agent/config.json"),
            "packet_sha256": digest(ROOT / ".agent/packet.json"),
            "driver_sha256": digest(Path(__file__)),
            "trial_only_not_sibling_feature_request": True,
            "coordinator_enabled": False,
            "explorer": "Not invoked: helper/caller/test locations already independently read; no meaningful unanswered localization question.",
            "attempts": 1,
            "gate": "Current-input validation, automatic independent Reviewer pass, full high-risk Primary diff and broader regressions; no forced rework or acceptance override.",
            "preparation_script_seconds": time.monotonic() - started,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "phase_time_note": "Command durations and preparation-script time measured; agent active reasoning time and direct-Primary comparator not instrumented, no savings claim.",
        },
    )
    legacy = invoke(
        "legacy-baseline",
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "tests/test_datetime_trial.py",
            "tests/unit/test_adapters.py",
            "-q",
            "--junitxml=.agent/legacy-baseline.xml",
        ],
    )
    assert legacy["exit"] == 0, legacy
    feature = invoke(
        "feature-before",
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            EXTRA,
            "-q",
            "--junitxml=.agent/feature-before.xml",
        ],
    )
    assert feature["exit"] == 1, feature
    static = invoke(
        "static-before",
        [sys.executable, "-B", "-m", "pyright", "--pythonpath", sys.executable, "src"],
    )
    assert static["exit"] == 0, static
    print(
        json.dumps(
            {"ready": True, "legacy": legacy, "feature": feature, "static": static},
            indent=2,
        )
    )


def run():
    registration = read(BASE / "registration.json")
    assert digest(Path(__file__)) == registration["driver_sha256"]
    for path, sha in registration["paths"].items():
        assert digest(ROOT / path) == sha, path
    result = invoke(
        "live-unit",
        [
            sys.executable,
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(ROOT / ".agent/packet.json"),
            "--config",
            str(ROOT / ".agent/config.json"),
            "--coder-report",
            str(ROOT / ".agent/coder.json"),
            "--review-report",
            str(ROOT / ".agent/reviewer.json"),
        ],
    )
    print(json.dumps(result, indent=2))


def audit():
    registration = read(BASE / "registration.json")
    assert digest(BASE / "registered-driver.py") == registration["driver_sha256"]
    for path, sha in registration["paths"].items():
        if path != SOURCE:
            assert digest(ROOT / path) == sha, path
    assert digest(ROOT / ".agent/config.json") == registration["config_sha256"]
    assert digest(ROOT / ".agent/packet.json") == registration["packet_sha256"]
    for path, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        assert digest(SNAPSHOT / path) == sha, path
    for path, sha in read(FROZEN / "provenance.json")["copied_original_files"].items():
        assert digest(FROZEN / path) == sha, path
    before = (FROZEN / SOURCE).read_text(encoding="utf-8")
    after = (ROOT / SOURCE).read_text(encoding="utf-8")
    assert after == before.replace(
        'value.replace("Z", "+00:00")', 'value.strip().replace("Z", "+00:00")'
    )
    coder, reviewer = (
        read(ROOT / ".agent/coder.json"),
        read(ROOT / ".agent/reviewer.json"),
    )
    assert coder["status"] == "ready_for_review"
    assert coder["validation_summary"]["executed"] == 21
    assert coder["validation_summary"]["inputs_unchanged"]
    assert all(
        c["status"] == "passed"
        for c in coder["validation_summary"]["configured_checks"]
    )
    assert reviewer["runtime_facts"]["inputs_unchanged"]
    assert reviewer["runtime_facts"]["observed_read_hashes"][SOURCE] == digest(
        ROOT / SOURCE
    )
    assert reviewer["runtime_facts"]["observed_read_hashes"][EXTRA] == digest(
        ROOT / EXTRA
    )
    assert set(reviewer["verified_check_ids"]) == {
        "ruff-format",
        "ruff-check",
        "pyright",
    }
    primary_commands = [
        (
            "primary-tests",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "-q",
                "--junitxml=.agent/primary-regression-audit.xml",
            ],
        ),
        ("primary-lint", [sys.executable, "-B", "-m", "ruff", "check", "src", "tests"]),
        (
            "primary-format",
            [sys.executable, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
        ),
        (
            "primary-types",
            [
                sys.executable,
                "-B",
                "-m",
                "pyright",
                "--pythonpath",
                sys.executable,
                "src",
            ],
        ),
    ]
    for name, argv in primary_commands:
        result = invoke(name, argv)
        assert result["exit"] == 0, result
    write(
        BASE / "audit.json",
        {
            "protected_unchanged": True,
            "original_fixture_unchanged": True,
            "only_source_change": "Outer whitespace stripping in existing private helper",
            "coder_validation": coder["validation_summary"],
            "reviewer_decision": reviewer["decision"],
            "reviewer_protocol_errors": reviewer["runtime_facts"][
                "protocol_error_count"
            ],
            "local_unit_seconds": read(BASE / "live-unit.json")["seconds"],
            "source_sha256": digest(ROOT / SOURCE),
            "audit_driver_sha256": digest(Path(__file__)),
            "formal_semantic_release": "HOLD",
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "direct_primary_comparison": "Not measured; do not claim coordination savings",
        },
    )
    print(json.dumps(read(BASE / "audit.json"), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    parser.add_argument("--revision", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    if args.revision == 2:
        BASE = WORK / "reviewer-real-unit-2"
        ROOT = BASE / "candidate"
        SNAPSHOT = WORK / "reviewer-real-unit-runtime-2"
        TASK = "reviewer-real-unit-2"
    globals()[args.action]()
