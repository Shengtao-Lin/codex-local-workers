"""Read-only source-evidence diagnostic, not a patch or hidden-test hint."""

import json
import shutil
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as T
import reviewer_causal_investigation as E

BATCH = (
    S.KIT
    / "benchmarks/work/harness-convergence/reviewer-dependency-evidence-20261020-1"
)


def prepare():
    assert S.read(E.BATCH / "decision.json")["correct_focal_conclusion"] == 1
    old = S.read(E.BATCH / "registration.json")["cells"]["defect"]
    environment = T.run(
        [
            S.PYTHON,
            "-B",
            "-c",
            "import json,json.encoder,sys;print(json.dumps({'version':sys.version,'json':json.__file__,'encoder':json.encoder.__file__}))",
        ],
        S.KIT,
    )
    assert environment["exit_code"] == 0
    original_modules = json.loads(environment["stdout"])
    S.save(
        BATCH / "dependency-origin.json",
        {**original_modules, "fixture_python": str(S.PYTHON)},
    )
    rows = {}
    for label in ("json-1", "json-2"):
        root = BATCH / "cells" / label / "isolated"
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            assert S.sha(source) == digest
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        snapshots = {}
        for key, name in (("json", "__init__.py"), ("encoder", "encoder.py")):
            relative = "context/json_dependency/" + name
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original_modules[key], dest)
            assert S.sha(dest) == S.sha(original_modules[key])
            snapshots[relative] = S.sha(dest)
        config = S.read(root / ".agent/config.json")
        config["explorer_required_citation_paths"].append(
            "context/json_dependency/encoder.py"
        )
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        question = (
            old["question"]
            + " Relevant imported-dependency source snapshots from the actual fixture interpreter: context/json_dependency/__init__.py and context/json_dependency/encoder.py. Read dependency evidence as well as target code and tests; report source-backed distinctions and do not claim any test was executed."
        )
        rows[label] = {
            **old,
            "root": str(root),
            "question": question,
            "dependency_snapshots": snapshots,
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
            },
        }
    S.save(
        BATCH / "registration.json",
        {
            "registered": 2,
            "order": ["json-1", "json-2"],
            "cells": rows,
            "weekly_stop": 50,
            "batch_seconds": 3600,
            "per_call_seconds": 600,
            "turns": 16,
            "reads": 8,
            "searches": 10,
            "errors": 6,
            "model": "openai/gpt-oss-20b",
            "context_length": 32768,
            "single_residency": True,
            "only_evidence_change": "Whole unmodified actual json dependency files, plus required dependency read. No selected answer lines, patch, original explanation, hidden test or new contract. This tests evidence availability AND read obligation, not one isolated factor.",
            "gate": "Both independent focal diagnoses must identify an actual contract discrepancy with read implementation/dependency evidence, no invented execution. Cache hits reported separately, not fresh-call credit. No Coder transfer unless this narrow gate passes.",
            "continue_rule": "Complete both ordinary outcomes, no revised questions or extra outputs. Stop on safety/input drift/infra/time/weekly50.",
            "exposure": "Same exposed JSON failure, repeated twice. Not new-task or role qualification.",
            "pins": {
                str(Path(__file__).resolve()): S.sha(__file__),
                str(Path(E.__file__).resolve()): S.sha(E.__file__),
            },
        },
    )
    print("Two dependency-source diagnoses frozen; no Coder/Reviewer calls")


def run(label, used, observed):
    E.run(label, used, observed, batch=BATCH)
