# Strata 通用任务入口

> 版本说明：本文正文保留task.1及后续task.3/task.4的接口与历史结果，不是task.20
> 的当前恢复说明。当前设计见[架构](strata-architecture.md)，安装和正式
> prepare/run/status/resume见[受监督使用入口](strata-supervised-usage.md)。task.20
> 显式返工会自动建立新检查与fresh审查；下文“后续审查另行安排”只描述旧版本。
> 通用任务接口存在不表示完整调查、任意能力组合或通用生产资格已取得。

候选：`0.3.0-task.1`，默认关闭。适用于可信本地项目的受监督试用。
实际资格以 `benchmarks/work/harness-convergence/strata-general-task-stage-20261024-1/decision.json`
和其引用的固定批次为准；接口存在不等于任意任务都已验证。

Primary 给目标、材料范围、关键行为和交付要求；Strata 自主读取、搜索、组织步骤，
并在实现任务中编辑、自测、修复。Primary 保留权限批准和最终接受。
一个 Strata iq3_s 驻留实例串行承担这些工作及独立审查，无需 LM Studio 后端。

## 两类任务，共用合同

- `investigate`：调查、提取、比较、材料整理，产物为带证据和不确定项的报告。
  不编辑、不运行项目测试；直接交给 Primary 核对。
- `implement`：批准范围内的 Python 修改。继续使用原编辑器、格式化、完整检查和
  有界自修；检查通过后，入口自动建立独立源码快照并调用 fresh 只读 Reviewer。
  Reviewer 不接受任务，Primary 最终验收。

任务模式是权限和验收路线，不需要安排一串必经的 Explorer/Coder 工位。
没有任务能力授权就不挂载额外工具；已有 web/固定操作/只读孩子的资格仍按原范围。
当前入口拒绝 web 与可写实现组合。固定操作仍只有 json-summary；没有任意 shell。

## 最小只读合同

```json
{
  "schema_version": 1,
  "task_id": "inspect-project-settings",
  "kind": "investigate",
  "goal": "提取项目声明的 Python 版本、核心依赖与可选依赖，并区分声明和实际安装状态。",
  "deliverable": "简洁的比较表、真实来源引用和未确认事项。",
  "scope": {"read": ["pyproject.toml"]},
  "risk": {"feature": "medium", "unit": "medium", "integration": "medium"},
  "required_behavior": [
    {"id": "declarations", "text": "仅依据批准文件回答，不把未声明解释为未安装。"}
  ],
  "acceptance_criteria": [
    {"id": "evidence", "text": "关键事实有实际读取的来源；缺失证据明确报告。"}
  ]
}
```

这份合同属于可信输入。网页、源码和子报告不能修改它或增加权限。
支持的本地文本材料沿用宿主清单：Python、TOML、JSON、INI/CFG、Markdown、TXT，
最多125个批准文件；不是任意二进制文档处理器。

配置复用已验证的 Strata 配置，显式加入 `"experimental_strata_task": true`。
安装包的 `config.this-host.json` 只适用于本机现有 Python/Strata/tokenizer 路径与hash。
不自动安装依赖、下载或切换模型。

```powershell
python .local-agents/strata-task.py prepare --contract task.json --config config.json --apply
python .local-agents/strata-task.py run --task-id inspect-project-settings --attempt-id first
python .local-agents/strata-task.py status --task-id inspect-project-settings
python .local-agents/strata-task.py cancel --task-id inspect-project-settings
```

prepare 不调用模型；不带 `--apply` 为预览。已有任务不能换新 attempt 名字重置预算，
也不能对同一补丁反复抽样 Reviewer。取消请求可以覆盖 Worker 和已启动的独立审查。
status 是归档状态；最终验收仍须确认源码和检查证据没有变化。

## 实现合同补充

`scope` 显式列出 read/readonly/modify/create/forbidden。新增 `implementation`：

```json
{
  "edit_targets": [{"path": "src/example.py", "anchor": "def existing_function("}],
  "focused_tests": ["tests/test_example.py"],
  "supplemental_tests": [],
  "validation_profile": "project-strict"
}
```

目标、required_behavior 和 acceptance_criteria 描述真实行为约束；不必指定逐行修法。
项目检查由可信配置决定，必须包含项目实际要求的格式、lint、类型和测试检查。
已有上限保持：4个源码文件、2个补充测试；16请求/24工具/4编辑、起点检查1次和
写后完整检查4次、1800秒。Reviewer 另用原10请求/16工具/900秒预算，单独计时。
只读任务保留原8请求/16工具/900秒；孩子如获准，仍扣父任务总账。

只读报告另有已存在的受控配置：显式设置
`"experimental_strata_capabilities": true`，任务不声明任何 capabilities 时，
仍不获得联网、固定操作、子派工或写入权限；使用10请求/16工具/12证据/900秒、
2次协议恢复，并由报告 schema 和宿主强制摘要最多2000字符。
这与普通只读8请求配置不是相同预算，统计时必须注明；不能把切换配置后的成绩
覆盖旧失败。真实任务原批次与这一配置的条件复测见
[试用记录](strata-real-pilot-results.md)，实际成绩以独立批次 decision 为准。
不要仅为获得报告限制而给任务填写不需要的能力授权。

`ready_for_primary` 只代表当前路线已交付待验收结果。实现路线必须有独立审查通过，
只读路线也可能有语义错误；自然语言要求（包括摘要长度）仍需要 Primary 核查。
范围、版本、当前完整检查、审查来源等机械条件由宿主强制执行。

## 当前恢复和信任边界

Worker 内部可以按原预算多次读取、编辑、检查和修复；无需 Primary 逐步指导。
统一入口目前覆盖首次运行、状态和取消，不提供自动 Reviewer→Coder 退回循环。
中断、预算耗尽或 Reviewer rework 后由 Primary 检查归档，必要时使用原实现入口的
明确 resume/feedback 流程；这不会补充预算，后续独立审查仍须另行安排。
不要创建新 task_id 来绕过旧失败、替换已关闭成绩或重抽相同审查。

实现检查会在宿主权限下执行修改后的 Python；工具和编辑范围不是 OS 沙箱。
公开联网仍仅限已合格的只读研究，不将不可信网页直接混入可写任务自动执行。
旧 timeout 调查 HOLD 不变，未放行通用语义权威、任意脚本、更深递归或 Coordinator。
目前尚无 Primary-only 对照或精确云用量测量，不承诺具体节省比例。

## 后续报告交接试验（非默认发布）

隔离候选`0.3.0-task.3`另试验完整报告归档和机械短预览；不要求模型把所有工作
压进短摘要，且保留全文和未知项供Primary验收。该候选仅显式
`experimental_strata_report_receipt: true`的普通只读路线可用，拒绝实现/能力工具组合。
本轮2/3合法交付、1/3完整内容接受，门槛仍HOLD，不替代本文`0.3.0-task.1`预览资格，
不视为生产推广或所有报告都已可靠。参见[独立结果](strata-report-delivery-results.md)。

后续`0.3.0-task.4`在同三格上取得3/3交付和所需事实内容接受，限定普通只读研究。
显式增加`experimental_strata_report_binding: "observed-line-v1"`后，模型只给path/line，
宿主绑定当前已观察原文；不再要求模型复制quote。默认旧协议、实现和Reviewer不变。
仍有一处非阻塞正文引用编号警告，且全是已暴露题，不代表普遍稳定。
配置片段、成本与精确边界见[已观察引用试验结果](strata-report-binding-results.md)。
