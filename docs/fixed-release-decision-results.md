# 固定放行实验结果 — 2026-10-10

## 结论

**HOLD：本轮不正式放行。** 实现与受控编排矩阵全部通过，但 Reviewer
盲审为 7/8，未达到事前冻结的 8/8。保留已有人工监督试验边界，不开启
全局 Coordinator，不改成自动返工或自动验收。没有根据结果降低门槛。

这次没有反复修补 runtime：只使用一个冻结候选，产品代码、提示词和
全局配置均未改动。实验配置明确使用已有 CLI 加载后端。旧 native
超时、Explorer 遗漏及其他历史失败仍保留。

## 固定分母下的结果

| 检查 | 结果 |
| --- | --- |
| 三轮角色切换与最小请求 | 9/9；单模型、正确上下文、并发 1 |
| 切换耗时 | 6.656–15.203 秒；与后续推理耗时分别记录 |
| 权限、依赖、重复派发等确定性检查 | 82 passed，属于下列完整回归的子集 |
| 三类任务各两轮 | 6/6 完整链通过，门槛至少 5/6 |
| Coder → Reviewer → Primary 实现单元 | 8/8 接受，无外部返工、无 Primary 代写 |
| 必需 Explorer | 4/4 完整；无缓存、无辅助恢复；一次行号纠正 |
| 受控 Coordinator 派发 | 6/6 完成，决策与提案无纠正；两个 consumer 均在 producer 接受后启动 |
| 依赖链集成 | 2/2，分别四项测试及 Ruff 通过 |
| Reviewer 固定盲审 | 7/8 有效：隐藏缺陷 4/4 检出，正确实现 3/4 正确放过 |
| 完整回归 | 1008 tests + 117 subtests passed |

默认值单元是直接 C/R 对照，不伪造 Explorer/Coordinator 调用信用。
两个 labels 单元和两条 receipt 链使用受控 Coordinator。Reviewer 在
真实实现审查中有两次协议纠正，均完成；这不等于所有输出一遍即正确。
盲审使用合成 Coder 档案，不能计入真实 Coder 成功率。

## 唯一未满足的放行项：R1

`display-default-a-r1` 是正确实现：

```python
def display_name(record):
    return record.get("name", "unnamed")
```

Reviewer 的报告承认它保留已有空字符串/None，也承认没有 mutation，
却仍给出 `high / contract_violation / rework`。随后建议又说可以保持
实现不变，主要理由变为边界测试覆盖不足。测试缺口确实存在于这个
刻意削弱普通测试的对照中，但不能证明其声称的生产实现违约。

Primary 读取源码并执行独立边界探针，确认该结论是误报。第二轮同一
正确实现被 Reviewer 正确放过；两轮源码、测试和配置哈希一致。
因此这里有审查判断波动的直接证据，不是“改坏另一处又改回去”。
第二轮成功没有覆盖第一轮失败，也没有触发额外同题重跑。

## 为什么不继续改提示直到全绿

计划允许最多一个有依据的修复候选，并不要求必须用掉。此次没有建立
R1 对应的确定性 runtime 缺陷；继续添加提醒再得到一轮成功，不能证明
语义判断问题被可靠修复。故完成固定评估并作 HOLD 决策，不动门槛，
不消耗余下预算去制造新的小样本全绿。

I1 在本次 CLI 环境中通过了重复加载和实际链检查；这不等于查明 native
超时根因。E1 本轮未复发，但此前无辅助遗漏仍有效，不能推导一般探索
能力已稳定。W1 本轮未出现。C1 的受限派发与依赖顺序通过；未测试自由
分解陌生需求。R1 仍开放。

## 产品含义

现有模型可以在已知窄任务上完成实现与受控编排，不应据本轮宣布整个
方案失败；同样不能据实现链全过宣布产品放行。继续使用时维持原有
Primary 裁决：Reviewer 的 rework 是待核实建议，不能直接驱动修改。
这不是新授权的降级发布，全球开关仍关闭。

如另行决定进入下一轮，目标应限于 Reviewer 的“代码缺陷 / 测试缺口 /
未决疑问”是否被混淆及其处置成本，而不是同时重改三个角色。不要靠
字符串规则自动否定报告，也不要把缺少测试一律排除：有些测试缺口确实
需要返工，必须依据契约与风险判断。本轮不实施未经验证的分类补丁。

经济性比较按原计划以正确性门槛通过为前提，所以没有启动；Primary
主动时间和云 token 未精确测量，不能宣称已节省成本。

## 可核查记录

- 冻结计划：`docs/fixed-release-decision-plan.md`
- 加载入口：`benchmarks/fixed_release_trial.py`
- 固定矩阵入口：`benchmarks/fixed_release_matrix.py`，复用既有执行机制
- 所有本轮证据：`benchmarks/work/capability-fit/fixed-release-1/`
- `registration.json`：运行前规则和哈希
- `functional-audit-1.json`：八个真实单元及保护文件/最终源码验证
- `final-audit-1.json`：加载、Explorer、Coordinator 依赖、盲审完整分母
- `primary-stage-decision-1.json`：本轮最终裁决
- `matrix/runs/`、`controls/runs/`：原始 `.agent` 与不可变 Primary 判定

最终哈希核查确认冻结 runtime、配置、计划、驱动及受保护文件未漂移。
新驱动 Ruff 检查通过，`git diff --check` 通过。未 commit/push、未修改
兄弟仓库、未清理历史或用户改动。weekly used 从 40% 到最后实测 45%，
上限 50%；停止原因是完成固定评估并得出明确结论，而非额度耗尽。
