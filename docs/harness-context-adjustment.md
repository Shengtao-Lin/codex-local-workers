# 有界 agent 的上下文恢复对照

2026-10-06。用户授权按设计审查调整现有 harness。当前周使用率开工实测 26%，停止线 40%。保留当前模型、单模型驻留、全部历史、保护测试及未提交改动；Coordinator 继续等待三角色资格。

## 经代码核查后的问题定义

三个角色已有工具循环，属于受限 agent。此前“读过内容被删除后无法恢复”的分析过于宽泛：Coder 已有一次 trim 后重读及最多 80 行重复读源码回放；Reviewer 也有最多 6000 字符回放。不能把历史语义失败直接归因于完全没有恢复机制。

本次可复现的问题更窄：Reviewer 在 required reads 完成后的一次重复读取，可触发下一轮仅允许 REPORT；实际读取发生在很早以前时，原内容可能已经离开最近五轮消息。源码回放和强制提交绑在一起，妨碍模型恢复材料后继续调查依赖。仅“读过所有要求的文件”不证明审查结束。

## 第一个隔离候选

`reviewer_context_recovery: true` 为显式 opt-in，默认 false。每次实际模型请求前索引其中保留的结构化源码观察。已读范围离开该索引后，再读最多 40 行可得到 `context_restored`，不强制 REPORT；同范围最多恢复两次、整个调用最多八次。已经保留的重复读取仍走原无进展策略。普通 turn/deadline、权限、引用、输入一致性及报告门槛均保留。

恢复不增加新证据或填写任何验证结论，也不改变历史已读行账本。可见性索引不解析自由文本回放为引用权威；因此已有自由文本回放时可能发生冗余恢复，开销由上述次数限制。仅在 structured observations 中的实际源码才用于此可见性判断。

资格管理风险 feature/unit/integration 均 high。契约为 `citation-authority-unchanged`、`bounded-source-restoration`、`qualification-before-coordinator`。Primary 实现和审查；不计本地 Coder 成功。

基线冻结：`benchmarks/work/capability-fit/roleq-context-baseline-1`。候选冻结：`roleq-context-candidate-1`。候选不改默认配置、系统提示、模型或采样。

## 验证与决策规则

确定性检查覆盖：保留的源码仍被识别为重复、被裁剪的源码恢复、恢复后仍可继续使用调查工具、次数限制、scope 拒绝、配置类型、模型/packet 文本不能伪造已读账本。完整循环使用真实 ReviewerRuntime 和模拟动作客户端；这是控制流验证，不是模型能力成绩。

实时对照登记于 `roleq-context-comparison-1/plan.json`：同一候选 runtime，已知 window-groups hidden/clean 各开/关一次，共四次 fresh context；顺序为 hidden off/on、clean on/off。记录实际恢复事件、真实报告及人工因果审查。不得将未触发恢复的成功称作恢复机制改善，不将既有题当未见资格题。任意改进需要更长调查链的配对复现才能推广。

本轮不同时改 Coder 策略。下一轴应先记录其实际请求中的源码/错误保留情况，再比较已有 budgeted retention 和默认 recent；恢复源码和撤销强制修复策略须分别测试。Explorer 已有聚焦定位的正面证据，暂保持其工具协议。

## 结果

首轮新增测试因测试未 prepare 审查日志目录而失败，修正测试生命周期后 53 项 Reviewer 测试通过；旧失败结果保留。完整回归 580 passed、49 subtests passed、零排除（`context-full-1.xml`），Ruff 和 diff-check 通过。

四次实时对照完成，均正常返回 pass_to_primary。Primary 对照实际源码和已冻结子类反例裁决：hidden off/on 均为漏审，clean on/off 均无误报。四次恢复事件均为零。hidden-on 实际动作只有三次 READ_FILE、一次 SEARCH、一次 REPORT，失败发生在最近五轮裁剪之前。开关分组只是本轮兼容性观察，不能计作恢复机制改善或证明该机制无效；也不能把耗时差当效率收益。

