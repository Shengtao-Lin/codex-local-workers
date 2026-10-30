"""New bounded Reviewer phase: typed issue assessment, original sixteen expectations."""

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import convergence_evidence_protocol as previous
from convergence_coder import KIT, save
from system_convergence import read_object, ref, sha256

BASE = KIT / "benchmarks/work/system-convergence/assessment-20261011-1"
TARGET = BASE / "reviewer-kit"
ROOT = BASE / "reviewer"
OLD = previous.BASE


def bind():
    previous.BASE, previous.TARGET, previous.ROOT = BASE, TARGET, ROOT


def prepare():
    BASE.mkdir(parents=True, exist_ok=False)
    save(
        BASE / "baseline.json",
        {
            "prior_decision": ref(
                KIT,
                (OLD / "reviewer/stage-decision-1.json").relative_to(KIT).as_posix(),
            ),
            "prior_explorer": ref(
                KIT,
                (OLD / "explorer/stage-decision-1.json").relative_to(KIT).as_posix(),
            ),
            "weekly_used_start": 2,
            "weekly_used_ceiling": 15,
            "axis": "Reviewer chooses typed issue nature, runtime maps that explicit choice to disposition; no keyword routing or automatic contract SAT judgment",
            "deterministic_compat_fix": "Citation-shape repair preserves the active ID representation, never produces an unsatisfiable required-but-forbidden field",
            "models_sampling_context_budget_and_sixteen_standards_unchanged": True,
            "production_promoted": False,
            "all_prior_failures_preserved": True,
        },
    )
    shutil.copytree(
        OLD / "reviewer-kit",
        TARGET,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )


def register():
    bind()
    xml = BASE / "reviewer-full-regression-1.xml"
    cases = list(ET.parse(xml).iter("testcase"))
    assert not any(
        c.find("failure") is not None or c.find("error") is not None for c in cases
    )
    assert [c.get("name") for c in cases if c.find("skipped") is not None] == [
        "test_symlink_path_is_rejected"
    ]
    previous.previous.BASE, previous.previous.RUNTIME = ROOT, TARGET / ".local-agents"
    previous.previous.prepare()
    registration = read_object(ROOT / "registration.json")
    configs = {}
    for cell in registration["cells"]:
        root = Path(cell["root"])
        config = read_object(root / ".agent/config.json")
        config["reviewer_evidence_ids"] = True
        config["reviewer_assessment_protocol"] = True
        save(root / ".agent/protocol-config.json", config)
        save(root / ".agent/assessment-config.json", config)
        configs[cell["id"]] = ref(root, ".agent/assessment-config.json")
    save(
        ROOT / "protocol-registration.json",
        {
            "registration": ref(ROOT, "registration.json"),
            "driver": ref(KIT, "benchmarks/convergence_evidence_protocol.py"),
            "runtime": registration["runtime"],
            "configs": {
                c["id"]: ref(Path(c["root"]), ".agent/protocol-config.json")
                for c in registration["cells"]
            },
            "weekly_used_ceiling": 15,
            "legacy_budget_superseded": True,
            "offline_full_regression": ref(BASE, xml.name),
            "candidate": "reviewer-typed-issue-assessment-1",
        },
    )
    save(
        ROOT / "assessment-registration.json",
        {
            "protocol_registration": ref(ROOT, "protocol-registration.json"),
            "wrapper": ref(KIT, "benchmarks/convergence_reviewer_assessment.py"),
            "configs": configs,
            "registered": 16,
            "weekly_used_ceiling": 15,
            "candidate": "reviewer-typed-issue-assessment-1",
            "same_corpus_not_blind_generalization": True,
            "original_expected_dispositions_unchanged": True,
            "no_semantic_auto_fill": True,
            "no_live_changes_or_resampling": True,
        },
    )


def run(cell_id):
    bind()
    freeze = read_object(ROOT / "assessment-registration.json")
    assert sha256(Path(__file__)) == freeze["wrapper"]["sha256"]
    assert (
        sha256(ROOT / "protocol-registration.json")
        == freeze["protocol_registration"]["sha256"]
    )
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
    original_run = previous.previous.subprocess.run

    def configured_run(argv, **kwargs):
        args = list(argv)
        args[args.index("--config") + 1] = str(root / ".agent/assessment-config.json")
        return original_run(args, **kwargs)

    previous.previous.subprocess.run = configured_run
    try:
        previous.run(cell_id)
    finally:
        previous.previous.subprocess.run = original_run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "register", "run", "regression"))
    parser.add_argument("cell", nargs="?")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "register":
        register()
    elif args.action == "regression":
        bind()
        previous.regression()
    else:
        run(args.cell)
