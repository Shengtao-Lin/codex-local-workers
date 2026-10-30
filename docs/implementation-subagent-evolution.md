# 统一实现 Subagent：能力扩展与复用顺序

2026-10-23。用户批准开始逐步演进；最新weekly used停止线50%，原轮起点34%。
原已关闭批次的40%记录保留，不用新授权改写旧成绩。
默认关闭、兄弟仓库和 Strata 安装只读、不 commit/push，不更换模型或多模型驻留。
这不是已有通用 Agent 放行，也不把旧 HOLD、失败或实验预算覆盖掉。

最新阶段：原生独立安装候选 `strata-release-v4-20261023-2` 已6/6完整独立接受，
三个已暴露任务族各两次。通用pytest/source profile、真实宿主修复控制和原生
故障收尾已测，Web/skills/多文件/Coordinator仍未开放。live全部首次编辑通过，
不证明自主语义修复。产品使用见 `strata-preview.md`；最终预览发布判定另见
`strata-release-quality-20261023-1/decision.json`，旧失败/下文起点描述保留。

## 目标与已知起点

最新原生Agent smoke 已执行：`strata-native-agent-20261023-1`，3个离线控制
符合预期，唯一live因目录SEARCH与精确文件清单不兼容而HOLD，零编辑。
真实模型主动补读已发生，但编码/修复/最终验收尚未评估。原生循环与本地
Messages路由可工作，不等于通用代理放行。manifest-only搜索候选13离线
控制通过，尚未接入或重跑；同时发现完整状态重复进入持久会话的上下文增长。

协调接口补充：`docs/strata-kit-coordination.md`。离线批次
`strata-kit-bridge-20261023-1` 已在真实 installed ToolRuntime 验证14项工具桥
控制；host callback 仍是替身，没有真实文件/检查或模型循环接入。不能与
上一批28项离线控制相加当作 live 成绩。保持原候选、默认配置和成绩不变。

后续已接到真实受控宿主：`strata-bridge-host-20261023-2` 四格预期结果、
`strata-bridge-gates-20261023-1` 完成验收负控；独立164测试及静态检查通过。
前两批的控制预期/独立命令错误保留。仍是 scripted native frontend，
0模型调用，不是原生Agent或通用profile放行；末尾控制副本故意漂移，当前
不得接受。见协调文档的具体边界与交接。最新weekly35%，上限40%。

Primary 给目标、关键合同、权限和最终验收；本地实现代理负责调查、实现、
补充测试、自测、有限修复和自审。自审不能冒充独立 Reviewer；Worker 测试
不能代替不可改的关键保护测试。风险高的 direct-Primary 路径要求完整独立审查。

当前 `strata-subagent-20261023-1` B2/2、`strata-complex-20261023-2` 2/2
均为实验独立接受；实际额外读取0，单函数、事先定位和详细材料，未证明
自主项目调查、多文件写入、自己写测试、失败后语义恢复或云成本下降。
旧 project2/4、Explorer1/2 和 Reviewer 漏错继续有效。

## 复用发现：模型 API 和配套 Harness 不是同一层

已安装 `F:/Strata/harness` 的 BUNDLE/package 显示 DeepSeek Harness
`0.2.1-alpha.3`。精确静态核对以下组件，不导入、不启动它们：

| 组件 | 可复用方向 | 还不能推断什么 |
| --- | --- | --- |
| dsh-agent-loop / SDK JSON-RPC | 本地代理循环、任务生命周期 | 已适配 iq3_s 或符合本仓库验收 |
| dsh-tool-fs / fs-search | 读写、查找、窗口化证据 | 默认具备 packet 路径保护 |
| dsh-skill / skill-filesystem | 目录发现、摘要、按需加载 | 已加载的 skills 有效、安全或不扩权限 |
| dsh-tool-web | 搜索/抓取接口 | 已有可工作的 provider |
| compaction / sessions | 持久记录、上下文管理 | 压缩后保留合同、当前版本和未解失败 |
| dsh-tool-subagent | 委派接口 | 本轮需要递归或同时启动多个代理 |

静态证据有明确适配障碍：sdk-minimal patch 声明 DeepSeek API key adapter、
`danger-full-access` 和持久 shell；fs 工具说明缺省 mutation policy 时直接调用
provider；Web 工具说明 provider 缺失仍可展示但执行失败。不能将安装视为启用，
不能直接运行 bundled profile，也不把这些静态声明当作当前 GUI 的实际运行配置。
`benchmarks/strata_capability_audit.py` 只读取8个固定文件、归档hash和行证据；
未出现某警告不表示已安全。它从不读取密钥、执行 YAML、加载插件或调用模型。

