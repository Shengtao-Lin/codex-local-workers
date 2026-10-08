"""Two fresh read-only Explorer compatibility calls after final-channel enforcement."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "roleq-final-channel-compat-1"
SNAPSHOT = WORK / "roleq-final-channel-candidate-1"


def prepare():
    BASE.mkdir(exist_ok=False)
    sources = {
        "src/example.py": "def normalize_name(name):\n    return name.strip()\n",
        "tests/test_example.py": "from example import normalize_name\n\n\ndef test_spaces():\n    assert normalize_name('  Ada  ') == 'Ada'\n",
    }
    cells = []
    for mode in ("locate", "investigate"):
        root = BASE / mode
        for relative, source in sources.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        config = read(SNAPSHOT / ".local-agents/config.json")
        config.update(
            python=sys.executable,
            explorer_mode=mode,
            explorer_required_citation_paths=[
                "src/example.py",
                "tests/test_example.py",
            ],
            explorer_require_test_assertion_citation=True,
        )
        write(root / ".agent/config.json", config)
        cells.append(
            {
                "mode": mode,
                "hashes": {
                    p: digest(root / p) for p in [*sources, ".agent/config.json"]
                },
            }
        )
    write(
        BASE / "plan.json",
        {
            "classification": "Post-fix protocol compatibility only; not unfamiliar localization, semantic or Coordinator qualification",
            "feature_id": "final-channel-action-authority",
            "feature_risk": "high",
            "unit_risk": "small",
            "integration_risk": "high",
            "risk_rationale": "Read-only smoke supports, but never accepts, the high-risk protocol change",
            "dependencies": ["d6"],
            "owned_contract_ids": ["formal-explorer-output-compatibility"],
            "cells": cells,
            "max_calls": 2,
            "retry": False,
            "model": "openai/gpt-oss-20b",
            "single_model_residency": True,
            "weekly_used_ceiling": 40,
            "coordinator_started": False,
            "driver_sha256": digest(Path(__file__)),
        },
    )


def run(mode):
    plan = read(BASE / "plan.json")
    if digest(Path(__file__)) != plan["driver_sha256"]:
        raise ValueError("driver drift")
    for relative, sha in read(SNAPSHOT / "freeze.json")["files"].items():
        if digest(SNAPSHOT / relative) != sha:
            raise ValueError("snapshot drift")
    cell = next(c for c in plan["cells"] if c["mode"] == mode)
    root = BASE / mode
    for relative, sha in cell["hashes"].items():
        if digest(root / relative) != sha:
            raise ValueError("input drift")
    write(BASE / f"{mode}-started.json", {"started_at": time.time()})
    question = "Locate normalize_name in src/example.py and its whitespace expectation in tests/test_example.py. Read and cite the implementation and actual assertion lines. Do not claim tests were executed."
    start = time.monotonic()
    completed = subprocess.run(
        [
            sys.executable,
            str(SNAPSHOT / ".local-agents/local-explore.py"),
            "--config",
            str(root / ".agent/config.json"),
            "--task",
            question,
            "--task-id",
            f"final-channel-compat-{mode}",
            "--report",
            str(root / ".agent/explorer.json"),
            "--full-report",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    record = {
        "exit": completed.returncode,
        "seconds": time.monotonic() - start,
        "output": completed.stdout + completed.stderr,
        "inputs_unchanged": all(
            digest(root / p) == sha for p, sha in cell["hashes"].items()
        ),
    }
    write(BASE / f"{mode}-result.json", record)
    print(record, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "locate", "investigate"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        run(args.action)
