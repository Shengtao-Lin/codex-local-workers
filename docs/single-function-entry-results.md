# 单函数正式入口候选：未放行

日期：2026-10-12。证据根目录：
`benchmarks/work/system-convergence/single-function-entry-20261012-1/`。

## 阶段决策

按固定顺序完成两个原有任务、各三次正式 `local-unit.py` 调用。
候选在 live 开始后没有变化，未换模型、未改验收、没有外部修复。

**独立全检查 2/6，正式完整链 0/6；Reviewer 实际调用 0 次。候选不放行。**
没有绕过失败的 Coder 门槛手动派发 Reviewer，也没有把 pytest 通过改记为任务成功。

| 冻结任务 | 行为测试 | 全检查通过 | Coder ready / Reviewer / 完整链 |
| --- | --- | --- | --- |
| `get_many` 既有 E501 修复 | 三次均 11/11 | 0/3 | 0 / 0 / 0 |
| `OutputPresentScorer.score` 新行为 | 三次均 9/9 | 2/3 | 0 / 0 / 0 |

修复题原本行为就正确，其 11/11 仅说明未破坏已有行为，不是完成修复。
行为题第二次新增 101 字符的注释，仍违反 E501；不能把三次行为测试通过说成三次全检查通过。

## 本轮改动

只新增默认不启用的 `coder_single_function` 候选，以及固定实验驱动、负控和报告：

- 正式 WorkerRuntime 内按当前目标函数、版本 hash、完整合同和最新观察重组精简上下文。
- 写权限进一步收窄到一个既有 Python 函数；禁止新建、单行编辑、签名改变、邻接函数改变和多文件配置。
- 沿用现有 SAFE_REPLACE、写锁、不可变归档、验证、自动交接和 Reviewer；未另造绕过这些门槛的执行通路。
- 在实验配置中开启已有 `autoformat_on_diff_whitespace`，保留原 formatter/lint/type/test 配置。
- 候选格式化增加当前版本校验、AST 语义不变检查和失败拒绝；格式化更新版本并使旧验证失效。
- 不自动填入模型的合同确认；上下文的确认字段初值是 unknown，不伪造 semantic acknowledgement。

根配置、模型配置、Reviewer 候选和原历史均未调整。实验外不应启用此未合格模式。
只有默认不启用还不等于完全没有接入成本：runtime 新增了同目录 helper 依赖，安装验证覆盖了其分发。

## 有效的发现

### 1. 已有受控格式化确实能在正式入口发挥作用

presence-1 和 presence-3 均经历：
`模型编辑 → format check 失败归档 → 授权文件格式化 → 新版本全检查通过`。
事件中 `unexpected_validation_input_changes` 为空，独立验收重复确认 pytest、Ruff format/lint、Pyright 全过。
这两次不是上一轮那种事后副本诊断，而是正式 runtime 执行证据。

但 Ruff formatter 不承诺改写长注释或长 docstring；另外四次的 E501 不能靠开启 formatter 自动解决。
本轮没有删规则或改阈值。

### 2. 新精简候选漏掉了关键的收尾协议说明

presence-1/3 的代码已正确，但每次 VALIDATE 都采用默认 `phase=check`。
现有 `_validated_terminal_state()` 要求 `validation_phase == final`，所以其终态拦截和 one-shot 收尾没有激活。
模型继续“无变化替换 → VALIDATE”，最终耗尽协议错误预算。

新 helper 的短提示只说“验证通过后 FINISH_SUCCESS”，没有保留 check/final 的明确区别。
**这是本次接入设计的缺口，不能解释为模型不会实现功能。**
模型原本仍可以直接正确 FINISH_SUCCESS，因此不能说漏掉一个字段是所有失败的唯一原因。
同时，现有安全边界正确阻止了假交接：没有把失败 Coder archive 送给 Reviewer。

### 3. 上一轮 patch-only 的成功没有自动迁移到自主动作循环

