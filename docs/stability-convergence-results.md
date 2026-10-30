# 固定范围筛查结果 — 2026-10-09

## 阶段结论

**HOLD：不放行完整 E/C/R，也不启动 Coordinator。**
六类既有任务、每类两轮的固定筛查已完成。产品路径中的 Coder/Reviewer
实现链在这个窄范围表现良好，Explorer 的最终答案完整性仍不稳定。
停止是因为已经形成预先约定的阶段决策，不是用完预算：本轮 weekly used
从 30% 到最后实测 33%，授权上限 40%。

| 项目 | 结果 | 含义 |
| --- | --- | --- |
| Coder 初始调用单元 | 14/14 验收 | 包含调用内验证/修复；不是首个编辑即正确 |
| 独立 Reviewer 最终报告 | 14/14 pass_to_primary | 均经 Primary 复核；不代表报告每个字都准确 |
| Reviewer 实际执行检查 | 6/14 调用执行全部三项 | 其余按既有策略读验证证据；不能计执行信用 |
| Explorer runtime success | 3/4 | 无缓存命中 |
| Explorer 完整回答用户问题 | 2/4 | 一个调用失败，一个 success 但答案不完整 |
| 依赖链最终集成 | 2/2 | 每轮生产者先人工接受，消费者后启动 |
| 完整题目链（含必需 Explorer） | 10/12 | 实现成功不覆盖 Explorer 失败 |
| 夹具正负例预检 | 18/18 符合预期 | 防止测试不具区分力 |
| runtime 回归 | 1006 tests + 115 subtests passed | 与本地模型能力指标分开 |

未发生需要 Primary 修改生产实现或下发额外 rework packet 的情况。
两次 Reviewer 各有一次引用协议纠正，最终完成；没有调用级基础设施失败。
完整保护文件、最终实现哈希、冻结 runtime 和全局配置审计通过。

## 实际阻塞

1. `label-rollup-r2`：Explorer 找到并读到了三个相关文件，先引用了超出
   文件末尾的行范围，随后重复搜索并进入一次 report-only recovery，
   最终遗漏必需 caller 文件引用。最后请求实测输入仅 800 tokens，
   不是 context-length 溢出，也不是模型没加载。
2. `async-receipt-r2`：runtime 返回 success，真实调用链和收集器测试引用
   正确，但没有指出要求定位的 `test_receipt_roundtrip` 集成测试。
   读过整个测试文件不等于最终回答包含这项证据，按不完整计。
3. Reviewer 精度：两次 `public-fields` 报告把测试中的空字符串键说成
   空字符串值的验证证据；一次异步报告把异常栈展开说成 loop returns。
   实现和最终判断正确，报告精度瑕疵单独保留，不宣称严格解释质量全过。

本次只测试了已知的窄任务，不能推导陌生大型仓库、复杂异步边界、SQL、
事务等均已稳定。此前 ToolRegistry 功能链 1/2 的历史仍然有效，没有删掉
失败或把复杂题重新分类后合并出漂亮总分。没有盲审缺陷对照，漏报率未知。

## 下一步：只解决一个明确问题

冻结 Coder/Reviewer 候选，不再同时改三个角色。下一轮聚焦 Explorer
“已读证据 → 完整最终报告”，而不是增加读取次数、上下文、turn budget
或换模型。

- 用本次两份失败/不完整档案写离线回归，覆盖 EOF、必需 caller 引用、
  已读集成测试未引用，以及 report-only 时保留完成义务。
- 检查恢复提示是否完整呈现必需路径与已读范围。当前恢复主要重放源码；
  这是需要验证的呈现改进方向，尚未通过对照证明是唯一原因。
- 现有 `explorer_required_source_anchors` 能校验已知 anchor。确实已知的
  定位义务可复用该机制；未知位置不能预填标准答案冒充自主探索。
  文件级引用通过也不能自动推出问题每个子义务已答全。
- 模型仍应自行选择实际证据；不得由 runtime 自动补齐遗漏引用并计成功。
  对未知位置的语义完成度继续由 Primary 判断，或显式返回未解决项。
- 改动后只重跑四个新鲜 Explorer 单元作对照，旧 2/4 不回填。
  若通过，再补盲审正负例及第三轮；若仍失败，给出窄范围人工导航的
  产品选择，不继续堆任务专用适配器。人工导航不能算 Explorer 放行。

## 可核查产物

- 冻结规则：`docs/stability-convergence-candidate.md`
- runner：`benchmarks/convergence_screen.py`
- runtime：`benchmarks/work/capability-fit/convergence-runtime-1/`
- 固定输入/逐调用完整历史：`benchmarks/work/capability-fit/convergence-screen-1/`
- 审计：上述目录的 `audit-1.json`，可用 `benchmarks/convergence_audit.py` 重放
- 两份 Explorer 独立判定：各题 `.agent/explorer-primary-adjudication.json`
- 每个 Coder 的不可变 Primary 判定：各题 canonical run 的 `review.json`
- 完整回归：`benchmarks/work/capability-fit/convergence-regression-1.xml`

本轮未修改产品 runtime、默认配置或兄弟仓库；没有 commit/push。
新增冻结驱动、只读审计器、总结及实验档案，全部旧改动和历史保留。
Primary 主动耗时和云 token 未测量；weekly 百分点变化不等价于精确成本，
本轮没有证明已经减少 Primary 工作。
