"""One separately authorized R2 candidate; no production changes or retries."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import harness_convergence_r2 as old

B = old.base
PREVIOUS = B.KIT / "benchmarks/work/harness-convergence/r1-r2-20261013-2"
CHECK_KEYS = ("required_behavior", "required_order", "forbidden_orderings", "acceptance_scenarios")


def localized_messages(root, facts, diagnostics):
    current = old.repair_context(root, facts)
    lines = (root / B.SOURCE).read_text(encoding="utf-8-sig").splitlines()
    bound = []
    for error in diagnostics:
        path = Path(error["filename"]).resolve()
        if path != (root / B.SOURCE).resolve() or error["code"] != "E501":
            raise ValueError("Unexpected diagnostic scope/rule")
        line = error["location"]["row"]
        bound.append({"rule": error["code"], "path": B.SOURCE,
                      "line": line, "column": error["location"]["column"],
                      "message": error["message"], "current_source_line": lines[line - 1],
                      "source_sha256": current["target"]["sha256"]})
    if len(bound) != 2 or {e["line"] for e in bound} != {84, 90}:
        raise ValueError("Expected both frozen draft errors")
    current["validation_failure"] = {"check_id": "ruff-check", "exit_code": 1,
                                      "diagnostics": bound,
                                      "source_sha256": current["target"]["sha256"]}
    return [{"role": "system", "content": old.load_runtime().SINGLE_FUNCTION.PATCH_PROMPT},
            {"role": "user", "content": json.dumps(current, ensure_ascii=False)}]


def prepare(batch, usage):
    allowed = B.KIT / "benchmarks/work/harness-convergence"
    if not batch.is_relative_to(allowed) or batch == allowed or usage >= 15:
        raise ValueError("New bounded batch required below usage stop")
    batch.mkdir(parents=True, exist_ok=False)
    existing = B.read(PREVIOUS / "baseline.json")
    baseline = {p: B.sha(Path(p)) for p in existing if Path(p).is_file()}
    listed = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                                     cwd=B.KIT, text=True, encoding="utf-8").splitlines()
    for relative in listed:
        path = B.KIT / relative
        if path.is_file():
            baseline[str(path)] = B.sha(path)
            target = batch / "checkpoint" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    B.save(batch / "baseline.json", baseline)
    B.save(batch / "environment.json", {
        "usage_used": usage, "usage_stop": 15,
        "git_status": B.command(["git", "status", "--short"]),
        "git_head": B.command(["git", "rev-parse", "HEAD"]),
        "residency": B.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"]),
        "siblings": {name: B.command(["git", "-C", str(B.KIT.parent / name), "status", "--short"])
                     for name in ("agent-runtime-kit", "agent-evaluation-harness")}})
    order = [f"failed-draft-localized-{i}" for i in range(1, 4)]
    for name in order:
        root = batch / "cases" / name / "isolated"
        root.mkdir(parents=True)
        for folder in ("src", "tests"):
            shutil.copytree(B.FIXTURE / folder, root / folder,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".ruff_cache"))
        shutil.copyfile(B.FIXTURE / "pyproject.toml", root / "pyproject.toml")
        shutil.copyfile(B.LONG / B.SOURCE, root / B.SOURCE)
        packet = B.read(B.LONG / ".agent/packet.json")
        packet["run_id"] = "r2-localized-20261013-" + name
        B.save(root / ".agent/packet.json", packet)
        B.save(root / ".agent/config.json", B.read(B.LONG / ".agent/config.json"))
    case = batch / "cases" / order[0]
    root = case / "isolated"
    facts = old.checks(root, case, "baseline")
    if [r["exit_code"] for r in facts["checks"]] != [0, 0, 1, 0] or not facts["junit"]["all_behavior_pass"]:
        raise ValueError("Unexpected frozen baseline")
    observed = B.command([str(old.FIXTURE_PYTHON), "-B", "-m", "ruff", "check", "--output-format", "json", "src", "tests"], cwd=root)
    B.save(batch / "diagnostic-observation.json", observed)
    diagnostics = json.loads(observed["stdout"])
    if observed["exit_code"] != 1:
        raise ValueError("Expected real Ruff failure")
    for name in order:
        root = batch / "cases" / name / "isolated"
        # The three copies are byte-identical; rebind machine diagnostics only to current root.
        rebound = [{**e, "filename": str(root / B.SOURCE)} for e in diagnostics]
        B.save(batch / "cases" / name / "rendered-request.json", {
            "messages": localized_messages(root, facts, rebound),
            "schema": old.load_runtime().SINGLE_FUNCTION.PATCH_SCHEMA,
            "current_source_sha256": B.sha(root / B.SOURCE), "arm": "localized",
            "snapshot": "failed-draft"})
    B.save(batch / "registration.json", {
        "user_authorization": "开始吧 following new R2 repair candidate proposal",
        "feature_id": "r2-complete-localized-error-representation",
        "risk": {"feature": "high", "unit": "high", "integration": "high"},
        "risk_rationale": "Protected sequential/cancellation contract; diagnostic representation only",
        "owned_contract_ids": ["sequential-trace-batch", "preservation", "diagnostic-attribution"],
        "dependencies": ["R1 and new no-model controls pass before live"],
        "order": order, "registered_cells": 3, "proposals_per_cell": 1,
        "usage_ceiling": 15, "r2_gate": "Frozen 648-character draft 3/3 all-check pass",
        "candidate_change": "Replace raw Ruff text with complete hash-bound structured diagnostics; no system prompt or schema change",
        "unchanged": ["model", "sampling", "context", "one proposal", "hard contract", "protected tests", "formatter check-only", "checks", "exact patch guards"],
        "old_hold": str(PREVIOUS / "decision.json"), "r3_authorized": False,
        "no_reviewer": True, "no_retry": True, "product_acceptance": False})
    B.save(batch / "freeze.json", {"cases": {
        name: {p.relative_to(batch / "cases" / name / "isolated").as_posix(): B.sha(p)
               for p in B.files(batch / "cases" / name / "isolated")} for name in order}})
    print(json.dumps({"prepared": str(batch), "preserved_paths": len(baseline), "cases": 3}))


def freeze(batch, controls):
    import xml.etree.ElementTree as ET
    if list((batch / "cases").glob("*/started.json")):
        raise ValueError("Cannot freeze after live")
    tree = ET.parse(controls)
    if not tree.findall(".//testcase") or any(tree.findall(".//" + tag) for tag in ("failure", "error", "skipped")):
        raise ValueError("Offline controls failed")
    B.save(batch / "live-freeze-approved.json", {
        "runtime": {str(p.relative_to(B.KIT)): B.sha(p) for p in B.files(B.KIT / ".local-agents")},
        "drivers": {str(p.relative_to(B.KIT)): B.sha(p) for p in (
            Path(__file__), B.KIT / "benchmarks/harness_convergence.py",
            B.KIT / "benchmarks/harness_convergence_r2.py")},
        "controls": {"path": str(controls), "sha256": B.sha(controls)},
        "rendered": {name: B.sha(batch / "cases" / name / "rendered-request.json")
                     for name in B.read(batch / "registration.json")["order"]},
        "order": B.read(batch / "registration.json")["order"], "r3_authorized": False})


def run(batch, name, usage):
    frozen = B.read(batch / "live-freeze-approved.json")
    if usage >= 15 or B.sha(batch / "cases" / name / "rendered-request.json") != frozen["rendered"][name]:
        raise ValueError("Usage stop or request drift")
    B.save(batch / "cases" / name / "usage-before.json", {"used": usage, "stop": 15})
    old.run(batch, name)


def close(batch, usage):
    order = B.read(batch / "registration.json")["order"]
    rows = {name: B.read(batch / "cases" / name / "result.json")
            if (batch / "cases" / name / "result.json").exists() else {"terminal": "NOT_RUN"}
            for name in order}
    changed = [p for p, digest in B.read(batch / "baseline.json").items()
               if not Path(p).is_file() or B.sha(Path(p)) != digest]
    passed = sum(row.get("all_check_pass") is True for row in rows.values())
    B.save(batch / "decision.json", {"decision": "R2_PASS_LOCALIZED_DIAGNOSTIC" if passed == 3 and not changed else "R2_HOLD_LOCALIZED_DIAGNOSTIC",
        "registered": 3, "passed": passed, "results": rows, "preservation_drift": changed,
        "usage_end": usage, "usage_stop": 15, "r3_started": False, "r4_admission": False,
        "historical_hold_unchanged": True, "product_acceptance": False})
    print(json.dumps({"passed": passed, "preservation_drift": len(changed)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "freeze", "run", "close"])
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--usage", type=int, required=True)
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
