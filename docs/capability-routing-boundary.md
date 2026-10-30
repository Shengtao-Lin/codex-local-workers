# 能力路由：先限制结论，再限制派工

2026-10-19，用户批准尝试能力路由。此阶段只有离线核对和既有守卫测试，
没有新 live、没有 Coordinator 调用，也没有新增本地任务族资格。
账户 weekly used 实测13%，沿用20%停止线；历史文档中的旧预算不替代当前指令。

## 已核实边界

证据索引：`benchmarks/work/harness-convergence/capability-routing-20261019-1/inventory.json`。
索引含原始决定及对应 canonical Primary review 的 SHA256，不覆盖原成绩。

| 场景 / 原候选 | 原独立完整链接受 | 当前处置 |
| --- | --- | --- |
| request_keys / unified preparation | 2/2 | 历史精确任务证据，不移植为 consolidated 资格 |
| single_content / unified preparation | 2/2 | 同上，不推广为任意解析任务 |
| messages_output / unified preparation | 1/2 | 未达原门槛，不能因一次成功派工 |
| 冻结 SSE 错误草稿 / consolidated | 0/2 | 该场景未合格，交 Primary 判断 |
| 冻结 Iterator 错误草稿 / consolidated | 0/2 | 同上，不推广为所有类型修复均不可行 |
| limit 算法优化、旧错误草稿 / noop-primary-complete-1 | 0/2 | 未合格 |
| 同算法优化、正确 legacy 起点 / 同候选 | 0/2 | 未合格；正确起点不是资格条件的充分证明 |
| 同算法优化、Primary 已审算法策略 / 同候选 | 1/2 | 辅助成绩单列，未证明稳定或减少成本 |

这些行不构成一个共同成功率分母；候选、任务和辅助程度不同。
不将旧 limit 起点研究重复开展，也不自动把“Primary 负责判断”变成“Primary 必须实现”。
所有历史失败、NOT_RUN、Reviewer 漏检及 R4 HOLD 保持。

## 怎样使用这个边界

先由 Primary 确认合同/风险与任务族；Coordinator 不能凭自己的类别标签授权调用。
资格必须匹配候选及实际配置、合同、批准范围、源码起点、检查/恢复模式。
版本不匹配、未测、已失败、需要未授权辅助时，返回 Primary 决策，不用无止境同题重试补齐资格。
这不是把所有未测任务宣布不可完成，也不禁止单独批准的研究实验。

已有 `.local-agents/coordinator-limited.py::route_plan` 检查 owner、精确修改范围、
禁止新增文件和非空 evidence。它**并不核实 evidence 是否真的证明能力**。
所以不能把模型填写的非空 evidence 当成资格证明；仍由 Primary 提供可信能力目录。
本次复用该守卫做离线正负控制，没有改生产守卫或扩大其保证。

`benchmarks/capability_boundary_audit.py` 只是固定历史证据的核对器，
不是语义分类器，不写生产 catalog，不调用模型、不产生 dispatch。
`EXACT_REPEAT_EVIDENCE` 即使出现，也只是标签，不是执行权限。

## 本次验证及结论

12项离线控制：历史/同版本/部分成功/未运行区别，以及既有守卫的 owner、scope、
create、空证据拒绝。模型0调用。初次 lint 发现一个无效 noqa，已删除；
该工程问题不是 Worker 失败，首次 XML 保留，最终结果另存 controls-v2.xml。

当前 consolidated 候选没有从这些记录获得可直接派工的正常任务资格。
因此本次不启动 Coordinator，也不悄悄回切旧候选使目录看起来可用。
两项历史2/2说明存在值得保留的局部能力证据；它们不证明当前候选、陌生任务或经济性。

后续若要恢复 live，应单独冻结“同候选的窄正常任务资格验证”，而不是直接宣布路由已解决稳定性。
这一页只明确入口边界，不预先注册任务、预算或成功标准；R5仍未准入。
