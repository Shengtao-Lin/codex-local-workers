"""Append-only close of prospective packet-meaning comparison."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import exception_contract_diagnostic as X


def close(used):
    T, batch = X.T, X.BATCH
    fixture, grid = T.read(batch / "fixture.json"), []
    for name, row in T.read(batch / "cells.json").items():
        cell = Path(row["root"]).parent
        result = T.read(cell / "result.json")
        wires = [
            T.read(p)["body"]
            for p in (cell / "wire").glob("*-request.json")
            if T.read(p)["url"].endswith("/chat/completions")
        ]
        assert len(wires) == 1
        expected = (
            fixture["explicit_user_message"]
            if name.startswith("explicit-")
            else fixture["user_message"]
        )
        assert wires[0]["messages"] == [
            {"role": "system", "content": fixture["system_message"]},
            {"role": "user", "content": expected},
        ]
        assert (
            wires[0]["model"] == "qwen/qwen3-coder-30b"
            and wires[0]["max_tokens"] == 4096
        )
        assert result["applied"] and not result["protected_drift"]
        assert T.read(cell / "response.json")["stats"]["finish_reason"] == "stop"
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 25
        failed = [
            t.attrib["name"]
            for t in tests
            if t.find("failure") is not None or t.find("error") is not None
        ]
        grid.append(
            {
                **result,
                "behavior_passed": 25 - len(failed),
                "behavior_total": 25,
                "failed_tests": failed,
            }
        )
    assert all(
        T.sha(p) == sha for p, sha in T.read(batch / "freeze.json")["pins"].items()
    )
    counts = {
        a: sum(g["all_checks_passed"] for g in grid if g["arm"] == a)
        for a in ("original", "explicit")
    }
    T.save(batch / "grid-results.json", grid)
    T.save(
        batch / "metrics.json",
        {
            "actual_chat_requests": 6,
            "extra_probes": 0,
            "reviewer_calls": 0,
            "all_checks_passed": counts,
            "per_arm": 3,
            "accepted_units": 0,
            "complete_chains": 0,
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    T.save(
        batch / "preservation.json",
        {
            "all_pins_match": True,
            "protected_drift": [],
            "old_scores_unchanged": True,
            "prospective_contract_only": True,
            "production_changes": False,
            "siblings": "read-only",
            "commit_push": False,
        },
    )
    T.save(
        batch / "decision.json",
        {
            "status": "NO_CONTRACT_WORDING_ONLY_RECOVERY",
            "registered": 6,
            "executed": 6,
            "all_checks_passed": counts,
            "per_arm": 3,
            "r4_passed": False,
            "fresh_credit": False,
            "conclusion": "Explicit all-Mapping/error-domain clause did not solve this frozen repair. Actual explicit proposals add a Mapping branch inside the same broad try, retaining except Exception to TypeError. Primary contract clarity issue acknowledged but not sole observed cause.",
            "next": "One independently registered actual-error-location-bound block versus whole-function representation diagnostic, identical explicit contract/facts in both; no more context/diagnosis/wording stacking",
            "weekly_used_start": 5,
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
        },
    )
    X.M.write(
        batch,
        "handoff.md",
        "# 前瞻合同澄清对照\n\n原文字0/3、明确Mapping输入域文字0/3，六次均正确应用但未通过原25项行为/静态检查。固定测试和旧合同/成绩不变；Primary表达不足有责任，但澄清不是本样例单独的有效修复。\n\n实际明确臂代码仍在broad try内部添加Mapping分支，外层except Exception继续转TypeError。下一步只隔离整函数再生成与错误块再生成；模型收到同样明确合同和实际失败，宿主只从真实错误行绑定原代码块，不提供算法/修复代码。没有Reviewer或完整链接受信用。\n",
    )
    print(json.dumps(T.read(batch / "decision.json")))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--used", required=True, type=int)
    close(p.parse_args().used)
