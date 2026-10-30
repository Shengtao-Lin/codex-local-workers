"""Independent offline transport stage. Generated records are append-only."""

import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
BATCH = KIT / "benchmarks/work/harness-convergence/capture-transport-20261017-2"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=KIT).decode("utf-8")


def prepare(used):
    if not 0 <= used < 15:
        raise ValueError("weekly ceiling reached")
    paths = set(git("ls-files", "-m", "-o", "--exclude-standard", "-z").split("\0")) - {
        ""
    }
    files = {p: sha(KIT / p) for p in sorted(paths) if (KIT / p).is_file()}
    save(
        BATCH / "baseline.json",
        {
            "head": git("rev-parse", "HEAD").strip(),
            "branch": git("branch", "--show-current").strip(),
            "status": git("status", "--short"),
            "files": files,
            "tracked_diff_sha256": hashlib.sha256(
                git("diff", "--binary").encode()
            ).hexdigest(),
            "weekly_used": used,
        },
    )
    register(used)


def close(used):
    for name in ("combined-v2.xml", "engine-parity-v1.xml"):
        tree = ET.parse(BATCH / name)
        assert tree.findall(".//testcase") and not any(
            tree.findall(".//" + k) for k in ("failure", "error", "skipped")
        )
    previous = (
        KIT
        / "benchmarks/work/harness-convergence/r4-contract-first-20261017-1/live-freeze.json"
    )
    old_pins = read(previous)["pins"]
    assert all(sha(Path(path)) == value for path, value in old_pins.items())
    baseline = read(BATCH / "baseline.json")
    permitted = {
        "benchmarks/harness_capture_transport.py",
        "docs/local-model-harness-convergence-plan.md",
    }
    drift = [
        p
        for p, value in baseline["files"].items()
        if p not in permitted and (not (KIT / p).is_file() or sha(KIT / p) != value)
    ]
    assert not drift, drift
    sources = [
        "benchmarks/" + name
        for name in (
            "capture_validation_facts.py",
            "reviewer_canonical_capture.py",
            "capture_fixture_support.py",
            "reviewer_capture_entry.py",
            "reviewer_capture_envelope.py",
            "harness_capture_transport.py",
        )
    ]
    sources += [
        "tests/" + name
        for name in (
            "test_canonical_capture_transport.py",
            "test_capture_legacy_parity.py",
            "test_capture_policy_boundaries.py",
        )
    ]
    save(
        BATCH / "freeze.json",
        {
            "pins": {**old_pins, **{str(KIT / p): sha(KIT / p) for p in sources}},
            "registration_sha256": sha(BATCH / "registration.json"),
            "model_calls": 0,
        },
    )
    save(
        BATCH / "preservation.json",
        {
            "existing_worktree_drift": drift,
            "frozen_semantic_candidate_unchanged": True,
            "old_results_unchanged": True,
            "sibling_writes": False,
            "commit_push": False,
        },
    )
    save(
        BATCH / "decision.json",
        {
            "stage": "Offline canonical observation transport",
            "qualification": "PASS_OFFLINE_COMPONENT",
            "model_calls": 0,
            "weekly_used_start": baseline["weekly_used"],
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "tests": {
                name: len(ET.parse(BATCH / name).findall(".//testcase"))
                for name in ("combined-v2.xml", "engine-parity-v1.xml")
            },
            "initial_failures_retained": [
                "entry-v1.xml: missing pre-existing assessment/evidence-ID fixture flags; corrected before live",
                "initial lint: B023 closure binding and unused test variable; corrected before live",
            ],
            "evidence": [
                "Real Coder command and canonical archive, original handoff gate, actual non-skipped JUnit, interpreter/producer/profile/source epoch bindings",
                "Real producer factual outputs equal all20 old profiles, with JSON type-sensitive comparison",
                "All20 full semantic bundle composition equality with explicitly stubbed provider; authentic entry verified separately, not a fake canonical upgrade",
                "Opt-in subprocess installed entry, typed input preservation and after-bundle drift rejection",
            ],
            "limits": [
                "No new live/holdout/full-chain capability credit",
                "Trusted local repo, not OS sandbox or malicious-host signing",
                "Fixed interpreter dependency environment, explicit local Python manifests not exhaustive third-party lockfile attestation",
                "No production/handoff edits or default enablement",
            ],
            "next": "Register and freeze a fresh three-task two-repeat two-arm complete-chain matrix; same unchanged qualified Reviewer and capture preparation for both arms; do not relabel old None slice as fresh.",
            "r4_passed": False,
        },
    )


def register(used):
    save(
        BATCH / "registration.json",
        {
            "feature_id": "validated-observation-transport",
            "unit_id": "canonical-provider",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "risk_rationale": "Incorrect provenance could feed stale or invented facts to review. No production integration until negative controls and actual canonical replay pass.",
            "owned_contract_ids": [
                "canonical-epoch",
                "trusted-capture-producer",
                "lossless-factual-dto",
                "legacy-input-parity",
            ],
            "weekly_used_start": used,
            "weekly_used_ceiling": 15,
            "models": {
                "reviewer": "meta/muse-glimmer",
                "coder": "qwen/qwen3-coder-30b",
                "explorer": "openai/gpt-oss-20b",
            },
            "single_residency": True,
            "live_calls_registered": 0,
            "production_changes": False,
            "commit_push": False,
            "siblings": "read-only",
            "criterion": "Offline authentic canonical consumer, rejection controls, lossless old20 parity and installed entry smoke before registering any new live. Do not modify the frozen semantic candidate or old batches.",
            "scope": [
                "benchmarks/",
                "tests/",
                "docs/local-model-harness-convergence-plan.md",
            ],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", nargs="?", choices=["prepare", "close"], default="prepare"
    )
    parser.add_argument("--used", required=True, type=int)
    args = parser.parse_args()
    (prepare if args.action == "prepare" else close)(args.used)
    print(BATCH)
