"""Immutable closeout for an R1 HOLD; never launches a model or edits runtime."""

from __future__ import annotations

import argparse
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import harness_convergence as capture


CONTROL_MAP = {
    1: ["valid_model_proposal_changes_only_target_method", "promotion_controls[valid]"],
    2: ["single_function_guard_matches_safe_editor_newlines"],
    3: ["concurrent_source_change", "duplicate_run_id", "authorized_path_and_current_hash"],
    4: ["missing_replace_target", "ambiguous_replace"],
    5: ["rejects_noop_without_spending", "failed_validation_second_noop"],
    6: ["bad_edit_cannot_write", "path_escape", "reparse_component"],
    7: ["promotion_controls[baseline]", "green_baseline_allows_edit"],
    8: ["scoped_formatter_safety_and_invalidation[ok]", "autoformat_changes_only_authorized"],
    9: ["scoped_formatter_safety_and_invalidation"],
    10: ["ruff_f821_becomes_early_repair_focus", "junit_failure_summary", "static_fail"],
    11: ["block_after_validation_keeps_actual_validation_facts"],
    12: ["single_failed_validation_noop_allows_real_edit", "finish_cannot_use_validation_from_before_edit"],
    13: ["all_skipped_tests", "promotion_controls[zero]", "changed_input_cannot_handoff", "timed_out_validation"],
    14: ["promotion_controls[unknown]", "promotion_controls[false]", "green_diagnostic_claims_cannot_bypass"],
    15: ["patch_phase_real_loop_requires_fresh_validation"],
    16: ["duplicate_run_id_is_blocked", "stale_convenience_report_cannot_trigger"],
    17: ["verified_archive_can_handoff", "independent_pass_requires_changed_source", "high_risk_contract_review"],
    18: ["legacy_contract_ids_remain_compatible", "patch_mode_configuration_is_explicit"],
    19: ["context_delivers_all_contracts", "missing_required_context_fails"],
    20: ["packet_disk_state_mismatch", "context_keeps_task_constraints"],
}