官方来源：[Strata](https://github.com/Niko1221/Strata)、
[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)。
本机精确版本/声明优先于网上最新版本，包存在与实际有效插件树分别记录。

## 实施顺序和失败分支

### 0. 本轮：冻结现有成功候选，完成复用核对

不修改已冻结候选，不为下一题再叠一串 wrapper。
新增只读清单工具、负控和本设计；归档独立批次
`strata-capabilities-20261023-1`，0 Worker 调用，不记作任务成功率。

### 1. 先解耦验收，再选最小代理接口

当前 preparation/canonical capture/check 对函数观察族和四个检查 ID 有实际
绑定。不能删 actual-observations 配置假装得到通用模式。另建默认关闭、版本化
的通用证据 profile：必需真实检查/JUnit、完整源/保护输入绑定、身份、diff、
独立 Primary 验收；类型化函数观察作为有实际支持时的额外证据。

先负控验证缺检查、0测试、版本过期、保护文件变动、错误身份、伪造成功均拒绝，
再对旧 profile 做同版本回归。缺这些控制不得 live。当前尚未实现此新 profile。

随后在同一任务接口下比较复用路径：优先评估安装已有 SDK/工具服务能否注入
既有 scope/editor/check/archive；若必须用宽 shell、云凭据、改安装配置或另 fork
安全底座，则不直接迁移，保留现有 bounded kernel，并只移植需要的窄接口。
“复用整个现成 loop”需要安全和证据适配控制，不以少写代码为由跳过。

### 2. 第一批实测：自主调查 + 源码/补充测试

冻结两个有合规解的隔离工作单元：一题跨真实依赖调查，一题源码与新增测试
协同修改；不得全部给出目标全文又声称验证自主定位。Primary 给行为需求、
批准源码/测试根、关键保护测试，不预先提供算法或所有精确位置。
补充测试只允许批准的新路径；不能删保护断言、修改可信检查或增加依赖。

同一模型、单驻留，起始提议沿用每单元12请求/3有效编辑/每次写后完整检查/
900秒/12288输出/4096推理/64K客户端，不默默扩预算。新动作和请求都计费。
若确因多文件提案或工具开销不足，应先提交新登记而不是无限重启。
只有在 profile/多文件授权/归档控制齐全后才能登记 live；当前还没有新增 live。

普通失败使放行 HOLD，但固定配对可继续诊断；安全、漂移、基础设施故障、
驻留变化、总时间或 weekly40%立即停止派新任务并核查，不 reroll 抹掉失败。
故障归类为权限/证据适配、协议/预算或语义，不统一归咎模型。

### 3. 只在实际失败时验证自修与 Primary 退回

每次修改自动完整检查，真实失败交回同任务剩余预算。Primary 退回链接不可变
attempt，累计请求/编辑/检查/时间；新调用不得获得一套免费的新预算。
只退回已确认的缺陷证据，不注入隐藏测试答案或代写修法；新语义指导记 assisted。
没有失败就记“未验证恢复”，不人为制造退回刷次数。

### 4. Skills、联网和更宽执行逐项接入

Skills 先摘要发现、再按需读取；只挂载批准且 hash 固定的根，禁自动扫描用户
全部 skills。技能说明不授予 shell、权限、依赖安装或修改验收权。技能脚本若要
执行，仍必须过宿主授权。不得把全部技能正文塞进初始上下文。

联网先文档抓取/搜索 provider 的可用性和错误边界，再做真实任务；无 provider
不能让模型假装搜索。外部内容标明来源/时间且视为不可信数据，防 prompt injection、
私网/本机敏感地址访问、凭据泄漏和源码外传。并非开放任意网络 shell。
自审可加但不等于 fresh Reviewer。递归委派、全局默认和 Coordinator 本轮不启用。

## 收益与停止判断

逐单元记录额外读/搜索、有效修改、完整检查、修复成功、no-op、协议恢复、
错误放行/误拒、最终接受、阻塞与 Primary 的定位/语义提示/代写/终验。
一次性 Harness 适配与每任务的准备/协调成本分开；未知云 token、主动时间写 unknown。
不能因本地耗时减少就声称省云 usage；weekly 仅是停止观测。

每项工具/skill 只有在提升独立正确性、恢复或减少 Primary 工作时才保留；
无收益不为了“全能”堆插件。终点是有证据的可用任务族，不是插件数量。
