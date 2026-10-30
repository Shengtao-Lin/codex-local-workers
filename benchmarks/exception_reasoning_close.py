"""Close the matched semantic diagnostic, preserving partial progress."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import exception_reasoning_diagnostic as R


def close(used):
    T, batch = R.T, R.BATCH
    fixture = T.read(batch / "fixture.json")
    grid, diagnoses = [], []
    for name, row in T.read(batch / "cells.json").items():
        cell = Path(row["root"]).parent
        result = T.read(cell / "result.json")
        wires = [
            T.read(p)["body"]
            for p in sorted((cell / "wire").glob("*-request.json"))
            if T.read(p)["url"].endswith("/chat/completions")
        ]
        expected = 2 if name.startswith("diagnosed-") else 1
        assert len(wires) == result["model_requests"] == expected
        assert all(
            w["model"] == "qwen/qwen3-coder-30b" and w["max_tokens"] == 4096
            for w in wires
        )
        assert wires[-1]["messages"] == T.read(cell / "request.json")["messages"]
        facts = R.D.INTERFACE.restore_literal(wires[-1]["messages"][1]["content"])
        if expected == 2:
            explanation = T.read(cell / "diagnosis.json")
            assert facts.pop("untrusted_model_diagnosis") == explanation
            diagnoses.append(
                {
                    "case": name,
                    "explanation": explanation,
                    "primary_assessment": "Identifies erroneous TypeError translation and calls for propagation/ValueError. Does not clearly specify the all-Mapping domain including missing fields; actual repair must be scored separately.",
                    "not_a_gold_or_acceptance_certificate": True,
                }
            )
        assert facts == fixture["facts"]
        assert not result["protected_drift"] and result["applied"]
        tests = ET.parse(cell / "checks/junit.xml").findall(".//testcase")
        assert len(tests) == 25
        failures = [
            t.attrib["name"]
            for t in tests
            if t.find("failure") is not None or t.find("error") is not None
        ]
        grid.append(
            {
                **result,
                "behavior_passed": 25 - len(failures),
                "behavior_total": 25,
                "failed_tests": failures,
            }
        )
    assert all(
        T.sha(p) == sha for p, sha in T.read(batch / "freeze.json")["pins"].items()
    )
    counts = {
        a: sum(r["all_checks_passed"] for r in grid if r["case"].startswith(a + "-"))
        for a in ("direct", "diagnosed")
    }
    T.save(batch / "grid-results.json", grid)
    T.save(batch / "primary-adjudications.json", diagnoses)
    T.save(
        batch / "metrics.json",
        {
            "actual_chat_requests": 9,
            "extra_probes": 0,
            "reviewer_calls": 0,
            "all_checks_passed": counts,
            "total_per_arm": 3,
            "complete_chains": 0,
            "seconds": sum(r["seconds"] for r in grid),
            "primary_active_seconds": None,
            "cloud_tokens": None,
        },
    )
    T.save(
        batch / "decision.json",
        {
            "status": "NO_DIAGNOSIS_ONLY_QUALIFICATION",
            "registered": 6,
            "executed": 6,
            "actual_chat_requests": 9,
            "all_checks_passed": counts,
            "denominator_per_arm": 3,
            "partial_progress": "Explanations identify error-type translation; repaired drafts still classify missing-field mappings as unsupported scalars. See exact per-case test counts.",
            "r4_passed": False,
            "fresh_credit": False,
            "full_chain_credit": False,
            "weekly_used_start": 5,
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "next": "Primary audits contract-to-test input-domain clarity before blaming patch/harness or adopting an extra semantic stage. Preserve fixed tests and old scores.",
        },
    )
    R.M.write(
        batch,
        "handoff.md",
        "# 先诊断再编辑对照\n\n固定9请求、6单提案：直接修复0/3、先诊断后修复0/3 all-check；零Reviewer/完整链接受。解释识别异常转换，但代码仍把缺字段Mapping当unsupported类型。逐格行为进展见grid-results.json，不把部分修复抹去。\n\n下一步先审计Primary合同的输入域是否写清楚；equivalent singleton sequence与保护测试要求所有Mapping错误传播一致，但文字未明确空/缺字段Mapping也在新输入域。若澄清，只可新登记前瞻合同版本，不改测试、不覆盖旧失败、不算未暴露题或已放行。没有证据应采用这个额外语义阶段，故不实施到runtime。\n",
    )
    print(json.dumps(T.read(batch / "decision.json")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--used", required=True, type=int)
    close(parser.parse_args().used)
