"""Matched exposed-draft diagnosis; only ordering of existing model facts changes."""

import argparse
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import bounded_evidence_support as S
import bounded_evidence_tasks as E
import prepared_slice_trial as T
from test_installable_bounded import INSTALL

BATCH = T.I.BASE / "failure-priority-20261022-1"
OLD = T.BATCH
ORDER = ["A1", "B1", "B2", "A2"]
ENTRY = S.KIT / "benchmarks/failure_priority_entry.py"
ORIGINAL_COMMAND = T.command


def command(root, mode="unit", replay=None):
    args = ORIGINAL_COMMAND(root, mode=mode, replay=replay)
    args[2] = str(ENTRY)
    if root.parent.name.startswith("B"):
        args.append("--failure-priority")
    return args


def prepare(used):
    suites = ET.parse(BATCH / "protocol-green.xml").getroot().findall("testsuite")
    assert suites and all(
        int(s.get("failures", 0))
        == int(s.get("errors", 0))
        == int(s.get("skipped", 0))
        == 0
        for s in suites
    )
    old = S.read(OLD / "cells.json")
    assert S.read(OLD / "decision.json")["accepted"] == 0
    rows = {}
    for cell in ORDER:
        seed = Path(old["message-id-" + cell[1]]["root"])
        with tempfile.TemporaryDirectory(
            prefix="priority-control-install-"
        ) as directory:
            staging = Path(directory)
            INSTALL.install(S.KIT, staging, apply=True)
            root = BATCH / "cells" / cell / "isolated"
            shutil.copytree(staging, root)
        for name in ("src", "tests"):
            shutil.copytree(
                seed / name,
                root / name,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", ".ruff_cache"
                ),
            )
        shutil.copyfile(seed / "pyproject.toml", root / "pyproject.toml")
        packet = S.read(seed / ".agent/packet.json")
        identity = {
            key: BATCH.name + "-" + cell for key in ("task_id", "unit_id", "run_id")
        }
        packet.update(identity)
        for name, value in (
            ("packet", packet),
            ("config", S.read(seed / ".agent/config.json")),
            ("capture-spec", S.read(seed / ".agent/capture-spec.json")),
        ):
            S.save(root / f".agent/{name}.json", value)
        setup = [
            S.PYTHON,
            "-B",
            root / ".local-agents/local-bounded-prepare.py",
            "--packet",
            ".agent/packet.json",
            "--config",
            ".agent/config.json",
            "--capture-spec",
            ".agent/capture-spec.json",
            "--apply",
        ]
        result = E.run(setup, root)
        S.save(BATCH / "preparation" / f"{cell}.json", result)
        assert result["exit_code"] == 0
        preflight = command(root, "preflight")
        preflight[preflight.index("--report") + 1] = str(root / ".agent/preflight.json")
        result = E.run(preflight, root)
        S.save(BATCH / "preflight" / f"{cell}.json", result)
        assert result["exit_code"] == 0
        proof = BATCH / "replay" / cell / "isolated"
        shutil.copytree(root, proof)
        response = proof.parent / "reference.json"
        S.save(
            response,
            [
                {
                    "kind": "replacement",
                    "content": E.extract(OLD / "reference-checks" / T.TARGET, T.SYMBOL),
                }
            ],
        )
        result = E.run(command(proof, replay=response), proof, timeout=180)
        S.save(proof.parent / "process.json", result)
        assert result["exit_code"] == 0
        rows[cell] = {
            "root": str(root),
            "identity": identity,
            "target": T.TARGET,
            "private_tests": str(OLD / "private/test_independent.py"),
            "seed": str(seed),
            "start_sha256": S.sha(root / T.TARGET),
            "files": {
                p.relative_to(root).as_posix(): S.sha(p)
                for p in root.rglob("*")
                if p.is_file()
                and not any(
                    v in p.parts
                    for v in ("__pycache__", ".pytest_cache", ".ruff_cache")
                )
            },
        }
    for suffix in ("1", "2"):
        a, b = rows["A" + suffix], rows["B" + suffix]
        assert a["start_sha256"] == b["start_sha256"]
        p1, p2 = (
            S.read(Path(a["root"]) / ".agent/packet.json"),
            S.read(Path(b["root"]) / ".agent/packet.json"),
        )
        for key in ("task_id", "unit_id", "run_id"):
            p1.pop(key)
            p2.pop(key)
        assert p1 == p2
    S.save(BATCH / "cells.json", rows)
    pins = [
        Path(__file__),
        ENTRY,
        Path(T.__file__),
        Path(T.I.__file__),
        Path(T.N.__file__),
        BATCH / "cells.json",
        OLD / "private/test_independent.py",
        BATCH / "protocol-green.xml",
    ]
    pins += [
        p
        for p in (S.KIT / ".local-agents").rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "failure-fact-priority-diagnostic",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "hypothesis": "Existing typed counterexamples may be more usable when placed before repeated contract metadata; not yet established as a cause of failure",
            "candidate": "Experimental wrapper reorders validation_failure and target first, then remaining unchanged facts; inner failure list before excerpt. No added/dropped content or instructions, same character count, source binding unchanged.",
            "arms": {
                "A": "current flat-v1 renderer",
                "B": "same entry with failure-priority ordering",
            },
            "order": ORDER,
            "registered": 4,
            "weekly_stop": None,
            "weekly_used_start": used,
            "batch_seconds": 5400,
            "pins": {str(p): S.sha(p) for p in pins},
            "exposure": "Two frozen failed drafts from the same now-exposed message ID task, matched pairs; original0/2 remains failed. No holdout or new task credit.",
            "controls": "9 lossless-render controls, equal payload length, every actual input roundtrips; four installed offline full-chain replays. Initial collection error used pytest's reserved request name, preserved separately.",
            "budget": S.read(OLD / "registration.json")["budget"],
            "models": S.read(OLD / "registration.json")["roles"],
            "gate": "B2/2 complete independent acceptance and improvement over A, no assisted edits/safety drift; otherwise no adoption. Even positive result needs separate transfer evidence before qualification.",
            "continue_rule": "Ordinary failure HOLD but finish fixed order; infra/safety/protected drift/time stops. No replacement units or extra retry, no new semantic hints. No further prompt variants on this task if no gain.",
            "unchanged": [
                "models",
                "scope",
                "contract",
                "public/private checks",
                "output schema",
                "edit/check/repair budgets",
                "Reviewer",
                "handoff",
                "production defaults",
            ],
            "Primary": "Preparation and independent review only; no semantic feedback during live; all actual inputs remain available in archives",
        },
    )
    print("Four matched exposed-draft cells ready; no live yet")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        T.BATCH, T.ORDER, T.command = BATCH, ORDER, command
        T.run(args.cell, args.weekly_used)
