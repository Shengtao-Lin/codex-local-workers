# 执行模式与推理后端：架构判断

> 历史设计：下文记录2026-10-23时的候选与判断，保留原证据，不作为当前操作说明。
> 当前职责和边界见[Strata架构](strata-architecture.md)，实际入口见
> [受监督使用](strata-supervised-usage.md)。task.20已使用原生AgentLoop加可信宿主、
> 完整检查和fresh Reviewer，并支持显式同任务返工；不是下文单函数/直接Primary
> 实验的资格扩张。执行模式/后端解耦仍是原则，当前模型可替换性并未普遍验证。

状态：2026-10-23 设计建议；不改变生产默认或现有放行规则。

后续用户已批准逐步统一实现代理。接入细节与失败分支见
`docs/implementation-subagent-evolution.md`。只读批次
`strata-capabilities-20261023-1` 确认安装自带 DeepSeek Harness 组件，
但 bundled SDK 的云 adapter / full-access 声明与当前安全边界不匹配。
优先评估受控复用，不直接启动默认 SDK，也不误称已接入 skills/Web。

## 结论

可以并行验证 E/C/R 与统一实现子代理，但不要另做一个“Strata 框架”。
Strata/LM Studio 是推理后端；E/C/R/统一子代理是执行和审查方式。
它们应是两个独立维度，而不是相互替代的产品或两个 runtime 分支。

```text
Primary：需求、风险、工作单元、权限、最终验收
  ├─ 分角色执行：可选 Explorer → Coder → Local Reviewer → Primary
  └─ 统一实现代理：读取/搜索 → 修改 → 宿主检查/修复循环 → Primary
           │
       共用可信宿主
       scope/版本绑定编辑/验证/任务预算/证据归档/审查政策
           │
       推理适配：Strata 或 LM Studio
       模型配置：模型、量化、context、输出、采样、超时
```

模型能力决定哪些任务族适合哪种模式；后端品牌本身不决定工作流。
同一后端可以承载多个角色，同一个模型也可以用于不同模式。
“平行”是策略并列和资格分别记录，不是同时驻留两个模型。

## 当前证据能支持什么

- `strata-subagent-20261023-1`：旧流程 A2/2、直接 Primary 的 B2/2；
  B 未启动 Reviewer，但也没请求额外证据，未触发 Primary 退回。
  这是熟题、详细合同与保护测试下的窄可行性，不是通用代理资格。
- 之前 `strata-project-20261023-2` 仍是最终接受2/4，两个语义缺陷未被
  检查或 Reviewer 发现；不能因为新模式绕过 Reviewer 就抹去这些证据。
- Explorer 后续仍为1/2。统一子代理的成功不能算 Explorer 放行。
- 已验证的单驻留机制是请求前后核对和实验锁，不是全局原子后端切换器。

因此暂不替换现有 E/C/R 默认、不启用 Coordinator，也不证明云成本下降。
Primary 目前仍承担详细合同、测试准备和完整终验；去掉一次本地审查主要
减少的是这轮本地耗时，不自动减少 Primary 的工作。

当前 prototype 是既有 Coder 宿主上增加受控工具并调整审查路由，不是
新造通用代理框架。它有真实的执行循环和持久证据，不是仅一次 LLM call；
但定位、任务细化与测试仍由 Primary 大量预备，写权限仍只改单函数。
不能把“入口跑通”说成已经能接整份项目需求并自主完成。
现有 context 还会主动提供整份目标模块与保护测试资料；复杂例子仍未
请求补读，不能把这一结果解释为工具探索能力已验证。今后若用更简短
任务 brief 检验自主定位，需要明确真实的信息展示/来源，不能暗中隐藏
输入却继续声称模型读过，或强制无意义读取来刷工具使用率。

## 值得修正的设计耦合

### 1. 通用验收证据不该被函数观察适配器卡住

