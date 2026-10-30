"""Immutable baseline for the missing flat-profile diagnostic callback."""

import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/flat-diagnostics-20261022-1"


def freeze():
    files = {}
    for path in [S.KIT / "AGENTS.md", *(S.KIT / ".local-agents").rglob("*")]:
        if not path.is_file() or any(
            part in {"__pycache__", ".pytest_cache", ".ruff_cache"}
            for part in path.parts
        ):
            continue
        relative = path.relative_to(S.KIT).as_posix()
        output = BATCH / "preimages" / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream, path.open("rb") as original:
            shutil.copyfileobj(original, stream)
        files[relative] = S.sha(output)
    S.save(
        BATCH / "registration.json",
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "feature_id": "flat-diagnostic-callback-parity",
            "feature_risk": "medium",
            "unit_risk": "medium",
            "integration_risk": "high",
            "risk_rationale": "Restore existing source-bound diagnostic evidence, never validation/acceptance authority.",
            "owned_contract_ids": [
                "wire-only-adapter",
                "source-bound-static-facts",
                "unchanged-safety-and-budgets",
            ],
            "dependencies": ["preparation-entry-20261022-1"],
            "finding": "compatibility_profile.proposal_rules forwards render but not base.diagnostics; H.context checks hasattr and silently emits an empty diagnostics list.",
            "candidate": "Forward the existing diagnostics callback when available; no new parser, hints, tools or budget.",
            "controls": [
                "red reproduction",
                "same callback/default/schema identity",
                "installed scripted static-error then repair with current path/hash evidence",
                "stale source and protected file negative controls",
                "same-version focused installed/regression suites",
            ],
            "scope": [
                ".local-agents/bounded/compatibility_profile.py",
                "tests/test_flat_diagnostics.py",
            ],
            "unchanged": [
                "models",
                "prompts",
                "schema",
                "budgets",
                "editor",
                "checks",
                "Reviewer",
                "handoff",
                "defaults",
                "historical results",
            ],
            "live_registered": 0,
            "live_policy": "Separate frozen cross-task registration after offline controls; no message-id retries.",
            "weekly_stop": None,
            "weekly_used_observed": 42,
            "authority": "Latest user authorizes autonomous in-scope iteration until user stop; no fixed weekly stop currently.",
            "preimages": files,
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "git_status": subprocess.check_output(
                ["git", "status", "--short"], cwd=S.KIT
            ).decode(),
        },
    )
    print("Frozen", len(files), "files; no live registered")


def close():
    registration = S.read(BATCH / "registration.json")
    changed = {
        name: S.sha(S.KIT / name)
        for name, digest in registration["preimages"].items()
        if S.sha(S.KIT / name) != digest
    }
    assert set(changed) == {".local-agents/bounded/compatibility_profile.py"}
    assert all(
        S.sha(BATCH / "preimages" / name) == digest
        for name, digest in registration["preimages"].items()
    )
    tests = {}
    for name in ("red", "green"):
        suites = ET.parse(BATCH / f"{name}.xml").getroot().findall("testsuite")
        tests[name] = {
            key: sum(int(s.get(key, 0)) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
    assert tests["red"]["failures"] == 8
    assert tests["green"] == {"tests": 80, "failures": 0, "errors": 0, "skipped": 0}
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_DIAGNOSTIC_CALLBACK_PARITY",
            "model_calls": 0,
            "confirmed": "Wire compatibility adapter silently discarded the existing static-focus callback; original raw checks remained visible. Installed scripted F841 repair now exposes the exact rule/path/current-source/hash.",
            "adopted": "Forward existing callback only, unchanged production defaults and validation authority.",
            "not_proven": [
                "caused prior semantic failures",
                "live completion improvement",
                "general qualification",
                "economic saving",
            ],
            "controls": tests,
            "overlap": "green includes same tests as prior suites; do not sum across phases",
            "changed_existing": changed,
            "preimages_preserved": True,
            "next": "Independent frozen static repair comparison, then new real-source behavior transfer; no message-id retries.",
        },
    )
    S.save(
        BATCH / "handoff.json",
        {
            "state": "offline parity fixed; new live requires its own registration",
            "candidate_sha256": changed[
                ".local-agents/bounded/compatibility_profile.py"
            ],
            "models": "unchanged",
            "weekly_stop": None,
            "authority": "Continue autonomously within existing scope until user stops; phase closure is not whole-task completion.",
        },
    )
    print("Offline phase closed; no live inference")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["freeze", "close"])
    args = parser.parse_args()
    freeze() if args.mode == "freeze" else close()
