# 分层诊断：推理环境、交互方式与任务语义

2026-10-06。用户授权按研究结论修改与执行；weekly used 开始 46%，停止线 60%。保持当前模型、单驻留及生产配置；不修改兄弟仓库、不安装依赖、不 commit/push。

## 目的与边界

先证明相同模型在短上下文、无工具情况下的实现能力，再决定是否值得改工具循环。不能由一个微问题推断模型整体能力，也不能把 runtime 回归通过或 Reviewer 合法 REPORT 当语义成功。Coordinator 阶段 1 仍 HOLD，原资格门槛不变。

feature_id 为 layer-isolation，feature/unit/integration 风险 high。Primary 拥有 scope-and-hash-guards、immutable-evidence、separate-semantic-and-format-scores、no-qualification-credit；风险来自模型补丁应用和保护测试执行，不向本地模型委派 gate 决策。具体八题为 medium 单元，无依赖。该 harness 与现有 VALIDATE 一样假定可信本地仓库，不宣称 OS 隔离。

## 第一批：直接生成

冻结 `roleq-layer-baseline-1`；新增八类题：精确整数、缺失/空值、异步等待及错误传播、成功记录聚合、稳定去重、相似符号编辑、跨文件时间单位、跨文件路径编码。前两类明确为已暴露语义控制；其余也只用于开发诊断，不计未见资格。

每题两轮独立 workspace，第二轮逆序，最多 16 次请求，不按语义失败提前删题或补抽成功。参考实现通过全部 pytest/Ruff，初始错误变体必须失败，才冻结全部输入并调用模型。参考不进入模型 scope。

直接臂无 agent 循环、无服务端 grammar，使用普通 JSON 返回完整授权文件；这是必要的输出格式要求，不称为完全无格式负担。给齐当前源码/保护测试与短契约，保持采样、上下文与每请求输出预算。相对于完整 Coder 同时改变了信息呈现与交互方式，所以只作分层诊断，不作单变量因果断言。补丁先整体校验，再经冻结 runtime 的已读/hash/scope 编辑门槛；独立执行保护测试及 Ruff，分别记录格式、语义、静态检查、基础设施错误、时间和原响应。

每批最多两次调用，Primary 批间核查 usage；不伪称 runner 能自动读取账户 usage。中断或已开始格不自动重放。首批语义失败仍按登记完成 16 格；基础设施失败暂停诊断，未运行格保留。

预登记阶段决策：至少 6/8 题两轮语义均通过，才开启相同题的最小工具循环与完整 Coder 对照；否则先排查服务/语义下限。此阈值是诊断分流，不是产品通过率或放宽资格 gate。第二阶段需另行冻结，不冒充本批已执行。

## 后续分支

- 工具层：保留授权编辑、保护测试、真实验证；缩短交互说明与历史作为候选，和完整 Coder 对照。精简交互不能等同取消安全 gate。成功 Coder 仍需独立 Reviewer 和 Primary 才能接受。
- 服务层：核对实际后端、模板、KV 配置，再考虑单变量 Flash Attention 对照，保留原配置并恢复；不凭网上 issue 直接关参数、升级或换模型。模型替换与环境安装另行明确范围。
- Reviewer：隐藏缺陷/干净代码配对，按真实因果识别和误报计分；不靠引用格式得分。
- 胜出候选完成原六题两轮、Reviewer 对照和依赖链资格后才引入 Coordinator；本轮诊断不替代它们。

## 执行结论：首层已完成，未进入工具层

冻结批次 `roleq-layer-direct-1`：16/16 请求完成，零模型重试。普通 JSON 合格 11/16；其中原保护 pytest 通过 9/11，静态检查通过 8/11。五个格式失败中四个有外层 Markdown，一个有损坏的 JSON 引号；这些格的原 `semantic_pass: false` 只是“未得到通过证据”，不能写成五次代码语义测试失败。

两个重复均通过原语义验收的是 missing-label、async-fetch、success-totals、edit-anchor。duration-pair 两次用 `isdigit()` 放行非 ASCII 数字；其语义家族此前已暴露，初始 manifest 标成 new-diagnostic 不准确，追加更正但不重写 manifest。本批本来就没有任何未见资格信用。

`roleq-layer-output-audit-1` 在新 workspace 离线解释五个格式失败及 encoded-path r1：只剥一层完整外部 JSON fence，不能修引号、改源码或请求模型。exact-count 两次仍放行 bool/int 子类；stable-latest r2 去 fence 后通过原测试，r1 JSON 损坏保持无法执行。encoded-path 两次使用 `quote(..., safe='+')`，虽可逆但违反无额外 safe 字符契约。原 fixture 缺少规范编码断言，是 Primary 测试盲区；新独立 `a+b → a%2Bb` 断言两次都失败。保留 r1 原测试通过记录，不把它追改成原轮失败或接受。