本轮接受默认关闭的隔离候选与确定性控制流修复，未推广至生产配置。Primary 审查新代码和测试，runtime SHA 与冻结候选一致：`a1eb09418036c14dd18a37c085f2dc5d3830c45e44194deb7674cf9d45fc6e57`。没有本地 Coder 单元，合成旧 archive 只用于独立 Reviewer 对照。

下一步重点是能实际触发裁剪的长调查链配对，同时单独测量 Coder 的当前可见源码；当前 exact-type 漏审已有“短上下文下仍失败”的证据，不能继续沿上下文方向反复修同一题。没有完整能力资格或 Coordinator 放行。结束时周使用率实测 26%。

## 长链跟进：恢复候选出现反例

继续开工时 weekly used 27%。新增九个相关源码/测试文件的 Decimal 报价链，跨目录逻辑包括目录价格、数量、折扣、运费、税额、最终舍入。公开验收对 clean/hidden 均通过，独立边界验证 clean 通过、hidden 失败：0.048375 元最终应为 5 分，逐项先舍入再相加错误地返回 4 分。三个新增 fixture/observer 测试通过。源码、保护测试、runtime、packet/config 和驱动 hash 在首调用前冻结于 `roleq-context-chain-1`。

自然调查无需预置历史就触发了裁剪。旧 Reviewer hidden 第 10 次请求丢失入口、舍入及测试的结构化观察，回读后触发 report-only；仍正确指出舍入问题。恢复候选 hidden 也检出问题，但没有实际触发恢复。clean 恢复候选触发八次恢复，始终重复辅助文件，未读测试并耗尽 16 轮；关闭恢复时 clean 完成审查。其末次实际报告输入仅 4627 tokens，加上输出预算约占 24576 上下文的 35%。这说明单纯允许重读会放大固定五轮裁剪形成的循环。**原恢复候选停止推广**，不执行已不必要的 scripted-prefix 诊断。

另一个需要保留的混杂因素：部分报告把契约里的 “aggregate quantities” 解读为必须先按 SKU 合并内部数据结构。原参考用逐行数量乘价格再求和，输出对重复 SKU 等价，但措辞可以引起实现形态歧义。人工裁决必须单列此争议，不以参考实现本身作为所有语义正确性的证明，也不把这种建议当作有独立反例的缺陷。后续新题应描述重复 SKU 的外部金额关系，避免规定内部形态；本批原 packet 不改。

## 第二个候选：预算保留

Reviewer 新增显式 `reviewer_context_retention: budgeted`，默认仍 recent；恢复开关 false。与 Coder 已有实现对齐：预留输出和安全余量后，以剩余预算 80% 的保守字符估计保留历史，最多 64 条消息；保留初始契约和最近五轮，客户端原有超上下文 preflight 继续生效。预算足够时不因超过五轮就删除仍有用的源码。此修改不取消重复读取与 report-only 策略，是独立对照轴。

新增保留九文件证据、预算裁剪及配置不足拒绝测试。完整回归 **585 passed、49 subtests passed、零排除**（`context-budget-full-1.xml`）；候选冻结 `roleq-context-budget-candidate-1`。

Coder 第一对实际结果：recent 16 次请求后 no_new_evidence_before_edit、零修改；budgeted 16 次请求完成修改及五项保护测试，可信 handoff、独立 Reviewer 和 Primary 均通过。budgeted 的最后请求保留全部源码、测试及最新 validation reference；recent 的入口源码已离开结构化观察。只证明此开发题的初步差异，尚不支持整体资格。已登记 fresh workspace 第二对，倒序执行以减少固定顺序影响。

Reviewer 预算模式与 recent 的 hidden/clean 两轮交错对照共八次已登记于 `roleq-context-budget-comparison-1`；执行中。周使用率最新 28%，Coordinator 未启动。

## 本轮阶段决策

八次 Reviewer 对照已完成。budgeted 四次完成：hidden 两次都有正确的舍入因果和契约一致修法，clean 两次无 findings。recent 三次完成：hidden 两次正确检出舍入问题，同时附带上述数量汇总争议；clean 一次 pass，另一次因 `LM Studio must return exactly one native tool call` 失败。该协议失败发生在裁剪前，不能归因于上下文丢失，也不是轮数耗尽。

