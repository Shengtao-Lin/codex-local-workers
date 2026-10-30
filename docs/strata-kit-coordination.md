# Primary / Strata Harness / kit：协调契约原型

2026-10-23，默认关闭。承接 implementation-subagent-evolution.md。
本轮只验证原生工具调度 seam，未启动 Agent/SDK/模型，没有改生产默认。

后续状态更新：用户将停止线上调至weekly50%；原生Agent已在独立最小
composition中启动并实际调用本地模型，`strata-native-agent-20261023-1`
为HOLD（下述原型段落保留其当时状态）。旧默认SDK、shell/FS/Web/skills仍
未加载，生产默认未改变。

## 首次真实原生 Agent smoke

复用已安装 AgentLoop、LLM registry、DeepSeek Messages adapter、session和
工具服务，不加载 bundled SDK profile。local-only fetch 固定47831/v1/messages，
拒绝重定向/其他endpoint/model；每次请求前后核对同一Strata实例。
这个实现路径不请求 LM Studio API，但“机器未安装/服务未启动”的独立安装
场景仍未实测，不能以LM Studio loaded0代替。

原宿主新增可选client_type注入与真实provider计数回执，默认行为不变；旧
driver源版本在 strata-bridge-gates-20261023-1/candidate-source 中保留。
原宿主run继续唯一负责工具派发和检查。native_request_reservations 与 host
请求机会共同<=12、同一900s截止/3编辑及每次完整写后检查；实际HTTP另计
native_http_requests，不把宿主的offline-client逻辑请求计数当真实模型用量。
不加载retry插件，不允许resume获得新预算。HTTP最多600s且不超过任务剩余时间。

前置：原生生命周期4项（终态、异常、max-token、取消），预算9项通过；
真实宿主composition正控1项、max-token与传输异常负控2项均符合预期，0HTTP。

