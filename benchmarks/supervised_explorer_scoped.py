"""Navigation-scoped Explorer comparison, no semantic answers or runtime changes."""

import shutil
from pathlib import Path

import bounded_evidence_support as S
import supervised_explorer_trial as E

BATCH = E.BATCH.with_name("supervised-explorer-scoped-20261019-1")
HINTS = {
    "raw": [
        "src/evaluation_harness/adapters/common.py",
        "src/evaluation_harness/adapters/generic_otel.py",
        "tests/unit/test_adapters.py",
    ],
    "fingerprint": [
        "src/evaluation_harness/canonical/fingerprint.py",
        "tests/unit/test_canonical.py",
    ],
}


def prepare():
    if not (E.BATCH / "decision.json").exists():
        raise ValueError("Prior batch not closed")
    previous = S.read(E.BATCH / "registration.json")
    rows = {}
    for cell, old in previous["cells"].items():
        root = BATCH / "cells" / cell
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in old["files"].items():
            source = Path(old["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Previous frozen source drift")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        hints = HINTS[cell.rsplit("-", 1)[0]]
        rows[cell] = {
            **old,
            "root": str(root),
            "question": old["question"]
            + " Likely paths for navigation only (not conclusions): "
            + ", ".join(hints)
            + ". Verify the evidence yourself.",
        }
    S.save(
        BATCH / "registration.json",
        {
            **previous,
            "cells": rows,
            "candidate": "Same installed Explorer/model/budget; only known source/test path navigation added before run",
            "exposure": "Both questions exposed; all prior failures retained",
            "gate": "4/4 independently verified locating reports under navigation-scoped packets; no false test coverage or protected drift",
            "primary_cost": "Primary selected likely paths using already observed repository. Navigation-assisted preparation; no in-run hints, semantic answers or implementation supplied. Not autonomous unknown-repository qualification.",
            "pins": {
                str(p): S.sha(p)
                for p in [Path(__file__).resolve(), Path(E.__file__).resolve()]
            },
        },
    )
    print("Four navigation-scoped Explorer cells frozen; no model calls")


if __name__ == "__main__":
    prepare()