Coder 倒序 fresh replication 再次得到 recent 失败、budgeted 成功；两次 budgeted 都通过五项保护测试、Ruff、可信 handoff、独立 Reviewer 和 Primary immutable accept，实际修复一致。recent 两次无编辑，均 no_new_evidence_before_edit。没有给模型参考实现或改变保护测试。此处的 2/2 属于同一报价开发题的复现，不是两个新题。

来源可见性记录是结构化观察索引；packet 内累计 diff 和自由文本 replay 没有解析，因此某路径从索引消失不证明所有内容副本消失。budgeted hidden-r1 最后一次 report-only 恢复也发生一次这种索引缺失，不应写成全程零丢失。

又以 budgeted 做窗口分组、timeout 两题迁移，首轮两次都失败；按预登记停止，各自第二轮未执行。窗口保留 `isinstance`，timeout 混淆缺省与显式 None。随后单次 OSS Explorer investigate 成功解释了子类被放行的因果，Primary 核对了源文件 hash 与测试 23–25 行；只转述其因果事实，未提供参考实现。Coder 一次继承修复仍只增加 bool guards、未通过验收，按计划关闭此路线。Explorer 首次启动因 Primary 的独立配置缺少 managed coder/reviewer IDs 而在模型前 blocked；修正配置后的一次实际模型调用有两次协议纠正，全部保留。没有 Reviewer 启动或成功信用。

**接受预算保留为下一轮本地开发基线**：`.local-agents/config.json` 的 coder/reviewer retention 均设 budgeted，recovery false；模型和单驻留不变。运行时缺省仍 recent，未更改公共 example 配置或安装到真实项目。旧配置已在冻结快照中保留。本轮停止扩展已失败的测试路线，不改语义契约来取得成功，也不提前启动 Coordinator。

证据总结：`roleq-context-budget-comparison-1/primary-assessment-1.json`。完整回归 585 passed、49 subtests passed；源码与测试静态检查通过。第二对复制驱动仅在全部运行后排序 imports，原始驱动留存在 `roleq-context-coder-repeat-1/replication-driver-before-format.py`，与准备 manifest 的 hash 一致。当前 weekly used 31%，从本轮开工 27% 增加 4 个百分点，未触发 40% 停止线。云端 tokens 和 Primary 主动时间仍 unknown。

这形成了可核查的阶段结论：工作记忆策略确有可修复影响；改善该策略后仍有独立的语义失败。下一轮应以新基线评估其余能力及依赖单元链，不能将一个报价题的成功扩展为整体稳定。

## 依赖链跟进：编辑恢复与语义边界仍阻断首单元

使用 `roleq-budget-next-baseline-1`，登记已有 bounded-report 两单元题的两轮独立快照：参数解析接受后才允许报表消费，保护测试补充非 ASCII 数字拒绝、带前导零的字符串往返和相同 id 的稳定顺序。这是已知开发题的扩展，不计未见题。模型、驻留、采样与预算策略均不变，Explorer 因位置已知不调用，Coordinator 不启动。

Primary 首次驱动准备漏了计划指纹。该次 Coder 完成 20 项测试、Ruff 和独立 Reviewer，Primary 核对实际 diff 后接受单独参数单元；但档案不能通过依赖计划门槛，因此不计链路成功。保留 `roleq-dependent-retention-1` 与精确驱动副本。另有首个参考预检因系统临时目录权限失败，换仓库内独立临时目录后通过。上述均不计模型质量失败。

新批次 `roleq-dependent-retention-2` 在调用前生成绑定计划的 packet，核验所有 packet、参考实现和缺失父单元接受时的机械拒绝，预检 2 passed。首个 Coder 却在 12 轮内耗尽协议错误预算：修改后直接按未观察版本改单行、给单行工具多行文本、VALIDATE 缺少 contract_check，以及再次未观察即改单行。实际验证仅一次，因新增尾随空白在 diff-quality 阶段被拒，未执行测试。最后请求实际输入 7703 tokens，不能把这个失败归为上下文不足。

