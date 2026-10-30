"""Append-only indexing, costs and closing of the fixed transfer/recovery batches."""

import argparse
import datetime
import json
import urllib.request
from pathlib import Path

import unified_transfer_trial as N

T, M, BATCH = N.T, N.M, N.BATCH


def environment():
    with urllib.request.urlopen(
        "http://127.0.0.1:12345/api/v1/models", timeout=10
    ) as response:
        models = json.load(response)["models"]
    config = T.read(
        Path(T.read(BATCH / "cells.json")["request_keys-candidate-1"]["root"])
        / ".agent/config.json"
    )
    T.save(
        BATCH / "environment.json",
        {
            "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timing": "During matrix, not falsely backdated as initial snapshot",
            "cwd": str(N.KIT),
            "head": T.git("rev-parse", "HEAD").strip(),
            "python": str(M.PYTHON),
            "python_sha256": T.sha(M.PYTHON),
            "configured_roles": {
                k: v
                for k, v in config.items()
                if k in {"coder_model", "reviewer_model", "explorer_model"}
                or "context_length" in k
            },
            "loaded_instances": [
                {"key": m["key"], "instances": m.get("loaded_instances", [])}
                for m in models
                if m.get("loaded_instances")
            ],
            "single_residency_snapshot": sum(
                len(m.get("loaded_instances", [])) for m in models
            )
            <= 1,
            "scope": "Read-only snapshot, no load/unload or compatibility model calls",
        },
    )


def wire_metrics(cell):
    records = []
    for p in sorted((cell / "wire").glob("*-request.json")):
        request = T.read(p)
        if not request["url"].endswith("/chat/completions"):
            continue
        response_path = p.with_name(p.name.replace("-request.json", "-response.json"))
        response = T.read(response_path) if response_path.exists() else {}
        try:
            raw = json.loads(response.get("raw", "{}"))
        except (ValueError, TypeError):
            raw = {}
        records.append(
            {
                "model": request["body"]["model"],
                "seconds": response.get("seconds"),
                "usage": raw.get("usage"),
                "request_sha256": T.sha(p),
                "finish_reasons": [
                    c.get("finish_reason") for c in raw.get("choices", [])
                ],
            }
        )
    return records


def costs(batch, rows):
    per_cell = []
    for name, row in rows.items():
        cell = Path(row["root"]).parent
        if not (cell / "result.json").exists():
            continue
        calls = wire_metrics(cell)
        per_cell.append(
            {
                "case": name,
                "calls": calls,
                "prompt_tokens": sum(
                    (c.get("usage") or {}).get("prompt_tokens", 0) for c in calls
                ),
                "completion_tokens": sum(
                    (c.get("usage") or {}).get("completion_tokens", 0) for c in calls
                ),
                "calls_missing_usage": sum(not c.get("usage") for c in calls),
                "primary_active_seconds": None,
                "cloud_tokens": None,
                "time_components": "Raw HTTP durations retained. Loading/validation/inference split not separately measured; result has whole wall time.",
            }
        )
    T.save(
        batch / "metrics.json",
        {
            "per_cell": per_cell,
            "primary_work_reduction": "UNMEASURED; no economic claim",
            "one_time_harness_development_included_in_savings": False,
        },
    )


def index(name):
    row = T.read(BATCH / "cells.json")[name]
    root = Path(row["root"])
    packet = T.read(root / ".agent/packet.json")
    archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
    review = T.read(archive / "review.json")
    if review["decision"] == "accept":
        assert T.read(root.parent / "result.json")["eligible_for_primary"]
        assert T.read(root.parent / "reviewer.json")["decision"] == "pass_to_primary"
    T.save(
        root.parent / "primary-decision.json",
        {
            "decision": review["decision"],
            "canonical_review": str(archive / "review.json"),
            "sha256": T.sha(archive / "review.json"),
            "semantic_takeover": False,
        },
    )


