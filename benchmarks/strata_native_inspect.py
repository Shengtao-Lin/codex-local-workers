"""Primary-owned independent checks; never emits task acceptance by itself."""

import argparse
import os
import sys
from pathlib import Path

import strata_native_matrix as M


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=M.CASES[1:])
    parser.add_argument("--batch", type=Path, default=M.BATCH)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    root = args.batch.resolve() / "cells" / args.case / "isolated"
    report = M.S.read(root / ".agent/native-host-report.json")
    prepared = root / ".agent/prepared" / report["run_id"]
    config = M.S.read(prepared / "config.json")
    sys.path.insert(0, str(root / ".local-agents"))
    from bounded import capture_fixture_support as F

    gate = F.load(root / ".local-agents/local-unit.py", "native_independent_gate")
    gate.verify_handoff(root, report, config=config)
    topic = args.case.split("-")[0]
    batch, _ = M.origin(topic)
    private = batch / "private" / topic / "test_independent.py"
    checks = [
        M.J.run_check(command, root)
        for command in [
            [M.S.PYTHON, "-B", "-m", "pytest", "-q", "tests", private],
            [M.S.PYTHON, "-B", "-m", "ruff", "format", "--check", "src", "tests"],
            [M.S.PYTHON, "-B", "-m", "ruff", "check", "src", "tests"],
            [M.S.PYTHON, "-B", "-m", "pyright", "--pythonpath", M.S.PYTHON],
        ]
    ]
    M.S.save(root.parent / "independent-checks.json", checks)
    gate.verify_handoff(root, report, config=config)
    print(checks[0]["stdout"][-1400:])
    print("Independent checks:", [c["exit_code"] for c in checks])
    assert all(c["exit_code"] == 0 for c in checks), checks


if __name__ == "__main__":
    main()
