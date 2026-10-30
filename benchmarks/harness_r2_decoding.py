"""One-factor decoding comparison; never changes production runtime files."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import harness_r2_output as output

B = output.B
old = output.old
PREVIOUS = B.KIT / "benchmarks/work/harness-convergence/r2-output-20261014-1"
ORDER = ("schema-1", "plain-1", "plain-2", "schema-2", "schema-3", "plain-3")


@contextmanager
def decoding(module, arm):
    if arm not in ("schema", "plain"):
        raise ValueError("Unregistered decoding arm")
    original = module.LMStudioClient

    def client(*args, **kwargs):
        kwargs["structured_output"] = arm == "schema"
        return original(*args, **kwargs)

    with patch.object(module, "LMStudioClient", client):
        yield


def wire_matches(request, rendered, reference=None):
    actual = copy.deepcopy(request)
    response_format = actual.pop("response_format", None)
    expected = (
        {
            "type": "json_schema",
            "json_schema": {
                "name": "local_coder_action",
                "strict": True,
                "schema": output.WHOLE_SCHEMA,
            },
        }
        if rendered["arm"] == "schema"
        else None
    )
    return (
        response_format == expected
        and (rendered["arm"] != "plain" or "response_format" not in request)
        and actual["messages"] == rendered["messages"]
        and (reference is None or actual == reference)
    )


def prepare(batch, usage):
    allowed = B.KIT / "benchmarks/work/harness-convergence"
    if not batch.is_relative_to(allowed) or batch == allowed or not 0 <= usage < 15:
        raise ValueError("Bounded new batch below usage stop required")
    batch.mkdir(parents=True, exist_ok=False)
    existing = set(map(Path, B.read(PREVIOUS / "baseline.json")))
    existing.update(B.files(PREVIOUS))
    listed = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=B.KIT,
        text=True,
        encoding="utf-8",
    ).splitlines()
    existing.update(B.KIT / p for p in listed if (B.KIT / p).is_file())
    baseline = {}
    for index, path in enumerate(sorted(existing), 1):
        baseline[str(path)] = B.sha(path)
        if index % 20000 == 0:
            print(f"Preservation hashed {index}/{len(existing)}", flush=True)
    B.save(batch / "baseline.json", baseline)
    for relative in listed:
        source = B.KIT / relative
        if source.is_file():
            target = batch / "checkpoint" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    B.save(
        batch / "environment.json",
        {
            "weekly_used": usage,
            "stop": 15,
            "git_status": B.command(["git", "status", "--short"]),
            "head": B.command(["git", "rev-parse", "HEAD"]),
            "residency": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
            "siblings": {
                name: B.command(
                    ["git", "-C", str(B.KIT.parent / name), "status", "--short"]
                )
                for name in ("agent-runtime-kit", "agent-evaluation-harness")
            },
            "seed": "unknown; unchanged",
            "actual_kv_cache": "unknown",
        },
    )
    reference = PREVIOUS / "cases/whole-1/isolated"
    frozen = B.read(PREVIOUS / "freeze.json")["cases"]["whole-1"]
    if any(B.sha(reference / p) != h for p, h in frozen.items()):
        raise ValueError("Historical no-op fixture drift")
    rendered = B.read(PREVIOUS / "cases/whole-1/rendered-request.json")
    prior_freeze = B.read(PREVIOUS / "live-freeze-approved.json")
    if (
        B.sha(PREVIOUS / "cases/whole-1/rendered-request.json")
        != prior_freeze["rendered"]["whole-1"]
    ):
        raise ValueError("Historical prompt drift")
    for name in ORDER:
        root = batch / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for folder in ("src", "tests"):
            shutil.copytree(
                reference / folder,
                root / folder,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".ruff_cache"),
            )
        shutil.copyfile(reference / "pyproject.toml", root / "pyproject.toml")
        packet = B.read(reference / ".agent/packet.json")
        packet["run_id"] = batch.name + "-" + name
        B.save(root / ".agent/packet.json", packet)
        B.save(root / ".agent/config.json", B.read(reference / ".agent/config.json"))
        B.save(
            root.parent / "rendered-request.json",
            {**rendered, "arm": name.split("-")[0]},
        )
    facts = old.checks(
        batch / "cases" / ORDER[0] / "isolated", batch, "baseline-checks"
    )
    if [r["exit_code"] for r in facts["checks"]] != [0, 0, 1, 0] or not facts["junit"][
        "all_behavior_pass"
    ]:
        raise ValueError("Unexpected baseline checks")
    B.save(
        batch / "registration.json",
        {
            "stage": "R2_DECODING",
            "feature_id": "single-function-decoding-factor",
            "risk": {"feature": "high", "unit": "high", "integration": "high"},
            "risk_rationale": "Preserve exact scope and sequential/cancellation invariant in isolated fixture",
            "owned_contract_ids": [
                "sequential-trace-batch",
                "preservation",
                "diagnostic-attribution",
            ],
            "dependencies": [
                "R1 controls",
                "strict whole adapter controls",
                "transport controls",
            ],
            "authorization": "2026-10-14 继续下一步吧 following decoding comparison proposal",
            "order": list(ORDER),
            "registered_cells": 6,
            "model_calls_per_cell": 1,
            "changed_factor": "HTTP response_format present json_schema vs absent",
            "fixed": "whole-1 messages, model, sampling, context/output budgets, parser, binding, protected tests",
            "gate": "Fixed arm 3/3 all-check; all six complete, wire equal except response_format, preservation intact",
            "autoformat": False,
            "retry": False,
            "reviewer_calls": 0,
            "weekly_used_start": usage,
            "usage_ceiling": 15,
            "stop": "Six ordinary outcomes; infrastructure/safety/usage stop preserves NOT_RUN; no second candidate",
        },
    )
    B.save(
        batch / "freeze.json",
        {
            "cases": {
                name: output.file_map(batch / "cases" / name / "isolated")
                for name in ORDER
            }
        },
    )
    print(
        json.dumps({"prepared": str(batch), "preserved_paths": len(baseline)}),
        flush=True,
    )


def freeze(batch, controls):
    tree = ET.parse(controls)
    if list((batch / "cases").glob("*/started.json")) or not tree.findall(
        ".//testcase"
    ):
        raise ValueError("Cannot freeze after live or without controls")
    if any(tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")):
        raise ValueError("Controls incomplete")
    dependencies = [Path(__file__), B.KIT / B.PLAN] + [
        B.KIT / path
        for path in (
            "benchmarks/harness_r2_output.py",
            "benchmarks/harness_r2_localized.py",
            "benchmarks/harness_convergence.py",
            "benchmarks/harness_convergence_r2.py",
            "tests/test_harness_r2_decoding.py",
            "tests/test_harness_r2_output.py",
        )
    ]
    B.save(
        batch / "live-freeze-approved.json",
        {
            "runtime": {
                str(p.relative_to(B.KIT)): B.sha(p)
                for p in B.files(B.KIT / ".local-agents")
            },
            "drivers": {str(p.relative_to(B.KIT)): B.sha(p) for p in dependencies},
            "controls": {"path": str(controls), "sha256": B.sha(controls)},
            "order": list(ORDER),
            "batch_files": {
                p: B.sha(batch / p) for p in ("registration.json", "freeze.json")
            },
            "rendered": {
                n: B.sha(batch / "cases" / n / "rendered-request.json") for n in ORDER
            },
        },
    )


def run(batch, name, usage):
    frozen = B.read(batch / "live-freeze-approved.json")
    if name not in ORDER or not 0 <= usage < 15:
        raise ValueError("Unregistered case or usage stop")
    for earlier in ORDER[: ORDER.index(name)]:
        result = B.read(batch / "cases" / earlier / "result.json")
        wire = B.read(batch / "cases" / earlier / "wire-verification.json")
        if result.get("protected_changes") or not wire["matches"]:
            raise ValueError("Earlier safety/evidence failure")
    for path, digest in frozen["batch_files"].items():
        if B.sha(batch / path) != digest:
            raise ValueError("Registration changed")
    if B.sha(Path(frozen["controls"]["path"])) != frozen["controls"]["sha256"]:
        raise ValueError("Controls changed")
    case = batch / "cases" / name
    if B.sha(case / "rendered-request.json") != frozen["rendered"][name]:
        raise ValueError("Input drift")
    rendered = B.read(case / "rendered-request.json")
    binding = json.loads(rendered["messages"][1]["content"])["target"]
    B.save(case / "usage-before.json", {"weekly_used": usage, "stop": 15})
    module = old.load_runtime()
    try:
        with (
            output.interface(module, "whole", binding),
            decoding(module, rendered["arm"]),
            patch.object(old, "load_runtime", return_value=module),
        ):
            old.run(batch, name)
    except Exception as exc:
        B.save(
            case / "execution-error.json",
            {"type": type(exc).__name__, "message": str(exc)},
        )
        raise
    request = B.read(case / "request.json")["body"]
    reference = B.read(PREVIOUS / "cases/whole-1/request.json")["body"]
    reference.pop("response_format")
    matches = wire_matches(request, rendered, reference)
    B.save(
        case / "wire-verification.json",
        {"matches": matches, "only_factor": "response_format"},
    )
    if not matches:
        raise ValueError("Wire differs beyond registered factor")


def close(batch, usage):
    rows = {}
    for name in ORDER:
        case = batch / "cases" / name
        rows[name] = (
            B.read(case / "result.json")
            if (case / "result.json").exists()
            else {
                "terminal": "INCOMPLETE_INFRA"
                if (case / "started.json").exists()
                else "NOT_RUN",
                "all_check_pass": False,
            }
        )
    drift = []
    baseline = B.read(batch / "baseline.json")
    for index, (path, digest) in enumerate(baseline.items(), 1):
        if not Path(path).is_file() or B.sha(Path(path)) != digest:
            drift.append(path)
        if index % 20000 == 0:
            print(f"Preservation verified {index}/{len(baseline)}", flush=True)
    wires = all(
        (batch / "cases" / n / "wire-verification.json").exists()
        and B.read(batch / "cases" / n / "wire-verification.json")["matches"]
        for n in ORDER
    )
    scores = {
        arm: sum(
            r.get("all_check_pass") is True
            for n, r in rows.items()
            if n.startswith(arm)
        )
        for arm in ("schema", "plain")
    }
    qualified = (
        [arm for arm, score in scores.items() if score == 3]
        if wires and not drift
        else []
    )
    B.save(
        batch / "decision.json",
        {
            "stage": "R2_DECODING",
            "decision": "R2_DECODING_PASS" if qualified else "R2_DECODING_HOLD",
            "scores": scores,
            "qualified_arms": qualified,
            "results": rows,
            "registered": 6,
            "wire_verified": wires,
            "preservation_drift": drift,
            "preserved_paths": len(baseline),
            "weekly_used_end": usage,
            "usage_stop": 15,
            "historical_hold_unchanged": True,
            "r3_started": False,
            "r4_admission": False,
            "product_acceptance": False,
            "primary_live_intervention": False,
            "scope_limit": "One exposed static repair; not general model capability or multi-file readiness",
        },
    )
    print(
        json.dumps({"scores": scores, "qualified": qualified, "drift": len(drift)}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "run", "close"])
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--usage", required=True, type=int)
    parser.add_argument("--case")
    parser.add_argument("--controls", type=Path)
    args = parser.parse_args()
    batch = args.batch.resolve()
    if args.action == "prepare":
        prepare(batch, args.usage)
    elif args.action == "freeze":
        freeze(batch, args.controls.resolve())
    elif args.action == "run":
        run(batch, args.case, args.usage)
    else:
        close(batch, args.usage)
