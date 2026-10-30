"""Four fixed, exposed syntax-repair cells; only diagnostic parser differs."""

import argparse
import ast
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import prepared_task_matrix as M

S, T, P = M.S, M.T, M.P
CONTROLS = P.I.BASE / "ruff-syntax-focus-20261022-1"
BATCH = P.I.BASE / "ruff-syntax-focus-20261022-2"
OLD = P.I.BASE / "noop-block-recovery-20261022-1"
ORDER = ["syntax-B1", "syntax-A1", "syntax-A2", "syntax-B2"]


def prepare(used):
    controls = {}
    for name in ("green.xml", "core.xml"):
        suites = list(ET.parse(CONTROLS / name).getroot().iter("testsuite"))
        assert all(
            int(s.attrib.get(k, 0)) == 0
            for s in suites
            for k in ("failures", "errors", "skipped")
        )
        controls[name] = sum(int(s.attrib["tests"]) for s in suites)
        assert controls[name] > 0
    old = S.read(OLD / "cells.json")["legacy-B2"]
    root = Path(old["root"])
    source_path = root / M.TARGET
    source = source_path.read_text(encoding="utf-8")
    node = next(n for n in ast.parse(source).body if getattr(n, "name", None) == "_sse")
    packet = S.read(root / ".agent/packet.json")
    spec = {
        "header": "".join(source.splitlines(keepends=True)[: node.lineno - 1]),
        "start": T.extract(source_path, "_sse"),
        "reference": T.extract(OLD / "reference-checks/legacy" / M.TARGET, "_sse"),
        "symbol": "_sse",
        "contract": packet["goal"],
        "public": (root / "tests/test_contract.py").read_text(encoding="utf-8"),
        "private": Path(old["private_tests"]).read_text(encoding="utf-8"),
        "cases": S.read(root / ".agent/capture-spec.json")["cases"],
        "scenarios": packet["acceptance_scenarios"],
        "risk_rationale": "Preserve exact event encoding and Python target, no semantic or budget expansion. Primary full review remains required.",
    }
    # Deliberately invalid Python-target syntax must not be repaired or refused
    # by fixture construction. Copy the exact archived draft, then run checks.
    template = BATCH / "templates/syntax"
    for name in (
        M.TARGET,
        "src/product/__init__.py",
        "tests/test_contract.py",
        "pyproject.toml",
    ):
        destination = template / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        assert not destination.exists()
        shutil.copyfile(root / name, destination)
    private = BATCH / "private/syntax/test_independent.py"
    private.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(old["private_tests"], private)
    reference = BATCH / "reference-checks/syntax"
    shutil.copytree(
        OLD / "reference-checks/legacy",
        reference,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
    )
    observed = {
        "baseline": M.L.checks(template, private),
        "reference": M.L.checks(reference, private),
    }
    S.save(BATCH / "task-controls/syntax.json", observed)
    assert observed["baseline"][0]["exit_code"] == 0
    assert any(check["exit_code"] != 0 for check in observed["baseline"])
    assert all(check["exit_code"] == 0 for check in observed["reference"])
    material = template, private, reference
    assert S.sha(material[0] / M.TARGET) == S.sha(source_path)
    assert S.sha(material[1]) == S.sha(old["private_tests"])
    rows = {}
    for label in ORDER:
        arm = label.split("-")[1][0]
        override = (
            {
                ".local-agents/worker-runtime.py": CONTROLS
                / "preimages/worker-runtime.py"
            }
            if arm == "A"
            else None
        )
        row = M.cell(
            BATCH,
            label,
            "syntax",
            spec,
            material,
            Path(__file__),
            runtime_override=override,
        )
        row["arm"], row["repeat"] = arm, int(label[-1])
        proof = BATCH / "replay" / label / "isolated"
        request = S.read(
            proof
            / ".agent/tasks"
            / row["identity"]["task_id"]
            / "runs"
            / row["identity"]["run_id"]
            / "proposal-request-1.json"
        )
        text = request["messages"][1]["content"]
        assert ("CURRENT_STATIC_DIAGNOSTIC\n" in text) == (arm == "B")
        if arm == "B":
            focus, _ = json.JSONDecoder().raw_decode(
                text.split("CURRENT_STATIC_DIAGNOSTIC\n", 1)[1]
            )
            assert focus[0]["rule"] == "invalid-syntax"
            assert focus[0]["source_sha256"] == row["start_sha256"]
            assert focus[0]["line"] == 22
        assert "Cannot use an escape sequence" in text
        rows[label] = row
    assert len({r["start_sha256"] for r in rows.values()}) == 1
    S.save(BATCH / "cells.json", rows)
    S.save(
        BATCH / "registration.json",
        {
            "feature_id": "current-ruff-syntax-diagnostic-localization",
            "feature_risk": "high",
            "unit_risk": "high",
            "integration_risk": "high",
            "registered": 4,
            "order": ORDER,
            "offline_controls": controls,
            "A": "Installed flat whole-function host, preserved pre-fix Worker parser; raw Ruff/Pyright evidence still visible.",
            "B": "Identical host/profile plus two-regex invalid-syntax recognition; exact message/path/line/current source hash displayed early. No semantic repair advice.",
            "exposure": "One exposed failed legacy-B2 draft, two repetitions per arm. Not a new task or rerun that replaces original results.",
            "common_budget": "C12requests/3edits/3post checks/1initial/12format preparations/2protocol recoveries/900s/4096output. R16requests/4errors/600s/4096output.2220s/cell,5400s/batch. No output-profile switch in either arm.",
            "models": {
                "coder": "qwen/qwen3-coder-30b",
                "reviewer": "meta/muse-glimmer",
                "context_length": 24576,
                "single_residency": True,
            },
            "gate": "B2/2 full independent acceptance with zero protection drift, assistance or wrong release; relative completion/request benefit must be separately observed. Parser correctness can pass without a Worker completion benefit. No general or recovery-profile promotion from this diagnostic task.",
            "continue_rule": "Finish all four on ordinary failure, retaining HOLD. Stop on safety/infrastructure/drift/deadline/user stop. No semantic hints, new attempts or same-code Reviewer rerolls.",
            "next_branch": "If no conversion gain, retain factual parser fix only; stop tuning exposed syntax task. Return to existing qualified supervised product path and compact handling of unresolved failures, not broader automatic repair.",
            "weekly_used_start": used,
            "weekly_cap": None,
            "primary": "Reuse exact original source/contract/checks and frozen reference. Primary-only cost comparison absent; preparation and per-cell final review remain, active seconds/cloud tokens unknown.",
            "pins": M.pins(
                BATCH,
                Path(__file__),
                S.KIT / "tests/test_ruff_syntax_focus.py",
                CONTROLS / "preimages/worker-runtime.py",
                CONTROLS / "green.xml",
                CONTROLS / "core.xml",
                material[1],
            ),
        },
    )
    print("Four fixed parser-only cells prepared; no live yet", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--cell", choices=ORDER)
    parser.add_argument("--weekly-used", type=int, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.weekly_used)
    else:
        P.BATCH, P.ORDER = BATCH, ORDER
        P.run(args.cell, args.weekly_used)