当前 `.local-agents/bounded/prepare_unit.py` 要求 capture target 与可写函数
一致；`capture_validation_facts.py:FAMILIES` 只支持少量调用形态。
`build_samples` 需要 SourceTrace/AdapterContext 等类型，当前没有对应
观察族。正常 pytest 可以验证它，但现有入口仍会在 observation 前置
条件上阻塞。这是宿主适配范围，不是模型能力失败。
`consolidated_harness.py:check` 还校验固定四个 configured-check ID，因此
不能仅删一个配置项来完成解耦；必须是带负控的新版本可信 profile。

建议区分：

- 必需验收证据：当前 diff、保护输入/hash、真实配置检查/JUnit、运行身份；
- 可选辅助观察：特定函数的类型化输入输出、示例、专用诊断。

这不等于静默删除现有 `actual-observations` 检查。应另建明确版本的通用
证据契约并做负控，再迁移；既有 qualified profile 的要求保持不变。
本轮没有修改生产 capture，也不制造错误参数的“观察”来假装支持新任务。

### 2. 审查政策必须显式，而不是绕过旧状态机

实验 B 复用 coder-only 模式和 canonical handoff，生产归档仍是
`validation_passed_pending_review`，实验 Primary 结论单独保存。
这保证了试验不误变成生产 acceptance，但不是长期正式入口。

以后统一的可信审查政策应明确 required reviewers：
E/C/R 要求 Local Reviewer+Primary；经单独批准的 agent 模式要求完整
Primary 验收。区分“按政策未运行”“未到门槛”“启动失败”。不能把
缺失 Reviewer 报告当 PASS，或继承小风险 ECR 的 compact Primary 验收。

### 3. Primary 退回需要任务级预算，而不是每次重置调用预算

当前 Consolidated 每调用最多12请求/3有效编辑，支持减少 recovery credits，
但不是完整的跨 packet 任务账本。新的 packet 还会产生起点检查和新身份。
要正式支持退回，应链接不可变 attempt，并累计请求、编辑、检查、时间、
已解决/未解决 finding；明确新起点检查如何计费，不宣称重启调用免费。
只回传合同关联的缺陷证据，不塞完整历史，也不偷偷注入隐藏验收答案。

### 4. 不要让试验 wrapper 链成为产品接口

当前 Strata 入口通过 transport/client 适配、rules 注入和 coder-only 路由
复用既有宿主；试验适合，但每次加题再多一层 wrapper 会扩大维护成本。
上一阶段归档目录遗漏已经造成真实基础设施失败。

宜逐步形成窄扩展点：推理 client、proposal/evidence codec、review policy、
可选 observation provider。复用一个 editor/validator/archive，不 fork 两套。
一次迁移一个边界，原模式回归不通过就不切换；本文件不授权大重构。

### 5. 任务授权不能永久等同单函数

当前试验仍是单函数编辑、已知文件清单、Primary 预先定位。它不代表
模型能自行拆解项目或改多文件。以后按行为完整的工作单元开放能力，
但多文件写入、批准目录内检索、补充测试都要有独立保护与资格证据。
不要为了让某个例子通过而临时扩大权限。

## 最小演进方向

保留同仓库、同可信底座的两条实验策略；执行模式和模型绑定分开。
资格至少绑定任务族、风险、模型/量化、协议候选和验收政策，而不写成
“Strata 更强所以全部放行”。架构建议中的名称不是当前已实现配置项。

先用更复杂的真实行为单元检验统一代理；失败分别归因于代码语义、
输出/编辑协议、宿主适配和权限/预算。再按实际阻塞选择一个扩展点改造。
Coordinator 以后仍须证明能从批准计划产生可靠工作包，不能仅证明调度。
本轮不做后端切换器、通用 DAG、新角色、全局默认或整体框架重写。

补充实测：`strata-complex-20261023-2` 两个新行为合同都独立通过：
乱序/重复工具事件归并158测试，严格 UTF8 二进制 trace164测试，均通过
format/lint/Pyright。每题一次有效提案，无额外读取或 Primary 救场。
这支持逻辑更复杂的单函数单元可行，不支持跨文件、自主定位或通用规划。
当前模型每题实际输入约6.9K/7.6K tokens，未显示64K context容量不足。
