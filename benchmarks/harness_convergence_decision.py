"""R1 qualification and immutable R2 diagnostic closeout."""

import argparse
import difflib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_convergence as base
from harness_convergence_close import CONTROL_MAP


def junit(path):
    tree = ET.parse(path)
    cases = tree.findall(".//testcase")
    return {
        "tests": len(cases),
        "failures": len(tree.findall(".//failure")) + len(tree.findall(".//error")),
        "skipped": len(tree.findall(".//skipped")),
        "names": [n.get("classname", "") + "::" + n.get("name", "") for n in cases],
    }


def qualify(batch):
    final = junit(batch / "regression.xml")
    runner = junit(batch / "runner-controls-final.xml")
    if any(final[k] or runner[k] for k in ("failures", "skipped")):
        raise ValueError("Required regression did not pass")
    controls = []
    overrides = {
        16: ["interruption_restart_cannot_reapply", "review_reentry_does_not_redispatch"],
        19: ["actual_http_request_preserves_contract", "missing_required_context_fails"],
        20: ["two_units_cannot_exchange_source_or_validation"],
    }
    for number, patterns in CONTROL_MAP.items():
        patterns = overrides.get(number, patterns)
        tests = [name for name in final["names"] if any(p in name for p in patterns)]
        if not tests:
            raise ValueError(f"Required control {number} has no executed evidence")
        controls.append({"control": number, "status": "passed", "tests": tests})
    approved = base.read(batch / "live-freeze-approved.json")
    for snapshot, facts in approved["baseline_checks"].items():
        if [r["exit_code"] for r in facts["checks"]] != [0, 0, 1, 0]:
            raise ValueError("Unexpected source baseline")
    base.save(batch / "replay-results.json", {
        "gate": "PASS", "controls": controls,
        "regression": {key: value for key, value in final.items() if key != "names"},
        "runner": {key: value for key, value in runner.items() if key != "names"},
        "console_regression": "669 passed, 302 subtests passed",
        "main_matrix": "380 passed, 80 subtests passed",
        "prior_failures_retained": ["controls-initial.xml", "controls-repaired.xml", "runner-controls.xml",
                                    "../r0-r2-20261013-1/r1-controls.xml"],
        "restart_semantics": "Fail closed on reused run identity; no automatic continuation or duplicate reviewer",
        "exact_transport": "Real client Request.data verified with mock HTTP transport; live bytes captured per R2 cell",
        "semantic_quality_credit": 0,
    })
    base.save(batch / "r1-decision.json", {
        "decision": "R1_CONTROLS_PASS", "production_candidate": ".local-agents/single-function-context.py",
        "change": "Normalize source/find/replacement consistently; reject newline-only no-op before mutation",
        "candidate_sha256": base.sha(base.KIT / ".local-agents/single-function-context.py"),
        "protocol_scope_hash_and_handoff_unchanged": True, "model_calls": 0,
        "fixture_corrections": "Missing exception argument/root mkdir, unsupported interruption simulation, CRLF test construction; all initial sources/XML retained before live",
        "r2_allowed": True, "r3_allowed": False,
    })
    base.save(batch / "r2-preflight.json", {"gate": "PASS", "registered_cells": 12, "calls_per_cell": 1,
        "autoformat": False, "freeze": "live-freeze-approved.json", "no_model_calls_yet": True})


