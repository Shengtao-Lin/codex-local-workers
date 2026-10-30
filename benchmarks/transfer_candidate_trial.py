"""One frozen async sentinel unit under the unchanged supervised runtime."""

import argparse
import asyncio
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import mixed_feature_benchmark as mixed
from capability_fit import WORK, freeze, write
from inherited_context_recovery import digest, read
from normal_unit_candidate_trial import verify_candidate
from supervised_scope_check import invoke

BASE = WORK / "transfer-candidate-1"
SNAPSHOT = WORK / "transfer-candidate-runtime-1"
ORIGINAL = WORK / "supervised-scope-1"


def prepare():
    verify_candidate()
    BASE.mkdir(exist_ok=False)
    freeze(SNAPSHOT.name)
    mixed.CORPUS, mixed.WORK = ORIGINAL / "corpus.json", BASE / "runs"
    config = WORK / "normal-unit-candidate-1/candidate/.agent/config.json"
    root = Path(mixed.prepare("async-stop", 1, config, "transfercand")["root"])
    packet = read(root / ".agent/qual-unit-reference.json")
    prior_cell = next(
        c
        for c in read(ORIGINAL / "manifest.json")["cells"]
        if c["id"] == "async-stop-r1"
    )
    prior = read(Path(prior_cell["root"]) / ".agent/qual-unit-reference.json")
    for field in (
        "goal",
        "risk",
        "scope",
        "focused_tests",
        "required_behavior",
        "acceptance_scenarios",
        "validation_profile",
        "owned_contract_ids",
        "edit_targets",
    ):
        assert packet[field] == prior[field], field
    for path, sha in prior_cell["hashes"].items():
        if not path.startswith(".agent/"):
            assert digest(root / path) == sha, path
    for path, sha in read(WORK / "noop-primary-complete-1/freeze.json")[
        "files"
    ].items():
        assert digest(SNAPSHOT / path) == sha, path
    write(
        BASE / "registration.json",
        {
            "root": str(root),
            "identity": {k: packet[k] for k in ("task_id", "unit_id", "run_id")},
            "fixture": str(ORIGINAL / "corpus.json"),
            "fixture_sha256": digest(ORIGINAL / "corpus.json"),
            "frozen_initial_hashes": prior_cell["hashes"],
            "packet_sha256": digest(root / ".agent/qual-unit-reference.json"),
            "config_sha256": digest(root / ".agent/config.json"),
            "driver_sha256": digest(Path(__file__)),
            "gate": "One Coder -> automatic Reviewer -> independent focused/static/entry-call validation -> Primary decision. No retry, contract/test/prompt edits or reclassification.",
            "attempts": 1,
            "new_semantic_cases": 0,
            "coordinator_enabled": False,
            "explorer_credit": False,
            "explorer_reason": "Definition/caller/acceptance already read; no unanswered localization investigation.",
            "classification": "Previously exposed Primary-authored frozen async unit; near transfer, not real-project or unseen-task evidence",
            "weekly_used_ceiling": 50,
        },
    )
    shutil.copy2(Path(__file__), BASE / "registered-driver.py")
    result = invoke(
        root,
        "transfer-before",
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "--junitxml=.agent/transfer-before.xml",
        ],
    )
    assert result["exit"] == 1, result
    print(json.dumps({"root": str(root), "preflight": result}, indent=2))


def verify():
    verify_candidate()
    registration = read(BASE / "registration.json")
    assert digest(BASE / "registered-driver.py") == registration["driver_sha256"]
    assert digest(Path(registration["fixture"])) == registration["fixture_sha256"]
    root = Path(registration["root"])
    assert digest(root / ".agent/config.json") == registration["config_sha256"]
    assert (
        digest(root / ".agent/qual-unit-reference.json")
        == registration["packet_sha256"]
    )
    for path, sha in registration["frozen_initial_hashes"].items():
        if not path.startswith(".agent/") and path != "src/product/target.py":
            assert digest(root / path) == sha, path
    return registration, root


def run():
    registration, root = verify()
    assert digest(Path(__file__)) == registration["driver_sha256"]
    result = invoke(
        root,
        "transfer-live-unit",
        [
            sys.executable,
            "-B",
            str(SNAPSHOT / ".local-agents/local-unit.py"),
            "--packet",
            str(root / ".agent/qual-unit-reference.json"),
            "--config",
            str(root / ".agent/config.json"),
            "--coder-report",
            str(root / ".agent/coder.json"),
            "--review-report",
            str(root / ".agent/reviewer.json"),
        ],
    )
    print(json.dumps(result, indent=2))


def audit():
    _registration, root = verify()
    coder, reviewer = (
        read(root / ".agent/coder.json"),
        read(root / ".agent/reviewer.json"),
    )
    assert coder["status"] == "ready_for_review"
    assert reviewer["decision"] == "pass_to_primary"
    assert coder["validation_summary"]["executed"] == 2
    assert coder["validation_summary"]["inputs_unchanged"]
    assert [x["path"] for x in coder["changed_files"]] == ["src/product/target.py"]
    assert set(reviewer["verified_check_ids"]) == {"ruff-format", "ruff-check"}
    assert reviewer["runtime_facts"]["inputs_unchanged"]
    assert set(reviewer["runtime_facts"]["read_paths"]) >= {
        "src/product/target.py",
        "tests/test_target.py",
    }
    for name, argv in (
        (
            "transfer-primary-tests",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "-q",
                "--junitxml=.agent/primary-regression.xml",
            ],
        ),
        (
            "transfer-primary-lint",
            [sys.executable, "-B", "-m", "ruff", "check", "src", "tests"],
        ),
        (
            "transfer-primary-format",
            [sys.executable, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
        ),
    ):
        result = invoke(root, name, argv)
        assert result["exit"] == 0, result
    # Independent integration observation of the frozen public entry point.
    sys.path.insert(0, str(root / "src"))
    spec = importlib.util.spec_from_file_location(
        "transfer_entry", root / "src/product/entry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls, keys = [], [0, 1, 2, 3, 4]
    values = [0, False, "", None, 99]

    async def fetch(key):
        calls.append(key)
        return values[key]

    actual = asyncio.run(module.read_batch(fetch, keys))
    assert actual == [0, False, ""] and actual[1] is False and actual[0] is not False
    assert calls == [0, 1, 2, 3] and keys == [0, 1, 2, 3, 4]
    write(
        BASE / "audit.json",
        {
            "protected_unchanged": True,
            "entry_call_pass": True,
            "entry_values": actual,
            "entry_calls": calls,
            "coder_status": coder["status"],
            "reviewer_decision": reviewer["decision"],
            "reviewer_protocol_errors": reviewer["runtime_facts"][
                "protocol_error_count"
            ],
            "local_unit_seconds": read(
                root / ".agent/transfer-live-unit-invocation.json"
            )["seconds"],
            "formal_semantic_release": "HOLD",
            "cloud_tokens": None,
            "primary_active_seconds": None,
        },
    )
    print(json.dumps(read(BASE / "audit.json"), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    args = parser.parse_args()
    globals()[args.action]()
