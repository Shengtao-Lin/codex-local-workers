# 预算对齐与有限证据交互：最小对照设计

2026-10-18。状态：**离线准备，不是 live 注册或新放行**。准备批次：
`benchmarks/work/harness-convergence/evidence-interaction-prep-20261018-1/`。
本文件承接 `local-model-harness-convergence-plan.md`；不替换任何已关闭批次。
最新执行结论见 §9：用户批准后的固定十二格已结束，HOLD；前面的“等待批准”属于准备时状态。

## 1. 核实后的状态与当前目标

R3 开发链通过，R4 HOLD，R5 未准入。正式基底仍是
`coder_unified_preparation.py`，通过 `unified_coder_entry.py` 组合输出、格式化及静态定位适配。
正式迁移 `unified-transfer-20261018-1/decision.json`：12 格注册、11 执行、1 NOT_RUN；
候选 5/6（request_keys 2/2、single_content 2/2、messages_output 1/2），旧对照接受 1/5 已执行。
不将未运行记为模型失败，不重开该分母。

`unified-preparation-20261018-1` 的已暴露恢复新 3/3、旧 0/3 支持调度会阻碍恢复；
`static-span-formal-20261018-1` 的 metadata 循环退化通过检查及 Reviewer、被 Primary 拒绝，
是独立的审查可靠性问题。最新 `semantic-advice-20261018-1` 九请求全部完成：
直接/咨询后均 0/3 all-check，6 次编辑都应用成功；无模型加载、HTTP、长度故障。
这些结果不能概括为 patch 全坏或模型全无能力，也不支持继续追加咨询轮次。

本轮操作目标：在不放宽正确性的前提下，准备能够区分“预算/调度不足”与“按需证据交互收益”的
小批次对照。总体目标仍是可靠验收下减少 Primary 反复细化和救场；本轮不宣称证明经济收益。
最新用户只授权设计及可逆离线准备。新增 live 必须在准确候选、任务、预算、门槛齐备后集中确认。
weekly used 最新观测 8%，停止线 15%，用户后续更新优先。旧文档中的预算和批准均为历史。

### 代码与建议的差异

1. 验证槽不足仍存在：输出适配将请求/验证/编辑限制为 6/3/3，起点检查占一槽，最多两次写后检查。
   另外 `capture_coder_entry.py` 还有独立硬编码三次验证、三个 `edit_revision` 的限制；
   格式化也增加 revision。因此仅改 config 或外层 cap **不够**。本轮离线 v3 实际复现第三次编辑被拒。
   packet limits 优先于 config；两者及包装器都须注册一致，不能回退计数伪造预算。
2. 宿主已经负责编辑应用、版本绑定、静态位置反馈、受控格式化、检查、终态和交接。
   模型无需 VALIDATE/FINISH/自证成功；仍需理解合同、类型/行为边界、当前源码和真实失败，生成合法替换。
3. 正式提案接口缺信息只能 blocked；底层 `WorkerRuntime.read_file/search` 已存在，勿重新写一套工具。
   但重复/无新证据停止主要在旧循环，不在方法本身；复用方法时必须保留这些窄计数器。
4. 已证实阻碍：验证槽、包装器 revision cap。读权限不够是否造成最新语义失败尚未证实。
   没有依据认定缺 shell、多角色或更长提示是瓶颈。
5. messages_output 两次候选的首请求 system/user 内容逐字相同，目标源码 hash 相同
   `226ea47a005f6154be6dbabd097c39d03b4a7c37d328bd5f118c22f1d71619de`。
   成功首提案先区分 Mapping，第二提案增加 Message 单例；失败首提案将 model_validate 放入
   `except Exception: raise TypeError(...)`，第二提案仍保留该广泛捕获。两者 JSON 合法、编辑成功。
   最早可确认差异是首提案的类型/错误分流，不是应用器失配。不能据一对轨迹认定唯一根因，
   不把成功实现喂回 Worker。失败被检查拦住、未启动 Reviewer。

以上逐格记录位于正式迁移 `cases/messages_output-candidate-{1,2}/isolated/.agent/tasks/`
的 canonical runs；不是通过重新运行得到的比较。

## 2. 唯一核心假设与两臂

假设：相同安全底座和足够的有界修复机会下，按需获取批准证据能提高独立完整链接受，
或减少阻塞/退化/Primary 补充定位，而不牺牲错误放行控制。

| 项目 | A：aligned-unified | B：bounded-evidence |
|---|---|---|
| 基底 | 最新统一提案 + 本次共同预算 | 与 A 相同 |
| 模型输出 | 原 replacement / blocked | 同样编辑与 blocked，另可 READ / SEARCH |
| 新增能力 | 无 | 在共同批准事实集合中按需读取/定位 |
| 检查与结束 | 宿主自动执行 | 完全相同；不恢复 VALIDATE/FINISH |