新增 `layer_isolation_followup.py` 只生成未来加强版本：补上 plus、空格、百分号规范编码及近正确 mutant，同时更正 ASCII 家族 exposure。旧源码、语料、测试、模型原响应和分母保持不变。离线审查保存了首批 driver 副本；全部补丁经原 SafeEditor，不放松权限。

阶段决策：四类两轮稳定，低于预登记六类门槛，因此不启动最小循环/完整 Coder 大批对照，不启动 Reviewer 或 Coordinator。本次局部异步/聚合成功与此前真实项目失败不是同题比较，不能声称修好了真实 SQL/异步能力。下一项最小实验应选固定短题比较原始 Python 输出与 JSON 文件包装，避免将格式负担误判为能力下限；再根据结果做 serving 单变量核查。没有证据认定 Flash Attention 或某个后端是原因，因此本轮不改这些设置。

准备期曾发生宿主 Ruff 默认规则与显式 kit 规则不同、系统 pytest 临时目录权限错误；均在模型前解决，单列 Primary/环境问题。参考实现及错误变体预检八组通过；首轮全回归 634 passed、58 subtests（不含后加的离线审查测试），后续最终回归另行记录，不能用旧数字覆盖新增代码。

最终完整回归 **637 passed、58 subtests passed、零排除**，证据 `benchmarks/work/capability-fit/layer-full-2.xml`；新增五个 Python 文件 Ruff/格式检查通过，git diff-check 通过。对比冻结基线，全部 `.local-agents` runtime/config/tests hash 未变。结束 weekly used **48%**（开始 46%，上限 60%），按阶段结论停止而非预算耗尽；仅 Qwen 驻留且 idle、queued=0，无待运行模型调用。未 commit/push，未修改兄弟仓库。首批独立调用总计约 23.45 秒（预加载模型，含局部检查；不含准备、整体回归或 Primary 时间），不能据此宣称端到端节省。

## 第二批预登记：只改变输出形式

继续授权开工 weekly used 48%，停止线 60%。基线 `roleq-output-baseline-1`；批次 `roleq-output-form-1`，使用四道已暴露单文件题：exact-count、stable-latest、async-fetch、missing-label。每题 raw Python / 普通 JSON 两臂各两次，共 16 次，不重试、不按结果选题。第二轮逆序且每题两臂执行次序交换；每次独立 workspace。

配对 user payload 完全相同，只改 system 中的输出格式说明及对应解码器；两臂均无服务端 grammar，同模型、采样和输出预算。参考实现/错误变体先验证；首调用前固定全部 workspace、参考、测试、驱动 hash 与副本。原始 Python 臂仅允许唯一授权目标文件，仍经 SafeEditor 的 scope/hash 门槛。

主格式指标要求无 Markdown 外壳；内容测量预先允许剥除恰好一个完整外壳，两臂对称处理，不修引号或代码、不从 prose 提取子串。另记 decoded、source_compiles、semantic_evaluated、semantic_pass；无法执行者为 null，不伪造语义失败。每批两次并外部检查 usage，基础设施错误暂停。

阶段决策：如果某族 raw Python 两次仍错，则 JSON 包装不是该族失败的唯一原因；如果某族 raw 两次通过而配对 JSON 失败，才支持该族的输出形式收益。四道选定开发题不能支持通用能力或生产 promotion。完成 16 次形成阶段结论，不启动 Coordinator、不据此改模型/Flash Attention。

## 第二批结果：格式收益存在，但不能解释全部语义错误

`roleq-output-form-1` 完成 16 次请求，零重试；四组参考/错误变体预检通过。配对 user payload 相同，模型、加载参数、采样、上下文与输出预算不变。仅格式提示与解码器不同，均不使用服务端 grammar。

| 题型 | 原始 Python（去完整外壳后） | 普通 JSON（同样允许外壳剥除） |
| --- | --- | --- |
| exact-count | 0/2，均错误放行 bool/int 子类 | 0/2，同样错误 |
| stable-latest | 2/2 原保护测试通过 | 两次 JSON 引号损坏，语义未执行 |
| async-fetch | 2/2 原保护测试通过 | 2/2 原保护测试通过 |
| missing-label | 2/2 原保护测试通过 | 2/2 原保护测试通过 |

Python 内容可执行 8/8、语义通过 6/8；JSON 内容可执行 6/8、语义通过 4/6，另外两次不能记作语义错误。Python **8/8 都有 Markdown 外壳**，严格无外壳格式合规为 0/8；JSON 为 4/8。静态检查通过 Python 2/8、JSON 4/8，其余已执行代码的静态失败均为 Ruff format，lint check 均通过。两轮去重 Python 虽过 pytest，仍有格式错误，因此不能报告为正式单元通过。