def close(batch, usage):
    batch = batch.resolve()
    if (batch / "decision.json").exists():
        raise FileExistsError("Already closed; never overwrite history")
    rows = []
    for name in ("r1-controls.xml", "r1-reviewer-controls.xml"):
        tree = ET.parse(batch / name)
        for node in tree.findall(".//testcase"):
            failure = node.find("failure")
            error = node.find("error")
            rows.append({"id": node.get("classname", "") + "::" + node.get("name", ""),
                         "status": "failed" if failure is not None or error is not None else
                                   "skipped" if node.find("skipped") is not None else "passed",
                         "message": failure.get("message") if failure is not None else
                                    error.get("message") if error is not None else None,
                         "junit": name})
    controls = []
    for number, patterns in CONTROL_MAP.items():
        selected = [row for row in rows if any(p in row["id"] for p in patterns)]
        status = "failed" if any(r["status"] == "failed" for r in selected) else \
                 "covered" if selected else "not_covered"
        limitations = []
        if number == 10:
            limitations.append("F821/JUnit localization covered; real E501 fixture checks not run because gate closed")
        if number == 16:
            status = "partial" if status == "covered" else status
            limitations.append("Duplicate identity and stale report prevention covered; general crash/resume idempotence not established")
        if number == 19:
            status = "partial" if status == "covered" else status
            limitations.append("Renderer and missing-field controls covered; exact HTTP dispatch capture remains NOT_RUN")
        if number == 20:
            status = "partial" if status == "covered" else status
            limitations.append("Packet identity/current version covered; full cross-unit injection control remains NOT_RUN")
        controls.append({"control": number, "status": status, "tests": selected, "limitations": limitations})
    failures = [row for row in rows if row["status"] == "failed"]
    capture.save(batch / "replay-results.json", {
        "controls": controls, "cases": rows, "model_calls": 0,
        "required_controls_complete_and_passed": False,
        "junit_testcase_count": len(rows), "failures": failures,
        "console_counts": {"main": {"passed": 288, "failed": 3, "subtests_passed": 55},
                           "independent_review": {"passed": 4, "failed": 0}},
        "mock_checks_are_not_model_or_real_fixture_success": True,
    })
    capture.save(batch / "context-delivery.json", {
        "renderer_controls": [r for r in rows if "context_delivers_all_contracts" in r["id"]
                              or "missing_required_context" in r["id"]],
        "actual_r2_requests": 0, "sent_payload_capture": "NOT_RUN; R1 gate closed",
        "cannot_claim_model_received_context": True,
    })
    root_config = capture.read(capture.KIT / ".local-agents/config.json")
    resident = capture.command(["C:/Users/Lin/.lmstudio/bin/lms.exe", "ps"])
    try:
        with urllib.request.urlopen(root_config["lmstudio_base_url"] + "/models", timeout=10) as response:
            models = json.load(response)
    except Exception as exc:
        models = {"error": type(exc).__name__, "message": str(exc)}
    capture.save(batch / "environment-supplement.json", {
        "resident_unsandboxed": resident, "models_get_only": models,
        "usage_end": usage, "infrastructure": {
            "initial_lms_query": "Restricted lms ps stalled; only its verified PID was stopped. No model task was interrupted.",
            "native_python": "Baseline capture completed; no restart or overwritten output",
            "chronology": "Offline controls ran while read-only R0 hash/checkpoint capture completed. No pre-existing source/history edits; final registration completed before any model call (none occurred).",
        },
    })
    baseline = capture.read(batch / "baseline.json")
    changed = [path for path, digest in baseline.items()
               if not Path(path).is_file() or capture.sha(Path(path)) != digest]
    sibling_changes = [path for path in changed if "agent-evaluation-harness" in path or "agent-runtime-kit" in path]
    production_changes = [path for path in changed
                          if Path(path).is_relative_to(capture.KIT / ".local-agents")]
    cells = [{"case": name, "status": "NOT_RUN", "reason": "R1 required controls did not pass",
              "model_calls": 0, "patch_applied": None, "all_check_pass": None,
              "not_a_model_failure": True} for name in capture.read(batch / "registration.json")["order"]]
    capture.save(batch / "metrics.json", {"registered": 12, "executed": 0, "not_run": 12,
                 "cells": cells, "model_calls": 0, "reviewer_calls": 0,
                 "capability_score": None, "workflow_success_rate": None})
    capture.save(batch / "r2-preflight.json", {"gate": "HOLD", "reason": "R1 failure and coverage gaps",
                  "snapshots_frozen": True, "live_allowed": False, "new_live_candidate": False})
    capture.save(batch / "preservation-after.json", {
        "checked": len(baseline), "changed": changed, "sibling_changes": sibling_changes,
        "production_changes": production_changes,
        "new_files": ["benchmarks/harness_convergence.py", "benchmarks/harness_convergence_close.py",
                      "tests/test_harness_convergence_replay.py", str(batch)],
        "checkpoint_recoverable": (batch / "checkpoint/.local-agents/worker-runtime.py").exists(),
    })
    decision = {
        "stages": {"R0": "COMPLETE" if not changed else "DRIFT_REVIEW_REQUIRED",
                   "R1": "HOLD", "R2": "NOT_RUN"},
        "decision": "HOLD_AT_R1", "registered": 12, "executed": 0, "not_run": 12,
        "model_calls": 0, "usage_start": 1, "usage_end": usage, "usage_ceiling": 30,
        "stop_reason": "Required offline control failure; not usage limit or model capability failure",
        "confirmed": {
            "defect": "Single-function guard normalizes source to LF but compares raw CRLF find/replace. SafeEditor accepts the equivalent patch; runtime rejects it before application.",
            "production_locations": [".local-agents/single-function-context.py:55", ".local-agents/worker-runtime.py:3786", ".local-agents/safe-edit.py:187"],
            "variants": ["LF source / CRLF proposal", "CRLF source / CRLF proposal", "BOM+CRLF source / CRLF proposal"],
            "bytes_not_modified_on_rejection": True,
        },
        "limitations": ["This does not explain previous exact find=replace no-ops or cross-file semantic defects",
                        "R2 capability/context conclusions unavailable",
                        "Controls 16/19/20 remain partial; no complete restart or HTTP-delivery claim"],
        "next_unique_recommendation": "Authorize one newline-normalization parity repair in a separate candidate, complete the partial R1 controls, then re-register unchanged 12-cell R2. Do not increase prompts or budgets.",
        "r3_started": False, "handoff_changed": False, "production_changed": bool(production_changes),
        "brothers_changed": sibling_changes, "commit_push": False,
    }
    capture.save(batch / "decision.json", decision)
    handoff = f"""# R0 R1 R2 阶段交接

决定：HOLD_AT_R1。实际 weekly used {usage}%，上限 30%。停止原因是前置控制失败。

R0 已冻结 {len(baseline):,} 个文件，保留 dirty 工作文件快照与 tracked.diff。
原始 395 字符和归档 648 字符方法的源码/hash 已核对，12 个隔离单元已登记并冻结。
最终保全核对变化 {len(changed)} 个，生产 runtime 变化 {len(production_changes)} 个，兄弟变化 {len(sibling_changes)} 个。

R1 主批 288 passed、3 failed、55 subtests passed；独立审查证据控制另 4 passed。
三项失败为同一个确定性换行缺陷：SafeEditor 接受当前 hash 下的 CRLF 替换，
single-function guard 把源码归一成 LF 后仍用原 CRLF find 查找，误报定位不唯一。
LF 提案在 LF、CRLF、BOM+CRLF 文件上均通过。拒绝未产生写入或成功信用。

该缺陷是 harness/patch 接口适配问题，无模型参与。它不能解释此前准确的无变化替换、
流程提前 blocked 或跨文件业务逻辑错误。不能据此声称模型能力恢复或模型失败。

控制 16、19、20 只完成部分覆盖：重复身份/旧报告、防缺必需字段、packet 身份已测；
一般 crash/resume 幂等、准确 HTTP 请求捕获、完整跨单元注入还没有成立。
因此不能把已通过的普通回归宣称为完整 20 类 gate。

R2：registered 12，executed 0，NOT_RUN 12。每格状态见 metrics.json。
没有启动 LM completion、Reviewer、Explorer、Coordinator，没有 R3 或交接协议改动。

环境记录保留了一次 restricted lms ps 停滞，只结束了经核对的查询进程。
随后 unsandboxed inventory 核对仅 Qwen IDLE、24576、parallel 1；该事件不是 worker 质量失败。
离线重放与只读快照收尾曾重叠，未改已有源码或历史；没有把晚完成的记录伪称为早完成。

下一步唯一建议：独立授权一处换行归一化一致性修复，并补完 R1 剩余覆盖，
全部通过后重新登记原样 12 格。保留本次红色控制，不 xfail、不删门槛、不加提示或预算。

复核入口：registration.json、freeze.json、replay-results.json、r1-controls.xml、
context-delivery.json、metrics.json、preservation-after.json、decision.json。
"""
    with (batch / "handoff.md").open("x", encoding="utf-8") as handle:
        handle.write(handoff)
    print(json.dumps({"decision": decision["decision"], "frozen_paths": len(baseline),
                      "changed": changed, "registered": 12, "executed": 0}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--usage", required=True, type=int)
    args = parser.parse_args()
    close(args.batch, args.usage)
