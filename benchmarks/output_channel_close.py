"""Close the fixed diagnostic without modifying any frozen candidate/input."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import output_channel_trial as X

T, BATCH = X.T, X.BATCH


def close(used):
    rows = T.read(BATCH / "cells.json")
    grid = []
    for name in X.ORDER:
        root = Path(rows[name]["root"])
        cell = root.parent
        result = T.read(cell / "result.json")
        packet = T.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        responses = [T.read(p) for p in sorted(archive.glob("proposal-response-*.json"))]
        wire = [T.read(p)["body"] for p in sorted((cell / "wire").glob("*-request.json"))
                if T.read(p)["url"].endswith("/chat/completions")]
        assert len(wire) == len(responses)
        arm = name.split("-")[0]
        for request in wire:
            assert request["model"] == "qwen/qwen3-coder-30b"
            if arm == "raw":
                assert "response_format" not in request
            else:
                actual = request["response_format"]["json_schema"]
                assert actual["strict"] is True
                assert actual["name"] == "experimental_whole_function_v1"
                assert actual["schema"]["properties"] == {
                    "replacement": {"type": "string"}, "blocked_reason": {"type": "string"}}
        attempts = [T.read(p) for p in sorted(archive.glob("validation-attempt-*.json"))]
        checks = T.read(cell / "checks/results.json")
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 12 and not result["protected_drift"]
        if arm == "raw":
            assert len(responses) == 6
            assert all(r["raw"].startswith("```python") for r in responses)
            assert (archive / "cumulative.diff").read_text(encoding="utf-8") == ""
            diagnosis = "Markdown framing rejected before edit; no extraction allowed"
        else:
            assert len(responses) == 1
            json.loads(responses[0]["raw"])
            assert len(attempts) == 3
            assert attempts[1]["validation"]["focused_tests"]["stage"] == "diff_quality"
            assert all(test.find("failure") is None and test.find("error") is None for test in tests)
            assert checks[0]["exit_code"] == checks[1]["exit_code"] == checks[2]["exit_code"] == 0
            assert checks[3]["exit_code"] == 1
            assert "reportMissingParameterType" in checks[3]["stdout"]
            diagnosis = "Valid schema/applied behavior; initial+preformat+postformat checks consume cap before another proposal; missing helper parameter annotation remains"
        summary = "Frozen diagnostic replan: " + diagnosis + ". No acceptance or semantic takeover."
        command = X.M.command([X.M.PYTHON, "-B", root / ".local-agents/record-review.py",
            "--repo", root, "--task-id", packet["task_id"], "--run-id", packet["run_id"],
            "--decision", "replan", "--summary", summary], root)
        assert command["exit_code"] == 0, command
        T.save(cell / "primary-decision.json", {"decision": "replan", "summary": summary,
               "canonical_review": str(archive / "review.json"),
               "sha256": T.sha(archive / "review.json"), "semantic_takeover": False})
        grid.append({"case": name, **result, "diagnosis": diagnosis,
            "actual_chat_requests": len(wire), "validation_attempts": len(attempts),
            "independent_tests": {"total": len(tests),
                "passed": sum(t.find("failure") is None and t.find("error") is None for t in tests)},
            "reported_input_tokens": [r["stats"]["reported_input_tokens"] for r in responses],
            "response_finish_reasons": [r["stats"]["finish_reason"] for r in responses],
            "canonical_archive": str(archive)})
    T.save(BATCH / "grid-results.json", grid)
    baseline = T.read(BATCH / "baseline.json")
    # Only these newly-created experiment files changed after their baseline;
    # all inherited work, production files, and prior frozen stages must match.
    permitted = {"benchmarks/coder_output_channel.py", "benchmarks/output_channel_trial.py",
                 "benchmarks/output_channel_unit.py", "tests/test_output_channel.py",
                 "docs/local-model-harness-convergence-plan.md"}
    drift = [p for p, sha in baseline["files"].items()
             if p not in permitted and T.sha(X.KIT / p) != sha]
    pins = T.read(BATCH / "freeze.json")["pins"]
    pin_drift = [p for p, sha in pins.items() if T.sha(p) != sha]
    assert not drift and not pin_drift
    T.save(BATCH / "preservation.json", {"inherited_drift": drift, "frozen_pin_drift": pin_drift,
        "production_changed": False, "sibling_writes": False, "commit_push": False,
        "failed_previous_batch_reopened": False, "all_six_failures_preserved": True})
    T.save(BATCH / "metrics.json", {
        "actual_chat_requests": sum(g["actual_chat_requests"] for g in grid),
        "reviewer_calls": 0, "complete_chains": 0,
        "raw": {"units": 3, "applied": 0, "framing_rejections": 18},
        "schema": {"units": 3, "applied": 3, "private_and_visible_tests_passed": 3,
                   "all_static_checks_passed": 0, "model_saw_type_failure": False},
        "wall_seconds": sum(g["seconds"] for g in grid),
        "primary_active_seconds": None, "cloud_tokens": None,
        "weekly_used_start": 2, "weekly_used_end": used,
    })
    T.save(BATCH / "decision.json", {"status": "HOLD_DIAGNOSTIC_COMPLETE",
        "registered": 6, "executed": 6, "not_run": 0, "fresh_transfer_credit": False,
        "production_release": False, "goal_complete": False,
        "conclusion": "Constrained whole-function schema eliminates observed JSON escaping failures in 3/3 exposed repetitions; raw source fails framing in 3/3. Complete chains remain 0/6. Formatting/check scheduling consumes the validation cap before model receives the remaining type failure, so repair capability is unmeasured.",
        "weekly_used_end": used, "weekly_used_ceiling": 15,
        "stop_reason": "Fixed authorized comparison complete; clear new protocol-versus-scheduling conclusion, not usage exhaustion",
        "next_unique_action": "Separately register a check-scheduling candidate: run existing guarded formatting before counted post-edit validation, with unchanged actual execution/request/time caps and all old protections. Prove budget conservation and stale-input rejection offline before live. Do not increase checks or reclassify this batch as passing."})
    handoff = f'''# 输出通道对照结论

这次改变确实隔离出了两类问题，但没有取得完整链放行。

- 原始函数文本：三轮均失败，共18次提案都包含Markdown围栏，按冻结规则拒绝；0编辑。
- 真正受schema约束的JSON：三轮均成功解码并编辑；每轮12项可见/私有行为测试与Ruff均通过，Pyright均因内部辅助函数参数缺少类型注解失败。
- 三轮schema各只有1次模型请求，不是六次修复都失败。初始验证、编辑后的空白质量检查、受控格式化后的递归复验耗尽3次验证预算；模型从未收到最后的类型错误再做修复。
- Reviewer未启动，完整链0/6；不能宣称Reviewer失败或整个模型语义能力不足，也不能只凭12项通过推断完整合同已证明。

实际chat请求21次，未出现增加预算、手工修补模型输出、放宽测试或更换模型。两臂输入事实一致，输出说明/表示不同；逐轮反馈自然不同，非独立随机统计试验。所有任务已暴露，不能恢复为新题。

下一步唯一建议：独立登记验证调度候选，将已有受控格式化安排在计数的写后验收之前；不得增加实际命令/模型/时间上限。先证明预算守恒、错误展示和旧源码拒绝，再考虑新固定live批次。这是下一候选，不在本批现场修改。

25项离线控制通过，含两种通道真实host/canonical handoff无模型重放。controls-v2.xml保留23通过/2临时目录权限错误，controls-v3.xml保留25通过；controls-v1.xml是此前23项控制，不相加。旧冻结候选与生产runtime无漂移。

weekly used：2% → {used}%，停止线15%，本次因固定实验形成明确结论收尾，不是耗尽usage。Primary主动时间与云tokens未可靠测量，不声称节省成本。

见registration.json、grid-results.json、metrics.json、preservation.json、decision.json及各格canonical archive。未commit/push，兄弟仓库只读，旧失败批次未重开。
'''
    with (BATCH / "handoff.md").open("x", encoding="utf-8") as stream:
        stream.write(handoff)
    print(json.dumps(T.read(BATCH / "decision.json")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", type=int, required=True)
    close(parser.parse_args().used)