结论：对 stable-latest，JSON 源码转义负担的影响两轮均复现；对 exact-count，即使直接返回 Python，错误仍复现，不能归咎于 JSON 或工具循环。这不是“模型完全不会编码”，也不是“换个输出形式便稳定”；本机推理配置与模型语义能力尚未被因果分离。低温下两轮相同输出也不意味着足够的统计独立性。

后续应分两条有界路线：单文件源码返回只能作为受控适配候选，保留 scope/hash、formatter、保护测试与独立 Reviewer；语义分支先做推理后端/加载设置单变量检查，不能用格式改善替代。此处没有推进完整工具层资格或降低 gate，没有调用 Explorer、Reviewer、Coordinator，没有生产 promotion。

初版离线测试发现原始 Python fenced/plain 末尾换行不一致，已在任何模型调用前修正；失败 JUnit `output-unit-1.xml` 保留，修正后 8 passed。可核查裁决在 `roleq-output-form-1/primary-assessment-1.json`，全部原响应、源码、独立 JUnit 与冻结驱动保留。

本批最终完整回归 **645 passed、58 subtests passed、零排除**（`output-full-1.xml`）。新增脚本/测试 Ruff、format-check 和 git diff-check 通过；全部 `.local-agents` runtime/config/tests 与开工冻结 hash 一致。weekly used **48%→49%**，按预登记阶段结论停止，不是预算耗尽。仅 Qwen 驻留、idle、queued=0；没有 commit/push、依赖安装、模型/加载参数切换或兄弟仓库修改。

## 第三批预登记：可恢复的 Flash Attention 对照

开工 weekly used 50%，上限 60%。保持 Qwen3-Coder Q4_K_M 与当前引擎，只临时通过官方 `/api/v1/models/load` 改 Flash Attention，不编辑保存偏好。`roleq-fa-baseline-1` 冻结 runtime/config；`roleq-flash-attention-1` 固定 on-r1 → off-r1 → on-r2 → off-r2 → restored-on 五阶段，每阶段精确类型实现、缺失值实现、精确类型微问题各一次，共 15 次。前两题完全复用上一批已验证参考/错误变体的 fixture，准备期逐路径 hash 比对。所有实现均为原始 Python 内容，保留格式指标，不混入 JSON 编辑信封。

feature/unit/integration 风险 high，契约为 single-residency、restore-original-load-config、immutable-evidence、no-qualification-credit。持有 kit 的独占模型 lease；只允许单个原 Qwen 实例，busy/外来实例拒绝卸载。切换后比较完整 API 可见 config，除 flash_attention 外任何差异都停止评分。每阶段 finally 恢复并回读原配置，失败保留诊断且不推进下一阶段；加载请求允许 600 秒，不因命令初次 yield 取消模型。

两次 off 均正确、对应 on 错误且可见配置无漂移，才视为该样本上的候选收益；否则不推广。最后 restored-on 提供恢复控制。接口未暴露的 KV 精度、内部模板/引擎状态和重载缓存效应未完全隔离，不能声称严格排除了其他隐藏差异。批间核对 usage，任何基础设施错误停止，未跑格保留。Reviewer/Explorer/Coordinator 均不调用；没有完整资格或省成本结论。

