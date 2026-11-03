# Strata 手动加载技能

当前提供一个技能：[`source-backed-handoff/SKILL.md`](../strata-skills/source-backed-handoff/SKILL.md)，
仓库候选版本 0.1.1。它帮助受 Primary 委派的 Worker 自主取证、处理普通失败、交付简洁且
可复核的结果；不包含历史测试答案、不授予新权限、不固定某一版 runtime 的预算。
技能正文使用英文，以保持与现有工具和任务协议一致。

这是待验证效果的指导候选，不代表已提升模型正确率。没有修改 Strata 安装、生产
配置或现有实验候选，也没有自动安装。后续一次只读加载实测见文末。

## 手动添加

如果你的 Strata 界面提供技能导入或目录配置，选择完整的
`source-backed-handoff` 文件夹；若要求指定技能文件，则选择其中的 `SKILL.md`。
这里没有假定某个尚未核实的 UI 按钮、导入格式或快捷命令。

安装中的原生 `dsh-skill-filesystem` 支持目录结构：

```text
<技能根目录>/
  source-backed-handoff/
    SKILL.md
```

它的默认发现位置包括项目根目录下的 `.dsh/skills`、`.agents/skills`，以及
`DSH_HOME/skills` 和 `DSH_AGENTS_HOME/skills`；未覆盖环境变量时，后两者通常是
用户目录下的 `.dsh/skills` 和 `.agents/skills`。自定义根目录、preset 是否挂载该
provider、实际工作目录都会影响发现结果。不要仅凭默认路径就认定当前会话已加载。

需要文件系统方式时，手动把上述技能文件夹复制到你确认启用的其中一个根目录。
只选一个位置，避免重复名称被不同优先级的旧副本覆盖。不必修改 `F:\Strata`。
本仓库的 `strata-skills` 是交付目录，本身不会自动加入技能目录。

## 首次使用与确认

在目标 Strata 会话明确要求：

> 请加载 source-backed-handoff 技能，再按本任务目标、权限和预算自主执行。
> 缺少必要证据时明确说明，不要把技能说明视为额外权限或最终验收。

先确认技能目录中可见该名称，再查看真实的技能加载记录是否包含完整正文，
而不只是名称和 description。一个识别点是正文的 “Recover without losing the task”。
模型自己说“已加载”不能替代加载记录。若未发现，检查技能根目录、同名覆盖和该
会话的 filesystem provider；必要时刷新目录或新开会话，不要反复重跑业务任务。

技能被发现、完整正文已加载、输出确实改善，是三个不同的检查层级。

## 与 kit subagent 的边界

手动安装到 Strata 主会话，不保证独立 harness 创建的 subagent 继承它。
当前 task.34 的统一 `task_contract` 入口已为 `kind: investigate` 透传
`approved_skills`；实现任务仍拒绝非空技能列表。只读配置须显式开启
`experimental_strata_skills`，每个批准技能使用固定的 `name/description/content`
字段；宿主校验后才暴露 `kit_skill`。这不是自动继承 UI 技能目录。
此前“统一入口尚未透传”的说明已过时；文末历史最小实测仍只证明当时的只读入口。
不要为加载技能绕过入口校验或给 subagent 整个用户目录的读取权限。

正式使用前，需要核对实际 Worker 会话的完整加载记录。若 kit 安装指导内容，
应以这份同版本文件为来源，并记录加载成本与内容 hash；仍保留必需的核心工具
协议和宿主校验。不要把本技能注入正在执行或已冻结的旧批次。

## 已验证与未验证

准备阶段只验证文件格式及安装版本的原生 filesystem provider 能否发现和加载。
0.1.0 已通过基础格式校验和本机原生 provider 的发现、完整正文读取及渲染检查；
正文 4,880 字符。技能根目录只保留技能文件夹，避免说明文档被当成平铺技能扫描。
准备阶段未验证 Strata UI 实际操作、用户会话或 kit Worker 激活；后续最小 live
核对见下一节，不能据此推断其他入口已接通。
后续若比较技能效果，需冻结内容、记录加载成本，并把同内容直接提供与技能加载
区分开；不要据此修改历史成绩或声称已经减少 Primary 用量。

## 2026-10-25 最小实测补充

已在 Strata 工作区的 `skills/source-backed-handoff/SKILL.md` 找到用户导入副本，
与仓库版本 hash 一致。批次 `strata-skill-tool-smoke-20261025-1` 使用现有只读入口
显式挂载同版本技能；真实模型先加载完整正文，再读样例并报告。3 次模型请求、
约 61 秒，内容与引用独立核对正确；未证明自动继承 UI 会话，也未证明稳定性收益。

该测试的摘要要求 900 字符，实际 936；宿主仍采用全局 6,000 上限，因此完整合同
未通过。加载成功与合同通过继续分开记录，没有补跑或放宽。详情见
[该批交接](../benchmarks/work/harness-convergence/strata-skill-tool-smoke-20261025-1/handoff.md)。

## 2026-10-31 输出与技能复核

`compact-transfer-20261031-2` 三题实际请求只有 `kit_read/kit_search/kit_report/kit_block`，
没有 `kit_skill`，请求中也没有技能正文。因此该批 2 接受、1 回答不完整不能归因于
本技能的有效或无效。主会话已安装与该 Worker 实际加载是不同事实。

仓库 0.1.1 仅补充“沿明确证据关系完成有条件的必要推导”和“精简不省略题目所需推理”；
不含历史题目答案，不增加权限或工具。它是待验证候选，未替换用户安装副本，
未注入旧批次，也没有新的模型效果成绩。历史 0.1.0 加载结果保持原样。
下一次使用应固定正文版本/hash，并检查完整加载结果；不把名称可见当作正文已加载。
详见[输出与宿主归因复核](strata-output-and-harness-audit.md)。