初始任务/源码/依赖材料/失败事实逐字匹配；模型、采样、模板、量化、上下文、可读写范围、
应用器、版本绑定、formatter、可信 profile、Reviewer 和 Primary 标准相同。
B schema/system 必然有最小接口差异，按需返回的额外证据是干预的一部分。
不声称此试验能单独识别工具数量、上下文组织、自主决策各自效应。
安装时记录实际配置；未能核实的量化/模板/seed 写 unknown，出现配置漂移暂停，不偷偷替换。
模型保持 Qwen `qwen/qwen3-coder-30b` 与 Muse `meta/muse-glimmer`；两者 context 24576。
Explorer/Coordinator 均不参与，单模型驻留不变。

## 3. 共同预算（待正式注册）

| 资源 | 每单元共同上限/记账 |
|---|---|
| Coder 实际 HTTP 请求 | 12；READ/SEARCH、无效提案、输出截断恢复均计入 |
| 有效模型编辑 | 3；no-op 不算有效编辑，但消耗请求 |
| 起点检查 | 1，单列 |
| 写后完整 profile 验证机会 | 每次有效编辑 1，共 3；不与起点争槽 |
| 受控格式化 | 1 次命令；单列耗时/实际变更，保留真实 source revision |
| 输出 | 每请求 4096 tokens；最坏 49152，实际照实记录 |
| 协议/输出耗尽恢复 | 最多 2，包含在 12 中；只机械反馈，不加语义提示 |
| B 证据动作 | 最多 6，包含在 12 中；READ ≤120 行，SEARCH ≤10 个 literal 命中 |
| Coder 时间 | 总 900 秒，请求 180 秒；先到者停止 |
| Reviewer | 冻结原 16 请求/4 协议错误/600 秒/每请求 4096；不新增审查能力 |

12 请求给 3 次编辑、最多 6 次补读及最多 2 次协议恢复留有有限余量；这些不是保证全部用完的配额。
第 12 请求产生有效编辑仍有宿主验证机会（除非安全/总时间先到），A 不必耗尽空闲请求。
格式化在该次写后验证前发生；若格式化后需要复验，计入对应写后机会，不沿用旧检查。
禁止在已经用尽验证额度时继续应用未能检查的编辑。最多两个连续 no-op 停止；
保留三次重复读取、编辑前八次/失败后四次无新证据等停止策略。

注意：当前 validator 会因编译/测试失败或首个 static failure 短路。
“完整 profile 验证机会”不等于每次所有命令都执行；逐项记录 PASS/FAIL/NOT_RUN，
不能称跳过的回归通过，也不能仅运行旧失败测试取代 profile。最终接受必须当前版本全部必需检查通过。
不为此 fork validator。若确需补充短路后诊断，只能另提两臂共同、同版本、不可升级 canonical 状态的窄适配。

模型加载独立记录，每次上限沿用 360 秒；每单元外层上限 2220 秒（两次加载+Coder+Reviewer），
批次总墙钟 10800 秒。测量执行/检查/加载分别记账，不双算嵌套计时。
weekly used 每格前观察，达到 15% 不再启动；运行中安全退出方式在 runner 离线控制时确认，
不得以“预算检查”篡改已有运行结果。

## 4. 必要窄修改与不修改项

共同层：实验显式开关、预算 ledger、复用 capture binding 的身份/输入校验，解除旧包装器混合计数；
同时保留 revision、hash、保护输入和 canonical seal。不能给旧批次追补验证。
B 层：一个小 dispatcher 调已有受控 read/search；唯一事实来源是冻结共同 allowlist，
过滤内部 capture 文件、参考实现、私有验收与归档；不能因“底层可读”就暴露它们。
返回带 hash 的限长原始证据；改动后旧版本证据失效。映射旧方法中的 VALIDATE 导航提示，
不重新引入复杂动作协议、任意 shell、权限自授或摘要模型。

失败反馈保留原始命令、源码版本与结果；稳定 test-id/rule 可直接列当前/已解决/新出现。
无法可靠对应时写 unknown，保留原始记录，不做智能进展评分。
Reviewer 固定 fresh context 与 contract-first 候选；协议截断恢复不等于语义重审。
同代码同证据获得实质 rework/escalate 后，该格结束，不反复抽样直到 PASS。