Primary 对原样失败源码独立运行保护测试：18 passed、2 failed；全角和阿拉伯文数字被 `isdigit()` 放行，违背 ASCII-only 契约。因此不能声称修好空白或工具调用就一定成功。保护测试、其他源码和配置/packet hash 无漂移。Reviewer 未启动；第一单元 immutable replan，其余三个单元 pending，按预登记停止本批，不重复抽样到成功。两个隔离批次使用了相同 task/run 字符串，证据定位必须保留完整 workspace；后续驱动需用不同 batch 标识。

阶段结论仍是 HOLD：预算保留的报价长链改善成立，但没有获得依赖链资格。下一步先离线重放这组 edit→read→validate 错误转移，挑一个窄 harness 改动独立验证；不得取消当前版本观察、hash 或语义验收来取得成功，不扩大相同失败路线。证据 `roleq-dependent-retention-2/primary-assessment-1.json`。本轮没有生产 runtime 变更，新增驱动 Ruff/格式与 diff-check 通过；完整回归仍引用此前 585 passed、49 subtests，不把本次两项实验预检混入全套数字。weekly used 31%→32%，未到 40% 停止线；没有 commit/push。

## 后续修复：可信格式化前移与协议描述一致性

用户授权继续至 Coordinator 准入或 weekly used 40%。开工 32%，冻结 `roleq-edit-recovery-baseline-1`。D4 为显式默认关闭的 `autoformat_on_diff_whitespace`：仅授权已改 Python 文件、纯新增尾随空白、既有可信 Ruff format --check profile 且未用过自动格式化时，允许在完整验证前格式化一次。旧拒绝 attempt 不变，字节变化后重跑全部质量门槛和测试；保护文件变化立即 PolicyViolation。字符串内有效空白由真实 formatter 保持，不做盲目 strip，也不撤销 gate。

三项新增测试及四个子场景覆盖默认/配置/scope/单次边界、失败测试不能被擦除、保护输入变更拒绝和真实多行字符串。原失败源码的开关回放表明：off 在 diff-quality 前停止，on 保留失败记录后执行 20 个测试并暴露原有两个 Unicode 数字语义失败；两者都不能成功。回放不是模型成功。完整回归首次因新增源码未格式化而在安装测试失败，修正后 **588 passed、53 subtests passed、零排除**。独立 high-risk Reviewer pass，Primary 核对完整 delta、测试和同 SHA 后接受默认关闭候选（`v13-scoped-d4-1`）；合成 archive 没有 Coder 信用。

`roleq-whitespace-live-1` 登记同候选 binary 的开关链路对照。on 两轮四单元均经 Coder→Reviewer→Primary 接受，各轮 28 项集成测试与 Ruff/输入 hash 通过；off 首单元原有 Unicode 语义失败并重复 no-op，按规则停臂，剩三个单元 pending。**四个 on 调用均未触发新机制**；两次格式化来自原有测试后路径。因此只能接受该开发链路的两轮实际结果，不能把差异归因于前移格式化。未调用 Explorer，不满足“定位到依赖集成”的完整链路门槛，六题语义资格仍缺失，Coordinator 关闭。完整裁决 `roleq-whitespace-live-1/primary-chain-decision-1.json`。

独立代码核查另发现 Coder 系统提示要求 flat JSON，但服务端 schema 要求 action+arguments。已统一两个动作示例及说明为嵌套 arguments，保留 legacy flat 解析兼容；不加入语义示例或实现答案。新增协议一致性测试通过，完整回归 **589 passed、53 subtests passed、零排除**，冻结 `roleq-protocol-prompt-candidate-1`。现按 `roleq-protocol-transfer-1` 对三个已暴露边界题做有界迁移；每族首轮失败即关闭该族，不恢复原始自主成绩。此批 whitespace 开关仍关闭，避免混淆候选。当前 weekly used 最近实测 34%，继续按 40% 停止线执行。

## 读取边界修复与恢复实验裁决

迁移三题首轮全部失败，三个第二轮未执行；没有 Reviewer 调用。文件名题漏掉无点名称，窗口仍放行 int 子类，timeout 仍混淆缺省与 None 并放行子类。三份 a1 均 immutable replan，`roleq-protocol-transfer-1/primary-assessment-1.json` 保留分母。修正动作信封不能被写成语义能力改善。

