# 单函数终态修复：完整链打通，整体门槛未放行

日期：2026-10-12。阶段：`single-function-terminal-20261012-1`。

## 结论

只修改上轮单函数候选的终态转换，未改提示、helper、模型、验收或 Reviewer。
同一冻结批次结果如下：

| 任务 | 独立全检查 | 自动 Reviewer | Primary 接受隔离单元 | 完整链 |
| --- | --- | --- | --- | --- |
| OutputPresentScorer 单函数行为 | 3/3 | 3/3 pass_to_primary | 3/3 | 3/3 |
| get_many E501 修复 | 0/3 | 未启动 | 0/3，均 replan | 0/3 |

**阶段整体 3/6，原定 6/6 门槛没有达到，不作一般产品或任务族放行。**
可以确认这批次的终态转换和自动交接已工作；不能宣称 E501 修复能力或任意单函数任务稳定。
跨文件任务继续归 Primary，Coordinator 边界不扩大，根配置没有启用该实验模式。

## 唯一 runtime 修改

在 `WorkerRuntime.validate()` 已形成成功验证结果后，仅对单函数模式：

1. 要求本次调用已有实际编辑，绿基线及仅有 parent_run_id 不自动满足此条件。
2. 使用已有 `_assert_submission_contract()` 严格检查模型已经提交的合同确认。
3. 确认有效才把本次验证以 `phase=final` 写入不可变 archive。
4. 后续由现有终态 gate 检查文件版本和输入事实，拦截非 FINISH_SUCCESS 动作；
   允许一次收尾提醒，再使用既有受控终结。没有新建绕过 handoff 的分支。

必要 ordering 确认为 unknown/false 时保留 check 阶段，不补 true；没有新增模型声明。
默认非单函数模式不受此分支影响。

本批次三次成功调用都发生了 `single_function_terminal_promoted`，
随后无变化编辑被终态 gate 拒绝，模型响应一次提醒后正常 FINISH_SUCCESS。
live 中未用到“再次不配合后 runtime 终结”的后备分支，该分支由脚本化控制覆盖。

## 验证证据

- 负控及相关回归：224 passed、51 subtests passed。
- 完整 runtime / installer 回归：601 passed、302 subtests passed。
- 新负控明确覆盖：绿基线、缺失确认、必要确认 unknown/false、静态检查失败、零测试、
  校验后文件漂移、有效 check 升级 final，以及模型继续尝试编辑时一次提醒后受控终结。
- 六个 live 起点均从上轮不可变 preimage 恢复；源码、保护测试、项目配置 hash 与原冻结输入一致。
- 每个 case 都通过正式 `local-unit.py`，成功者自动调度原 Muse Reviewer；未手工补交接。
- Primary 独立重跑 pytest、Ruff format/lint、Pyright，审查完整改动文件和实际 diff，
  三个成功单元通过 `record-review.py` 写入各自 immutable review.json；三个失败单元记录 replan。

成功单元的 Coder 模型请求数依次为 4、5、4。
三次均有授权文件格式化及后续全量重验，无保护输入漂移。
Reviewer 三次都通过，但协议错误数为 **0、1、1**，不能写成无纠正成功：

- 第二次缺少一份保护测试的显示覆盖，报告被拒，补读后通过。
- 第三次 evidence_ids 不符合已显示 ID 约束，报告被拒，纠正后通过。

新 presence-3 最终源码 hash 为
`99fead2328bb4866a80ee2495c59e0c75b899a1d34a4b613f5ec144b270de044`，
与上轮 presence-1/3 卡住时的源码完全相同。
这次同样代码通过正式交接和独立审查，支持终态接入修复有效；它不等于在所有模型/任务上建立因果成功率。

## 尚未解决：E501 到有效修复

三次 get_many 最终源码 hash 均为
`7d75cbe0d262df5ed1b165daeb41391dd510d5ec522f855004953d289564cd8c`。
行为保护仍是 11/11，但长 docstring 仍违反 E501，随后多次精确替换失配。
没有进入终态，未启动 Reviewer，说明本修复未绕过失败检查。

进一步只读诊断：被拒提案的替换文本为 648 字符，其 SHA-256
`e72215db904e52e58655d3626ca5a3e17580ef3576a1d96d14a2d5aa9c2a501a`
恰好等于当前方法文本。这些提案不是新的有效 E501 修复。
该结论来自事件记录和当前方法 hash；没有保存的原始 find 文本不作臆测。
另外，Ruff formatter 不负责改写长注释/docstring，不能把开启 formatter 当作 E501 通用修复器。

下一步应只研究这条失败链的修复提案与当前源码绑定，以及失败后真正改变代码的能力，
保持本次已验证的收尾机制、Reviewer、模型和验收固定。
优先用归档构造确定性重放/负控，再决定是否引入仅生成受限 patch 的修复阶段；
不要再改 Coordinator，也不应靠放宽 lint 或盲增回合数掩盖失败。

## 保全、成本和限制

本轮 weekly used 从 19% 开始，收尾查询 21%，低于 30% 上限。
读数是共享账户取整 usage，不是精确单任务 token 成本。
停止原因是得到明确阶段结论，不是额度耗尽。

保留所有旧失败、现有改动、原始/格式化前快照和新运行 archive；无 commit/push。
兄弟仓库仅只读访问，未把实验实现复制回兄弟项目。
收尾复核 93,387 个冻结路径：本仓库的已存在文件变化仅 runtime 和本轮新建驱动
（驱动在 live 前修正 preimage manifest 的 archive_path 字段读取）；旧历史未变。
另检测到兄弟 `docs/operations.md` 的外部字节漂移，已单独记录，未恢复、覆盖或同步进隔离副本。
末次驻留检查仅 Muse，IDLE、context 24576、parallel 1；Coder/Reviewer 顺序切换，未并驻。
git diff --check 退出 0，仅既存 LF/CRLF 提醒。

证据目录：`benchmarks/work/system-convergence/single-function-terminal-20261012-1/`。
重点文件：`terminal-authorization.json`、`freeze.json`、`controls.xml`、`regression.xml`、
每个 case 的 `independent-result.json`、canonical Coder/Reviewer archive、`review.json`、`stage-conclusion.json`。
继承 checkpoint 的旧候选描述由 terminal-authorization.json 明确替代，其他历史不覆盖。