不改生产 `.local-agents` runtime、默认 config、正式 handoff 语义、权限/导入范围、模型、
验收/保护测试、不新增依赖、不 fork 全套系统。若局部任务必须更大范围才能合规，选题前剔除并说明，
运行后才发现则记 blocked，不能偷偷扩范围。R5 仍未准入。

## 5. 离线准备、任务封存与 live 决策

本次已添加 `benchmarks/evidence_budget_preparation.py`，**只供离线可行性控制，不能直接跑 live**。
对应 tests 证明三次模型编辑+一次 formatter 的 revision=4，仍得到起点+三次写后验证；
canonical 当前证据可验证、改源码后拒绝；READ/SEARCH 范围与重复观察、显式 opt-in、no-op 停止可复用。
所有失败控制版本保留在本批，不把脚本提案当模型能力或新题成绩。

尚需在任何 live 前完成：

1. 最小共同预算适配与 B dispatcher/安装入口；冻结候选、schema、依赖代码和协议 hash。
2. 针对此变更补负控：跨范围/私有证据、旧 hash、第三编辑检查、格式化/协议恢复计数、
   输出耗尽/总请求/时间停止、重复读取与 no-op、handoff 绑定；不重复无关旧控制。
3. **此后**准备新题并封存：T1 普通局部实现，T2 保持既有行为的修复，T3 需真实依赖/测试证据的局部任务。
   每题一个有明确合规解的局部单元；记录相互作用的行为要求，不用“单函数”代替复杂度说明。
   目前仅有槽位设计，具体符号/起点/合同尚未选定，不能宣称已有 12 格可运行注册。
4. 独立参考实现验证合同与环境；worker 输入与私有/reference/checks 隔离。
   验证两臂每格的起点 hash、上游 hash、初始消息和批准事实集合相等。不得为 B 故意删掉正常初始材料。
5. 提交候选 hash、准确任务清单、控制结果、共同预算和门槛一次确认；批准后另写不可覆盖的 live registration。

预计 3 题×2 重复×2 臂=12 格。预定顺序：
T1-A1、T1-B1、T2-B1、T2-A1、T3-A1、T3-B1；
T1-B2、T1-A2、T2-A2、T2-B2、T3-B2、T3-A2。
每格从独立快照起步，不继承另一格答案或人工语义指导。
普通失败使资格 HOLD，但安全和预算允许时继续其余诊断配对；不替补失败格。
配置/保护漂移、范围逃逸、安全问题立即停止；未启动格 NOT_RUN，不记模型失败。

保留完整链接受门槛：每臂 6 格、逐题 2/2，实际编辑+当前全部检查+fresh Reviewer+Primary 独立终验。
assisted/takeover 单列、不计自主接受。Reviewer 错误放行单列，即使 Primary 抓到也不能称审查可靠性已解决。
新候选若有错误放行，不提升资格；旧 metadata 错误放行仍保留，不被新样本冲掉。
6/6 只说明该批受限资格，既不是生产启用也不是 R5。
B 无可见收益不保留额外交互；A 也改善时不能把所有收益归给 B；双方都 6/6 则无完成率优势证据。
双方同类边界反复失败报告边界，不继续围绕原题堆提示。

## 6. Primary 负担与混杂因素

一次性：候选适配、负控、三题合同/保护检查/合规参考、封存和注册；预计是半天量级人工工程准备，
不是省下的任务执行成本，实际主动时间尚未测得，不能把估计当实测。
每格：起点核对、调度、终验；原目标是不补修法/边界、不人工定位缺失依赖、不代写。
若发生这些动作逐项标 assisted 与具体内容，并保留失败，不仅记录“无代写”。
已有 canonical/events 可统计请求、编辑、检查、no-op/恢复/耗时；Primary 主动时间、云 tokens
缺少可靠记录时为 unknown。没有 Primary-only 配对，不推算云端节省比例。

仍有混杂：B 证据量/消息组织/行动选择一起变化；共同预算与历史不同；小样本、随机性、
Primary 制题细化以及 Reviewer 未知缺陷检出能力。当前离线控制不能回答模型是否会主动利用工具。
未来 Coordinator 必须验证从批准计划生成可靠任务包，而不只是调度既制 packet；本轮不实施。

当前停止点是“设计和离线可行性已落盘，live 未准备完且未授权”，不是达到预算上限、R4 放行或模型失败。

## 7. 接手模型的执行顺序与交付门槛

本节为用户要求补充的执行交接，不构成新增 live 授权。先完成下面 S0–S3，再集中提交一次审批。
每阶段完成后分析证据并自主进入下一离线阶段；只有预算到线、必须扩大权限/范围或关键判断才需要提前暂停。

### S0：核对并建立独立准备批次