审计发现另一个确定性缺陷 D5：repair_focus 的符号扫描可能读取 forbidden 文件，SEARCH 的原始递归枚举没有逐层执行 SafeEditor 的 reparse/scope 检查。新增统一只读枚举器，在下降目录和读取文件前分别核验 read roots、forbidden、排除目录与 reparse；source/test 预取同样走读取权限检查。根目录 `.` 的合法搜索仍可用。没有放宽编辑已读行账本，也不宣称这是 OS 隔离或消除了 TOCTOU。

四项回归覆盖秘密文件不泄漏、预取拒绝、文件/目录 reparse 拒绝及正常根搜索。完整 **593 passed、53 subtests passed、零排除**（`prefetch-guard-full-1.xml`）。独立 high-risk Reviewer 经一次引用纠正后 pass，Primary 对完整 delta、测试和相同 SHA 审查后记录 accept（`v13-scoped-d5-1`）；合成 archive 不计 Coder 能力。候选 `roleq-prefetch-guard-candidate-1` 的 worker SHA 为 `0e7b51dc388945382992601ada5306b80950ccd9f989f84530603ec1f1c79f93`。

随后每个失败单元只给一次 fresh inherited context，不注入语义修法、不扩大 scope：文件名题 2 项测试和 Ruff、独立 Reviewer、Primary 均通过；窗口和 timeout 失败，没有 Reviewer。结果为 **继承式恢复 1/3**，不是初始成功 1/3。原 a1 保留，a2 均有独立 Primary 决策。错误的 parent 元数据字段造成的准备期失败另存 `roleq-inherited-context-1`，修正后用新目录 `roleq-inherited-context-2`。窗口最终代码还会拒绝普通正整数，不能用局部边界改善当进展接受。

## 角色互补反例：真实引用不等于正确诊断

`roleq-explorer-advice-1` 预登记一次不同问题形态：OSS Explorer 不只解释因果，而是根据当前窗口草稿及保护测试给出具体 guard 建议；Primary 仅核查，不能代写答案，然后才考虑一次 inherited Coder。保持原模型、单驻留，investigate 模式独立配置。该实验是已知题的本地指导恢复，不是新定位资格。

Explorer 14.97 秒、5 个动作、一次协议纠正后报告 success，实际读到了源码和测试；却声称当前代码接受普通正整数，没有提供替代 guard。Primary 对原样代码独立 pytest：**8 passed、1 failed**，`groups([1,2,3,4,5], 2)` 在第 7 行抛 ValueError。因为 `2 is not 2.__class__` 成立，报告的语义断言被反例直接否定。报告、observed hashes、原样源码和 JUnit 均保留。Primary 拒绝建议，没有启动 Coder 或 Reviewer，不将 operational success 计成有效诊断。

此结果不证明所有任务都无法协作，但排除了“当前两个角色只要串起来就能互相纠错”的假设。Explorer 的定位证据、诊断正确性、Coder 验收和 Reviewer 有效审查必须分别统计。继续重复这个已失败语义族或追加泛化提醒没有新证据价值。当前 weekly used 最近实测 38%，Coordinator 仍 HOLD。

## 40% 停止点：正式动作通道候选待独立验收

后续客户端审计发现 D6：Explorer 曾从 `message.reasoning` 搜索第一段 action JSON，或回传其中的 channel marker，作为正式动作执行。反例确认候选/废弃草稿可在正式回复前被执行；这是确定性协议问题，但现存 hash-only 日志不能证明前述语义失败来自该通道，不能改历史分数。

已删除该回退及错误日志中的原始 reasoning 摘录。只有正式 content 或既有单一 native tool call 可进入动作解析；reasoning-only 使用原有一次无动作纠正，之后失败关闭。新缓存键 `FINAL_ACTION_V2 + mode + task` 隔离旧协议报告，旧缓存/历史不删除，新缓存仍能复用。冻结 `roleq-final-channel-baseline-1` 与 `roleq-final-channel-candidate-1`。Explorer SHA `530c7ea74bfdf83246fab0d2ce260fbb6e2793686a0c1875c07cab35d42fea84`。

