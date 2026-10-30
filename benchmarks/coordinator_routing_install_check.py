"""Create-only offline installation qualification for explicit routing API."""

import argparse
import importlib.util
import tempfile
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T

SPEC = importlib.util.spec_from_file_location(
    "routing_installer", S.KIT / "scripts/install_local_agents.py"
)
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)

BATCH = (
    S.KIT / "benchmarks/work/harness-convergence/coordinator-routing-install-20261022-1"
)
FILES = [
    ".local-agents/coordinator-routing.py",
    ".local-agents/tests/test_coordinator_routing.py",
    "tests/test_coordinator_routing_install.py",
]


def run():
    assert not BATCH.exists()
    source = (
        S.KIT
        / "benchmarks/work/harness-convergence/project-identity-chain-20261022-4/decision.json"
    )
    assert S.read(source)["accepted_chains"] == 1
    S.save(
        BATCH / "registration.json",
        {
            "candidate": "Explicit installed coordinator-routing API, frozen decomposition-only adapter; no default/legacy changes or automatic dispatch/acceptance",
            "gate": "Installed portable negative controls and existing brief controls pass; five scripted request/output equivalence cases vs frozen candidate; Ruff and diff hygiene pass. Zero model calls.",
            "tests": "23 routing +18 brief installed;5 equivalence cases valid/correction/unresolved/invalid-owner/unqualified, not live success counts",
            "preparation": "Two new install-test import lint findings and standalone launcher import-path error corrected before registration; no model calls; source runtime/portable controls clean",
            "prior_control": "First installation round retained as HOLD: portable fixture started at hash a*64 and tried changing it to the same value. Second round uses a genuinely different hash plus an assertion. Runtime candidate unchanged; no weakened stale-binding control.",
            "source_live_evidence": str(source),
            "pins": {str(S.KIT / p): S.sha(S.KIT / p) for p in FILES},
            "authority": "Current autonomous in-scope packaging; all old results preserved; no production default enablement",
        },
    )
    with tempfile.TemporaryDirectory(prefix="routing-portable-tests-") as directory:
        root = Path(directory)
        INSTALL.install(S.KIT, root, apply=True)
        assert not (root / "benchmarks").exists()
        checks = [
            T.run(
                [
                    S.PYTHON,
                    "-B",
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    ".local-agents/tests/test_coordinator_routing.py",
                    ".local-agents/tests/test_coordinator_brief.py",
                ],
                root,
                timeout=120,
            )
        ]
    checks += [
        T.run(args, S.KIT, timeout=120)
        for args in (
            [
                S.PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_coordinator_routing_install.py",
            ],
            [S.PYTHON, "-B", "-m", "ruff", "check", *FILES, str(Path(__file__))],
            ["git", "diff", "--check"],
        )
    ]
    S.save(BATCH / "checks.json", checks)
    good = all(c["exit_code"] == 0 for c in checks)
    S.save(
        BATCH / "decision.json",
        {
            "status": "PASS_EXPLICIT_ROUTING_INSTALL"
            if good
            else "HOLD_OFFLINE_INSTALL",
            "model_calls": 0,
            "production_enabled": False,
            "permission": "Opt-in Primary-side API for the recorded scoped snapshot workflow only; no general plan-to-code or savings claim",
            "same_model_input_and_normalization": good,
            "prior_HOLDs": "Unchanged; install verification is not a replacement live score",
        },
    )
    print(
        "PASS explicit routing installation" if good else "HOLD offline checks",
        flush=True,
    )
    assert good, checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    BATCH = BATCH.with_name("coordinator-routing-install-20261022-" + str(args.round))
    run()