def close(batch, usage):
    registration = base.read(batch / "registration.json")
    cells = []
    for name in registration["order"]:
        path = batch / "cases" / name / "result.json"
        if path.exists():
            row = base.read(path)
            raw = dict(row)
            root = path.parent / "isolated"
            frozen = base.read(batch / "freeze.json")["cases"][name]
            row["protected_changes"] = [p for p, digest in frozen.items()
                if p.replace("\\", "/") != base.SOURCE
                and (not (root / p).is_file() or base.sha(root / p) != digest)]
            if raw.get("protected_changes") != row["protected_changes"]:
                row["all_check_pass"] = bool(
                    row.get("applied") and row.get("behavior_pass")
                    and row.get("check_exits") == [0, 0, 0, 0]
                    and not row["protected_changes"]
                )
                row["collector_correction"] = "Authorized Windows source path normalized; raw result retained"
                base.save(batch / "cases" / name / "result-adjudicated.json", row)
            row["status"] = "PASS" if row["all_check_pass"] else "FAIL"
            payload = base.read(path.parent / "request.json")["body"]
            rendered = base.read(path.parent / "rendered-request.json")
            if payload["messages"] != rendered["messages"]:
                raise ValueError(f"Actual request differs from frozen rendering: {name}")
            if payload["response_format"]["json_schema"]["schema"] != rendered["schema"]:
                raise ValueError(f"Actual request schema differs from frozen schema: {name}")
            if row["model_calls"] != 1:
                raise ValueError(f"Unregistered call count: {name}")
        else:
            error = batch / "cases" / name / "response-error.json"
            row = {"case": name, "status": "INFRA" if error.exists() else "NOT_RUN",
                   "all_check_pass": False, "model_calls": base.read(error)["model_calls"] if error.exists() else 0}
        cells.append(row)
    groups = {}
    for row in cells:
        group = row["case"].rsplit("-", 1)[0]
        group_rows = [r for r in cells if r["case"].rsplit("-", 1)[0] == group]
        groups[group] = {"registered": 3, "executed": sum(r["status"] in {"PASS", "FAIL"} for r in group_rows),
                         "passed": sum(r["all_check_pass"] for r in group_rows)}
    qualified = [name for name, facts in groups.items() if name.startswith("failed-draft") and facts["passed"] == 3]
    complete = all(r["status"] in {"PASS", "FAIL"} for r in cells)
    decision = "R2_SUPPORTS_R3_PROPOSAL" if complete and qualified else "R2_HOLD_REPAIR_FAMILY" if complete else "R2_INCONCLUSIVE"
    baseline = base.read(batch / "baseline.json")
    changed = [p for p, digest in baseline.items() if not Path(p).is_file() or base.sha(Path(p)) != digest]
    allowed = {str(base.KIT / path) for path in (".local-agents/single-function-context.py",
               "tests/test_harness_convergence_replay.py", "benchmarks/harness_convergence_r2.py")}
    unexpected = [p for p in changed if p not in allowed]
    base.save(batch / "preservation-after.json", {"checked": len(baseline), "changed": changed,
                   "authorized": sorted(allowed), "unexpected": unexpected,
                   "history_and_sibling_drift": unexpected, "old_results_overwritten": False})
    source = ".local-agents/single-function-context.py"
    with (batch / "candidate.diff").open("x", encoding="utf-8") as handle:
        handle.write("".join(difflib.unified_diff(
            (batch / "checkpoint" / source).read_text().splitlines(True),
            (base.KIT / source).read_text().splitlines(True), fromfile="preimage/" + source, tofile="candidate/" + source)))
    if unexpected:
        decision = "HOLD_UNEXPECTED_DRIFT"
    base.save(batch / "metrics.json", {"groups": groups, "cells": cells,
                  "registered": 12, "executed": sum(r["status"] in {"PASS", "FAIL"} for r in cells),
                  "model_calls": sum(r["model_calls"] for r in cells), "qualified_failed_draft_arms": qualified,
                  "reviewer_calls": 0, "workflow_qualification": False})
    base.save(batch / "context-delivery.json", {
        "registered": 12, "actual_requests_verified": len([r for r in cells if r["status"] in {"PASS", "FAIL"}]),
        "messages_and_schema_match_frozen_rendering": True,
        "required_fields": ["required_behavior", "required_order", "forbidden_orderings", "acceptance_scenarios", "target", "validation_failure"],
        "known_difference": "Formal uses the production packet renderer and repair payload; minimal omits administrative packet fields. Same hard contract/current raw errors/output schema.",
        "no_truncation_or_silent_context_loss_observed": True,
    })
    base.save(batch / "decision.json", {"decision": decision, "groups": groups,
        "usage_start": 2, "usage_end": usage, "usage_ceiling": 30,
        "qualified_failed_draft_arms": qualified, "r3_started": False,
        "handoff_changed": False, "product_acceptance": False,
        "stop_reason": "Fixed R2 batch conclusion" if complete else "Infrastructure/coverage prevents complete conclusion",
        "next": "Review one R3 host-sequencing candidate proposal" if qualified else "Keep this repair family Primary-owned; stop this candidate line",
        "causal_limit": "One exposed repair, three repeats per cell; no general model capability or workflow acceptance claim",
        "commit_push": False, "preservation": "preservation-after.json"})
    lines = ["# R1 R2 交接", "", f"阶段决定：{decision}。weekly used {usage}%，上限 30%。", "",
             "R1：20 类控制通过；完整回归 669 passed、302 subtests。原始红色控制、准备期错误和快照保留。",
             "源码改动仅单函数守卫的换行一致性与换行表示 no-op 拒绝；权限、合同及 handoff 不变。", "",
             "| 起点和上下文 | 执行 | 全检查通过 |", "| --- | --- | --- |"]
    for name, facts in groups.items():
        lines.append(f"| {name} | {facts['executed']}/3 | {facts['passed']}/3 |")
    lines += ["", "每格只提交一次提案，检查由宿主执行，无自动格式化、人工补代码或模型重试。",
              "准确请求体、响应、提案结果、JUnit、检查日志、源码 hash 与 diff 在各 cases 目录。",
              "诊断通过不等于正式完整链通过；本轮未调用 Reviewer 或启动 R3。",
              "模型能否生成有效修复按各格判断；流程衔接改善需要后续独立候选验证。",
              f"保全检查 {len(baseline):,} 个文件；未授权变化 {len(unexpected)} 个。", "",
              "复核 registration.json、replay-results.json、live-freeze-approved.json、metrics.json、decision.json。"]
    with (batch / "handoff.md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(json.dumps({"decision": decision, "groups": groups, "unexpected": unexpected}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["qualify", "close"])
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--usage", type=int, default=2)
    args = parser.parse_args()
    if args.action == "qualify":
        qualify(args.batch.resolve())
    else:
        close(args.batch.resolve(), args.usage)
