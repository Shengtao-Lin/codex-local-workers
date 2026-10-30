"""Close the final bounded source-reference diagnostic and consolidate evidence."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import exception_reference_diagnostic as X


def close(used):
    T, batch = X.T, X.BATCH
    f, grid = T.read(batch / "fixture.json"), []
    for name, row in T.read(batch / "cells.json").items():
        cell = Path(row["root"]).parent
        r = T.read(cell / "result.json")
        wire = [T.read(p)["body"] for p in (cell / "wire").glob("*-request.json") if T.read(p)["url"].endswith("/chat/completions")]
        assert len(wire) == 1 and wire[0]["model"] == "qwen/qwen3-coder-30b" and wire[0]["max_tokens"] == 4096
        key = "both_user_message" if name.startswith("both-") else "reference_user_message" if name.startswith("reference-") else "user_message"
        assert wire[0]["messages"] == [{"role": "system", "content": X.V.NEUTRAL}, {"role": "user", "content": f[key]}]
        assert r["applied"] and not r["protected_drift"]
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 25
        failures = [t.attrib["name"] for t in tests if t.find("failure") is not None or t.find("error") is not None]
        grid.append({**r, "behavior_passed": 25 - len(failures), "behavior_total": 25, "failed_tests": failures})
    assert all(T.sha(p) == sha for p, sha in T.read(batch / "freeze.json")["pins"].items())
    scores = {a: {"behavior_all": sum(g["behavior_passed"] == 25 for g in grid if g["arm"] == a),
        "all_checks": sum(g["all_checks_passed"] for g in grid if g["arm"] == a), "total": 3} for a in ("current", "both", "reference")}
    T.save(batch / "grid-results.json", grid)
    T.save(batch / "metrics.json", {"actual_chat_requests": 9, "extra_probes": 0, "reviewer_calls": 0,
        "scores": scores, "primary_active_seconds": None, "cloud_tokens": None})
    T.save(batch / "preservation.json", {"all_pins_match": True, "protected_drift": [], "production_changes": False,
        "source_reference_is_actual_preimage_not_gold": True, "file_rollbacks": False,
        "siblings": "read-only", "commit_push": False, "old_scores_unchanged": True})
    T.save(batch / "decision.json", {"status": "NO_REFERENCE_ONLY_RECOVERY", "registered": 9, "executed": 9,
        "scores": scores, "r4_passed": False, "fresh_credit": False, "full_chain_credit": False,
        "finding": "Historical reference helps retain legacy structure but still translates ValueError into TypeError and misses typed Message singleton. It is not a qualified recovery policy.",
        "next_key_decision": "Stop mechanical representation search. Any failed-validation semantic consultation by Muse would be a separately named advisory workflow, not a forged qualified Reviewer handoff; requires a role-flow decision and original shared budget/independence controls.",
        "weekly_used_start": 5, "weekly_used_end": used, "weekly_used_ceiling": 15})
    X.M.write(batch, "handoff.md", "# 修改前源码参考对照\n\n当前坏体、坏体+真实修改前参考、仅修改前参考三臂all-check均0/3。九次均实际应用，所有保护输入/pins保持。参考来自原canonical preimage，不是gold，不回滚文件。\n\n参考保留旧结构，但仍把ValueError转为TypeError，并漏Message单例；没有稳定修复，不能采用。此前单个成功例和块编辑行为25/25保留，不把它们扩为3/3资格。\n\n本阶段停止机械表示搜索，待关键角色流程判断。若要用Muse对失败稿给语义诊断，必须单独命名为advisory，而不是绕过passed gate伪造Local Reviewer；最终验证后独立审查、Primary接受仍必需。不得扩原模型/权限/验收或隐藏额外请求预算。\n")
    parent = batch.parent
    names = ["unified-preparation-20261018-1", "unified-transfer-20261018-1", "exception-context-20261018-1",
        "exception-reasoning-20261018-1", "exception-contract-20261018-1", "exception-block-20261018-1",
        "exception-body-20261018-1", "exception-reference-20261018-1"]
    T.save(batch / "consolidated-decision.json", {
        "status": "R4_HOLD_SEMANTIC_RECOVERY_DESIGN_DECISION", "goal_complete": False,
        "evidence": {n: {"path": str(parent / n / "decision.json"), "sha256": T.sha(parent / n / "decision.json")}
                     for n in names},
        "formal_recovery": {"new": "3/3", "old": "0/3", "fresh_credit": False},
        "normal_transfer": {"candidate_accepted": 5, "candidate_required": 6, "baseline_accepted": 1,
            "registered": 12, "executed": 11, "not_run": 1, "per_task": {"request_keys": "2/2", "single_content": "2/2", "messages_output": "1/2"}},
        "diagnostic_chat_requests": 45, "diagnostic_samples_are_correlated_not_a_pooled_success_rate": True,
        "excluded_explanations_for_retained_formal_failure": ["malformed JSON", "patch not applied", "missing expected ValueError assertion", "HTTP400", "context/output cap", "failed Reviewer dispatch"],
        "not_proven": ["Model globally incapable", "source anchoring is sole cause", "context length is root cause", "Primary work or cloud tokens saved"],
        "remaining_observed_failure": "Domain/error classification and effective semantic repair under current fixed model/budget; accepted correct first implementation remains valid evidence of some capability",
        "primary_packet_issue": "Original error-domain wording was implicit, and generic acceptance scenarios were not ideal; clarify prospective contracts, but the matched clarification did not solve this sample",
        "next_proposal_requires_role_flow_decision": "Optional one-shot Muse semantic advisor on failed draft, distinct from qualified Reviewer and final acceptance; share rather than secretly expand original role/time budgets, retain fresh mandatory post-validation Reviewer",
        "weekly_used_end": used, "weekly_used_ceiling": 15,
        "stop_reason": "Mechanical fixes/controlled comparisons closed with explicit failures; next meaningful change is cross-role advisory responsibility and review-independence/budget design, not another routine formatter/schema tweak",
        "production_changes": False, "siblings": "read-only", "commit_push": False})
    print(json.dumps(T.read(batch / "decision.json")))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--used", required=True, type=int)
    close(p.parse_args().used)
