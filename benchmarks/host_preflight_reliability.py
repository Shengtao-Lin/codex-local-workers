"""Immutable receipts for deterministic installed-entry repairs; no Worker calls."""

import argparse
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/host-preflight-20261022-1"
EDITABLE = (
    ".local-agents/local-bounded-review.py",
    ".local-agents/tests/test_coordinator_supervised.py",
    ".local-agents/README.md",
)


def freeze():
    status = subprocess.check_output(["git", "status", "--short"], cwd=S.KIT).decode(
        "utf-8"
    )
    files = [
        p
        for p in (S.KIT / ".local-agents").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]
    files.append(S.KIT / "AGENTS.md")
    preimages = {}
    for path in files:
        relative = path.relative_to(S.KIT).as_posix()
        destination = BATCH / "preimages" / relative
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        preimages[relative] = S.sha(path)
    S.save(
        BATCH / "baseline.json",
        {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "git_status": status,
            "preimages": preimages,
            "weekly_used_observed": 36,
            "weekly_stop": None,
            "authority": "Latest user: temporarily no limit; analyze and optimize",
        },
    )
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "deterministic-preparation-reliability",
            "feature_risk": "high",
            "integration_risk": "high",
            "units": [
                {
                    "unit_id": "non-consuming-review-inspection",
                    "risk": "high",
                    "contracts": [
                        "no-offline-dispatch",
                        "same-canonical-validation",
                        "live-one-shot",
                    ],
                    "dependencies": [],
                    "rationale": "Touching inspection/dispatch separation must not weaken anti-replay or evidence authentication.",
                },
                {
                    "unit_id": "order-independent-coordinator-fixtures",
                    "risk": "small",
                    "contracts": ["same-fixture-data-and-assertions"],
                    "dependencies": [],
                    "rationale": "Test discovery only; no Coordinator runtime or authority change.",
                },
            ],
            "allowed_existing_edits": list(EDITABLE),
            "new_files": [
                "tests/test_bounded_review_inspection.py",
                str(Path(__file__).relative_to(S.KIT)),
            ],
            "checks": [
                "Red reproduction before fix; immutable XML retained",
                "Installed inspect twice: exact same canonical inputs, zero model calls, no review archive/dispatch",
                "Then real CLI dispatch once against scripted loopback; second review denied; no semantic success credit",
                "Stale source/capture/JUnit and missing evidence remain rejected",
                "Original Coordinator fixtures in both collection orders, unchanged assertions",
                "Full runtime and relevant installed-entry regression without plugin preloading",
            ],
            "live_registered": 0,
            "qualification": "Offline reliability only; no change to scoped live qualification or old HOLD",
            "stop": "Complete deterministic evidence; unexpected trust/permission boundary requires reassessment",
            "preservation": "No history/default configuration/model/permissions/budget changes; sibling repositories read-only; no commit/push",
        },
    )
    print(f"Frozen {len(preimages)} current files in {BATCH}")


def preserve():
    old = S.read(BATCH / "baseline.json")
    changed = {p for p, sha in old["preimages"].items() if S.sha(S.KIT / p) != sha}
    cache_changes = {p for p in changed if p.startswith(".local-agents/.ruff_cache/")}
    source_changes = changed - cache_changes
    assert source_changes <= set(EDITABLE), source_changes - set(EDITABLE)
    assert all(
        S.sha(BATCH / "preimages" / p) == sha for p, sha in old["preimages"].items()
    )
    head = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
        .decode()
        .strip()
    )
    assert head == old["head"]
    S.save(
        BATCH / "preservation.json",
        {
            "head_unchanged": head,
            "preimages_intact": True,
            "changed_preexisting_files": {
                p: S.sha(S.KIT / p) for p in sorted(source_changes)
            },
            "tool_cache_changes": {p: S.sha(S.KIT / p) for p in sorted(cache_changes)},
            "other_runtime_and_default_configs_unchanged": True,
            "models_called": 0,
            "sibling_writes": False,
            "commit_push": False,
        },
    )
    print("Preservation verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "preserve"))
    args = parser.parse_args()
    (freeze if args.mode == "freeze" else preserve)()
