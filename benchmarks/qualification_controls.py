"""Fresh blind Reviewer controls and Primary evidence access, no auto-acceptance."""

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

import qualification_matrix as MATRIX
import supervised_scope_check as SCOPE
from capability_fit import WORK, write
from inherited_context_recovery import digest, read

BASE = WORK / "qualification-controls-1"


def prepare():
    MATRIX.verify()
    BASE.mkdir(exist_ok=False)
    cases = read(MATRIX.BASE / "corpus.json")["cases"]
    oracles = read(MATRIX.BASE / "primary-oracles.json")
    data = []
    tests = {
        "display-default": "from product.target import display_name\n\ndef test_normal():\n    assert display_name({'name':'Ada'}) == 'Ada'\n    assert display_name({}) == 'unnamed'\n",
        "lookup-fallback": "from product.target import lookup_or\n\ndef test_normal():\n    assert lookup_or(lambda key:7,'k',99) == 7\n    def missing(key):\n        raise KeyError(key)\n    assert lookup_or(missing,'k',99) == 99\n",
    }
    for identity in tests:
        case = copy.deepcopy(next(c for c in cases if c["case_id"] == identity))
        case["files"]["tests/test_target.py"] = tests[identity]
        data.append(case)
    write(BASE / "corpus.json", {"cases": data})
    SCOPE.FA.MIXED.CORPUS, SCOPE.FA.MIXED.WORK = BASE / "corpus.json", BASE / "runs"
    cells = []
    for repetition in (1, 2):
        for case in data:
            identity = case["case_id"]
            for opaque, defect in (("a", False), ("b", True)):
                # MIXED requires failing initial assertions. Control initial text
                # is deliberately wrong even for the weakened normal tests.
                control = copy.deepcopy(case)
                control["files"]["src/product/target.py"] = (
                    "def display_name(record):\n    return 'initial'\n"
                    if identity == "display-default"
                    else "def lookup_or(fetch, key, default):\n    return 'initial'\n"
                )
                # Separate immutable preparation corpus avoids rewriting a freeze.
                path = BASE / f"corpus-{identity}-{opaque}-r{repetition}.json"
                write(path, {"cases": [control]})
                SCOPE.FA.MIXED.CORPUS = path
                root = Path(
                    SCOPE.FA.MIXED.prepare(
                        identity,
                        repetition,
                        MATRIX.SNAPSHOT / ".local-agents/config.json",
                        "control-" + opaque,
                    )["root"]
                )
                source = (
                    oracles[identity]["mutants"][
                        1 if identity == "lookup-fallback" else 0
                    ]["src/product/target.py"]
                    if defect
                    else oracles[identity]["reference"]["src/product/target.py"]
                )
                cells.append(
                    {
                        "id": f"{identity}-{opaque}-r{repetition}",
                        "root": str(root),
                        "source": source,
                        "has_defect_primary_only": defect,
                        "expected_defect": "Present None and empty string must not default"
                        if identity == "display-default" and defect
                        else "Non-KeyError exceptions must propagate unchanged"
                        if defect
                        else None,
                    }
                )
    write(
        BASE / "manifest.json",
        {
            "controls": cells,
            "driver_sha256": digest(Path(__file__)),
            "criterion": "Two families, hidden/clean twice. Primary checks actual causal findings and suggested repair. Synthetic archive has no Coder credit.",
            "weekly_used_ceiling": 70,
        },
    )
    print("prepared eight Reviewer controls")


def verify():
    MATRIX.verify()
    manifest = read(BASE / "manifest.json")
    if digest(Path(__file__)) != manifest["driver_sha256"]:
        raise ValueError("control driver drift")
    return manifest


def run(identity):
    SCOPE.BASE, SCOPE.SNAPSHOT = BASE, MATRIX.SNAPSHOT
    SCOPE.verify = verify
    SCOPE.control(identity)


def evidence(identity, unit):
    manifest = MATRIX.verify()
    cell = next(c for c in manifest["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / f".agent/{unit}-bound.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    print((archive / "cumulative.diff").read_text(encoding="utf-8"))
    for name in (
        f"{unit}-coder.json",
        f"{unit}-reviewer.json",
        f"{unit}-primary-checks.json",
    ):
        path = root / ".agent" / name
        if path.exists():
            data = read(path)
            print(
                json.dumps(
                    {
                        "file": name,
                        **{
                            k: v
                            for k, v in data.items()
                            if k
                            in (
                                "status",
                                "decision",
                                "findings",
                                "all_checks_pass",
                                "tests_executed",
                                "validation_summary",
                                "failure_reason",
                            )
                        },
                    }
                )
            )
    if (root / ".agent/explorer.json").exists():
        print(json.dumps(read(root / ".agent/explorer.json")))
    print(
        json.dumps(
            {
                "root": str(root),
                "task_id": packet["task_id"],
                "run_id": packet["run_id"],
            }
        )
    )


def record(identity, unit, decision, summary):
    cell = next(c for c in MATRIX.verify()["cells"] if c["id"] == identity)
    root = Path(cell["root"])
    packet = read(root / f".agent/{unit}-bound.json")
    subprocess.run(
        [
            sys.executable,
            str(MATRIX.SNAPSHOT / ".local-agents/record-review.py"),
            "--repo",
            str(root),
            "--task-id",
            packet["task_id"],
            "--run-id",
            packet["run_id"],
            "--decision",
            decision,
            "--summary",
            summary,
        ],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "evidence", "record"))
    parser.add_argument("identity", nargs="?")
    parser.add_argument("--unit", default="qual-unit")
    parser.add_argument(
        "--decision", choices=("accept", "rework", "replan", "takeover")
    )
    parser.add_argument("--summary")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "run":
        run(args.identity)
    elif args.action == "evidence":
        evidence(args.identity, args.unit)
    else:
        record(args.identity, args.unit, args.decision, args.summary)
