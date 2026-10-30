"""Close six fixed diagnosis proposals without inflating a formal score."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import exception_context_diagnostic as X

T, BATCH = X.T, X.BATCH


def close(used):
    fixture = T.read(BATCH / "fixture.json")
    rows = T.read(BATCH / "cells.json")
    grid = []
    for name in X.ORDER:
        cell = Path(rows[name]["root"]).parent
        result = T.read(cell / "result.json")
        response = T.read(cell / "response.json")
        request = T.read(cell / "request.json")
        wires = [
            T.read(p)["body"]
            for p in (cell / "wire").glob("*-request.json")
            if T.read(p)["url"].endswith("/chat/completions")
        ]
        assert len(wires) == 1 and wires[0]["messages"] == request["messages"]
        assert (
            wires[0]["model"] == "qwen/qwen3-coder-30b"
            and wires[0]["max_tokens"] == 4096
        )
        assert wires[0]["response_format"]["json_schema"]["strict"] is True
        assert request["messages"][0]["content"] == fixture["system_message"]
        expected = (
            fixture["lean_user_message"]
            if name.startswith("lean-")
            else fixture["user_message"]
        )
        assert request["messages"][1]["content"] == expected
        assert result["applied"] and not result["protected_drift"]
        assert not result["accepted_unit"] and not result["complete_chain"]
        stats = response["stats"]
        assert stats["finish_reason"] == "stop"
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        failed = [
            t.attrib["name"]
            for t in tests
            if t.find("failure") is not None or t.find("error") is not None
        ]
        grid.append(
            {
                **result,
                "test_total": len(tests),
                "test_failed": failed,
                "reported_input_tokens": stats.get("reported_input_tokens"),
                "reported_output_tokens": stats.get("response_usage", {}).get(
                    "completion_tokens"
                ),
                "request_sha256": T.sha(cell / "request.json"),
                "response_sha256": T.sha(cell / "response.json"),
            }
        )
    assert all(
        T.sha(p) == sha for p, sha in T.read(BATCH / "freeze.json")["pins"].items()
    )
    T.save(BATCH / "grid-results.json", grid)
    scores = {
        a: sum(g["all_checks_passed"] for g in grid if g["arm"] == a)
        for a in ("full", "lean")
    }
    T.save(
        BATCH / "usage-correction.json",
        {
            "affected_samples": X.ORDER,
            "recorded_started_used": 4,
            "actual_observed_before_first_call": 5,
            "reason": "Account tool returned5 immediately before launcher, but launcher still passed4. Preserve original records and append correction; no threshold violation.",
            "threshold_compliance_changed": False,
            "weekly_used_ceiling": 15,
        },
    )
    T.save(
        BATCH / "metrics.json",
        {
            "actual_chat_requests": 6,
            "compat_probes": 0,
            "formatter_commands": 0,
            "reviewer_calls": 0,
            "accepted_units": 0,
            "complete_chains": 0,
            "all_checks_passed": scores,
            "denominator_per_arm": 3,
            "reported_input_tokens": sum(g["reported_input_tokens"] for g in grid),
            "reported_output_tokens": sum(g["reported_output_tokens"] for g in grid),
            "wall_seconds": sum(g["seconds"] for g in grid),
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    T.save(
        BATCH / "preservation.json",
        {
            "frozen_pins_unchanged": True,
            "old_formal_scores_unchanged": True,
            "protected_drift": [],
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
            "context_difference_only": "target.dependencies, literal transitive source closure",
        },
    )
    T.save(
        BATCH / "decision.json",
        {
            "status": "NO_CONTEXT_ONLY_RECOVERY",
            "registered": 6,
            "executed": 6,
            "all_checks_passed": scores,
            "denominator_per_arm": 3,
            "fresh_credit": False,
            "complete_chain_credit": False,
            "r4_passed": False,
            "weekly_used_registration": 4,
            "weekly_used_actual_live_start": 5,
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "stop_reason": "Fixed matched context comparison finished, no evidence pruning solves the semantic repair failure",
            "causal_scope": "Only this exposed failed snapshot, same Qwen and output format; six applied proposals with current failure evidence do not fix the error-type contract. Not global inability: first normal repetition passed complete chain.",
            "next_key_decision": "Whether to introduce a separately evaluated Coder semantic diagnosis-before-edit stage inside original total request/validation budgets, rather than further mechanical output/context edits. No semantic answers, auto repairs, weaker tests or qualification claims.",
        },
    )
    X.M.write(
        BATCH,
        "handoff.md",
        f"""# 异常修复上下文对照结论

固定六次单提案，完整上下文 **{scores["full"]}/3**、真实依赖闭包 **{scores["lean"]}/3** all-check。
六次均正确JSON、通过原编辑守卫并实际应用；真实25项测试/静态检查仍有失败。零Reviewer、零完整链接受、零新题信用。

## 现在可以确认什么

- 旧正式矩阵保留5/6候选接受，逐题2/2、2/2、1/2；11/12执行，最后一条旧对照NOT_RUN。旧对照有1条真实完整链接受，不抹掉它。
- 本次错误不是patch没打上、无效JSON、HTTP400、输出/上下文耗尽或Reviewer没有启动；是已应用实现把真实校验异常转成TypeError，保护测试拒绝。
- 第二请求确实有with pytest.raises(ValueError)、实际TypeError、当前源码与hash。不能说反馈丢失。第二提案扩大catch仍保留问题。
- 只裁剪无引用依赖没有解决本样例，不能继续以“上下文太长”当已确认根因。重复小样本不推出所有语义任务不行：同合同第一轮25项与完整链通过。
- 既有格式化/静态错误定位修复取得恢复3/3、新正常任务5/6，不等于语义修复已稳定。

## 下一关键设计判断

建议单独评估Coder在失败后先说明合同/实际结果差异，再提出修复。说明仍是不可信模型输出；宿主不替它生成算法或自动认定正确。
维持原六请求、三验证、三编辑/一次格式化上限、同模型/权限/合同/保护测试与独立审查；新增说明请求只能在原预算内分配。
这改变Coder语义调试流程，已不是格式、路径或单行schema的机械修补；尚未实现或调用新阶段。
先独立登记控制与失败理解/实际修复对照，只有得到正式资格才重新谈未暴露迁移；旧失败永不回填、不恢复为新题。

weekly used实际live起点5%，收尾{used}%，上限15%。本次停在明确上下文对照结论与新的语义流程设计点，不是预算耗尽，不是假称目标完成。
成本见metrics.json；Primary主动时间与云token未知，不声称省成本。
""",
    )
    print(json.dumps(T.read(BATCH / "decision.json")))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--used", required=True, type=int)
    close(p.parse_args().used)
