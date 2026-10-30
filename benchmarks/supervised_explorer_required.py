"""Exercise existing required-read recovery on the same navigation-scoped tasks."""

import json
import shutil
from pathlib import Path

import bounded_evidence_support as S
import supervised_explorer_scoped as C
import supervised_explorer_trial as E

BATCH = E.BATCH.with_name("supervised-explorer-required-20261020-1")


def prepare():
    if not (C.BATCH / "decision.json").exists():
        raise ValueError("Prior comparison must close")
    old = S.read(C.BATCH / "registration.json")
    rows = {}
    for cell, row in old["cells"].items():
        root = BATCH / "cells" / cell
        root.mkdir(parents=True, exist_ok=False)
        for name, digest in row["files"].items():
            source = Path(row["root"]) / name
            if S.sha(source) != digest:
                raise ValueError("Frozen input changed")
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        config = S.read(root / ".agent/config.json")
        config["explorer_required_citation_paths"] = C.HINTS[cell.rsplit("-", 1)[0]]
        (root / ".agent/config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        rows[cell] = {
            **row,
            "root": str(root),
            "files": {name: S.sha(root / name) for name in row["files"]},
        }
    S.save(
        BATCH / "registration.json",
        {
            **old,
            "cells": rows,
            "candidate": "Same exact scoped questions, existing Explorer config requires citation of the already supplied paths; existing empty-search recovery enforces actual READ_FILE. No runtime change or new semantic hints.",
            "pins": {
                str(p): S.sha(p)
                for p in [Path(__file__).resolve(), Path(E.__file__).resolve()]
            },
            "gate": "All4/4 complete correct independent locating reports, same budgets, no false coverage claims or safety drift",
        },
    )
    print("Existing required-read mechanism frozen for four exposed cells")


if __name__ == "__main__":
    prepare()
