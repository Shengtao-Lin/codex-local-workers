"""Frozen no-op candidate: clean normal-path repetition of the reviewed contract."""

import argparse
from pathlib import Path

import reviewer_real_unit_trial as trial
from capability_fit import KIT, WORK, write
from inherited_context_recovery import digest, read

trial.BASE = WORK / "normal-unit-candidate-1"
trial.ROOT = trial.BASE / "candidate"
trial.SNAPSHOT = WORK / "normal-unit-candidate-runtime-1"
# The existing helper's -2 suffix selects the explicitly corrected contract.
trial.TASK = "normal-unit-candidate-2"
FIXED = WORK / "noop-primary-complete-1"


def verify_candidate():
    for path, sha in read(FIXED / "freeze.json")["files"].items():
        assert digest(KIT / path) == sha, "Live candidate drift: " + path


def prepare():
    verify_candidate()
    trial.prepare()
    prior = read(WORK / "reviewer-real-unit-2/candidate/.agent/packet.json")
    packet = read(trial.ROOT / ".agent/packet.json")
    for field in (
        "goal",
        "risk",
        "required_behavior",
        "scope",
        "focused_tests",
        "acceptance_scenarios",
        "validation_profile",
        "owned_contract_ids",
    ):
        assert packet[field] == prior[field], field
    for path, sha in read(FIXED / "freeze.json")["files"].items():
        assert digest(trial.SNAPSHOT / path) == sha, path
    write(
        trial.BASE / "normal-path-registration.json",
        {
            "fixed_candidate": str(FIXED),
            "candidate_drift": False,
            "corrected_contract_unchanged": True,
            "clean_original_source": True,
            "new_semantic_cases": 0,
            "model_changes": False,
            "single_model_residency": True,
            "coordinator_enabled": False,
            "explorer_credit": False,
            "calls_per_cell": 1,
            "gate": "Current validation and protected inputs, automatic Reviewer pass, high-risk Primary actual diff and complete copied-fixture regression. No auto retry or gate change.",
            "wrapper_sha256": digest(Path(__file__)),
            "weekly_used_ceiling": 50,
        },
    )
    # Exact registered helper retained before run; audit checks its hash.
    import shutil

    shutil.copy2(Path(trial.__file__), trial.BASE / "registered-driver.py")


def run():
    verify_candidate()
    registration = read(trial.BASE / "normal-path-registration.json")
    assert digest(Path(__file__)) == registration["wrapper_sha256"]
    trial.run()


def audit():
    verify_candidate()
    trial.audit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "audit"))
    args = parser.parse_args()
    globals()[args.action]()