def recovery():
    batch = N.U.BATCH
    decision = T.read(batch / "decision.json")
    costs(batch, T.read(batch / "cells.json"))
    text = f"""# 固定恢复批次交接

新流程完整链 **{decision["new_accepted"]}/3**，旧流程 **0/3**。固定六格全部执行，失败不覆盖。
每个新单元实际应用两次模型编辑，原三次验证，且仅一次既有受控格式化；独立18项测试、Ruff、Pyright和真实观测检查通过。
三次均自动启动同一冻结Reviewer并通过，Primary逐份全量审查后记录accept，没有语义代写或放宽合同。
旧流程均在普通Ruff格式化复验中耗尽原验证槽，无法把实际RUF013交给第二提案修复；其行为测试通过不等于完整链通过。

改善归于此批登记的机械组合：统一格式化准备加唯一静态错误声明行定位，未隔离二者各自效应。
Reviewer仍出现输出耗尽及原预算内恢复，全部wire保留；不是零协议开销或普遍语义正确证明。
此题已暴露，只获恢复资格，不计新题，不是产品放行。旧循环回归和Reviewer漏检历史不变。
成本见metrics.json，Primary主动时间/云token未知，不宣称减少Primary工作。

下一步：独立冻结三种正常实现任务，两次两臂，原候选6/6及逐题2/2门槛；不回填旧矩阵。
收尾weekly used {decision["weekly_used_end"]}%，停止线上限15%；生产runtime未改，兄弟仓库只读，不commit/push。
"""
    M.write(batch, "handoff.md", text)