先运行 `Get-Location`，读取 AGENTS.md、本设计及主计划顶部的最新状态；核对 Git HEAD/现有改动、
实际 weekly used 和相关已有进程。上限仍为 15%，不能把上轮 8% 当当前值；不可测则不要冒称预算充足。
不启动、切换或卸载模型，不中断已有批次。发现并发写入时，先避免冲突。
读取上一准备批次的 audit/decision/handoff、controls-v7.xml 和两个新文件；仅按引用核对必要历史。
建立新的独立准备目录并保存基线/本轮文件 hash；不得重用或覆盖已关闭记录。
上一 preparation-freeze 是当时文件版本的证据；本次文档新增本节属于明确授权的后续修订，
不能回写旧 hash 掩盖版本变化。现有离线适配不是正式入口，也没有 B dispatcher。

### S1：实现共同预算与最小 B 接口，完成离线边界控制

只在实验代码中窄适配。先核对 host、packet/config 与 capture wrapper 的所有实际限额，
分别记 initial check、effective edit、post-edit check、formatter、request、protocol recovery 和 no-op。
复用同一应用器、validator、capture binding、canonical archive 和 Reviewer；不用复制整套 runtime。
B 只增加批准事实集合内的 READ/SEARCH；A 保持提案接口。按第 3–4 节预算与安全约束实现。
检查真实请求构造和初始材料一致性，不仅检查配置标签。离线 fake client 禁止网络，
覆盖第 5 节负控及安装入口；确认三个有效编辑都有新版本验证机会，且过期验证不能交接。
成功控制与失败控制都保留。若必须改生产语义、扩大写入/导入权限或大重构，停下报告更小替代。

### S2：冻结协议，再封存准确任务

S1 通过后先冻结 A/B 实现、schema、共同预算、Reviewer、检查与依赖版本，再选择三道新任务。
每题产出上游出处/hash、独立起点、合同、行为相互作用说明、读写清单、公开检查、私有终验与合规解证明。
参考解只用于离线验题，不进入 Worker 输入；两臂每个重复从同一冻结起点独立复制。
不得把旧 messages_output/metadata 或其变体包装成未暴露新题，不因某臂不利而临时换题。
若验题迫使候选改变，登记新候选版本并重新完成相关控制；已经暴露给实现者的题明确标记，
不得继续宣称其为严格未暴露迁移证据。未找到合规任务则报告，不扩大依赖或运行环境。

### S3：完成可执行注册草案，集中请求 live 批准

交付 readiness/decision、准确 12 格 manifest、候选和任务 freeze、逐项控制证据、预算 ledger 说明、
固定配对顺序、普通失败继续规则、安全/时间/weekly 停止条件，以及可直接执行但尚未运行的命令。
记录 Primary 制题/适配等一次性投入；缺少可测数据写 unknown。
确认源码错误被 checks 拦住、Reviewer 错误放行、最终错误接受、误拒、assisted、NOT_RUN 分开统计。
给用户一份集中确认摘要：改了什么、具体测哪些任务、最多多少调用/时间、什么算通过、什么会停止。
此时暂停等待新 live 授权；不得用已有 goal、旧批准或“自主推进”绕过确认。

本阶段完成定义是“离线可复核、候选与准确任务已冻结、可供一次审批”，不是 R4 PASS。
若预算先到，保存部分成果、尚未完成项和明确交接，不把未运行当失败，也不自动启动 R5。

## 8. S0–S3 离线实施结果与待审批批次

2026-10-18：`bounded-evidence-prep-20261018-1` 已完成候选冻结、三题封存和离线就绪核对。
本节最新 weekly used 观测 9%，用户上限 15%；前文 8% 为准备开始时观测。
有效任务版本是 `task-freeze-v4.json` / `cells-v4.json`；更早准备目录与失败记录保留。
正式候选 `bounded_evidence_candidate.py` 共用统一提案基底，A/B 仅按需读取接口不同；
`candidate-freeze.json` 在新题选择前写入。现有生产配置与 runtime 未改。

三题均来自只读的 agent-runtime-kit，抽取到独立模块并保留上游文件/代码块 hash：

| 题目 | 起点及任务 | 交互要求 |
|---|---|---|
| T1 | service/app.py 的 `_sse`：增加多行编码 | CRLF/CR 归一化、末尾空行、事件名拒绝，同时保留单行输出 |
| T2 | openai_compatible.py 的 `_sequence`：支持有限 Iterator | 保留 Sequence 对象身份、拒绝标量/不支持容器、空迭代器与原异常传播 |
| T3 | gemini.py 的 `_usage`：累计 thoughtsTokenCount | 逐字段非负、默认值/原转换、实际 StrictModel/Usage 依赖及输入不变 |

