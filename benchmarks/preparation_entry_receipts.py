"""Freeze receipts for the installed, non-executing preparation entry."""

import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import bounded_evidence_support as S

BATCH = S.KIT / "benchmarks/work/harness-convergence/preparation-entry-20261022-1"


def freeze():
    pins = {}
    paths = [S.KIT / "AGENTS.md", *(S.KIT / ".local-agents").rglob("*")]
    for path in paths:
        if not path.is_file() or any(
            part in {"__pycache__", ".ruff_cache", ".pytest_cache"}
            for part in path.parts
        ):
            continue
        name = path.relative_to(S.KIT).as_posix()
        destination = BATCH / "preimages" / name
        if destination.exists():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        pins[name] = S.sha(destination)
    S.save(
        BATCH / "registration.json",
        {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "feature_id": "installed-preparation-entry",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "risk_rationale": "Preparation emits trusted evidence policy/config, so scope, versions and existing gates must remain authoritative.",
            "owned_contract_ids": [
                "preview-no-writes-or-execution",
                "no-overwrite-or-scope-expansion",
                "same-capture-producer-and-final-gates",
                "preserve-packet-config-and-history",
            ],
            "dependencies": ["capture-preflight-20261022-1"],
            "hypothesis": "Explicit installed material assembly can remove repetitive hash/copy/binding work without moving semantic planning or acceptance into a model.",
            "candidate": "Opt-in preparation CLI: existing approved packet, config and capture specification; preview by default; generate only capture material and run-specific inputs on explicit apply.",
            "scope": "Fresh isolated workspace with explicit approved source manifest; no snapshot discovery, sibling writes, contract/test authoring or model calls.",
            "config_changes": ["experimental_capture_policy_sha256 only"],
            "checks": [
                "Preview leaves every workspace byte unchanged; rejects malformed scope/target/profile/path and output conflicts before writes",
                "Generated material matches existing manual preparation semantics and retains exact packet/config except new policy hash",
                "Installed offline replay with real checks and authenticated Reviewer input; zero live credit",
                "Current full runtime and installed-entry regression; preservation verification",
            ],
            "live_registered": 0,
            "live_policy": "A separate immutable registration is required before any live; no semantic-transfer credit for preparation controls.",
            "no_changes": [
                "models",
                "production defaults",
                "prompts",
                "repair budgets",
                "handoff semantics",
                "Reviewer",
                "qualification families",
                "historical outcomes",
            ],
            "weekly_used_observed": 39,
            "weekly_stop": None,
            "stop": "Verified phase conclusion or material design/authority issue; autonomous in-scope revisions retain failed controls.",
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
            .decode()
            .strip(),
            "git_status": subprocess.check_output(
                ["git", "status", "--short"], cwd=S.KIT
            ).decode(),
            "preimages": pins,
        },
    )
    print(f"Frozen {len(pins)} files; zero live registered: {BATCH}")


def close():
    registration = S.read(BATCH / "registration.json")
    changed = {
        p: S.sha(S.KIT / p)
        for p, sha in registration["preimages"].items()
        if S.sha(S.KIT / p) != sha
    }
    assert set(changed) <= {".local-agents/README.md"}
    assert all(
        S.sha(BATCH / "preimages" / p) == sha
        for p, sha in registration["preimages"].items()
    )
    assert (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=S.KIT)
        .decode()
        .strip()
        == registration["head"]
    )
    checks = {}
    for name in ("first.xml", "host.xml", "focused.xml", "full-regression.xml"):
        suites = ET.parse(BATCH / name).getroot().findall("testsuite")
        checks[name] = {
            key: sum(int(s.get(key, 0)) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        checks[name]["seconds"] = sum(float(s.get("time", 0)) for s in suites)
    assert checks["full-regression.xml"]["tests"] == 745
    assert all(
        checks["full-regression.xml"][key] == 0
        for key in ("failures", "errors", "skipped")
    )
    sources = [
        ".local-agents/bounded/prepare_unit.py",
        ".local-agents/local-bounded-prepare.py",
        "tests/test_bounded_preparation.py",
        "benchmarks/preparation_entry_receipts.py",
    ]
    static = []
    for argv in (
        [str(S.PYTHON), "-B", "-m", "ruff", "check", *sources],
        [str(S.PYTHON), "-B", "-m", "ruff", "format", "--check", *sources],
        ["git", "diff", "--check"],
    ):
        result = subprocess.run(
            argv, cwd=S.KIT, capture_output=True, text=True, check=False
        )
        static.append(
            {
                "argv": argv,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    S.save(BATCH / "static-checks.json", static)
    assert all(c["exit_code"] == 0 for c in static)
    S.save(
        BATCH / "preservation.json",
        {
            "head_unchanged": registration["head"],
            "preimages_intact": True,
            "changed_preexisting_files": changed,
            "new_source_hashes": {p: S.sha(S.KIT / p) for p in sources},
            "default_configs_unchanged": True,
            "sibling_repositories": "read-only",
            "commit_push": False,
        },
    )
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_INSTALLED_PREPARATION_CONTROLS",
            "checks": checks,
            "failure_classification": "first.xml: all22 controls blocked by Windows sandbox temporary-directory permission before candidate exercise. Same tests under permitted host execution22/22; expanded controls27/27. First failures retained, not model failures.",
            "overlap": "22, 27 and 745 contain overlapping tests; do not add denominators",
            "model_calls": 0,
            "live_registered": 0,
            "scope": "Explicit no-execution preparation entry only; no runtime/prompts/models/checks/defaults/qualification changes",
            "limits": [
                "Primary still supplies detailed contracts, protected tests, explicit dependencies and project config",
                "Static preview is not executable validation or import discovery",
                "One unit per fresh isolated workspace; inherited/in-place multi-unit preparation unsupported",
                "No evidence of precise Primary cloud or time savings",
            ],
            "next": "Separately registered two-cell real-slice integration using same execution candidate and new preparation; no general production promotion",
            "weekly_used_observed": 40,
            "weekly_stop": None,
        },
    )
    print("Preparation controls closed: 745 full-suite pass, zero model calls")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("freeze", "close"), nargs="?", default="freeze"
    )
    (freeze if parser.parse_args().mode == "freeze" else close)()
