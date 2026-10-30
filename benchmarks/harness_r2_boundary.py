"""Terminal-newline ownership candidate; isolated R2 only, no production writes."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import shutil
import subprocess
import textwrap
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import harness_r2_decoding as decoding_trial
import harness_r2_output as output
import harness_r2_rendering as rendering

B = output.B
old = output.old
PREVIOUS = B.KIT / "benchmarks/work/harness-convergence/r2-rendering-20261014-1"
ORDER = ("raw-1", "owned-1", "owned-2", "raw-2", "raw-3", "owned-3")


def terminal_boundary(args):
    """Own only the terminal line ending, not body layout or code repair."""
    if "blocked_reason" in args:
        return args
    result = copy.deepcopy(args)
    original = args["find"].replace("\r\n", "\n").replace("\r", "\n")
    replacement = args["replace"].replace("\r\n", "\n").replace("\r", "\n")
    if original.endswith("\n\n") or replacement.endswith("\n\n"):
        raise ValueError("Multiple terminal newlines outside function boundary")
    body = replacement.removesuffix("\n")
    tree = ast.parse(textwrap.dedent(body))
    if (
        len(tree.body) != 1
        or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef))
        or tree.body[0].end_lineno != len(body.splitlines())
    ):
        raise ValueError(
            "Replacement must end with the single function, not extra source"
        )
    result["replace"] = body + ("\n" if original.endswith("\n") else "")
    return result


@contextmanager
def boundary_interface(module, arm, binding):
    if arm == "raw":
        with output.interface(module, "whole", binding):
            yield
        return
    if arm != "owned":
        raise ValueError("Unknown boundary arm")
    original_parser = module.SINGLE_FUNCTION.patch_action
    bound = copy.deepcopy(binding)

    def parse(raw):
        args = terminal_boundary(output.normalize_whole(raw, bound))
        return original_parser(json.dumps(args, ensure_ascii=False))

    with (
        patch.object(module.SINGLE_FUNCTION, "PATCH_SCHEMA", output.WHOLE_SCHEMA),
        patch.object(module.SINGLE_FUNCTION, "patch_action", parse),
    ):
        yield


def wire_matches(request, rendered, reference):
    return (
        request == reference
        and rendering.restore_literal(request["messages"][1]["content"])
        == rendered["facts"]
        and request["messages"] == rendered["messages"]
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
    reference = PREVIOUS / "cases/json-1/isolated"
    frozen = B.read(PREVIOUS / "freeze.json")["cases"]["json-1"]
    if any(B.sha(reference / p) != h for p, h in frozen.items()):
        raise ValueError("Historical no-op fixture drift")
    rendered = B.read(PREVIOUS / "cases/literal-1/rendered-request.json")
    prior_freeze = B.read(PREVIOUS / "live-freeze-approved.json")
    if (
        B.sha(PREVIOUS / "cases/literal-1/rendered-request.json")
        != prior_freeze["rendered"]["literal-1"]
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
            {
                **rendered,
                "arm": name.split("-")[0],
                "messages": rendered["messages"],
                "facts": rendered["facts"],
            },
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
            "stage": "R2_BOUNDARY",
            "feature_id": "single-function-terminal-boundary",
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
                "terminal-boundary controls and same literal wire",
            ],
            "authorization": "2026-10-14 继续迭代直到R2通过或者weekly used到达15%",
            "order": list(ORDER),
            "registered_cells": 6,
            "model_calls_per_cell": 1,
            "changed_factor": "Host terminal-newline ownership: raw exact replacement vs canonical original terminal newline",
            "fixed": "literal-1 messages and facts, plain JSON, model, sampling, budgets, scope, protected checks",
            "gate": "Fixed arm 3/3 all-check; six complete, all wire identical to literal-1, preservation intact",
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
            "tests/test_harness_r2_rendering.py",
            "tests/test_harness_r2_boundary.py",
            "benchmarks/harness_r2_rendering.py",
            "benchmarks/harness_r2_decoding.py",
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
    binding = rendered["facts"]["target"]
    B.save(case / "usage-before.json", {"weekly_used": usage, "stop": 15})
    module = old.load_runtime()
    try:
        with (
            boundary_interface(module, rendered["arm"], binding),
            decoding_trial.decoding(module, "plain"),
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
    reference = B.read(PREVIOUS / "cases/literal-1/request.json")["body"]
    matches = wire_matches(request, rendered, reference)
    B.save(
        case / "wire-verification.json",
        {
            "matches": matches,
            "only_factor": "host terminal-newline binding; request identical",
        },
    )
    response = B.read(case / "response.json")["content"]
    try:
        args = output.normalize_whole(response, binding)
        normalized = terminal_boundary(args) if rendered["arm"] == "owned" else args
        B.save(
            case / "boundary-observation.json",
            {
                "arm": rendered["arm"],
                "changed_by_host": args != normalized,
                "raw_arguments": args,
                "applied_arguments": normalized,
                "scope": "terminal line ending only; no formatter",
            },
        )
    except (ValueError, SyntaxError) as exc:
        B.save(case / "boundary-observation.json", {"rejected": str(exc)})
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
        for arm in ("raw", "owned")
    }
    qualified = (
        [arm for arm, score in scores.items() if score == 3]
        if wires and not drift
        else []
    )
    B.save(
        batch / "decision.json",
        {
            "stage": "R2_BOUNDARY",
            "decision": "R2_BOUNDARY_PASS" if qualified else "R2_BOUNDARY_HOLD",
            "scores": scores,
            "qualified_arms": qualified,
            "results": rows,
            "registered": 6,
            "executed": sum("model_calls" in r for r in rows.values()),
            "not_run": sum(r["terminal"] == "NOT_RUN" for r in rows.values()),
            "weekly_used_start": B.read(batch / "registration.json")[
                "weekly_used_start"
            ],
            "candidate_sha256": B.sha(Path(__file__)),
            "stop_reason": "Fixed batch conclusion or recorded infrastructure/usage stop",
            "next": "R3 design only for qualified arm; otherwise close this factor series without more prompt candidates",
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