四项新增测试覆盖草稿 JSON、channel marker、连续无正式输出、保留正式 native action、旧缓存拒绝和当前缓存复用。初版测试漏了 timeout 构造参数，纠正后获得真正反例；首次全回归又因混合换行格式失败，格式化后保留旧结果并重跑。最终完整 **604 passed、58 subtests passed、零排除**（`final-channel-full-3.xml`），Ruff/格式/diff-check 通过。新增 benchmark 调度测试确认被 Primary 拒绝的 Explorer success 不能触发 Coder、输入漂移阻断、调用与任务关联且不能重复执行。

独立 Reviewer 首次 16 轮后提交超长引用被拒；先收窄为六个相关保护测试并给真实源码范围，再审仍于 16 轮耗尽，此时仍在读取新证据，最后请求 10611 输入 tokens，不是 context-length 拒绝。准备期另有一次 Primary benchmark 代码块放置错误，没有模型调用，保留失败驱动后修正为新 trial。两次实际审查失败保留，不能写成审查通过。Primary 已读完整 D6 delta，但**候选尚未独立验收**。

随后同一 OSS、单驻留做 locate/investigate 两次全新只读兼容检查：均 success，分别 7/4 个动作、零协议错误、零缓存命中，源码/配置 hash 未变，引用经 Primary 核对。两次均未触发无动作纠正，因此只证明正常协议兼容，不证明语义提升或 Coordinator 准入。

已准备一次诊断性 Reviewer 16→32 轮配置：仅在收窄后仍有真实读取进展的这个审查使用，不改生产默认、契约或引用门槛。**调用前查到 weekly used 40%，未启动。** 请求及配置在 `v13-scoped-d6-3/.agent/review-request-budget32.json` 和 `config-budget32.json`，说明在 `budget32-plan.json`。停止时没有运行中的模型/测试会话。下次获授权后先复核预算、候选 hash 和这项待验收审查，不重放已失败的语义实验；之后仍需补完整三角色资格，不能因 D6 通过就直接放行 Coordinator。

最终证据 `roleq-final-channel-candidate-1/stop-assessment-1.json`。Coordinator 仍 HOLD；全部历史、现有改动及模型保留，未 commit/push、未修改兄弟仓库。

## 60% 授权复工：D6 验收与原生工具隔离对照

用户将 weekly used 上限提高至 60%；复工实测 40%。已验证冻结候选全部文件和工作区 runtime/config/tests hash 一致，无 managed writer 锁；LM Studio 可用，单驻留。默认命令环境一度 helper setup 失败，改用既有受批准的显式 PowerShell，未修改机器配置。

执行此前准备的 `independent-component-budget32-1`：Reviewer pass_to_primary，实际六项保护测试与 Ruff 两项通过，引用/输入 hash 合法，Primary 完整 delta 复核后 immutable accept。**实际第 16 轮已提交成功报告，没有消耗额外额度**；此前两个失败保留，不能据此声称加大预算是原因。D6 正式完成组件验收，不增加 Coder 成功或 Coordinator 资格；生产 Reviewer 上限未改。证据 `roleq-final-channel-candidate-1/acceptance-followup-1.json`。

下一隔离轴是 Coder 原生命名工具及类型化参数：现有通用 JSON 信封的 arguments 没有逐动作字段定义，可能增加编辑/验证形状负担；这是假设，不是语义错误的既定原因。`native_coder_adapter.py` 在 benchmark 内通过现有客户端发送 native tools，仅调整协议开头，保留 packet、系统行为约束、当前 action allowlist、scope/hash、实际验证和 handoff。VALIDATE 的声明仍由模型填写，不补答案；失败工具不能绕过 runtime。生产配置不切换。

`roleq-native-coder-1` 在首次调用前固定窗口/timeout 两个已知题的四个 fresh 单元，交错顺序 envelope→native / native→envelope；每格一次，无重复抽样。六项 adapter 测试先通过，旧语义分母不变，Explorer N/A（定位已知）。仅真正过 Coder gate 的单元才交独立 Reviewer。实际模型元数据另存：Coder Q4_K_M、OSS MXFP4、Muse Q4_K_M，均保持现有 key 和 context；文件 hash 未取得，不把服务端元数据当作二进制校验。

