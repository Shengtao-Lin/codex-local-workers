"""Immutable evidence for the approved Explorer mechanical installation fix."""

import argparse
import difflib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/explorer-install-20261020-1"


def inventory():
    paths = [S.KIT / "AGENTS.md", *sorted((S.KIT / ".local-agents").rglob("*"))]
    return {
        str(p.relative_to(S.KIT)).replace("\\", "/"): S.sha(p)
        for p in paths
        if p.is_file()
        and not any(v in p.parts for v in ("__pycache__", ".pytest_cache"))
    }


def freeze():
    before = inventory()
    for name in (
        ".local-agents/explorer-runtime.py",
        ".local-agents/tests/test_explorer_runtime.py",
    ):
        target = BATCH / "preimages" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((S.KIT / name).read_bytes())
    S.save(
        BATCH / "registration.json",
        {
            "scope": "Approved mechanical prerequisite-read fix and installation checks only",
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "git_status": subprocess.check_output(
                ["git", "status", "--short"], cwd=S.KIT
            ).decode(),
            "production_before": before,
            "weekly_used": 6,
            "weekly_stop": 50,
            "live_calls_planned": 0,
            "unchanged": [
                "models",
                "budgets",
                "default configuration",
                "Reviewer",
                "Coder",
                "Primary disposition",
                "Coordinator disabled",
                "old HOLD and scores",
            ],
            "gate": "Installed Explorer controls pass; no unrelated production drift",
        },
    )


def verify_install(attempt):
    evidence = BATCH / f"installation-attempt-{attempt}"
    evidence.mkdir(parents=True, exist_ok=False)
    # A real external disposable target: the installer correctly refuses nested targets.
    with tempfile.TemporaryDirectory(
        prefix="local-worker-explorer-install-"
    ) as directory:
        target = Path(directory)
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "scripts/install_local_agents.py",
                "--target",
                str(target),
                "--apply",
            ],
            cwd=S.KIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        S.save(
            evidence / "install.json",
            {
                "command": result.args,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        if result.returncode:
            raise RuntimeError("Installation failed; retained install.json")
        checks = []
        for args in (
            [
                "-m",
                "unittest",
                "discover",
                "-s",
                ".local-agents/tests",
                "-p",
                "test_explorer*.py",
                "-q",
            ],
            [".local-agents/local-explore.py", "--help"],
        ):
            observed = subprocess.run(
                [sys.executable, "-B", *args],
                cwd=target,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                check=False,
            )
            checks.append(
                {
                    "command": observed.args,
                    "exit_code": observed.returncode,
                    "stdout": observed.stdout,
                    "stderr": observed.stderr,
                }
            )
        S.save(
            evidence / "installed-checks.json",
            {
                "checks": checks,
                "network": "Mocked clients only; no Worker calls",
                "config_json_absent": not (
                    target / ".local-agents/config.json"
                ).exists(),
                "benchmarks_absent": not (target / "benchmarks").exists(),
                "runtime_matches_source": S.sha(
                    target / ".local-agents/explorer-runtime.py"
                )
                == S.sha(S.KIT / ".local-agents/explorer-runtime.py"),
            },
        )
        if any(c["exit_code"] for c in checks):
            raise RuntimeError(
                "Installed checks failed; retained installed-checks.json"
            )
    before = S.read(BATCH / "registration.json")["production_before"]
    after = inventory()
    changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
    S.save(
        BATCH / "preservation.json",
        {
            "production_changed": sorted(changed),
            "only_authorized_paths": set(changed)
            <= {
                ".local-agents/explorer-runtime.py",
                ".local-agents/tests/test_explorer_runtime.py",
            },
            "production_after": after,
        },
    )


def close():
    before = S.read(BATCH / "registration.json")["production_before"]
    after = inventory()
    changed = sorted(
        p for p in before.keys() | after.keys() if before.get(p) != after.get(p)
    )
    cache_paths = [p for p in changed if ".ruff_cache" in Path(p).parts]
    delivered = [p for p in changed if p not in cache_paths]
    allowed = [
        ".local-agents/explorer-runtime.py",
        ".local-agents/tests/test_explorer_runtime.py",
    ]
    if delivered != sorted(allowed):
        raise RuntimeError(f"Unrelated delivered source drift: {delivered}")
    for name in allowed:
        diff = "".join(
            difflib.unified_diff(
                (BATCH / "preimages" / name)
                .read_text(encoding="utf-8")
                .splitlines(True),
                (S.KIT / name).read_text(encoding="utf-8").splitlines(True),
                fromfile="before/" + name,
                tofile="after/" + name,
            )
        )
        with (BATCH / (Path(name).name + ".diff")).open(
            "x", encoding="utf-8"
        ) as stream:
            stream.write(diff)
    suites = ET.parse(BATCH / "regression-final.xml").getroot().findall("testsuite")
    results = [
        {k: suite.get(k) for k in ("tests", "failures", "errors", "skipped", "time")}
        for suite in suites
    ]
    if not results or any(int(r["failures"]) or int(r["errors"]) for r in results):
        raise RuntimeError("Final offline regression is not green")
    installed = S.read(BATCH / "installation-attempt-2/installed-checks.json")
    if any(c["exit_code"] for c in installed["checks"]):
        raise RuntimeError("Installed regression is not green")
    S.save(
        BATCH / "preservation-final.json",
        {
            "delivered_paths_changed": delivered,
            "only_authorized_source_paths": True,
            "tool_cache_drift": cache_paths,
            "raw_preservation_record_retained": "preservation.json",
            "note": "Ruff generated cache files are reported separately, not shipped source changes",
        },
    )
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_MECHANICAL_INSTALLATION_ONLY",
            "regression": results,
            "live_calls": 0,
            "independent_acceptance": "Primary reviewed bounded preimage diff and installed controls",
            "defaults_and_other_runtime_unchanged": True,
            "semantic_gate": "HOLD",
            "coordinator": "NOT_ADMITTED",
            "historical_failures": "Retained, including sandbox denial and wrong test budget key",
            "production_change": "Explorer missing required read preserves bounded read opportunity",
            "not_approved": [
                "automatic semantic Reviewer rework",
                "global default enablement",
            ],
        },
    )
    S.save(
        BATCH / "handoff.json",
        {
            "mechanical_fix": "Installed source acquisition prerequisite fix passed offline controls",
            "capability": "No new semantic or transfer claims; prior HOLD unchanged",
            "next_boundary": "Limited task-family evidence and Primary final acceptance remain required",
            "cost": "Offline preparation only; exact Primary time and cloud tokens unknown",
            "no_commit_push": True,
            "siblings": "Read-only; untouched",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("freeze", "verify-install", "close"))
    parser.add_argument("--attempt", type=int, default=2)
    args = parser.parse_args()
    phase = args.phase
    if phase == "freeze":
        freeze()
    elif phase == "verify-install":
        verify_install(args.attempt)
    else:
        close()