def close(used):
    frozen = T.read(BATCH / "live-freeze.json")
    assert all(T.sha(p) == sha for p, sha in frozen["pins"].items())
    grid = []
    for name in N.ORDER:
        row = frozen["cells"][name]
        root = Path(row["root"])
        cell = root.parent
        if not (cell / "result.json").exists():
            assert not (cell / "started.json").exists()
            assert all(T.sha(root / p) == sha for p, sha in row["files"].items())
            grid.append({"case": name, "status": "NOT_RUN"})
            continue
        result = T.read(cell / "result.json")
        packet = T.read(root / ".agent/packet.json")
        archive = root / ".agent/tasks" / packet["task_id"] / "runs" / packet["run_id"]
        if not (archive / "review.json").exists():
            assert not result["eligible_for_primary"], (
                "Eligible unit needs actual Primary review"
            )
            record = M.command(
                [
                    M.PYTHON,
                    "-B",
                    root / ".local-agents/record-review.py",
                    "--repo",
                    root,
                    "--task-id",
                    packet["task_id"],
                    "--run-id",
                    packet["run_id"],
                    "--config",
                    root / ".agent/config.json",
                    "--decision",
                    "replan",
                    "--summary",
                    "Fixed transfer unit did not pass original complete-chain gate; preserve failure without takeover or rerun.",
                ],
                root,
            )
            assert record["exit_code"] == 0, record
        if not (cell / "primary-decision.json").exists():
            index(name)
        grid.append(
            {
                **result,
                "coder_failure_reason": T.read(cell / "coder.json").get(
                    "failure_reason"
                ),
                "primary_decision": T.read(cell / "primary-decision.json")["decision"],
                "archive": str(archive),
                "actual_chat_requests": len(wire_metrics(cell)),
            }
        )
    candidates = [r for r in grid if "-candidate-" in r["case"]]
    count = sum(r.get("primary_decision") == "accept" for r in candidates)
    success = count == 6
    baseline = T.read(BATCH / "baseline.json")
    drift = [
        p
        for p, sha in baseline["files"].items()
        if p
        not in {
            "docs/local-model-harness-convergence-plan.md",
            "benchmarks/unified_transfer_trial.py",
        }
        and (not (N.KIT / p).is_file() or T.sha(N.KIT / p) != sha)
    ]
    assert not drift, drift
    origin = T.read(BATCH / "origins.json")
    assert all(
        T.sha(Path(origin["repo"]) / p) == sha for p, sha in origin["files"].items()
    )
    T.save(BATCH / "grid-results.json", grid)
    costs(BATCH, frozen["cells"])
    T.save(
        BATCH / "preservation.json",
        {
            "inherited_drift": drift,
            "all_frozen_pins_match": True,
            "own_pre_freeze_preparer_changes": "New transfer preparer extended with actual command capture and registration controls before live; final bytes pinned unchanged",
            "sibling_source_hashes_match": True,
            "production_runtime_changes": False,
            "commit_push": False,
        },
    )
    T.save(
        BATCH / "decision.json",
        {
            "status": "PASS_NARROW_TRANSFER" if success else "HOLD_FIXED_GATE",
            "registered": 12,
            "executed": sum(r.get("status") != "NOT_RUN" for r in grid),
            "not_run": sum(r.get("status") == "NOT_RUN" for r in grid),
            "candidate_accepted": count,
            "candidate_required": 6,
            "per_task": {
                t: sum(
                    r.get("primary_decision") == "accept"
                    for r in candidates
                    if r["case"].startswith(t + "-")
                )
                for t in N.TOPICS
            },
            "baseline_accepted": sum(
                r.get("primary_decision") == "accept" and "-baseline-" in r["case"]
                for r in grid
            ),
            "reviewer_qualification": "Frozen original16/16 plus exposed-real4/4; no new independent16 sample claim",
            "r4_matrix_passed": success,
            "product_release": False,
            "coordinator_enabled": False,
            "weekly_used_start": T.read(BATCH / "registration.json")[
                "weekly_used_start"
            ],
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "stop_reason": "All fixed candidate chains accepted"
            if success
            else "Fixed6/6 unreachable or budget stop; unrun inputs unchanged",
            "primary_semantic_takeover": False,
            "primary_active_seconds": None,
            "cloud_tokens": None,
            "next": "Audit complete gate evidence before any broader qualification"
            if success
            else "Analyze earliest retained failure, distinguish proposal/validation/protocol/semantic issues; never reopen scores",
        },
    )
    table = "|单元|Coder|Reviewer|Primary|独立检查|\n|---|---|---|---|---|\n"
    for r in grid:
        table += (
            "|"
            + "|".join(
                str(r.get(k, "NOT_RUN"))
                for k in (
                    "case",
                    "coder_status",
                    "reviewer_decision",
                    "primary_decision",
                    "checks",
                )
            )
            + "|\n"
        )
    M.write(
        BATCH,
        "handoff.md",
        f"""# 固定正常实现迁移批次

候选完整链接受 **{count}/6**，门槛仍为6/6且逐题2/2。固定12格，未运行不计成功。
结果：{"固定矩阵达标，仍需完整准入证据审计，不启用产品默认。" if success else "未达固定门槛，保留未运行输入，不补跑或换题冲分。"}

{table}

## 证据与解释边界

1. 实际应用的源码、diff和每次失败见原canonical归档；独立可见/私有测试与静态检查分别保存，不用Coder摘要代替代码。
2. 通过代码检查但未终态完成的旧单元仍失败；具体原因见grid-results.json的coder_failure_reason及事件。没有自动接受。
3. 对照是原R0循环与整个已冻结候选组合，不把改善全归给单个机制。三组模型、合同、测试和Reviewer相同，配置差异在entry-controls-v2.json逐项列出。
4. request_keys/single_content是从未运行的保留题，messages_output是新真实依赖合同。只有当前固定完整链有迁移信用，旧诊断与旧失败不回填。
5. Reviewer原16/16和已暴露真实4/4资格来自未改的冻结候选；本批clean报告不能替代缺陷挑战。输出耗尽/恢复全部保留。Primary执行高风险全量审查，无实现代写。
6. 成本见metrics.json；Primary主动时间/云token未知，没有证明减少Primary工作。原模型单驻留，兄弟仓库只读，生产runtime不改，不commit/push。

## 附加离线复核

旧冻结控制在live后复跑为9通过/2失败：测试复制已有执行归档，原重复run_id守卫拒绝。
不改冻结测试；由初始清单与canonical preimage重建无历史副本后，同两项原安全断言2/2通过。
首次失败XML、重放XML及新包装测试全部保留，不把两次合并成一轮11/11或模型成功率。
新注册测试首次3通过/1个缺省字段断言错误，修正测试读取后4/4；实际配置不变。

weekly used {used}%，停止线15%。下一步见decision.json，不因局部成功扩大权限或角色。
""",
    )
    print(json.dumps(T.read(BATCH / "decision.json")))


