"""Close a failed representation gate without hiding one semantic partial success."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import exception_block_diagnostic as B


def close(used):
    T, batch = B.T, B.BATCH
    fixture, grid = T.read(batch / "fixture.json"), []
    for name, row in T.read(batch / "cells.json").items():
        cell = Path(row["root"]).parent
        result = T.read(cell / "result.json")
        wire = [T.read(p)["body"] for p in (cell / "wire").glob("*-request.json") if T.read(p)["url"].endswith("/chat/completions")]
        assert len(wire) == 1
        assert wire[0]["messages"][1]["content"] == fixture["user_message"]
        assert wire[0]["messages"][0]["content"] == (B.BLOCK_PROMPT if name.startswith("block-") else B.D.PROMPTS["whole"])
        assert wire[0]["model"] == "qwen/qwen3-coder-30b" and wire[0]["max_tokens"] == 4096
        assert result["applied"] and not result["protected_drift"]
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 25
        failed = [t.attrib["name"] for t in tests if t.find("failure") is not None or t.find("error") is not None]
        grid.append({**result, "behavior_passed": 25 - len(failed), "behavior_total": 25, "failed_tests": failed})
    assert all(T.sha(p) == sha for p, sha in T.read(batch / "freeze.json")["pins"].items())
    counts = {a: {"behavior_passed": sum(g["behavior_passed"] == 25 for g in grid if g["arm"] == a),
                  "all_checks_passed": sum(g["all_checks_passed"] for g in grid if g["arm"] == a), "total": 3}
              for a in ("whole", "block")}
    T.save(batch / "grid-results.json", grid)
    T.save(batch / "metrics.json", {"actual_chat_requests": 6, "extra_probes": 0, "reviewer_calls": 0,
        "scores": counts, "primary_active_seconds": None, "cloud_tokens": None})
    T.save(batch / "preservation.json", {"all_pins_match": True, "same_user_message": True,
        "protected_drift": [], "old_scores_unchanged": True, "production_changes": False, "siblings": "read-only", "commit_push": False})
    T.save(batch / "decision.json", {"status": "HOLD_BLOCK_DIAGNOSTIC", "registered": 6, "executed": 6,
        "scores": counts, "r4_passed": False, "fresh_credit": False, "complete_chain_credit": False,
        "partial_success": "block-3 passed25 behavior tests, format and Pyright; one B904 at raise TypeError inside except still fails original lint. Other blocks retain truthiness/required-field classification errors. No post-hoc repair of this sample.",
        "next": "If continuing, isolate bad-implementation anchoring from task wording with matched full-body/hidden-body generation; do not adopt this0/3 block candidate or auto-fix semantics/lint",
        "weekly_used_start": 5, "weekly_used_end": used, "weekly_used_ceiling": 15})
    B.M.write(batch, "handoff.md", "# 错误块输出对照\n\n整函数与实际错误行绑定代码块all-check均0/3。块输出有1/3通过全部25项行为测试，但该样例仍有原B904 lint失败；没有把它补成成功或免除lint。其余块把空Mapping或缺字段Mapping当不支持类型。\n\n两臂相同明确合同、依赖、失败和repair_span；只输出粒度不同。原guard、hash、scope与保护测试均保持。没有独立Reviewer、完整链或新题信用。下一步如继续，只测试坏实现是否对重写造成锚定，不继续格式/上下文/解释堆叠，不在已闭批里改分。\n")
    print(json.dumps(T.read(batch / "decision.json")))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--used", required=True, type=int)
    close(p.parse_args().used)