四格已完成，均未接受，也没有启动 Reviewer。JSON 对照窗口 9 项测试失败 1 项，timeout 8 项失败 2 项；实际 diff 分别仍放行 int 子类，以及混淆缺省与显式 None。timeout 已改为真除法，不能照抄模型总结称小数仍未修复。原生两格均首次 READ_FILE 成功，第二次请求耗尽 4096 输出 tokens，未执行部分动作、没有编辑；实际输入分别 4461/4535 tokens，不能称为上下文装满，更不能计成两次语义测试失败。四格都有 immutable Primary replan，详见 `roleq-native-coder-1/primary-assessment-1.json`。

新增协议疑点：隔离适配器发送 native tools，但底层循环仍把返回动作写成 assistant JSON、结果写成 user OBSERVATION，没有保持原生 tool_calls/tool_result 往返。LM Studio 的[工具调用说明](https://lmstudio.ai/docs/developer/openai-compat/tools)要求后续历史包含工具调用及相应结果。两次都在首次接续失败与此假设一致，但尚未构成因果证明，不据此宣布模型不支持 native tools，也不直接改生产三角色。

本批按预登记关闭该适配器路线，不提高输出预算重试。下一步是独立冻结正确工具历史候选，先离线验证调用/结果绑定、动态 action gate、截断孤立消息和工具 metadata 的 token 预算，再做小型 live 往返兼容测试；兼容通过后才考虑语义对照。当前 weekly used 42%（上限 60%），形成上述阶段结论；Coordinator 仍 HOLD。生产完整回归仍引用 D6 的 604 passed、58 subtests，不把六项 adapter 测试冒充全套重跑。历史、现有改动和模型保留，未 commit/push。

## 继续至 60%：协议修复与能力阻塞分开验收

本次开工实测 weekly used 42%，上限仍 60%。保持三模型、单驻留和全部历史，没有改只读兄弟仓库、commit/push 或安装依赖。

`roleq-native-history-1` 增加成对 assistant tool_calls / tool result 历史，仅转换本客户端实际发出且与 runtime 观察相邻的动作，不把压缩孤立消息或未发出动作伪造成调用；截断观察按原样保留。窗口题完成 14 次 native 交互和真实验证，不再第二次截断，但仍未修复 bool/int 子类边界。timeout 首次返回多个工具调用被拒，未执行。这两次均 replan；仅支持交互兼容改善，不能声称语义改善。

据此验收 D7：native 请求显式携带 `parallel_tool_calls: false`，preflight 估算同时计入工具定义；服务端若仍返回多个调用，原拒绝保持。文本/JSON 模式不加该标志或 native schema 成本，估算仍非精确 tokenizer 计数。完整回归 **618 passed、58 subtests passed、零排除**；四项聚焦测试、Ruff、独立高风险 Reviewer 和 Primary 全 delta 审查通过，记录 `v13-scoped-d7-1` immutable accept。worker SHA `0543c2700a495f95697bf1b0dd89770de8764ef38b40291bbb27fd275176415a`。生产只保留这项请求修复，不切换 Coder 为 native。新 timeout 单次探针 `roleq-native-single-call-1` 能编辑/验证，仍 8 项中失败 2 项，replan。

随后封闭以下有界开发对照，均不重写旧分母或计未见资格：

| 对照 | 可核查结果 | 决策 |
| --- | --- | --- |
| Reviewer 成对历史开/关 × hidden/clean | 两个 hidden 均错误 pass；两个 clean 无误报；开启 hidden 实际 3 次工具结果回传，零协议错误 | 不推广，交互合法不等于审查有效 |
| Qwen 发布方完整采样组合 | 首轮 0/2；按预登记不跑余下两格 | 不改默认采样 |
| 失败测试执行轨迹 | 0/2；保留实参、经过行与返回事件，原失败身份与测试判定不变 | 隔离诊断，不推广 |
| 原子行为 ID + 具体验收场景 | 首轮 0/2；按预登记不跑余下两格 | 不推广；没有拆实现单元、降风险或减测试 |

完整采样组合来自 [Qwen 模型说明](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct#best-practices)：0.7 / 0.8 / 20 / 1.05。每动作输出上限仍 4096，故不声称复现发布方完整长输出推理方案。每批 manifest、canonical archive、实际 diff 和 Primary replan 均保留；Reviewer 历史实验的 unused-variable lint 问题保留原 hash 驱动副本后才修正，单列 Primary 驱动问题。

短只读语言对照 `roleq-semantic-floor-1` 答对继承关系和缺省值，但 `type(x) is int` 在 `[2, True, Child(2)]` 上给出 `[false,true,false]`；该请求仅 74 输入 tokens。一次错误不能证明整体能力或归因到量化，但表明这次错误无需长上下文、工具循环或动作 grammar。实际 Q4_K_M 文件 SHA-256 为 `79ad15a5ee3caddc3f4ff0db33a14454a5a3eb503d7fa1c1e35feafc579de486`，与[发布文件记录](https://huggingface.co/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/blob/main/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf)一致；hub key 确实映射到该文件，没有证据支持下载损坏。未改模型加载设置。

当前 Coordinator 仍 HOLD。继续增加相同家族的提醒、重试、token 上限或将机械报告合法性当有效审查，均不能补齐资格。下一项有区分价值的方向是保持既有验收、对已下载替代模型做小样本角色适配；这需要用户放宽“保持当前模型”的限制，已明确询问，不擅自切换或降低 gate。扩大确定性语义自动修复权限也不是本轮已授权的普通格式化修复。

最终完整回归 **625 passed、58 subtests passed、零排除**（`native-wire-final-2.xml`），新增 benchmark/测试 Ruff 和 diff-check 通过，生产 worker SHA 与 D7 验收快照一致。weekly used 42%→45%，不是达到 60% 的预算停止；下一模型适配分支等待范围授权。结束核对仅 Qwen 驻留、idle、queued=0，没有仍运行的本地调用。所有原子契约/采样第二轮未执行格明确保留为 not run，不补写成功或失败。

## 分层诊断：停止把格式、语义和 harness 混算

用户授权按外部研究结论实施分层对照。开工 weekly used 46%，冻结 `roleq-layer-baseline-1`，没有改生产 runtime、模型、加载参数或角色分工。八类题 × 两轮直接生成全部完成，普通 JSON 格式 11/16 合格；这 11 格原 pytest 通过 9 格、静态检查通过 8 格，余五格语义未执行，不能当作五次代码错误。missing-label、async-fetch、success-totals、edit-anchor 两轮均通过，只支持短小局部任务，不证明真实 SQL/多角色链路已修复。

新隔离目录 `roleq-layer-output-audit-1` 离线重放原输出，不请求模型、不修源码或 JSON 引号；只去掉完整外层 Markdown。精确类型两轮仍放行 bool/int 子类；ASCII 数字两轮仍被 isdigit 放行；stable-latest 第二轮去 fence 后通过，第一轮 JSON 引号损坏。独立审查也发现 Primary 新 fixture 的缺陷：encoded-path 原测试只检查 roundtrip 和斜杠，漏掉 plus 必须编码；两个模型补丁均使用 safe='+'，新增独立规范编码断言后两轮失败。旧成绩、原保护测试和所有响应保持不变，未来加强版另存 `layer_isolation_followup.py`，含近正确 mutant；duration-pair 的已知语义暴露标记亦追加更正。

四类两轮通过，未达到预登记六类开启工具层的分流条件。阶段结论是先用固定短题区分原始 Python 与 JSON 包装，再定位 serving/语义能力，不继续堆提示、不自动换模型或改 Flash Attention。最小工具循环、完整 Coder 大批对照和 Coordinator 均未启动，原角色资格 gate 不变。详见 [分层计划与执行结果](layer-isolation-plan.md) 和 `roleq-layer-direct-1/primary-assessment-1.json`。

最终完整回归 **637 passed、58 subtests passed、零排除**（`layer-full-2.xml`），新增脚本/tests Ruff 与格式检查通过，diff-check 通过。生产 runtime/config/tests 全部与基线 hash 一致。weekly used 46%→48%，本次按诊断阶段决策停止；模型仍仅 Qwen idle，未 commit/push、未修改兄弟仓库。
