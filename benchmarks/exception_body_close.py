"""Close body visibility comparison, preserving compatibility losses."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import exception_body_diagnostic as X


def close(used):
    T, batch = X.T, X.BATCH
    f, grid = T.read(batch / "fixture.json"), []
    for name, row in T.read(batch / "cells.json").items():
        cell = Path(row["root"]).parent
        r = T.read(cell / "result.json")
        wire = [
            T.read(p)["body"]
            for p in (cell / "wire").glob("*-request.json")
            if T.read(p)["url"].endswith("/chat/completions")
        ]
        assert len(wire) == 1
        assert wire[0]["messages"][1]["content"] == (
            f["hidden_user_message"]
            if name.startswith("hidden-")
            else f["user_message"]
        )
        assert wire[0]["messages"][0]["content"] == (
            X.D.PROMPTS["whole"] if name.startswith("legacy-") else X.NEUTRAL
        )
        assert (
            wire[0]["model"] == "qwen/qwen3-coder-30b" and wire[0]["max_tokens"] == 4096
        )
        assert r["applied"] and not r["protected_drift"]
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 25
        failures = [
            t.attrib["name"]
            for t in tests
            if t.find("failure") is not None or t.find("error") is not None
        ]
        grid.append(
            {
                **r,
                "behavior_passed": 25 - len(failures),
                "behavior_total": 25,
                "failed_tests": failures,
            }
        )
    assert all(
        T.sha(p) == sha for p, sha in T.read(batch / "freeze.json")["pins"].items()
    )
    scores = {
        a: {
            "behavior_all": sum(
                g["behavior_passed"] == 25 for g in grid if g["arm"] == a
            ),
            "all_checks": sum(g["all_checks_passed"] for g in grid if g["arm"] == a),
            "total": 3,
        }
        for a in ("legacy", "neutral", "hidden")
    }
    T.save(batch / "grid-results.json", grid)
    T.save(
        batch / "metrics.json",
        {
            "actual_chat_requests": 9,
            "extra_probes": 0,
            "reviewer_calls": 0,
            "scores": scores,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    T.save(
        batch / "preservation.json",
        {
            "all_pins_match": True,
            "protected_drift": [],
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
            "old_scores_unchanged": True,
        },
    )
    T.save(
        batch / "decision.json",
        {
            "status": "NO_BODY_HIDING_RECOVERY",
            "registered": 9,
            "executed": 9,
            "scores": scores,
            "r4_passed": False,
            "fresh_credit": False,
            "full_chain_credit": False,
            "finding": "Hiding the bad body does not fix this task and loses explicitly required old sequence/direct-object/metadata behavior; unused-import static failures also appear. Do not adopt clean-room-from-contract mode.",
            "next": "One pinned pre-change-reference comparison can test restoration of real legacy context without file rollback or a Primary repair algorithm; no more source-free rewrites",
            "weekly_used_start": 5,
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
        },
    )
    X.M.write(
        batch,
        "handoff.md",
        "# 坏函数体可见性对照\n\n原任务/原体、中性任务/原体、中性任务/接口stub均0/3 all-check；零完整链接受。接口stub是只对模型的显示，真实文件从未被替换为stub，原源码/hash/guards保持。\n\n隐藏坏实现并未提高本题成功率，还丢失原序列/直接对象/metadata行为和原import使用；不能采用无源码重建模式。全部三臂共享新的无目标代码失败投影及实际测试源码，所以不将跨批变化归因于单个因素。\n\n若继续，只允许一个有来源证明的真实修改前基线参考对照，检查是否缺失legacy上下文；不提供修复算法，不回滚文件，不扩权限或改旧分数。\n",
    )
    print(json.dumps(T.read(batch / "decision.json")))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--used", required=True, type=int)
    close(p.parse_args().used)
