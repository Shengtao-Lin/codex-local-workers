# Explorer 收敛结果与受控试验边界

2026-10-09。本轮阶段决策：**可以开始已知窄范围的隔离 Coordinator 试验**。
不等于 v2.1 产品全面放行，也没有开启全局 Coordinator。

## 改了什么

仅调整 Explorer 的通用定位提示：始终显示最终必需引用的路径；提醒逐项
核对问题要求的 caller、实现、单元测试及集成测试位置；使用实际已显示
行号，不把 READ_FILE 请求末尾误当文件末尾。没有加入本题测试名、标准
答案或任务专用适配器，没有自动补引用、增加预算、更换模型或放松校验。
Coder、Reviewer 和全局 config 与上一轮冻结版本的哈希相同。

## 已执行证据

| 检查 | 本轮结果 |
| --- | --- |
| Explorer 新鲜定位调查 | 4/4 完整回答，零缓存命中；两条各一次协议纠正 |
| Reviewer 盲审对照 | 8/8 有效：正确 4、隐藏缺陷 4；无误报或错误通过 |
| 第三轮真实 Coder → Reviewer → Primary | 7/7 单元验收，无 Primary 代写或额外 rework packet |
| 最终生产者／消费者集成 | 4 tests + 两项 Ruff 通过；生产者先验收后才启动消费者 |
| 夹具正负例预检 | 18/18 符合预期 |
| 全量回归 | 1008 tests + 117 subtests passed |
| 冻结输入与最终源码审计 | 通过，未使用的第二轮实现单元不计信用 |

默认值对照检出了普通测试未覆盖的 None/空字符串错误；异常对照检出了
宽泛 Exception 捕获导致的异常吞没。每个判断均对实际源码复核并用独立
边界探针验证，不凭 Reviewer 自述。合成对照不计 Coder 成功。
一份对照的修复建议开头措辞不精确，但紧随的具体修复例子和因果判断正确，
该瑕疵保留在独立判定中。审计读取器曾误用字段，纠正读取后通过，没有
改写执行档案。

上一轮 Explorer 严格 2/4、完整链 10/12 以及 ToolRegistry 的复杂任务失败
全部保留。本轮 4/4 是小样本新鲜对照，不是统计稳定率证明；也不能据此
认定提示改动是唯一因果因素。旧缓存命中行为未重新验证；通用提示调整
不自动修正过去缓存的答案。

## 下一步只做一个有边界的 Coordinator 试验

使用全新隔离工作区，最多两个有依赖的单元，来自已验证的六类任务：
display-default、public-fields、lookup-fallback、async-first-present、
label-rollup、async-receipt。

1. Primary 给出 feature 契约、范围和风险，Coordinator 只提出分解与 packet。
2. Primary 验证计划、scope 和依赖后才派发，不让 Coordinator 自增权限。
3. 继续单模型驻留，使用当前模型；成功 Coder 自动交独立 Reviewer，最终
   仍由 Primary 验收。每个必需 Explorer 单独计成功，不能被后续修复覆盖。
4. 精确的跨单元值传递、错误传播和最终集成仍须实测。

暂不扩展复杂异步协议、SQL/事务、安全、陌生大型项目或无人值守运行。
全局 `coordinator_enabled` 保持 false，试验专用配置另行冻结。

## 产物与停止点

- `.local-agents/explorer-runtime.py`：通用提示修改。
- `.local-agents/tests/test_explorer_runtime.py`：新增恢复义务/EOF/未引用测试回归。
- `benchmarks/explorer_completion_trial.py`：四条新鲜 Explorer 对照驱动。
- `benchmarks/work/capability-fit/explorer-completion-1/`：注册、独立判定、
  第三轮逐调用档案、最终审计及 `primary-stage-decision-1.json`。
- `benchmarks/work/capability-fit/explorer-completion-controls-1/`：八条盲审对照。
- `benchmarks/work/capability-fit/explorer-completion-full-1.xml`：完整回归。

weekly used 从 33% 到最后实测 36%，上限仍为 40%。本轮因达到预定阶段
决策停止；没有 commit/push、修改兄弟仓库或丢弃既有改动。
没有精确测量 Primary 主动时间/云 token，不能宣称已经证明节省云成本。