唯一live：HTTP200两次，约28.14/24.68秒；实际输入7773/17646 tokens、输出
572/503。先kit_read批准的测试，再kit_search(path=src/evaluation_harness,
query=isinstance()。该路径属于packet-readable源码根，但不是exact evidence
file，ApprovedEvidence机械终止为policy_violation。57.094秒宿主时间，1次有效
补读，0编辑、0写后检查，无Reviewer/Primary接受。不能算代码质量失败或成功。

confirmed偏离：旧接口把合法readable父目录当越过精确fact manifest；原生
工具说明只描述path，模型选择了通用目录SEARCH。安全限制正确执行，但
目录级检索应能仅搜索已批准文件，不应自动扩大为全仓库读取。模型也没有
遵循exact-files限制，因此不把责任单归宿主或模型。

supported第二个适配问题：无状态host每次重建完整task_material，桥把它再
追加到持久原生会话；一次read后输入从7.8K涨到17.6K。未到context上限，
不认定它是本次拒绝的原因。后续应只回传新证据/资源/失败和必要当前源码，
不要每步重复不可变合同和完整模块；当前模型上下文仍不缺容量证据。

`strata_manifest_search.py`是尚未接入的新离线候选：不遍历目录，只在已批准
exact files里筛选前缀，保留packet scope、literal、10结果、4 evidence、
版本/重复限制，报告未扫描的批准文件。13项单测通过，另复用9预算控制共22。
缺少真实host组合重放，不是第二次live通过；原失败不可覆盖。

## 采用组合，不让两套控制器同时指挥

```text
Primary：目标、硬边界、关键保护测试、权限审批、最终独立验收
  ↓ 批准任务（持久 task/unit/run 身份 + 共同预算）
Strata 自带 Harness：单个实现 Agent 的循环、工具发现、skills、上下文
  ↓ 窄工具调用（模型不能提供 run 身份或扩大权限）
kit 可信宿主：scope、版本检查、单写锁、应用修改、完整检查、归档
  ↑ 当前源码/实际检查失败/仍需完成项，受同一总预算约束
  ↓ 完整证据包（不是最后一条 assistant 摘要）
Primary：accept / 基于真实缺陷的剩余额度 rework / replan
```

上图是目标接口，不是已完成全部接入。现在已测的是中间的原生工具调度。
E/C/R 是独立可选策略；不在 unified loop 外再开一个 Coder 循环争抢修复，
不自动加本地 Coordinator，也不额外调云模型。当前模型仍 iq3_s，单驻留。

| 谁 | 独占职责 | 不能越权做什么 |
| --- | --- | --- |
| Primary | 用户意图、架构、范围、风险、终验 | 不把 SDK ok 当代码正确 |
| 原生 Agent loop | 选下一步调查/提案，按需 skill，保存会话 | 不直接写主仓库、不用原生 shell 绕过宿主 |
| kit host | 授权、任务账本、编辑/检查/证据/交接 | 不偷偷增加合同或放宽验收 |

## 原生接口实查

本机 dsh-tools 类型和实现提供单调 `tools.guard`：已有 deny 不能被 permissive
pre-execute waterfall force-allow。SDK protocol 提供 initialize、prompt、wait、
resume、shutdown；initialize 带 provider/model，不能假定已支持本地路由。
`session/prompt` 返回入队消息ID，`wait` 返回表示空闲；子代理 status ok/error
和 lastAssistantMessage 都不是 kit 验收证据。
`dsh-authorization` 是获取凭据的交互服务，不是文件路径授权器，不能混用。

证据位置（安装只读）：
`dsh-tools/lib/types/index.d.ts` 的 guard / ToolExecutionInput；
`dsh-sdk-protocol/lib/types/types.d.ts` 的 SessionPromptResult / SessionWaitParams；
`dsh-sdk-jsonrpc-server/lib/types/server.d.ts`；`dsh-authorization/lib/types/index.d.ts`。

## 本轮实际实现的最小桥

`benchmarks/strata_kit_tool_bridge.mjs` 不导入或启动 SDK，不加载原生 fs/shell/
Web/LLM。由独立原生 ToolRuntime context 挂载，只注册：

- kit_read：请求源码范围，真实权限/窗口由 host 决定。
- kit_search：请求文本证据，host 决定许可范围和计数。
- kit_propose：路径、当前 expected_sha256、提案，由 host 校验版本/编辑/完整检查。
- kit_block：证据不足或无法完成，不让模型宣布成功。

task/unit/run 由可信 host 绑定，不接受模型参数里的 run_id。每次调用要经过
显式同步 host authorize；缺失、抛错、异步结果、非 true 均 fail closed。
注册 guard 阻断其他工具，即便它们被另一个插件注册，或 pre-execute 允许。
桥只允许一个活跃 host 操作，透传取消信号；host 仍须真实锁和可取消、可终止
执行。参数先做形状检查，路径、hash 和行为权限不另造一份实现，交原宿主。

**目前 host dispatch 是测试 stub，不是真实文件读写/验证。** 本轮对 installed
ToolRuntime 的执行控制是实测，不把 stub 当完整安全联通，更不表示已有 OS
隔离或通用 Agent 放行。Context 必须专用；结束时应完整销毁，不把带开放原生
工具的 GUI context 当成安全 child。动态修改包/挂载其他插件仍属于可信部署边界。

## Skills、网络和任务返回怎么配合

Skills 优先复用 registry/provider：host 选择批准目录与固定hash，Agent 先看
摘要、需要时加载正文；不扫描全部用户目录，不让脚本执行隐含权限。技能正文
不能改变关键合同、模型预算或检查标准。不得塞满整个 catalog 正文。

Web 使用独立 provider 的受控能力，先验证可用性、私网访问/重定向防护与数据
出站限制；外部网页只作为证据，不能指示修改权限或读取密钥。当前不启用。
早期已批准范围不需要每个补读问 Primary；权限不足或合同歧义才升级。

Primary 退回必须指明合同缺陷和当前证据，不代写解法；同一 task 账本累计
原生 loop 请求、工具、有效编辑、完整检查、协议恢复和时间，不能 resume 就
重置。原生持久会话可复用，但压缩后仍要由 host 重建合同、当前版本、未解
失败。精确 prompt、diff、checks 和结论由 kit 保存；原生会话日志是补充证据。

## 下一项准入（未完成）

### 2026-10-23 实际宿主联通控制（本轮更新）

`strata_bridge_host.py` 将 native frontend 作为现有 Consolidated 的 offline
client：每次 complete 只交出一个工具动作，原 host run 继续执行读/修改/检查；
下一个真实 context 或终态回传工具结果。没有复制编辑/验证器，也不按工具
重新启动 Worker 或重置12请求/3编辑/1起点+3写后检查的预算。
`strata_native_replay.mjs` 使用已安装真实 ToolRuntime，但动作是冻结脚本，
不是 Agent、SDK 会话或 LLM。传入 proposal 的 path/hash 先绑定当前授权目标；
实际源码 guard、格式化、版本化写入、检查、锁和 canonical sealing 仍由原宿主完成。

`strata-bridge-host-20261023-2` 四格都得到预期宿主结果：
正控2个请求（1真实读取+1提案）、1编辑、1写后检查、验证交接；
禁止读、旧hash和错误目标各1请求，0编辑/0写后检查，policy_violation。
独立测试164 passed，Ruff format/lint通过。独立 Pyright 首次命令遗漏已有
--pythonpath，104环境导入错误保留；`strata-bridge-gates-20261023-1` 仅修正
该命令通过，不重新运行四格或pytest/Ruff。

最终三个验收负控拒绝：缺检查/零测试的篡改 validation 参数在 epoch 绑定
处被拦住（不是新跑了零测试 suite）；真实保护文件验证后漂移被顶层交接
拒绝。便捷报告改变不影响正确 canonical 证据，这是正确的反向控制。
正控副本最后故意追加保护测试注释做漂移，原文件preimage已保存，所有历史
归档不改；**当前这个控制副本已 stale，不得拿之前绿色报告接受当前文件**。

`strata-bridge-host-20261023-1` 的负控对象预期错误、-2独立Pyright调用错误
均保留；都是离线准备错误，不算模型错误，也不改旧HOLD或任务成绩。
源版本副本、原命令/结果和负控理由在新批次内。Provider调用0。

当前可以确认工具桥连接了真实受控宿主，但仍保留专用capture，不是通用
多文件profile。native Agent 尚未接入；未来其内部模型请求与工具动作必须
分别计数并进入共同task预算，不能把当前offline动作计数当完整LLM预算。
原生完整prompt/压缩/session恢复、取消中的真实检查终止、写测试和网络
均未由本轮证明。Weekly最终35%，停止线40%，原模型驻留未变。

1. 默认关闭的通用证据 profile：不静默删除旧 capture；先负控验证验收完整性。
2. 把桥 callback 连上既有宿主：实际 path/version/budget/lock/检查/归档负控，
   包括未知工具、旧hash、保护输入漂移、取消后仍写、失败回执被误当 PASS。
3. 显式 local-only client，禁止 SDK cloud fallback；单驻留请求前后核查。
4. 再做冻结的一道依赖调查与一道源码+补充测试任务，无 shell、无递归、无
   自动接受。Primary 比较实际结果与介入成本，再决定保留哪部分。

若无法在原生 loop 下保住这些边界，继续用现有可信 loop，并只复用 skills/
上下文等有价值模块。不为了“全用上”把已验证的约束全部推翻。