官方字段依据：[Load a model](https://lmstudio.ai/docs/developer/rest/load)。CLI 未提供 Flash Attention 开关，故不伪造 CLI 参数或安装 SDK；使用已有 REST API，并记录请求、响应和回读配置。

## 第三批结果：FA 对照被 V Cache 量化依赖阻断

`on-r1` 实际三次调用完成：精确类型实现失败、缺失值控制题通过；微问题返回 `[False, True, False]`，既不是合法 JSON，其值也与要求的 Python 求值结果不同。随后 `off-r1` 在加载阶段返回 HTTP 500，关闭组尚未发生模型推理。其余 12 个计划调用均 not run，不能计成功/失败，也不能声称做完 on/off 对照。

只读 LM Studio server log（`C:/Users/Lin/.lmstudio/server-logs/2026-10/2026-10-06.1.log`，2026-10-06 19:16:50）提供明确 `model_load_failed`：当前 V Cache Quantization 要求 Flash Attention 开启；需要启用 FA 或把 V Cache Quantization Type 设为 f16。REST 回显未包含该精度字段，因此“可见 config 一样”不能视为完整推理环境一致。本批不知道实际是 q4、q8 或其他 V 精度，不能猜测。

finally 恢复路径从无驻留状态成功加载原 Qwen，完整 API 可见配置与原值一致，FA=true、context=24576、parallel=1；CLI 回读仅 Qwen 驻留、idle、queued=0。没有改保存偏好，也没有在失败后偷偷改 V Cache/上下文以让候选加载。

阶段结论：发现的是**加载配置依赖**，尚非语义不稳定的已证实根因。下一步先核对 K/V 的具体精度及可恢复配置途径，保持 FA=true，只比较原 V 精度与 f16；建立可加载的 f16 基线后，再比较 FA on/off。若显存不足则记录基础设施限制，不同时缩短 context 或更换量化冒充单变量实验。当前批次封闭，不盲重试。

完整回归 **649 passed、58 subtests passed、零排除**（`fa-full-1.xml`），新增切换/恢复/漂移/外来实例保护测试通过；Ruff、format-check、git diff-check 通过，全部 `.local-agents` runtime/config/tests hash 与基线一致。weekly used 开始/结束均显示 **50%**，不表示 token 零消耗；本次按基础设施阶段决策停止。未 commit/push、未修改兄弟仓库、未切换模型或安装依赖。完整裁决 `roleq-flash-attention-1/primary-assessment-1.json`。

### 外部依据链接（历史调查）

## 用户设置 V Cache F16 后的当前实例短测

用户截图显示 Qwen3-Coder：K Cache Q8_0、V Cache F16、FA=true、context=24576，并确认已加载。`roleq-vcache-f16-user-1` 在首调用前冻结六次请求：exact-count 实现、missing-label 实现、精确类型微问题各两轮。驱动不卸载/重载或编辑偏好，保留当前实例；API 可见配置前后相同，只有 Qwen 驻留。

结果：精确类型保护测试 **0/2**，两次仍使用 `isinstance(value, int)` 并错误接受 bool/int 子类；缺失值保护测试 **2/2**；微问题 **0/2**，均返回 `[False, True, False]`（非 JSON，且值错误）。这是当前实例未观察到改善，不是“已证明 F16 无效”：REST 不暴露 K/V 精度，实际 loaded 精度尚不能独立核验，用户截图/确认作为外部配置证据单独保留。不启动 FA 关闭重载，以免自动加载套用另一套保存偏好后混淆变量。

下一步先确认实例实际 K/V 精度，再决定加载参数对照；不重复同题或继续堆语义提示。Coordinator 仍 HOLD，无模型能力接受。辅助解析/配置恢复相关回归 **24 passed**（`vcache-unit-1.xml`）；新增驱动 Ruff 通过，本轮未重跑全套，上次全回归仍为 649 passed、58 subtests。weekly used 开始/结束显示 51%；未 commit/push、未改生产 runtime、未改兄弟仓库，结束 Qwen idle。裁决 `roleq-vcache-f16-user-1/primary-assessment-1.json`。

## 用户纠正加载状态后的独立重测

用户随后明确说明上一批 V Cache 尚未正确加载。因此 `roleq-vcache-f16-user-1` 不能用于 F16 效果判断；原响应和测试不改写，追加 `user-correction-1.json` 留存纠正。新批 `roleq-vcache-f16-user-2` 在用户再次确认加载后，冻结同一题库并完成两轮共六次请求；不卸载、重载或修改参数。

精确类型保护测试仍 **0/2**，实现错误放行 bool/int 子类；缺失值控制题 **2/2**。微问题正确率 **0/2**：第一轮 `[false, true, false]` 是合法 JSON，第二轮 `[False, True, False]` 非合法 JSON；两轮值均错误，正确值应为 `[true, false, false]`。不能把第一轮格式合规当作稳定恢复。

结论限于用户重新加载后的当前实例：此组短测仍未观察到语义恢复。API 不暴露 K/V 精度，实际 F16 仍是用户确认而非独立核验；没有完成 FA on/off 配对实验，不能归因到模型权重或推理后端。Coordinator 继续 HOLD，不计角色资格。六次原响应、实现和独立验收记录完整保存；新增重测入口 Ruff/format、git diff-check 通过，本次未重跑全套 runtime 回归。结束仅 Qwen idle、queued=0；weekly used 52%，未 commit/push 或修改生产 runtime/config。

## 三个 Coder 模型交叉筛查（coder-model-screen-1）

### 冻结设计与配置证据

2026-10-06，weekly used 52% 开始，上限 60%。新快照 `coder-model-screen-baseline-1` 保存开工 runtime/config、Git 状态和服务清单；原有未提交改动不动。三模型各跑同样 8 题一次，共 24 次请求，无重试、无工具循环、无答案 few-shot。题目为已有开发诊断题，不是陌生资格题；encoded-path 使用已补充 canonical encoding 断言的版本。每个参考实现通过、每个错误变体失败后才开始推理。每格独立工作区、保护测试、原始请求/响应、JUnit 与静态检查均保留。

单文件返回完整 Python；双文件返回完整文件 JSON，预先允许剥除一个完整 Markdown 外壳来测语义，严格格式指标仍记不合规。同一道题在三模型间提示不变。固定 temperature=0.1、top_p=0.9、top_k=40、min_p=0、repeat_penalty=1、输出预算4096，不启用服务端 grammar。此为共同操作点比较，不是各模型最优采样能力比较。

CLI 确认 Qwen 官方包 Q4_K_M、mradermacher i1 IQ4_XS、Devstral Q4_K_M。只读保存配置确认三者 K=q8_0、V=f16；每次新加载后 API 确认 context=24576、parallel=1、FA=true，无 speculative draft。KV 精度和实际聊天模板未获独立引擎日志验证，不能说已排除模板/加载问题。API 显示 eval batch 分别1024/512/2048，未擅自改动；所以不是仅量化一个变量的因果实验。选中引擎为 CUDA12 llama.cpp 2.51.0。每个模型完成后卸载，再加载下一模型，结束恢复开工的无驻留状态；未改保存偏好。

### 结果与诊断脚本缺陷

| 题型 | Qwen Q4_K_M | Qwen i1 IQ4_XS | Devstral Q4_K_M |
| --- | --- | --- | --- |
| exact-count | fail | fail | fail |
| missing-label | pass | pass | fail |
| async-fetch | pass | pass | pass |
| success-totals | pass | pass | pass |
| stable-latest | pass | pass | pass |
| edit-anchor | pass | pass | pass |
| duration-pair | fail | fail | fail |
| encoded-path | fail | fail | fail（离线验收原响应） |
| 语义通过 | 5/8 | 5/8 | 4/8 |
| 语义及全部静态检查通过 | 2/8 | 2/8 | 3/8 |
| 严格无外壳格式合规 | 0/8 | 0/8 | 1/8 |

24 次响应收齐，但直接 runner 在 Devstral 最后一格误把“完整文件返回中的未变化文件”发送给 SAFE_REPLACE，被合理的 no-op 保护拦截。保留 `model-2/infrastructure-error.json`，不冒充原 runner 正常完成。新增独立 `coder_model_screen_audit.py` 将原响应应用到全新且 hash 相同的题目快照，仅跳过逐字相同的文件，其他编辑仍走 scope/hash guard；保护测试实际运行并失败。离线审计 **0 次新模型调用**，不修模型答案、不改旧驱动、不放松生产 no-op gate。审计结果在 `offline-noop-audit-1/result.json`。

两个 Qwen 都使用 isinstance 而非 exact type；Devstral 排除了 bool 但漏掉 int 子类。Devstral missing-label 将显式 None 当成缺失。三者均未满足 ASCII/URL 编码边界。这些失败在没有 agent 循环时出现，因此完整工具循环不是这些错误的必要条件；但共同请求使用 JSON 包装源码/契约，不能由此直接断言纯模型能力不足、后端无错或三个模型都不适合任何 Coder 工作。

### 阶段决策

没有模型达到预登记的 >=6/8 语义筛查候选线，停止本批，不进入完整角色资格或 Coordinator，不更换生产 Coder。这是一次共同条件下的筛查，不是稳定成功率估计，也不能凭一轮给模型排通用能力名次。

下一步应优先区分 **契约呈现与错误修复能力**：冻结自然语言分段源码与当前 JSON 包装的配对提示；随后给初次失败者同样的真实 pytest 失败证据，限制一次修复，单独统计修复转化率。避免继续重复无反馈首答或加大任务复杂度。修复证据不能直接给参考答案；迁移题必须与开发题分开，Reviewer 仍需独立资格评估。

本轮原相关回归31 passed；增加 no-op 离线处理测试后新测试文件8 passed（前7项重复，合计32个不同测试）。Ruff、format-check 与 git diff-check 通过；本轮未跑全套 runtime 回归，未修改生产 runtime/config、兄弟仓库或 Git 历史。weekly used 52%→53%，因阶段结论停止而非额度耗尽。

## 契约呈现与一次报错反馈（contract-presentation-repair-1）

### 预登记设计

weekly used 53% 开始，上限60%。新冻结 `contract-presentation-repair-baseline-1`；五道已知开发题 exact-count、missing-label、duration-pair、encoded-path、async-fetch，三模型各跑 JSON 输入和分段原文输入两臂。两臂契约文字、可读源码/测试、输出格式、采样参数不变，仅改变输入呈现；按模型/题目交替两臂顺序。每格独立源码、原始响应、不可覆盖的 attempt-0/1 记录与 JUnit。复用上一批参考/错误变体验证，逐路径 hash 确认题目一致。

共30次首答。只有已经解析、实际执行且 pytest 失败者获得一次修复：保留原对话，加入真实 pytest 完整输出和当前可写源码，不给参考答案、手工定位提示或额外样例。静态检查单独失败、无法解码者不追加调用。最多60次，实际30次首答+15次修复=**45次**。继续使用 scope/hash guard，完整文件中未变化者跳过编辑，不弱化生产 SAFE_REPLACE no-op 保护。模型加载完成后核对可见配置；每组完成卸载，结束无驻留。

预登记的呈现收益标准：同一模型至少两题 sections-only 语义成功、没有 json-only 成功，才作为小样本候选收益。一次重复不证明稳定性，原始输出不合规不自动等于语义错误，Reviewer/Coordinator 不调用。

### 正式结果（不包含事后提取审计）

| 模型 | 首答语义通过 /10 | 首答未执行 | 报错后修复转化 | 最终语义通过 /10 | 最终语义+全部静态检查 /10 |
| --- | --- | --- | --- | --- | --- |
| Qwen Q4_K_M | 4 | 1 | 2/5 | 6 | 0 |
| Qwen i1 IQ4_XS | 4 | 1 | 1/5 | 5 | 1 |
| Devstral Q4_K_M | 5 | 0 | 3/5 | 8 | 5 |

每个/10分母为5题×2种呈现，并非10道独立题。两种输入分别的首答成功为 Qwen 2/5 vs2/5、i1 2/5 vs2/5、Devstral 2/5 vs3/5；没有模型达到预登记呈现收益线。首答合计13通过、15实际测试失败、2无法执行。修复后正式语义合计19通过、2仍失败、9未执行，不能把9个未执行记为9个已证实的语义错误。

可核查的恢复：Qwen 修复 duration JSON、encoded sections；i1 修复 exact sections；Devstral 修复 duration 两臂、encoded JSON。Devstral exact 两臂修复仍保留漏拒绝 int 子类的实现，因此真实语义缺陷仍存在。没有静态修复步骤，表中的静态失败不能通过忽略 Ruff 自动变成正式成功。

### 事后离线归因：正确修复被输出包装拦下

预登记筛查完成后，另建 `rejected-output-audit-1`，选取**全部9份语义未执行响应**，不挑选看起来正确的答案。无模型调用；仅当存在恰好一个明确标记的 Python/JSON 代码块时取该块，仍要求完整合法路径集合、可编译、scope/hash保护及实际测试。路径、引号、代码均不人工修补，多块或结构歧义继续拒绝。此为事后诊断，不修改正式分数，不推广为生产解析规则。

其中6份可执行，**6/6保护测试通过**：Qwen exact 两臂修复；i1 exact JSON、duration两臂、encoded JSON修复。剩余3份仍拒绝：Qwen duration sections首答、encoded JSON修复，以及i1 encoded sections首答。完整源码、执行证据和原响应 hash 均留存。

因此，应修正“这些模型不会修这些错误”的过强解释：真实失败反馈后，部分模型已生成能过保护测试的代码，但其解释文字/交付结构超出当前协议。直接调用首答差，不能代表带执行反馈的有界代理必然失败。另一方面 Devstral 的 exact 语义错误与三份结构歧义仍在，不能把一切归因于格式。

### 阶段决策与下一步

因可核查阶段结论停止，weekly used 53%→54%，不是额度耗尽。没有生产模型切换或 Coordinator 放行。下一步优先实现**仅限诊断完整文件响应的默认关闭适配候选**，再用冻结对照验证：无歧义单代码块归一化、保留拒绝原因、交给可信 formatter、独立验收并保留一次真实错误修复。不得把“从文本找动作”重新引入 agent工具/推理通道；不能执行 prose 中指令，不能修路径或扩scope，歧义多块继续失败。格式恢复、语义修复和全检查通过率分开统计。

候选还需在新的迁移题上重复，与原路径对照；本批开发题只能用于诊断，不能充当角色资格。成功后再决定将候选纳入 Coder harness，而不是直接修改生产 JSON/工具协议或增加 Coordinator。

相关确定性回归 **39 passed**（`presentation-regression-1.xml`）；新脚本与测试 Ruff/format、git diff-check通过。未重跑完整 runtime suite，全部生产 `.local-agents` 文件与本轮冻结一致；未 commit/push、未修改兄弟仓库或保存模型偏好。

## 默认关闭完整文件候选与迁移验证（complete-file-transfer-1）

### 实现与冻结设计

新增 `benchmarks/complete_file_candidate.py`，仅诊断完整文件返回使用，默认 `enabled=False`；未接入生产 Coder、工具动作解析或 reasoning 通道。显式开启时，原解码失败才允许提取恰好一个语言正确的 tagged code block；多块、错误语言、缺文件、重复路径或越界路径拒绝，不修路径/源码/引号。完整解码及编译全部文件后才编辑。仅可写 Python 源码送入固定可信 Ruff formatter，AST 必须一致；之后仍走原 scope/hash guard、完整保护测试和静态检查，保护测试不格式化。格式化行为不是模型动作。

新建 `complete-file-transfer-baseline-1` 冻结 runtime/config/状态，三个新近迁移题：window-bounds（双参数 exact int、空输入也校验）、port-roundtrip（ASCII/范围/前导零、双文件往返）、async-stop（None sentinel、保留其他假值、异常传播）。每题参考实现通过、初始错误实现和针对关键边界的近正确错误变体均失败。题型来自已知语义家族，不能冒充完全陌生资格题。

每模型三题两轮。原路径与候选共用同一份首答，输入及工作区内容相同；各自在实际 pytest 失败后至多一次修复，第二轮交换两臂执行顺序。默认不修解码失败/单纯静态失败，不给参考答案。冻结上限18首答+36修复=54调用，实际 **18首答+20修复=38调用**，36个路径结果全部完成。各模型逐批单驻留、每批卸载，结束无驻留；加载可见 config 和保存偏好 hash 持续核对。weekly used 54%→55%。

### 两轮结果

| 模型 | 原路径最终语义 /6 | 候选最终语义 /6 | 原路径全部检查 /6 | 候选全部检查 /6 | 原路径/候选修复转化 |
| --- | --- | --- | --- | --- | --- |
| Qwen Q4_K_M | 2 | 2 | 2 | 2 | 0/4、0/4 |
| Qwen i1 IQ4_XS | 2 | 2 | 2 | 2 | 0/4、0/4 |
| Devstral Q4_K_M | 4 | 4 | 2 | 4 | 0/2、0/2 |

每个/6为3题×2轮，并非6道独立题。三模型 async-stop 两轮均通过；window-bounds 全部失败；port-roundtrip 两个 Qwen 两轮均失败、Devstral 两轮语义均通过。候选将 Devstral port 的两个格式失败变为全部检查通过，无原路径成功回退或保护失效，满足预登记“至少两个额外全检查通过且无成功损失”的**局部候选收益**标准。该收益全部来自格式化，不是新增语义能力。

本批所有返回已能由原解码器解析，`normalized` **0次**；不能声称代码块归一化通过迁移验证。两臂的实际报错反馈均未产生语义修复转换，说明上一批开发题上观察到的恢复能力未自动迁移到这两类更复杂契约。不能将“formatter已消除Ruff失败”混算成“Coder已稳定”。

具体失败证据：Qwen 的 window 实现写了排除 subclass 的错误消息，但实际仍是 `isinstance(..., int)` 加排除 bool；Devstral 也未满足该边界。Qwen port 使用 `isdigit()`/逐字符 `isdigit()`，且有修复错误拒绝契约明确允许的前导零。所有这些代码均实际执行过保护测试，不是解析导致的未测语义。

### 阶段决策

保留候选默认关闭，**不接入生产完整文件通道、不放行 Coordinator**。formatter 的局部收益已复现；下一步不应继续把格式适配当成核心语义修复方案。若继续诊断，优先做一次有界的错误证据对照：原始 traceback 与包含实际运行值类型、期望/实际结果的结构化反例，禁止提供参考实现。当前 window traceback 将 `Child(1)` 显示为 `bad = 1`，可能导致模型误读；这是待验证假设，不是已证实根因。对 port 同时保留被错误拒绝的合法输入和被错误接受的非法输入，避免修一个边界破坏另一个。无新证据时不重放本批同题、也不提高 repair 次数。

相关回归 **49 passed**（`adapter-regression-1.xml`），含默认关闭、歧义拒绝、路径/文件保护与 AST 检查。新文件 Ruff/format、git diff-check通过；完整 runtime suite 本轮未重跑。生产 `.local-agents` 与冻结一致；历史结果和已有未提交改动保留，无 commit/push、依赖安装或兄弟仓库修改。

## 有界反馈对照结束，转入受监督范围验证

本轮按三阶段推进：最后一次结构化反例对照、确定委派范围、真实 E/C/R 流程。开工实际 weekly used56%，停止线60%。保持生产模型 Explorer=OSS、Coder=Qwen、Reviewer=Muse及单模型驻留；直接模型比较的配置仅存在于实验快照。

### 结构化反例结果与退出决策

`typed-feedback-2` 复用上一批**全部10组首答失败**，traceback与typed各一次修复，共20调用。两臂初始源码、保护测试、输出适配/格式化一致，typed只追加可信进程实际执行的输入repr、真实类型、期望与实际结果。覆盖两个参数和合法/非法端口输入，不提供参考实现。第二轮交换两臂顺序。

traceback修复0/10，typed修复2/10：Qwen port第一轮、Devstral window第一轮各一次；第二轮未复现，IQ4_XS没有转换。未满足“至少两次额外收益且同模型/家族重复”的预登记条件。关闭继续加强提示的分支，不把孤立成功升级为生产修复。

此前 `typed-feedback-1` 已发生两次调用，随后可信probe输出阿拉伯数字遇到GBK UnicodeEncodeError。旧响应、失败和诊断保留；`typed_feedback_utf8.py` 对probe进程显式加 `-X utf8`，另建批次和快照，不覆盖旧结果。该准备故障不是worker语义失败。新反例观察测试及既有相关回归 **52 passed**（`typed-regression-1.xml`）。

### 真实工具循环：两类候选任务各两轮

冻结 `supervised-scope-baseline-1` 与 `supervised-scope-1`。四个真实schema-v2 packet保留medium风险、单元契约、锚点、只读保护测试及可信pytest/Ruff profile。任务为async-stop、success-totals，各两轮。未启用完整文件适配器或结构化反馈候选；调用实际local-unit，Coder成功自动交给独立Reviewer。

async fixture增加只读入口和legacy干扰模块，Explorer独立定位入口→helper→假值断言。两次均读到了真实文件/行证据，Primary核对引用及语义定位 **2/2成功**，不由后续Coder覆盖。已有导航信息不再次发起探索。

四次Coder均ready_for_review、Reviewer均pass_to_primary；Primary实际读了源码与canonical cumulative.diff，独立执行保护测试和静态检查，**4/4接受**。每次用record-review写不可覆盖的接受记录。Primary没有修改模型实现、没有发起返工。async两轮另运行公开入口的跨文件集成：false值保留、None停止、异常同对象传播和后续不访问，均通过。

Reviewer另做一个哨兵家族的clean/hidden各两轮。Primary合成canonical archive，提供能够通过但未覆盖假值的测试；隐藏实现用`if not value`，clean用`if value is None`。Reviewer **clean放行2/2，hidden有效检出2/2**，具体引用源码第5行并建议修复。Primary独立执行隐藏边界，clean返回`[0, False, '']`且访问0..3，hidden返回`[]`且只访问0。所有控制也记录了不可覆盖的Primary accept/rework裁决，控制没有Coder性能信用。

真实四unit+两Explorer本地调用总耗时约 **255.44秒**，包含该调用路径的模型切换；另四Reviewer控制不在此数内。Primary准备/审查/诊断活动时间和cloud tokens没有测量，因此**未证明整体减少Primary成本**。不能从四个小合成单元推断真实项目ROI。

### 本阶段收束

产品范围写入 `docs/worker-capability-scope.md`：两类任务有重复工具循环证据，可作为受监督候选；任务仍须足够大以抵消协调成本。精确类型、多参数边界、ASCII/规范化/跨文件校验没有普遍可靠性，关键不变量仍由Primary负责。模型选择不改，输出/反馈候选保留默认关闭。

Coordinator继续HOLD：本轮是两个已知任务家族与一个Reviewer缺陷家族的小范围验证，没有替代六题两轮、更多独立缺陷族及定位→依赖链集成的完整准入，也没有建立成本收益。后续应在此范围内选择一个新的、足够有价值的项目单元，先记录Primary活动与本地耗时再验收；不继续用同题堆提示或把正常路径通过当作通用稳定。

新脚本/测试Ruff与format通过，git diff-check通过；生产 `.local-agents` hash与冻结一致。完整runtime suite未重跑。全部历史和用户未提交改动保留，未commit/push、未修改兄弟仓库或模型保存偏好；结束恢复无驻留模型。实际weekly used结束仍显示56%，为界面粒度，不表示零消耗。阶段任务完成后停止，未触及60%上限。

### 外部依据链接

- [Qwen3-Coder 工具格式支持](https://github.com/ggml-org/llama.cpp/issues/15012)
- [LM Studio 流式/非流式工具差异报告](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1071)
- [Qwen Flash Attention 用户报告](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1353)
- [Aider 推理与编辑分离](https://aider.chat/2024/09/26/architect.html)
- [SWE-agent 交互设计](https://github.com/SWE-agent/SWE-agent/blob/main/docs/background/aci.md)
- [mini-swe-agent 简化控制流](https://github.com/SWE-agent/mini-swe-agent)