这是封存的局部变更需求，不宣称上游已经承诺这些新行为。抽取去掉类方法装饰器，T3 去掉未使用 cls，
T2 初始 scaffold 增加 Iterator import，模块声明导出原私有 helper 以保留抽取后的静态检查合理性。
源文件名/导入位置有这些明确隔离适配，原函数起点逻辑未预修。T3 的真实依赖定义也给两臂初始材料；
额外 READ 是否有收益仍待实测。Primary 已看过三题及参考解，不能称对制题者盲测。

离线证据：18 项候选/安全/安装/最终请求控制通过，7 项批准/usage/受管超时/防重跑控制通过。
十二格安装预检通过；三题脚本参考提案通过真实 configured checks、canonical gate、冻结 Reviewer 输入认证
及独立验收。没有调用 Reviewer 模型或形成其语义 PASS，也没有任何新 live/Worker 请求。
这些控制与历史控制有重用，不把它们相加为模型成功率。

两臂任务、源码、依赖、合同、公开测试、配置（除 arm）、packet（除 run_id）匹配。
真实初始请求保留：宿主路径、JUnit run_id、pytest 汇总耗时和 Python 对象 repr 地址存在天然差异；
readiness 审计仅归一化这些元数据后核对失败断言/绑定/位置等事实。没有改写送给模型的内容，
也不声称初始消息逐字相同。这些小差异是已披露的残余混杂因素。

准备失败分别来自测试夹具遗漏 Reviewer 原开关、fixture import/抽取导出、参考解类型标注、
误纳入 Ruff 缓存及比较器未处理运行元数据，均保留原始记录；不是本地模型成绩。
来源选择、合同/参考和验收准备是 Primary 一次性工程成本，主动耗时/云 token 未可靠测量。

就绪材料在该批 `readiness-v2/readiness.json`、`registration-v2-draft.json`、`experiment-freeze-v2.json`、
`decision-v2.json`、`handoff.md`。最终封装修订修正了归档脚本的 lint 并保留 v1，候选和任务均未改变。
运行器须取得绑定注册 hash 的新用户批准，并接收两分钟内的实际 usage 观测；
目前没有 live-approval.json。固定顺序、普通失败继续和 HOLD 规则沿用第 5 节。
运行器按 2220 秒单元/10800 秒批次限时处理其自己启动的进程树，未启动单元保持 NOT_RUN，
每格最终仍等待 Primary 对实际 diff 与合同作独立决策，不会凭脚本结果自动 accept。
Coder 记账上限为 12 次 complete 尝试；输入过大等本地预拒绝也保守占用一个请求槽，
实际 HTTP/输出用现有 request stats 核对，不把本地预拒绝说成服务端收到请求。

环境限制：只读模型清单命令 `lms ps --json` 尝试唤起服务后连接超时；未加载/切换模型，
当前驻留、实际模板/量化仍 unknown。live 前需用户确认 LM Studio 服务可用，
不得将本次离线预检当作 LM Studio 对 B schema 的实测兼容保证。
R4 仍 HOLD，R5 未准入；旧 5/6、NOT_RUN、metadata 审查漏检均保持。

## 9. 经批准的 live 批次结论

用户回复“批准”后，按原顺序完成12/12，无补跑、无未运行项。
最终独立完整链接受 A 0/6、B 2/6（T1 B1/2、T2 两臂0/2、T3 B1/2）。
33次 Coder 请求、17次实际编辑均有写后检查、16次 no-op；B 的 READ/SEARCH 使用0次。
三次 fresh Reviewer 均 PASS，其中 T3-A2 的显式 null→0 转换退化被 Primary 对照 preimage 拒绝。
原14测试仍 PASS，不改分母；本批 Reviewer 确认漏检1次，最终错误接受观察0次。
无基础设施故障、无保护漂移。R4 HOLD、R5 未准入、生产关闭；旧5/6及历史不变。

数值差异不支持归因于实际工具取证；三个新题也不能充当与历史批次的纯预算对照。
T3 的“不降低输入”条款未明确 cached>prompt 的等式；B1 的有限接受不证明这一区域的原行为兼容。
共同 loop 还把 no-op 从 recent receipt 改成 ledger 计数，影响未知，已在方法说明披露。
本轮不追加新机制或实验。latest weekly used 10%/上限15%，因固定批次完成停止。

证据：本批 `live-grid-results.json`、`live-metrics.json`、`live-cost.json`、`live-methodology-notes.json`、
`live-decision.json`、`live-handoff.md`；新增 live 授权保留在 `live-approval.json`/`live-registration.json`。