def audit(used):
    """Only after actual accepted six chains, never promotes a product default."""
    decision = T.read(BATCH / "decision.json")
    assert decision["r4_matrix_passed"] and decision["executed"] == 12
    assert all(n == 2 for n in decision["per_task"].values())
    previous = {
        "development": N.KIT
        / "benchmarks/work/harness-convergence/r3-readiness-20261016-1/decision.json",
        "reviewer": N.KIT
        / "benchmarks/work/harness-convergence/r4-contract-first-20261017-1/decision.json",
        "transport": N.KIT
        / "benchmarks/work/harness-convergence/capture-transport-20261017-2/decision.json",
        "mechanical_recovery": N.U.BATCH / "decision.json",
    }
    assert T.read(previous["development"])["qualification"] == "PASS"
    review = T.read(previous["reviewer"])
    assert review["qualification"] == "PASS" and review["executed"] == 20
    assert [(g["correct"], g["total"]) for g in review["groups"]] == [(16, 16), (4, 4)]
    assert T.read(previous["transport"])["qualification"] == "PASS_OFFLINE_COMPONENT"
    frozen = T.read(BATCH / "live-freeze.json")
    assert all(T.sha(p) == sha for p, sha in frozen["pins"].items())
    accepted = []
    for name, row in frozen["cells"].items():
        if "-candidate-" not in name:
            continue
        root = Path(row["root"])
        gate = M.F.load(root / ".local-agents/local-unit.py", "final_gate_" + name)
        identity = gate.verify_handoff(
            root,
            T.read(root.parent / "coder.json"),
            config=T.read(root / ".agent/config.json"),
        )
        index_record = T.read(root.parent / "primary-decision.json")
        assert index_record["decision"] == "accept"
        assert T.sha(index_record["canonical_review"]) == index_record["sha256"]
        accepted.append(
            {"case": name, "identity": identity, "canonical_review": index_record}
        )
    assert len(accepted) == 6
    T.save(
        BATCH / "gate-audit.json",
        {
            "stage": "R4",
            "qualification": "PASS_NARROW_SINGLE_FUNCTION_TRANSFER",
            "references": {
                k: {"path": str(p), "sha256": T.sha(p)} for k, p in previous.items()
            },
            "matrix": {
                "path": str(BATCH / "decision.json"),
                "sha256": T.sha(BATCH / "decision.json"),
            },
            "fresh_complete_chains": accepted,
            "candidate_accepted": 6,
            "every_task_two_of_two": True,
            "same_frozen_reviewer_original16_of16_exposed4_of4": True,
            "frozen_candidate_and_inputs_preserved": True,
            "primary_semantic_implementation_takeover": False,
            "r4_passed": True,
            "r5_controlled_evaluation_admitted": True,
            "r5_started": False,
            "explorer_new_qualification": False,
            "coordinator_enabled": False,
            "production_promoted": False,
            "default_enabled": False,
            "limits": [
                "Three narrow single-function contracts with declared dependencies, fixed environment and current models",
                "Repeated small correlated sample, not a universal success rate or unknown repository exploration qualification",
                "Primary full review retained; no measured economic advantage or cloud-token savings",
                "Reviewer earlier cyclic-metadata miss and all old failures remain valid history",
                "No cross-file/architecture/security work or automatic final acceptance",
            ],
            "weekly_used_end": used,
            "weekly_used_ceiling": 15,
            "stop_reason": "Requested narrow migration gate achieved; stop before Explorer/Coordinator evaluation or production integration",
        },
    )
    M.write(
        BATCH,
        "gate-handoff.md",
        "# 本阶段放行审计\n\n固定三类任务各两次完整链全部接受，候选6/6，原审查16/16及真实回归4/4资格未变。\n\n仅放行原计划范围内的单函数受监督能力与下一阶段的受控评估，不启用生产默认，不代表Explorer、Coordinator、跨文件任务或省成本已合格。所有旧失败和Primary发现的循环回归保留。\n\n核查详情见gate-audit.json、handoff.md、grid-results.json及每条原canonical记录。目标达到，本轮停止，不自动启动后续角色测试。\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["environment", "recovery", "index", "close", "audit"]
    )
    parser.add_argument("--case")
    parser.add_argument("--used", type=int, default=4)
    args = parser.parse_args()
    {
        "environment": environment,
        "recovery": recovery,
        "index": lambda: index(args.case),
        "close": lambda: close(args.used),
        "audit": lambda: audit(args.used),
    }[args.action]()