三次修复题仍留下 E501，其中扩写 docstring 后还产生两条超长行；随后多次替换未精确匹配当前函数。
完整入口保留了行动选择、验证和收尾，输入内容及输出 action schema 也不同于上轮仅生成 patch 的诊断执行器。
因此本批次不能支持“精简上下文已解决问题”，也不能隔离哪个变化单独导致回退。

独立代码全检查与完整链必须分开统计，Reviewer 未启动也不计失败审查或成功审查。

## 控制和实验质量

- 新负控覆盖函数边界、签名、额外定义、旧 hash、外部文件变化、禁止写动作、多文件配置、
  formatter 失败/语义改变/保护文件改变、旧验证不能提交。
- 首轮定向验证 221 passed、65 subtests passed。
- 扩展回归第一次有 36 个全局 pytest 临时目录权限错误，以及一个新增测试格式导致的安装检查失败。
  换仓库内独立临时目录后 591 passed、302 subtests passed，仍保留安装格式失败。
- 在任何 live 调用之前只作仓库格式化；随后新负控与安装 smoke 合计 23 passed。
  原始六份准备快照和失败日志没有覆盖，正式 live 使用另一个冻结子目录。
- 最终组合回归 **592 passed、302 subtests passed**，见 `regression-final.xml`；
  结果与阶段验收分开，不用单元回归通过替代 live 成功。
- 原始测试、模型、运行预算及失败记录保持不变；六次独立复验见各 case 的 `primary-independent.*`。

## 下一步：先修执行状态边界，不再凭结果扩充提示

本批次结束，不在同一个候选里临时补一句提示再挑成功案例。
建议下一候选只针对一个确定性问题：**已有有效编辑、当前全检查通过、合同确认有效之后的受控收尾**。

先用脚本化 client 和真实 runtime 复现：

1. 绿基线但没实现：不能收尾。
2. 编辑后 check 通过但合同确认缺失/unknown 且该合同要求确认：不能擅自补 true。
3. 已编辑、确认有效、当前检查全部通过：不应再暴露编辑/重复验证循环；只进入可审计的提交/交接状态。
4. 格式化或其他写入后旧验证失效、输入变化、检查失败：绝不能交接。
5. 自动交接继续复核原 canonical archive，Reviewer 仍必须独立审查。

这不是降低验收，而是把阶段转换放回可信 runtime；实现前需明确最终确认由谁提供，不能机械制造模型确认。
只在这些控制稳定后复测同一批次。E501 修复转化单独保持未合格，不因终态修复而自动放行。
跨文件任务仍由 Primary 处理，Coordinator 合格任务族不扩大。

## 历史、工作区和成本

开跑冻结 92,526 个路径；本仓库既有文件的本轮变化仅 `worker-runtime.py`，原始字节预像已核对保存。
新 helper、测试、驱动和报告均为新增文件；旧候选及失败记录未覆盖。
全部 live 副本的非授权输入 hash 未变，live 后候选 hash 未变。

收尾检测到兄弟 `agent-evaluation-harness` 的 `docs/operations.md` 与 `src/evaluation_harness/contracts.py`
相对开跑记录有字节变化，并出现新的未跟踪文件；其 HEAD 不变。
本任务未对兄弟路径发出写操作，不推断变化作者，也未恢复这些变化。
隔离副本没有同步外部改动，冻结验收不受影响。`agent-runtime-kit` HEAD/status 未变。
原始审计断言失败及改为明确记录外部漂移的审计版本均保留。

weekly used 起点 16%，实验结束时查询 18%，最终收尾查询 **19%**，上限 30%。
这是共享账户窗口的取整读数，不是精确任务 token 成本。收尾 Qwen 独占驻留、IDLE、context 24576、parallel 1。
`git diff --check` 退出 0，仅既存 LF/CRLF 提醒。
无 commit/push。停止原因是候选得到明确否定结论，而非 usage 耗尽。

主要证据：`authorization.json`、`preparation.json`、`live/freeze.json`、
每个 live case 的 canonical `.agent/tasks/.../runs/...`、`primary-stage-decision.json`、`stage-conclusion.json`。
