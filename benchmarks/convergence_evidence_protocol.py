"""Independent, frozen evidence-ID presentation phase; no semantic auto-fill."""

import argparse
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import convergence_reviewer as previous
from convergence_coder import KIT, PYTHON, save
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/protocol-20261011-1"
OLD = KIT / "benchmarks/work/system-convergence/followup-20261011-2"
TARGET = BASE / "reviewer-kit"
ROOT = BASE / "reviewer"


def prepare():
    BASE.mkdir(parents=True, exist_ok=False)
    save(
        BASE / "baseline.json",
        {
            "weekly_used_start": 1,
            "weekly_used_ceiling": 15,
            "previous_decision": ref(
                KIT, (OLD / "stage-decision-1.json").relative_to(KIT).as_posix()
            ),
            "unchanged_gates": read_object(OLD / "release-gates-1.json"),
            "source": str(OLD / "i1-candidate-kit"),
            "candidate_axis": "Reviewer selects runtime-issued IDs for actually displayed current ranges; runtime resolves only the selected IDs, never claims verification",
            "old_source_refs_only_trial": "tool-reviewer-canonical-1 already failed; this is not a repeat of that presentation",
            "models_context_sampling_budgets_unchanged": True,
            "scope_or_standards_relaxed": False,
            "production_promoted": False,
        },
    )
    shutil.copytree(
        OLD / "i1-candidate-kit",
        TARGET,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )


def register():
    xml = BASE / "reviewer-full-regression-2.xml"
    cases = list(ET.parse(xml).iter("testcase"))
    assert not any(
        c.find("failure") is not None or c.find("error") is not None for c in cases
    )
    skipped = [c.get("name") for c in cases if c.find("skipped") is not None]
    assert skipped == ["test_symlink_path_is_rejected"]
    previous.BASE = ROOT
    previous.RUNTIME = TARGET / ".local-agents"
    previous.prepare()
    registration = read_object(ROOT / "registration.json")
    for cell in registration["cells"]:
        root = Path(cell["root"])
        config = read_object(root / ".agent/config.json")
        config["reviewer_evidence_ids"] = True
        save(root / ".agent/protocol-config.json", config)
    save(
        ROOT / "protocol-registration.json",
        {
            "registration": ref(ROOT, "registration.json"),
            "driver": ref(KIT, "benchmarks/convergence_evidence_protocol.py"),
            "candidate": "reviewer-displayed-evidence-ids-1",
            "runtime": registration["runtime"],
            "configs": {
                c["id"]: ref(Path(c["root"]), ".agent/protocol-config.json")
                for c in registration["cells"]
            },
            "weekly_used_start": 1,
            "weekly_used_ceiling": 15,
            "legacy_budget_superseded": True,
            "registered": 16,
            "fixed_original_semantic_expectations": True,
            "correctness_not_inferred_from_display": True,
            "synthetic_old_archives_not_new_coder_or_full_chain_credit": True,
            "live_candidate_changes_or_resampling_allowed": False,
            "offline_full_regression": ref(BASE, xml.name),
            "offline_countertests": ref(BASE, "counter-corrected-2.xml"),
            "host_skip_not_counted_pass": skipped,
            "actual_junction_negative_control": ref(
                KIT, (OLD / "reparse-control/results.json").relative_to(KIT).as_posix()
            ),
        },
    )


def run(cell_id):
    freeze = read_object(ROOT / "protocol-registration.json")
    assert sha256(Path(__file__)) == freeze["driver"]["sha256"]
    assert sha256(ROOT / "registration.json") == freeze["registration"]["sha256"]
    for item in freeze["runtime"]:
        assert sha256(TARGET / ".local-agents" / item["path"]) == item["sha256"]
    # Reuse the immutable old runner, supplying only this phase's config path.
    previous.BASE, previous.RUNTIME = ROOT, TARGET / ".local-agents"
    cell = next(
        c
        for c in read_object(ROOT / "registration.json")["cells"]
        if c["id"] == cell_id
    )
    root = Path(cell["root"])
    assert (
        sha256(root / freeze["configs"][cell_id]["path"])
        == freeze["configs"][cell_id]["sha256"]
    )
    original_run = previous.subprocess.run

    def configured_run(argv, **kwargs):
        args = list(argv)
        index = args.index("--config") + 1
        args[index] = str(root / ".agent/protocol-config.json")
        return original_run(args, **kwargs)

    previous.subprocess.run = configured_run
    try:
        previous.run(cell_id)
    finally:
        previous.subprocess.run = original_run


def regression():
    """Explicit read-only dependency interpreter; every temp path is new."""
    number = next(
        n for n in range(1, 10) if not (BASE / f"regression-temp-{n}").exists()
    )
    temp = BASE / f"regression-temp-{number}"
    temp.mkdir(exist_ok=False)
    tempfile.tempdir = str(temp)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["R1_RUNTIME_ROOT"] = str(TARGET / ".local-agents")
    os.chdir(TARGET)
    sys.path[:0] = [str(TARGET / "benchmarks"), str(TARGET)]
    import tool_reviewer_protocol_reference_trial
    import tool_reviewer_test_consistency_trial

    tool_reviewer_protocol_reference_trial.PYTHON = PYTHON
    tool_reviewer_test_consistency_trial.PYTHON = PYTHON
    import pytest

    raise SystemExit(
        pytest.main(
            [
                ".local-agents/tests",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(temp / "pytest"),
                "--junitxml=" + str(BASE / f"reviewer-full-regression-{number}.xml"),
            ]
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "register", "run", "regression"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    {"prepare": prepare, "register": register, "regression": regression}.get(
        args.action, lambda: run(args.cell)
    )()
