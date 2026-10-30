# 受控 Coordinator 试点

执行授权（2026-10-07）：用户已批准开始；weekly used 停止线为 **10%**，
开工实际 2%。`coordinator-receipt-pilot-2` 登记四个 fresh 工作区，顺序为
Coordinator r1 → control r1 → control r2 → Coordinator r2。90 项离线
Coordinator 合约、监督步骤、协议测试通过。准备批次 1 的静态检查问题独立
保留，未调用模型，不计角色失败；全局 Coordinator 配置仍关闭。

## 当前准入

2026-10-07，E/C/R candidate 6 达到登记门槛：14/14 实现单元经确定性验证、独立 Reviewer、Primary 接受；Explorer 4/4；Reviewer 隐藏/clean 对照 8/8；两条依赖链各通过完整集成和 Primary 最终审查。

这是六类已知任务的受监督能力放行，不是陌生复杂项目、任意模型或自主开发的全面放行。旧失败和恢复记录保留。决策见 `benchmarks/work/capability-fit/qualification-matrix-6/assessment-initial-1.json`，输入审计和成本事实位于同目录。

## 已验收配置

保持 Explorer `openai/gpt-oss-20b`（32768）、Coder `qwen/qwen3-coder-30b`（24576）、Reviewer/Coordinator `meta/muse-glimmer`（24576），单模型驻留、串行执行。加载等待不是失败。

冻结的每题 `.agent/config.json` 包含完整配置；放行依赖以下显式实验设置：

```json
{
  "coder_context_retention": "budgeted",
  "reviewer_context_retention": "budgeted",
  "coder_repair_focus_retention": "latest",
  "explorer_output_limit_recovery": true,
  "explorer_duplicate_action_report_recovery": true,
  "coder_post_edit_validation_hint": true,
  "single_model_residency": true,
  "coordinator_enabled": false
}
```

这是合并到试点完整配置的片段，不能替代完整配置。保留验证 profile、静态检查、超时和模型设置。新开关生产默认值仍关闭；下一阶段只在独立工作区启用 Coordinator，不改全局配置或增加 token/轮次预算。

## 下一批边界

先用已放行的 async receipt 两单元链，每臂两个 fresh 工作区，登记相同源码、保护测试、模型及预算。对照臂 Primary 直接调度，试验臂受控 Coordinator 调度；测试调度增量，不声称未见迁移。通过后才登记一个不同的混合任务，不无限重复同题。

Primary 负责意图、拆分、风险、契约、scope 和最终接受。Coordinator 可提出建议、选择已批准的就绪单元、传递规范 packet 和真实失败证据；不能扩大权限、降低风险、修改保护测试、跳过 Reviewer 或替 Primary 接受。

保持真实 Explorer → producer → 确定性验证 → 独立 Reviewer → Primary 接受 → consumer → 同样审查 → 公共入口集成。单凭 Coder 成功文字不能触发下一单元。Coordinator 的 Muse 调用也必须单模型驻留。

调用模型前做离线负向检查：未知 unit、未接受依赖、篡改 packet/scope、失败验证、缺少 Reviewer、陈旧 hash/身份均拒绝。正确建议仅形成待 Primary 批准的请求；synthetic 对照不获 Coder 信用。

## 验收与停止

质量要求两轮角色及集成都接受，原始失败独立保留。有新证据才做针对性修复；同签名不变则关闭候选、不扩大批次。权限逃逸立即 Primary 接管。

效率单独衡量 Primary 主动分钟、准备/纠错/接管次数、可取得的云端 token、每角色调用及加载/执行时间。测不到保持 unknown；weekly 百分比不能换算单次 token。当前矩阵局部调用合计约 17 分钟，不含全部实验耗时和 Primary 工作，不能宣称节省。

质量通过但效率未改善只证明调度可用，继续默认关闭；效率改善还需陌生任务复验。不要弱化复杂题来放行，也不从小任务推导事务、并发、安全或公开兼容性能力。

## 首批结果：质量通过，收益未证实

`coordinator-receipt-pilot-2` 四条链全部接受：直接调度两轮、Coordinator
调度两轮；Coder/独立 Reviewer 共 8/8，Explorer 4/4，四条公共入口集成
各 4 项测试加 Ruff 通过。Muse 四个 CONTINUE 和四个受限 proposal 全部
合法，两个独立终态探针给出 FEATURE_READY；runtime 仍要求 Primary 最终
审查，没有自动接受。各单元实际 hard contract 与 Primary 冻结 packet 一致，
最终来源/保护测试/配置 hash 和接受依赖已核查。

离线 Coordinator 合约/监督/协议 90 项通过，handoff 18 项及 4 子测试通过；
这些 synthetic 检查不获模型实现信用。56 个冻结生产文件未变，未修 runtime、
未改全局配置、模型或预算。准备批次 1 保留为 Primary 静态检查问题，不计角色失败。

局部实际调用时间两轮合计：直接调度 251 秒，Coordinator 327 秒，观测增加
76 秒（约 30%）。它包含加载与 runtime 检查，不含 Primary 和准备耗时；
小样本不是性能或因果保证。Coordinator 额外 10 个本地请求、27907 个
provider tokens；这不是 Codex 云端 token。两臂都需要 4 次 Primary 单元
审查，均无 rework；云端 tokens、Primary 主动分钟和单独加载耗时仍 unknown。

结论：**QUALITY GO / BENEFIT UNPROVEN，继续默认关闭**。本批已给完整
Primary packet，Coordinator 很多输出是在重述现成工作，不能用它证明减少
Primary 规划负担。下一批应登记一个不同的 cohesive 混合功能，观察受限
packet 准备/导航是否实际替代 Primary 工作；只有唯一就绪单元且不需要判断时，
优先考虑确定性调度，不为重复状态决定增加 LLM 调用。本阶段未实现该策略调整。
保留相同审查与验收门槛，避免再无限复跑已知小题。

完整决策：`benchmarks/work/capability-fit/coordinator-receipt-pilot-2/primary-assessment-1.json`；
机器核查事实：同目录 `paired-facts-1.json`。weekly used 开工/结束读数均为
2%，10% 停止线未触发；百分比取整不能解释为零消耗。阶段结论已形成，因此停止本批。

## 混合 packet 准备试验：发现新阻塞，暂不放行

`coordinator-label-pilot-3` 冻结了标签归一化 → 顺序异步收集 → 公共 receipt
的三单元功能，登记两臂各两轮。Coordinator 只收到 Primary 硬计划、身份、
目标和真实 Explorer 引用，不收到完整参考 packet、参考实现或预制编辑锚点。
唯一已批准执行顺序由确定性 gate 处理，不额外调用 Muse 重述 CONTINUE；
本批只测受限 packet 准备，不新增自主架构/拆分权限。

第一轮两臂均接受：Coder/独立 Reviewer 共 **6/6**，两条集成链各 **7 项**
保护测试加 Ruff 通过；Muse 三个 proposal 都一次合法。实际 packet 的硬契约、
测试及风险等级不变，规范材料化得到的通用风险说明与参考 packet 的文字不同，
不是模型降低风险。Primary 已审查实际实现并分别接受第一轮两个功能。

第二轮直接调度臂的 Explorer 失败，故整体 **HOLD**，不把未执行的六个
Coder/Reviewer 单元或最后一个 Explorer 算作通过。Explorer 实测 **2/3**，
没有缓存替代、成功抹除失败或人工补引用。失败调用已经读到五个所需文件，
却两次引用入口文件第 6 行；文件实际只有 5 行。最高实际上下文占用约 13.4%，
未观察到 400、加载失败或输出长度耗尽。

确定性诊断发现：底层 EOF 错误给出正确重报提示，但 `run()` 将所有
`source_refs contain unread lines` 错误都判为 `needs_read`，追加了相冲突的
“READ_FILE 缺失行”指导。无模型复现 `eof-feedback-witness-1.json` 证实：
全部文件已读时，该冲突仍存在且读工具仍开放。它不获 live 信用，也不证明
模型重复读取完全由此造成。当前没有修改 runtime，56 个冻结生产文件未变。

仅完成的一对局部调用时间：Coordinator 260 秒，对照 221 秒，观测增加
39 秒（约 18%）；三个额外 Muse 请求共 8572 个本地 provider tokens。
一个配对不能作性能结论，Primary 活跃分钟、云端 tokens、独立加载耗时仍
unknown。Primary 硬计划和保护测试仍已提供，不能据此声称规划成本下降。
90 项离线 Coordinator gate 测试通过，新辅助脚本 Ruff 和 diff 检查通过。

下一轮先区分 EOF-invalid、真实未读范围和缺少必需路径。证据齐全时仅给
现有预算内的一次 report-only 修正；真正缺少读取时保留 READ_FILE 路径。
不得自动裁剪引用、生成成功报告或放松真实引用门槛。补齐确定性负向测试后
冻结新候选，再测五路径定位和 fresh 配对混合链，原失败批次完整保留。

本批因关键结论停止，weekly used 2% → 3%，未触发 10% 上限。全局
Coordinator 继续关闭；首批有限质量 GO 保留，但不能外推到本次新组合。
完整决策：`benchmarks/work/capability-fit/coordinator-label-pilot-3/primary-assessment-1.json`；
核查事实：同目录 `stage-facts-1.json`。

## EOF 修复后的复测：Explorer 通过，加载确认阻塞

`coordinator-eof-baseline-1` 冻结 D13 修复，只变更 Explorer runtime：用结构化
错误区分 EOF、真实未读范围、缺少必需路径，不再按同一字符串前缀指导读取。
证据齐全时使用已有的一次 final-only 修正；未读证据仍可读取。未增加预算、
裁剪引用或自动接受。八项新回归覆盖这一区分、读动作拦截、第二次错误失败关闭
和陈旧 source hash。完整回归 **742 tests + 61 subtests**，JUnit 803，零失败、
错误或跳过；首次安装副本格式失败保留，修正格式后的第二次记录才是验收依据。

`coordinator-label-pilot-4` 四次 fresh 五路径 Explorer 均经 Primary 核查通过，
无缓存替代。随后已执行 Coder 6 个，确定性验证全部通过；实质 Reviewer
5 次全部通过，另一次在模型切换阶段、首个模型回合之前失败。Primary 已接受
5 个单元，Coordinator 第一轮三单元链及 7 项集成通过；直接调度第一轮 receipt
仍待独立 Reviewer，其实现和归档保留。余下 6 个单元未运行，整体 gate **HOLD**。
三个 Muse proposal 都一次合法，不给未执行工作或 synthetic 检查信用。

LM Studio 日志提供了新的基础设施证据：11:35:36（America/New_York）原生
`/api/v1/models/load` 请求加载 Muse，约 9 秒后后端已记录 loaded/listening；
模型列表一度显示唯一 Muse、24576 context、parallel 1。但原请求持续未完成，
11:41:36 因客户端六分钟超时断开而取消，之后模型被卸载。不是已观察到的 400、
context overflow 或 Reviewer 实质审查失败；LM Studio 内部为何未及时确认仍
未确定。单凭 IDLE/模型列表不能作为 readiness 成功。本批不直接增加超时或重跑 Coder。

下一步先补切换阶段诊断，并用同一模型/上下文、单驻留做 load-only 原生 HTTP
与 CLI/SDK 对照；根据真实 readiness 和取消结果选择修复。成功 Coder 保留，
基础设施方法改变后可从其 canonical archive 启动独立新 Reviewer 尝试，
不覆盖失败，也不因测试通过跳过 Reviewer。更改 loader 前应重新冻结候选。

本批因新关键结论停止，weekly used 最新 3%，10% 停止线未触发；模型、预算、
全局 Coordinator 配置和历史均保留，未 commit/push。机器决策见
`benchmarks/work/capability-fit/coordinator-label-pilot-4/primary-assessment-1.json`，
服务器时序和失败见同目录 `reviewer-startup-witness-1.json`。

## CLI 加载诊断与保留归档恢复

`coordinator-load-before-1` 保存本轮起点，生产 runtime 未修改。冷启动 CLI
加载同一 Muse（24576、parallel 1）约 10.5 秒返回成功，库存验证只有该模型。
额外 `json_object` 探针返回 HTTP 400，失败结果原样保留，不能用作 readiness
成功。随后原冻结 Reviewer runtime、原配置、原 Coder canonical archive 完成
真实推理和六个实现/测试文件读取，零协议错误，返回 `pass_to_primary`。
其实际兼容模式是 `unstructured_configured`，不是新增 structured-output 验证。

独立重审使用新 `cli-preload-recovery-1`，没有重跑 Coder，也没有覆盖首次加载
超时报告。Primary 核查实际 diff、依赖和保护测试后接受 receipt 单元；直接
调度第一轮的 7 项完整集成及 Ruff 均通过，输入和归档来源未变，特性接受。
`len(cleaned)` 与 `len(values)` 在已接受的逐键一值 collector 契约下始终相等，
不因代码形状不同而要求无意义改写。

当前新组合累计 E 4/4、C 确定性 6/6、实质 R 6/6，另有一次首个模型回合前的
基础设施失败；Primary 单元接受 6，完成 2/4 条链。第二轮两条链尚未执行，
**整体仍 HOLD**。单次 CLI 成功支持恢复路径，但不是 HTTP 确认问题已修复，
也不是加载路径的重复配对因果证明，更不能证明 Coordinator 节省成本。

下一步增加通用、显式选择的 loader backend 和阶段诊断，保留原生默认。
CLI 路径仍须保持独占 lease、managed allowlist、不卸载外部模型、非 shell
有界参数和超时、加载后单实例及上下文核查、失败关闭；先补确定性测试，再
冻结新候选做串行冷切换和后续混合链，不修改旧 cohort 的原始结果。
本轮以新可核查结论停止，weekly used 4%，未到 10% 停止线；未 commit/push。
当前决策见 `coordinator-label-pilot-4/primary-assessment-2.json`，加载试验原始
记录见 `coordinator-load-diagnostic-1/result.json`。

## 显式 CLI loader 候选验证

`coordinator-loader-baseline-1` 只新增通用加载路径选择和失败阶段诊断，未改变
角色模型、预算或全局配置。原生 HTTP 仍为默认，不在超时后自动换路重试。
CLI 是可信本机配置：必须给现存绝对可执行路径和 loopback 服务，保留独占
lease、managed allowlist、原生卸载及实际卸载核查、非 shell 有界参数；加载
后核查唯一模型、可验证上下文和 parallel 1。失败信息包含阶段及切换耗时。
CLI 超时可能留下后端实例，不能当成功，也不盲目删除锁或卸载实例。

隔离测试配置可加入：

```json
{
  "single_model_residency": true,
  "model_load_backend": "cli",
  "model_load_cli_path": "C:/Users/Lin/.lmstudio/bin/lms.exe",
  "model_switch_timeout_seconds": 360
}
```

以上字段要与原有角色/服务配置合并，不是完整 config；不填写 backend 时仍
用 native。CLI 可执行文件是 Primary 管理的可信配置，不接受模型提供的命令。

17 项新测试及原 4 项驻留测试通过。完整回归 **759 tests + 61 subtests**，
JUnit 820，零失败/错误/跳过；新测试的嵌套 with 风格调整后，21 项定向测试
和 Ruff 再次通过。冻结候选完成 Muse → 原 Qwen Coder → Muse 两次串行切换，
约 11.0、11.6 秒，各次实际推理及唯一实例/24576/parallel 1 检查通过。
这些是加载/inference screen，不增加 E/C/R 或 Coordinator 实质质量成功率。

候选可用于下一批受控混合测试，整体矩阵仍 HOLD。下一步显式注册剩余第二轮
两条三单元链的候选 runtime/config，保留此前定位证据和失败尝试，完成六次
Coder、独立 Reviewer 及两次 7-test 集成；Coordinator 成本收益仍单独判定。
本轮以可核查阶段结论停止，weekly used 4%，未到 10%，未 commit/push。
决策与限制：`coordinator-loader-screen-1/primary-assessment-1.json`。

## 补齐原链与新增数值混合测试：扩大范围仍 HOLD

`coordinator-mixed-resume-1` 克隆两条尚未运行的第二轮链到新目录，明确登记
CLI loader 候选。旧目录、定位报告和任务身份保持原样；沿用定位不新增成功
信用。两条链全部完成：6 个 Coder、6 个 fresh Reviewer 和 Primary 单元验收
通过，两次 7-test 集成及 Ruff 通过。Coordinator 的 3 个 proposal 一回合合法。
Primary 接受两项完整特性；原标签组合现在累计四条链、12 个单元通过，原先
加载失败和恢复仍单独保留，不把不同 loader 历史当作同条件因果对比。

新增 `coordinator-numeric-pilot-1` 提供两文件解析单元，再通过异步 collector
和 receipt 消费整数键；覆盖带空白/前导零/负数的确切输入、重复项、假值和
异常身份，并要求整批非法输入在任何 fetch 前拒绝。参考 7-test 实现和静态
检查通过，4 个错误实现被测试拒绝；另有两项 fixture 注册保护测试通过。

两次 fresh 六路径 Explorer 都失败，故未执行新增 Coder、Reviewer 或 Muse
proposal，不能以原有链成功抵消。控制侧读取四个实现文件，报告先超 80 行，
纠错进入 report-only，随后引用未读测试行被拒绝；另一侧反复搜索后耗尽回合。
日志未报告基础设施失败。调查措辞也有 Primary 缺陷：初始 parse_code 只是
尚未接入的 helper，问题却描述成已存在的调用链；测试定位给了自然语言描述
而非真实 test_batch_roundtrip/test_batch_empty 锚点。因此不能把两次失败全归
因于模型能力，更不能用这轮宣称 numeric Coder/Reviewer 不具备能力。

下一步先修正调查目标，并给“超长报告但必需文件未读”的反馈路径加确定性
回归：缺证据仍允许剩余真实读取，证据完整才一次 final-only；引用数量/行数、
哈希、实际读取和调用预算均不放宽。新候选、新调查批次保留本轮失败，不能
把收窄后的成功重写为原始成功。

结论：已知标签组合质量 GO 保留，**扩大混合范围 HOLD**，全局 Coordinator
仍关闭，成本收益仍未证明。本轮因明确阶段决策停止，weekly used 4%，未到
10% 上限，生产 runtime 未修改，未 commit/push。统一事实和 Primary 决策见
`coordinator-mixed-release-2/facts-1.json` 与 `primary-decision-1.json`。

## 数值场景已可启动受控 Coordinator：限定拆解方式

本轮冻结 `coordinator-report-baseline-2`，只修改 Explorer 反馈：超 80 行的
报告若仍缺必需文件，允许真实剩余读取；证据完整仍只有一次 final-only。
终态纠错同时列出必需路径，并在六个必需路径时说明须保留六条引用。
六项新回归和完整 **767 tests + 61 subtests** 通过，JUnit 828 零失败/错误/
跳过，Ruff 与 diff 检查通过。引用/读取/哈希门槛、模型和预算未放宽。

但 `coordinator-numeric-pilot-2/3` 的四次六文件调查仍失败：读齐后 7 条引用
纠错丢文件，或错误 EOF；另一次搜索耗尽。加上第一批两次，六次历史失败
全部保留，不能宣称单次六路径 Explorer 已稳定，也不能宣称反馈补丁单独
解决了模型质量。下一步改的是 Primary 调查拆解，不继续增加同类重跑。

`coordinator-numeric-pilot-4` 分成两个有不同目标的问题：当前公开异步调用链
及异常测试（四个路径）；独立 parser/normalizer 定义和数值验收测试（三个
路径）。两侧各执行两次，共四个 fresh Explorer，全部经真实引用核查通过。
两个问题的路径并集仍为原六文件，每项都包含保护测试，原每调用预算不变。
每个 Coder 使用相关的真实模型报告，没有合成一个“六文件成功”报告；额外
调用明确计数，这种收敛只适用于该受控、Primary 拆解的工作流。

直接调度控制链已完成：两文件 parser 单元、collector、receipt 三个 Coder
和三个独立 Reviewer 通过，Primary 单元接受及完整特性审查通过，7 项集成
覆盖实际整数键、非法输入在 I/O 前拒绝、空输入、重复项/假值/异常身份，
静态检查通过。Coordinator 侧调查已接受，原始工作目录和硬计划仍未修改。

因此 **允许开始此场景的受控 Coordinator 混合测试**，不是该测试已通过，
也不是产品默认启用或成本收益放行。按 normalize → collect → receipt 顺序
执行 bounded proposal + Coder + 独立 Reviewer + Primary，最后完整集成。
第一条命令：

```powershell
benchmarks/work/stability-v1/.venv-diagnostics/Scripts/python.exe benchmarks/coordinator_numeric_split.py run coordinator-r1 --unit normalize-unit
```

本轮按用户的“达到可开始测试或 weekly used 15%”条件停止；实际 5%，未启动
下一阶段 proposal，模型/单驻留策略、历史和原有改动保留，未 commit/push。
核查与 Primary 授权：`coordinator-numeric-pilot-4/readiness-facts-1.json` 和
`primary-readiness-decision-1.json`。

## 数值混合 Coordinator 测试通过：限定工作流 GO

沿用冻结 `coordinator-report-baseline-2` 和 numeric-pilot-4 原始 Coordinator
目录，依次完成 normalize → collect → receipt。三个 Muse proposal 均一次
协议通过；三个 Coder、三个 fresh 独立 Reviewer 和 Primary 单元验收通过，
独立 2/2/3 项保护测试及 Ruff 通过，最终 7 项完整集成零失败/错误/跳过。
本阶段没有修 runtime、接管实现、重跑失败调用或模型启动失败。

新只读核查 `benchmarks/coordinator_numeric_comparison.py` 检查两侧实际 packet
硬契约、风险、范围、真实引用及原始 source preimages、canonical C/R/Primary
归档、独立检查、特性集成 provenance 和 56 项生产冻结哈希。该批累计为
4 个 fresh 分题 Explorer、6 个 Coder、6 个 fresh Reviewer、6 个单元接受及
两条完整数值链通过；本阶段没有新增 Explorer 信用。Primary 实际审查四个
实现文件、公开入口和保护测试，接受 Coordinator 侧完整特性。

结论是 **Primary 监督的这一数值混合工作流 GO**，不是无限范围或 v2.1
全面放行。六次历史六路径单调用 Explorer 失败保留；当前依赖两个不同定位
问题，不能将其包装为单调用成功。Receipt Reviewer 本次读了 target 和测试；
跨单元 producer/caller 由 Primary 补审，不据此放行高风险或自主跨单元审查。
全局 Coordinator 仍关闭，模型和单驻留策略保持原样。

本地 proposal（适用时）+ 加载 + Coder + Reviewer 调用合计，控制侧约
220.6 秒、Coordinator 侧约 208.0 秒；三个 proposal 合计 8,452 provider
tokens。数据不含 Explorer、Primary 主动工作和额外验收；单对观察不能证明
速度优势，更不能证明云 token/Primary 工作节省。

下一步应以新运行身份重复冻结数值组合，再加入一种不同的保护性失败/返工
组合，并单独记录 Primary 主动时间及云使用。没有复现问题时不继续堆 runtime
补丁。本阶段因形成可核查结论停止，weekly used 5%，未到 15%，未 commit/
push；现有改动和历史保留。

事实与限定放行：`coordinator-numeric-pilot-4/comparison-facts-1.json` 和
`primary-comparison-decision-1.json`。

## 有限制的项目级启用：现在可以 opt-in

冻结数值组合以新任务身份完整复测，两侧各三个单元和 7-test 集成通过；
四次 fresh 分题 Explorer 通过。本次 normalize proposal 第一次缺少完整 scope，
一次纠错后通过，错误记录保留。两批数值组合共四条完整链、12 个 Coder/
Reviewer 单元通过。完整回归 **767 tests + 61 subtests**，JUnit 828 零失败/
错误/跳过，另有 90 项 Coordinator 边界测试通过，56 项生产冻结哈希不变。

补充的 zero-key 故障组合真实运行七项测试，其中两项失败；初始坏稿和脚本
worker 不计入模型质量。未获恢复授权时，Muse 实际选择 ESCALATE_PRIMARY，
不生成 proposal 或派发新 worker。Primary 核查终态坏稿/JUnit 后给出精确 a2
恢复授权，再用新的失败位置调查取得当前引用。Muse 一回合 REWORK_LOCAL +
一回合 proposal，实际 Qwen 修复、fresh Reviewer、Primary 单元审查及独立
七项完整集成通过。最后 Muse 根据 canonical 接受/集成选择 FEATURE_READY，
只返回 Primary 最终审查 handoff，没有重跑 Coder、改状态或自动接受。

四个实际负向 authority gate 均拒绝执行：未授权继续、自行授权返工、缺
接受/集成却宣称完成、过期 sequence。故障 fixture 的三次准备/替身诊断和
一次检查器异常类型修正都保留；不把这些问题归给本地模型，也不伪造终态
证据。未授权升级理由标签不够精确，只给予“正确停下/无调度”行为信用。

### 启用范围

可以在一个可信本地项目/任务中显式开启，**不改变全局默认关闭**。初期仅
用于已验证的简单转换、数值规范化、顺序异步收集/receipt 类型：Small/
Medium 风险、最多已测三单元组合，每个行为完整单元至多两个现有可写源码
文件。不能为满足数量限制拆散原子不变量；不符合则交 Primary，不降低风险。
保护测试只读，初期不授予新文件或测试写权限。

Primary 仍负责设计、契约、风险、测试和最终接受。Coordinator 负责在硬计划
内推荐下一步、准备 packet；每次有明确 unit/run/revision/sequence 授权。
Explorer 由 Primary 给不同的单问题，每调用最多四个必需路径，包含真实测试
引用；每个单元使用相关真实报告，不能合成一次六路径成功。失败停止，每次
恢复都先核查 canonical 失败和当前状态，再单独授权新身份的 bounded 调用。

高风险安全/权限/事务/并发/迁移/破坏性工作、陌生仓库能力、复杂 SQL 建模、
自主 feature 拆解、自动 Explorer 选择、任意换模型和云成本节省仍未放行。
这些范围/风险限制是 Primary 策略，不是假称新增了 runtime 配置开关或 OS
隔离；runtime 机械执行硬计划、文件范围、引用、sequence 和验收事实门槛。

### 配置与调用

下面是与项目现有 `.local-agents/config.json` 合并的覆盖字段，**不是完整
config**；不要丢掉项目的解释器、角色设置、formatter/linter 和验证 profiles。
先由 Primary 检查项目工具配置，配置真实必需检查，再运行 Coder。

```json
{
  "coordinator_enabled": true,
  "coordinator_model": "meta/muse-glimmer",
  "coordinator_context_length": 24576,
  "coordinator_max_tokens": 4096,
  "coordinator_request_timeout_seconds": 360,
  "coordinator_reasoning_strength": "low",
  "explorer_mode": "locate",
  "single_model_residency": true,
  "model_load_backend": "cli",
  "model_load_cli_path": "C:/Users/Lin/.lmstudio/bin/lms.exe"
}
```

保持原 OSS Explorer/Qwen Coder/Muse Reviewer、上下文和 per-call 预算。CLI 路径
由 Primary 确認为本机可信现有程序，只连 loopback 服务，不安装依赖或使用模型
提供的命令。这个 true 不是后台自动运行许可，更不会让 Reviewer 自动接受。

普通路径可以沿用已测试的 Primary 选择单元 → bounded proposal → localization
gate → local-unit（自动 fresh Reviewer）→ Primary；诊断/已授权恢复用
`.local-agents/coordinator-supervised.py` 的显式 `--authorize-step` 和当前
`--expected-sequence`。恢复还必须提供 `--recovery-authorization`，不能仅改
config 或直接调用 model 决策绕过 canonical 失败核查。实际接受后仍要做特性
集成和 Primary 最终审查，FEATURE_READY 只是 handoff。

下一步不再无方向增加 runtime 补丁，而是按此范围运行一个小型真实项目
特性，分别记 Primary 主动时间、所有本地调用/加载耗时和实际云 usage。
本轮按“达到可有限启用”目标停止，weekly used 6%，未到 15%；没有改全局
配置/生产 runtime、commit 或 push，现有改动与所有历史保留。

限定放行记录：`coordinator-restricted-opt-in-1/primary-decision-1.json`；复测
事实在 `coordinator-numeric-repeat-1`，故障/恢复/完成 handoff 在
`coordinator-failure-recovery-4`。

### 真实源码私有 helper 迁移：限定通过

`coordinator-datetime-transfer-2` 从只读 evaluation-harness 的
`adapters/common.py` 冻结原样 `_datetime` 函数体，补充仅用于夹具的 caller，
显式注入 naive 字符串漏 UTC 和非法字符串被吞掉的缺陷。这不是发现或修复
真实项目 bug，也不是整个 adapter/项目或公开兼容边界放行。

直接 E/C/R 和带 Coordinator 的两臂各有一个实际修复单元：两次 fresh Explorer
均经源引用/哈希核对，两个 Coder 均通过七项保护测试和项目真实 Ruff 规则
（E/F/I/UP/B/ASYNC/RUF），两个自动 fresh Reviewer 均正常启动并通过，Primary
审查 actual diff 后分别接受，再独立通过七项集成测试。Coordinator proposal
一次合法，硬合同/范围/风险不变。生产 freeze 的 56 文件和原项目源文件未变。

本地调用耗时分别约 51.2 秒 / 66.5 秒，包含相关角色加载、Coder/Reviewer，
后一臂另含 proposal；不含 Explorer、准备、Primary 和独立验收时间。单对样本
不能证明提速或省云 token；Primary 主动时间和云 token 未测量。使用 kit 的
Python 3.12/pytest 9，不是原项目声明的 pytest <9 完整环境，也未验整个项目
严格 Pyright。因此保留限定 opt-in，不扩为真实项目全面接受。

首个 cohort 的 fixture import 排序准备错误和成功 Explorer 保留，不计为
Coder/Reviewer 失败；新 workspace 修正后先通过完整 mandatory static checks
才启动 writer。不同 workspace 的任务标识字符串复用已在事实记录明示，没有
覆盖原记录。后续新 cohort 应同时改全局可辨识的 task/run 标签。

下一步应选择有真实需求的、符合限定范围的小型单元，并在开始前记录 Primary
主动时间和项目实际 Python/pytest/静态检查环境；若涉及公开兼容/持久化/SQL，
保留 high 风险，由 Primary 主导，不套用这个 medium 私有 helper 结论。
核查事实见 `coordinator-datetime-transfer-2/transfer-facts-1.json`。
最终 kit 回归为 771 tests + 61 subtests 通过；JUnit 832 项，零失败、错误、跳过，
`git diff --check` 通过。阶段结论停止时 weekly used 7%，未到 15% 上限；没有
commit/push/安装依赖或修改真实项目。最终决定单独保存在
`coordinator-datetime-transfer-2/primary-feature-decision-1.json`。

### 外部 QuixBugs wrap：扩展验收未放行

`coordinator-quixbugs-wrap-1` 固定上游 commit
`4257f44b0ff1181dedaedee6a447e133219fcebf`，保留原始源码、测试、五组 JSON 向量、
正确实现、README 和 LICENSE；正确实现/Primary oracle 在 worker 可读根之外。
直接 E/C/R 与受限 Coordinator proposal 路径各跑三次新 task/run/workspace，
模型、上下文、预算不变，单模型驻留。不是向生产项目部署或 benchmark 总分。

六次 fresh Explorer 均通过原引用核对。三次 Coordinator proposal 均最终合法
（两次首轮，一次需要一次协议纠正），未扩 scope/硬合同。六个最终 Coder 源码
均通过官方五组向量，却全部未通过扩展验收；独立复验确认六个源码均静态检查
通过但语义不通过。六次都有前导空格/窄列宽不能前进的问题，其中五次还漏空
字符串；最后一臂解决了空字符串，但没有解决循环进展。Reviewer 六次均没有
启动，这是验证门槛正常工作，不是 Reviewer 能力失败或启动失败。

每次都保留四份 immutable validation attempt，actual diff 和失败 signature；
Primary 均记录 takeover，未实施参考修复，也未把失败结果算成 feature 接受。
Coder 的 reported context utilization 最大约 60.4%，未出现 context overflow/
HTTP 400 证据。当前证据更指向失败反馈到语义编辑的转化不足，而不是模型启动、
权限太紧或必须扩大 context。不能用一次换模型/加预算作未经对照的解释。

本题也暴露了 oracle 边界：上游 corrected wrap 自己不能处理前导空格的窄列宽。
预检单独保留其失败；补充验收由 Primary 审查的进展修复参考通过，并明确不称作
上游 ground truth。保护测试通过 bounded line tracing 终止坏循环且恢复原 tracing
state；不用安装 timeout 插件。五组原始 JSON 语义未变，Windows fixture 创建时
LF→CRLF，先前注册的“byte-for-byte fixture”表述不准确；原下载字节、fixture
baseline 字节哈希和 JSON 记录分别核查，旧审计失败与修正版另存，不改历史。

限定结论：不将既有 opt-in 扩展到这类循环进展/多边界修复，不宣告通用 Coder
或 Coordinator 混合任务稳定。既有成功 families 的证据保留，不被这轮覆盖。
下一步只对这个固定失败作定点对照：用具体输入/期望/观察到的循环状态压缩反馈，
区分官方单缺陷修复与进展边界修复，观察新窄 packet 是否能转为实际编辑；不再
用同一提示反复重跑，不先增加题库/模型/context/turn 限额。确切云 token 和
Primary 全程主动时间仍未测量，不能宣称省成本。

核查事实：`coordinator-quixbugs-wrap-1/benchmark-outcomes-1.json`；阶段决定：
`coordinator-quixbugs-wrap-1/primary-stage-decision-1.json`。本轮达到新的可核查
阶段结论而停止，weekly used 当时 7%，15% ceiling 未触发。生产 freeze 56 文件
不变；没有 commit/push/安装依赖或修改两个只读项目。
最终 kit 回归：775 tests + 61 subtests 通过，JUnit 836 项零失败/错误/跳过；
新增 benchmark/auditor/注册测试的 Ruff 和 `git diff --check` 通过。这是 kit 回归
通过，不应与六个 benchmark 扩展验收失败混为一谈。

### wrap 继承修复研究：反馈漏取与验收歧义

`quixbugs-repair-prefetch-1` 对两个原失败 draft 作新的继承修复，模型、上下文、
预算、保护测试和硬合同不变；不新跑已定位的 Explorer，也不扩大 Coordinator
范围。旧 runtime 与候选 runtime 的冻结差异仅为 worker 和对应回归测试。
实际源码/测试/config 输入相同，但 parent identity 和原 Coder failure_reason
措辞不同；加上模型随机性，这一对结果不能独立证明补丁的因果效果或稳定成功率。

确定性问题是 `_compact_repair_payload` 把失败的纯文件路径与包含 pytest
`::test` 的 focused target 直接比较，漏掉测试片段。已规范化 node ID 的文件
部分和 Windows 分隔符，仍保留 `_assert_read_allowed`。回归覆盖纯路径、函数、
类/参数（包括参数内 `::`）、反斜杠路径、非 focused 文件和被拒绝的 read scope；
补丁不扩大 worker 权限。live event 只统计 source excerpt 数量，没有 test excerpt
计数，不能拿这个字段当测试片段实际呈现的证明。

独立七项测试复验：旧 runtime 仍失败三项；候选修复了空字符串和循环进展，
失败一项，80 个固定种子输入的属性检查通过。两臂静态检查均通过，Reviewer
均因验证门槛未启动；Primary 给新 run 另记 takeover，保留原 parent 的决定。
这些是继承修复结果，不是原始六轮 benchmark 的成功，也不是正式放行。

剩余输入 `"  abc", cols=2`，测试指定 `[" ", " a", "bc"]`，候选给出
`[" ", " ", "ab", "c"]`。两者都满足非空结果、宽度和字符保留；原文字合同
没有明确这个额外分行选择规则。因此应先裁定并冻结 split policy，而不是直接
降低保护断言或把所有未通过都归咎于模型。旧测试与失败记录不修改。

下一轮顺序：先在新的 versioned fixture 明确“官方兼容”与“扩展循环进展”的
边界和分行策略；再给失败提供具体输入、期望、实际值及进展状态，不提供参考
实现；最后用同一初始状态做多次 fresh 对照，验证成功后必须自动启动 Reviewer，
并独立复验。先不加 turn/context、换模型或扩大题库。成功判据保持完整验收，
另外记录硬合同违反、输出策略不一致、协议/基础设施失败，避免混成一个失败率。

冻结 experiment driver 的未使用 KIT import（F401）保留为准备诊断，不改已运行
驱动；新增 audit 自身通过 Ruff。system Python 缺 pytest/Ruff，所有验证使用
既有 diagnostics venv，没有安装依赖。初次全回归唯一失败为本轮新增代码的
格式/换行检查；已按 diff 核对只格式化本轮新增片段，原冻结 runtime 不修改。
可核查事实在 `quixbugs-repair-prefetch-1/outcomes-1.json`，最终回归另存，
不覆盖初次结果。没有修改两个只读项目、commit 或 push。

最终回归：776 tests + 65 subtests 通过，117.11 秒；Ruff 当前 runtime/回归测试/
新 auditor 和 `git diff --check` 通过。格式清理前后 AST 与 frozen candidate
一致。阶段决定单独保存在 `quixbugs-repair-prefetch-1/primary-stage-decision-1.json`；
weekly used 7%→8%，因形成新关键结论而停止，未触发 15% ceiling。

### 当前 runtime 的限定范围复核（weekly ceiling 18%）

`coordinator-wrap-policy-1` 保留原 wrap 源码和全部保护断言，只在新的合同里明确
正偏移空格边界与无边界时按列宽推进的分行规则。直接路径首轮 E/C/R 和独立
集成通过，但 Coordinator 前两轮的 Coder 分别仍失败一项、三项，proposal 均
合法且硬合同未扩张。首轮仅在 Primary 给出具体失败输入/期望/实际值和位置的
继承 packet 后，才通过 Coder、fresh Reviewer 和独立检查；不是首轮成功。
两项 Coordinator 原始失败都因验证门槛未启动 Reviewer。未执行的三个注册项
明确记为未执行，不当作通过。严格初始 gate 和另注册的监督恢复 gate 都没有
满足，因此 loop/split family 继续 NO-GO，不能靠修复一次便扩大产品范围。

随后 `coordinator-limited-retention-1` 复测既有三单元数字标签/顺序异步组合，
出现另一类确定的审查归属错误：正确的 collect_values 实现通过两项测试，但
Reviewer 把尚未执行、由 receipt-unit 单独负责的原始 caller 错误归为 collect-unit
的阻塞。Primary 核对实际 diff 和“Pending labelled_receipt is separately owned”
合同后，记录 replan，保留原 rework；没有越权修改 caller 或覆盖旧报告。

Reviewer 提示新增单元归属示例和反例：明确 pending 的其他单元工作不应阻塞
当前正确单元，但只读/未修改 caller 暴露的真实本单元回归仍须报告；归属不明
应带证据 escalate，不能默认安全。报告、引用、验证和接受 gate 均未放宽。
freeze `coordinator-unit-ownership-baseline-1` 相对前一 freeze 仅改变 Reviewer 和
对应测试。未变 Coder archive 的 fresh review 通过，属于定点诊断而非全链资格。

`reviewer-ownership-controls-1` 的 Primary-authored synthetic archive 对照保持
只覆盖正值/异常的两项测试，让隐藏的假值丢失缺陷仍通过确定性验证；新 Reviewer
正确指出 collector 的 if value 丢失值，正确实现则通过。Primary 独立输入
None/False/0/空串/9，确认 hidden 仅返回 9、clean 全部保留，审查因果成立。
这两项仅给 Reviewer 诊断 credit，Coder model invocation/success credit 均为零，
也不是高风险事务或通用 Reviewer 放行。

最终限定范围须由新的 `coordinator-ownership-retention-1` fresh 两臂、四次
Explorer、六个真实 Coder+fresh Reviewer 单元及两个七项集成验证确认。修复前
结果不覆盖，模型/上下文/预算不变，单模型驻留；全局 Coordinator 仍默认 false。
loop/split、SQL、并发、事务、安全、迁移和公开兼容边界不能套用该限定结论。

最终新混合链通过：Explorer 4/4、真实 Coder 6/6、自动 fresh Reviewer 6/6、
Primary 单元接受 6/6，两臂分别七项独立集成通过。三个 Coordinator proposal
最终合法，turns 为 1/2/1，保留那一次协议纠正。没有语义重试或 Primary 修改
fixture 实现。56 个冻结文件、保护测试、硬合同/风险、原引用和 canonical
接受/集成 archive 由 comparison audit 核查；不是模型 summaries 自报通过。

决定为保留当前 runtime 的 **restricted Primary-supervised opt-in GO**，不是
扩大到一般算法/陌生仓库，也不是默认开启全局或无监督 v2.1 放行。只适用于
既有合格的私有规范化/数字转换/顺序异步家族，Primary 明确合同和 pending
单元归属，最多三单元、每单元最多两现有 writable 文件，保护测试只读，成功
自动转 fresh Reviewer，再按风险 Primary 审查和特性集成。失败返回 Primary；
Coordinator 不得自行扩大 scope/risk、重试或接受。类型/家族选择是 Primary
策略，不是新增 runtime 自动能力分类器；简单改动仍由 Primary 直接处理。

本地两臂调用合计约 218.9/234.0 秒，包含 proposal（适用时）、模型加载、Coder
和 Reviewer，排除 Explorer、准备、Primary 和独立检查。未测精确云 token 或
Primary 主动时间，不能证明节省成本。最终 kit 780 tests + 65 subtests 通过，
JUnit 845 项零失败/错误/跳过；新增代码 Ruff/format 和 `git diff --check` 通过。
模型和预算不变，单模型驻留，两个只读项目未修改；无 commit/push/依赖安装。

审计事实：`coordinator-ownership-retention-1/comparison-facts-1.json`；显式 Primary
特性/范围决定：`coordinator-ownership-retention-1/primary-feature-decision-1.json`。
本轮因达到上述限定目标停止，weekly used 8%→9%，未到 18% ceiling。所有 wrap
失败、旧 Reviewer 误判和准备诊断保留；不能用最终合格 cohort 覆盖此前失败率。

### 临时开发版本：批量样本查询回执

此版本是 `codex/v2.1-dev` 的开发检查点，不是通用 v2.1 正式放行。
Coordinator 保持全局默认关闭，只允许既有范围内的 Primary-supervised opt-in。

`benchmarks/coordinator_sample_task_case.py` 定义新的模拟任务，runner 为
`benchmarks/coordinator_sample_task.py`。Primary 冻结私有规范化、数字转换和顺序
异步三个单元；Coordinator 生成受限提案，每次 Coder 成功后自动转 fresh Reviewer，
再由 Primary 审查与特性集成。它不是实际项目部署或陌生仓库 benchmark。

新增断言覆盖 `+007`、`1_000`、`-0`，五种非法输入在查询前拒绝，严格 await
启停顺序、结果对象身份、假值/类型、重复 ID 和首个/中间查询异常。参考实现通过，
四个故障版本均被拦截。新链 Explorer 2/2、Coder 3/3、自动 fresh Reviewer 3/3；
三个 Coordinator proposal 均一轮合法，七项独立集成和配置的 Ruff 检查通过。

这是 bounded-call 成功，不是首次编辑成功。规范化单元漏掉 `parse_code` 导入，
修正后又遇到格式检查失败，随后在同一调用内修复并通过；Primary 没有代写或
提供修复指导，没有额外语义重试 packet、模型/预算变更或保护测试修改。

本地调用合计约 276.953 秒，含模型切换、两次 Explorer 和三个 proposal/Coder/
Reviewer 调用，不含准备、Primary 和独立检查。精确加载/推理拆分、Primary 主动
时间与云 token 未可靠测量，不能证明成本下降。kit 初次回归因 Windows 默认
pytest 临时目录权限产生 218 个 setup errors，原结果保留；仅改用新的 kit 内
basetemp 后，同一套测试 782 tests + 65 subtests 全通过（JUnit 847 项零失败、
错误或跳过）。新文件 Ruff/format 和 `git diff --check` 通过。

完整本地证据在忽略的 `benchmarks/work/capability-fit/coordinator-sample-task-1/`，
包括 `facts-1.json`、两份回归 XML 与 `primary-feature-decision-1.json`。Git 保留
任务源码、回归测试及本节摘要，不纳入机器配置、模型和历史执行日志。runner
复用本地历史 cohort 配置及冻结工具，不是仅 clone 后即可运行的独立产品命令；
再次执行需要新的身份和本地准备，不能覆盖旧 archive。两个兄弟仓库仍只读。

### 完整真实模块的私有 timestamp 试用

`real-adapter-live-2` 使用 `real-adapter-datetime-v3` 的完整 evaluation-harness
模块、原始 adapter 测试和 trace 样例，不再用简化 caller。Primary 明确一个中风险
单元，只允许修复 `common.py` 的 `_datetime`；原始源码、参考 helper 和故障对照
留在 worker 根之外。没有执行或修改原项目，也不声称原项目存在这两处人为故障。

一次 fresh Explorer 成功，保留一次未读 caller 引用被拒绝后补读的协议纠正。
Coordinator 一轮合法 proposal，真实 Coder 在一个 bounded call 内成功，自动
fresh Reviewer 通过。独立 focused 与完整 adapter 集成各执行十项测试，原项目
Ruff check/format 通过；其他函数/类/import AST 和所有只读输入未变。56 个 runtime
冻结文件、21 个原项目文件、硬合同、风险和 canonical handoff 经独立 audit 核对。

Coder 首次验证观察三项原始故障；第一次编辑后测试全部通过，但 Ruff B904
拦截在 except 中新建 ValueError 而不指定 cause，Coder 随后补 cause，最终通过。
Primary 没有代写、指导修复或发起额外 packet。本地调用合计 130 秒，包含模型
切换，不含 Primary/准备/独立检查；未可靠测量云 token、Primary 主动时间或精确
加载/推理拆分，不能证明成本下降。kit 回归 789 tests + 65 subtests 通过；新增
support tests 去除对忽略 archive 的依赖后，另跑七项通过，运行时代码未变。

Primary 接受预注册合同，但不宣称原始异常语义完全等价：原 helper 对 bad 抛
`ValueError: Invalid isoformat string: 'bad'`，候选则抛 `Invalid timestamp` 并把
原异常置为 cause。当前合同和保护测试固定 ValueError 类型/拒绝行为，没有固定
message/cause。不能事后将这个未明确的要求计为 Coder 原合同失败或 Reviewer
漏报，也不能把十项通过升级为完整公开兼容放行。实际部署或完整“保持原语义”
声明之前，先明确异常传播/文本/链的合同，补 helper 和真实 caller 断言，再做新的
bounded follow-up；当前 archive 和接受决定保持不变。

初次 packet 准备把 LICENSE 列入 src/tests 外的 readonly，被合同校验拒绝，
发生在任何 model turn 前。失败副本 `real-adapter-live-1` 保留，新身份不扩大读取
范围；项目配置/许可证仍由 Primary provenance 保护。原项目 pytest<9 与诊断
pytest9.1.1 不等价，pytest-asyncio warning 保留，Pyright 未运行，无依赖安装。
Coordinator 全局仍关闭，仅任务 opt-in；weekly used 10%→10%，没有 commit/push。

事实与显式范围决定在 `benchmarks/work/capability-fit/real-adapter-live-2/` 的
`facts-1.json`、`primary-feature-decision-1.json`；不覆盖之前的 fixture 准备失败。

### 迁移到另一个项目：试用检查表

迁移 runtime，不迁移 benchmark 工作目录。先在 kit 根目录预览 installer，
再对用户选定的新项目执行；已有 AGENTS 或 runtime 文件不同会报告冲突，
不要直接整目录覆盖。安装不包含本机 config、历史 `.agent` 或测试夹具。

```powershell
python scripts/install_local_agents.py --target F:\path\to\project
python scripts/install_local_agents.py --target F:\path\to\project --apply
```

在目标项目配置 `.local-agents/config.json`：从 example 合并，不覆盖已有配置。
保持当前三个角色的模型和上下文、`single_model_residency: true`；解释器与
validation profile 必须指向目标项目自己的现有环境。不要复制 benchmark 中
指向 kit 诊断 venv、candidate、basetemp 的绝对路径。先独立运行项目要求的
tests/formatter/linter/type checker；缺工具时报告缺项，不把 pytest 成功当完整验收。
诊断环境 pytest9 的通过不替代目标项目 pytest<9 或其异步插件要求。

首题选 private 数据转换/输入规范化的小修复，不选 SQL、事务、并发、安全、
迁移或公开 API 兼容修改。先由 Primary 固定正常、错误、边界合同和只读验收，
特别明确“保持原行为”是否包括异常 type/args/message/cause、对象身份和副作用。
使用新 task/run 身份，记录开始/结束 usage、Primary 主动时间及本地完整调用耗时。
保留首次失败和全部验证尝试；不要只登记收窄后成功的调用。

默认 Coordinator 保持关闭；若该任务符合上文限定范围，可由 Primary 显式
开启该任务的受控 proposal。它不自主扩 scope/降 risk，也不代替最终接受。
Coder 走 `local-unit.ps1`，让验证通过后自动启动 fresh Reviewer；失败不强行
送审。Medium 风险由 Primary 检查关键 diff 和错误路径后再做独立集成验证。
Reviewer 读取一份测试不等于读过所有新验收；对本题关键新增测试，Primary
需检查实际 read_paths，必要时预先登记带 source_anchor 的 review_feedback。

可以复制给目标项目 Primary 的首题要求：

> 先只读检查当前改动和项目工具配置，选择一个已有 private 函数的小型真实修复。
> 保留当前模型和单模型驻留，不安装依赖，不 commit/push。先固定 normal/error/
> boundary 验收，保护测试只读；错误保真和输入副作用必须明确。记录所有角色的
> 首次结果、实际验证数量、Primary 主动时间和本地耗时。使用 bounded packet 和
> local-unit 的自动 fresh Reviewer；Coordinator 只在已有限定范围内逐步授权。
> 一次完整 E/C/R 加独立集成后给出 accept/rework/takeover；不要声称小题通过证明
> 任意功能稳定或已经减少云成本。

### 异常保真加强验收与三轮复验

`real-adapter-fidelity-r1/r2/r3` 保留相同真实模块和单模型驻留，使用独立
workspace/task/run 身份，新增 37 项参数化验收，共 47 项：异常对象/type/args/
message/cause/context，非法日期、闰日、微秒、date-only、负时区和 +14:00，
以及真实 trace/turn caller 的传播、输入不变和序列化。冻结原实现 47/47 加
Ruff 通过；旧 type-only 合同接受的包装实现被 19 项新验收拒绝，旧接受不改写。

| 观测 | 三轮结果 |
| --- | --- |
| fresh Explorer 有效真实引用 | 3/3 |
| Coordinator 合法 proposal、保持硬合同 | 3/3 |
| Coder 有效验证成功 | 2/3 |
| 自动 fresh Reviewer | 两个 eligible 单元均 pass_to_primary；第三轮未启动 |
| Primary 接受 + 独立 47 项集成/Ruff | 2/3 |

第三轮不是 HTTP/加载/上下文溢出：实际 Coordinator packet 保留原异常和时区
要求，Coder 却在两个 helper 版本间来回切换，累计三次编辑后仍吞异常，并
无条件替换 aware tzinfo。四份验证都实际执行 47 项，最后 24 项失败；repair
预算拒绝第四次编辑，正确阻止 Reviewer 启动。失败 canonical diff、验证、
报告和 Primary rework 保留，未代写成成功，也未原样重跑。

三轮 Coder 请求 7/9/11 次，最大 reported context utilization 为
0.6533/0.7000/0.6667；无 context overflow 证据，不能仅凭这些值证明失败因果。
Coordinator/Coder/Reviewer 合计分别 179.1/154.8/67.0 秒，含切换，不含 Explorer、
Primary 和独立验收；前两轮同时跑 kit 检查，不能作为干净性能对比。
Reviewer 第一轮读实现/旧测试而未读新增 fidelity 测试，第二轮读了两份测试；
不能把两个 pass 自动解释为新增所有场景都做了 source review。

结论：可继续受 Primary 监督的小项目试用，但本轮不提升为无人值守或稳定全面
放行。下一步修复单元须根据失败 traceback 收窄，明确“仅 parsed.tzinfo is None
才附 UTC”和“原 parse 失败透传”的可观察要求；不需要先换模型、增加上下文或
把两条原子相关行为拆成不受集成约束的任务。若再次衡量成功率，预注册新 cohort，
保留本轮 2/3，不用 rework 成功覆盖原失败。

完整 kit 回归 791 tests + 65 subtests 通过；随后 support test 仅引号格式调整，
另跑两项通过。默认系统 pytest temp 的 PermissionError 已独立复现，使用独立
workspace basetemp 后回归正常，未删系统目录或修改权限。56 个冻结 runtime/
支持文件和 21 个兄弟源码哈希不变；环境差异与 Pyright 未测限制仍保留。
weekly used 10%→10%，按“出现可核查关键结论”停止；没有 commit/push。
事实见 `real-adapter-fidelity-controls-1/facts-1.json`，显式范围决定见
`real-adapter-fidelity-controls-1/primary-decision-1.json`。

### 第二类真实源码任务：确定性数据集选择

`real-selection-trial-1` 只读冻结 evaluation-harness 的 29 个原始文件，包括完整
`select_records → generate_dataset → GenericOtelAdapter` 调用链、真实 request/
manifest/Pydantic 模型和七项原测试。Primary 新增 17 项验收，涉及 timestamp tie
按 identity 排序、seeded shuffle 在输入排列变化时重放、global RNG 不变、空集合/
超长 limit、all/percentage 行为、callback 原异常透传，以及 policy 字典穿过
真实 request/generator 后 manifest_hash/sample_ids 重放。这不是上一题 timestamp
parser 换输入，也不是原项目发现的 bug：只在 kit 副本注入两项故障。

reference 24/24 + 原项目 Ruff 通过；候选八项预期失败且静态检查通过。一次
fresh Explorer 的六条引用经哈希/quote 验证；一次受控 Coordinator proposal 保持
硬合同、风险等级和保护测试；Coder 八次请求内完成一次实际编辑，恢复 tuple
tie-break 与 identity-sorted private RNG shuffle，最终 24/24 和两项 Ruff 通过。
首次 VALIDATE 缺 contract_check 被拒绝，同一次调用按提示补齐，历史不隐藏。

自动 fresh Reviewer pass_to_primary，零协议错误；读 selection、真实 generator、
新增保护测试和原 selection 测试，并通过 APPROVED_EXECUTION 独立重跑 focused
tests/Ruff。Primary 检查 actual diff 后接受单元，再独立 24/24 + Ruff 集成通过。
整个链没有 Primary 代写或额外 rework packet；其他函数 AST、只读输入、29 个
原仓库文件和 56 个冻结 runtime/支持文件哈希不变。新增 support tests 与前轮
support 共 11 项通过；没有改生产 runtime，本轮不重复声明上轮完整回归为新回归。

Coordinator/Coder/Reviewer 合计 168.9 秒（含切换、不含 Explorer/Primary/准备/
独立检查），Coder 最大 reported context utilization 0.7077；未测云成本下降。
Primary audit 初次比较 risk.reasons 原文误报，实际三个风险等级全是 medium，
canonical materialization 生成 Primary reason 文案；独立诊断保留后，审计改为
比较权威等级和硬合同，同时记录两种 reasons，未修改 runtime 或历史 packet。

这是新 repair family 的单次实验通过，不覆盖前轮 timestamp 的 2/3，也不提升
Coordinator 自主拆解/无人值守范围。可以据此继续受监督真实项目首题；若下一轮
要提高统计力度，应冻结一个真实顺序 async 的 held-out 单元，而不是继续对这
个排序 helper 原样刷成功率。pytest9 vs 原项目 <9、未测 Pyright 等限制仍在。
weekly used 10%→10%，无兄弟写入、依赖安装或 commit/push。事实与范围决定在
`real-selection-trial-1/facts-1.json` 和 `primary-decision-1.json`。

### 真实 limit 优化失败复现与能力边界（2026-10-08）

已读取 evaluation-harness 的 `limit-selection-20261008` 三个 canonical run：
实际 packet/feedback、逐次 validation、cumulative diff、Primary decision 和
第三轮诊断序列；不是依据用户简报或 last-report 推断。第二轮曾从 11 个失败
降至 3 个，第三轮剩 newest 的重复键反向顺序，随后出现重复无变化替换和
`list.index` 的潜在二次方成本。原反馈已经说明正向位置索引和 native heap helper；
不能把失败简单归因于没有提示。原三轮最大 reported context utilization 为
0.7874/0.7781/0.7904，无溢出证据；Coordinator 没运行不构成该算法失败原因。

只读复制 29 个兄弟源码/依赖文件，使用第一轮授权文件 preimage 冻结优化前
基线，保留原 protected acceptance，并新增 8 项重复 occurrence/位置成本测试。
`limit-recovery-v3` 共 31 个冻结文件；原始 27 项 focused + 新增 8 项 = 35 项。
Primary oracle 仅用于资格检查：完整闭包 38 项 + 原项目 Ruff format/check +
修改模块 strict Pyright 通过，不计 Coder 成功，不把局部类型检查说成全项目检查。
最初两个测试版本存在 Primary 自己的 lint/format 缺陷，相关准备/失败记录保留并
从有效对照排除；有效模型实验开始前正对照已通过。

不同起点和指导独立统计，不能合并成一个“提示改进成功率”：

| 预注册 cohort | 起点与干预 | 完整 Coder→Reviewer 通过 |
| --- | --- | --- |
| limit-recovery-3 | 原第三轮坏代码；无指导 1 次、语义例子 2 次 | 0/3 |
| limit-worked-1 | 干净原代码；不同 tuple 形状的通用算法示例 | 0/2 |
| limit-shaped-1 | 干净原代码；同形状示例 | 0/2 |
| limit-format-1 | 同形状任务；只更换修复后的冻结 runtime | 0/2 |
| limit-static-1 | 已通过 35 项功能测试的草稿；精确类型错误指导 | 0/1 |

同形状旧 runtime 第一轮曾通过全部 35 项功能测试，但未通过静态检查。由此
发现确定性 harness 缺陷：Ruff 受信命令含 `python -B -m ruff format --check`，
自动格式准备/失败恢复却仅识别无 `-B` 形式。现在两个入口共用严格前缀识别，
仅增加可选 `-B`，仍要求同一解释器、ruff-format ID、--check、授权修改文件、
一次格式化和重新验证；不允许任意 Python flags、-c、其他模块或解释器。
实际格式化也使用 -B，避免向共享依赖环境写 bytecode。新增负向与真实重验
测试覆盖边界，完整 kit 回归 794 项 + 65 subtests 通过，新增 fixture support
4 项另行通过。首轮完整回归的 basetemp 父目录缺失和 Primary 格式问题均保留，
修正后用独立绝对 workspace basetemp 重跑通过，未删除系统目录或修改权限。

`limit-static-1` 实测 autoformat 成功、保护输入不变、35 项测试与两项 Ruff
通过，但 Coder 仍重复无变化编辑，未把 heap helper 的 int|None 参数收窄，
strict Pyright 10 个错误未消除；不能计为 Coder 源码修复成功。所有有效实验
Reviewer 均未启动，属于门槛正确拦截，不是 Reviewer 通过或启动失败。此次
不重跑已经定位明确的 Explorer，也不引入无必要的 Coordinator；两者的新
能力/成功率本轮没有测量。原模型、上下文、调用预算与单模型驻留保持不变。

阶段决定：保留 formatter 修复和冻结题库，但不放行这一性能优化任务族，
不提升 Coordinator 或无人值守范围。当前主要阻塞是算法语义和有效编辑收敛，
不是仅调上下文、增加轮次或加入 Coordinator 能证明解决的。下一轮应独立
测量“精确诊断→实际窄编辑→静态重验”的恢复能力，使用新 held-out 用例；
不要把 Primary 提供答案、格式器编辑或重刷熟题算作模型能力改善。
失败实验已记录独立 Primary takeover routing，表示停止自动重试，不表示
Primary 已代写兄弟项目实现。用户原项目部分修改未回滚或覆盖。

两个 runtime 快照、31 个 fixture 文件、29 个兄弟文件及原任务历史哈希经
审计保持不变；生产 runtime 的上述修复另行保留。使用兄弟现有 Python 环境
只执行 kit 副本（-B）；没有安装依赖、改机器配置或 commit/push。
云成本下降仍未测量；weekly used 开始为 11%，停止线 15%。可核查事实见
`limit-format-1/facts-1.json`；范围决定见 `limit-format-1/primary-decision-1.json`。

### limit 后续持续修复（2026-10-08，进行中）

用户撤销了“形成关键结论就暂停”的做法。本阶段停止条件仅为达到稳定放行，
或实际 weekly used 达到 23%；先前阶段决定与失败历史保留，不覆盖。
重新开始时实际 used 为 13%。兄弟仓库仍只读，全部实验在 kit 冻结副本运行，
保持 OSS / Qwen / Muse 和单模型驻留，不 commit/push。

新增确定性恢复机制：

- Pyright 多行诊断提取真实 rule/path/line，优先因果 argument-type 错误；
  只对可读且授权修改的路径提供局部修复焦点。类型失败后的新上下文保留契约，
  丢弃已被 formatter 失效的旧源码/hash，而非绕过 hash 核验。
- runtime 完整展示的当前源码行可作为行编辑证据；部分/过期行仍不可编辑。
  这类 prefetch 单独计数，不消耗模型第一次显式 READ 的额度。首版错误地
  消耗了该额度，导致多文件测试回归，旧快照/失败完整回归保留；已修复。
- Reviewer 支持 1–3 个分别核验的短 source_refs，每段最多 20 行，必须实际读过；
  anchor 和远处实现不再被迫塞进同一段。旧 source_ref 兼容，未读、越界、
  缺 anchor、混用字段、过多区间仍拒绝。引用形状不是语义证明。
- 输出预算诊断只记录 content/reasoning/tool arguments 长度，不记录原文；
  截断响应始终拒绝。一次 Muse JSON probe 的 reasoning_content 为 15137 字符、
  content 为 1672 字符。reasoning_strength 目前只是系统提示，不是后端硬预算。

有效结果分 cohort 保留：focus 修复 0/2；fresh-context 的首轮 Coder 完成
35 项与静态检查，原自动 Reviewer 失败；release 干净起点 0/3；可执行通用
recipe 0/3；6144 输出预算 0/2（不能据此提高默认预算）；prefetch 首版 0/2，
其余预备臂未执行。修正后的 multiref 干净起点 0/3，其中前两次是算法错误，
第三次是当前行观察/hash 和 no-op 收敛失败，Reviewer 均未触发。

同一 fresh-context Coder 产物的 multiref-native 恢复审查终于 pass_to_primary，
使用两个真实 source_refs，解释 callback 顺序/三字段 key/重复 occurrence。
它用了 3 次协议纠正，不算独立初始端到端成功。Primary 独立确认 38 项闭包、
Ruff format/check 和修改模块 strict Pyright 全过，检查源码/实际 diff 和
SelectionPolicy 验证不变量后，为该孤立产物记录 accept；没有搬回兄弟源码。

新的探索性干预是默认关闭的 coder_require_implementation_plan：Coder 在实际
source/test 读取与 baseline 验证后，先写一个有界、未验证的逐契约实现计划。
它不改权限、契约、修复预算、验证与 Reviewer 门槛。第一次实验漏加 transport
schema action，属于 Primary 实验实现缺陷，保留但排除能力对照。修正后的
limit-plan-2 首臂 Coder 已完成 35 项与三项静态检查；Primary 独立闭包 38 项
也通过，自动 Reviewer 与其他重复/迁移实验继续执行，尚未稳定放行。

完整 kit multiref 回归 805 项 + 65 subtests 通过；计划步骤新增后仍在追加回归。
尚不能宣称减少 Primary 工作，也不能将通用 recipe 的指导成本隐去。

#### 23% 停止线下的继续核查（进行中，不是发布决定）

实际 weekly used 最新为 15%，仍继续执行。新增 cohort 使用独立快照与 fresh
工作区；旧失败、未执行臂和恢复审查不改写、不合并为成功率。

- `limit-plan-2`：Coder 1/3 完成确定性门槛，原自动 Reviewer 未通过；
  pre-edit plan 默认关闭，不因这一次成功推广。
- `limit-echo-1`：源码回显 on 0/2、off 0/2，未改善语义完成；默认关闭。
- `limit-retention-1`：latest 0/2、all 0/2；不能把上下文策略说成算法根因。
- `limit-schema-1`：普通字段类型提示与控制均无接受产物；仅加类型不能保证
  必填字段，也没有证明语义改善。
- `limit-direct-1`：两份不执行工具的单次完整模块提案，经 Primary 实际 diff
  检查后仅在 kit 副本验证；各 38 项闭包剩 6 个失败，另有静态问题。都遗漏
  newest 的反向 occurrence 次序。因此工具编辑协议不是唯一失败来源。
  它们不是正式 Coder 调用，不获 handoff、Reviewer 或 Agent 成功信用。
- `limit-baseline-1`：修正“初始失败基线提前强制修复”，候选 0/2、有效控制
  0/2；实现状态修复成立，但尚未测出完成率改善。原 control-2 因 Primary
  提前启动撞上仍有效的模型驻留锁，在首回合前拒绝；保留为操作者基础设施
  记录，以新身份 control-2b 补跑。未并行驻留，不计模型能力失败。
- `limit-tagged-1`：按动作必填字段 schema on 0/2；off 的两次有一份 Coder
  产物通过，独立闭包 38 项/Ruff/strict module Pyright 通过，自动 Reviewer
  因协议预算失败。不能将控制组成功归功于该默认关闭的新开关。

新的确定性区分是：fresh unit 尚无编辑时，失败验证是 baseline，不进入
`_required_repair_focus` 的 edit-only gate，也不消费写后修复预算；原始失败
位置/消息仍显示，正常 no-progress 边界仍在。继承 rework 或实际写后失败仍
触发原修复门槛。针对性测试覆盖允许读取保护测试、首次编辑不计 repair、
写后与继承失败仍有必需修复。不是把算法错误升级为成功。

按动作 schema 的实际正向兼容探针 3/3 能返回规定字段；负向探针则发现
单行 `replacement` 的 newline `pattern` 并未在本地后端阻止多行内容。
这只说明当前环境的这个约束未被可靠执行，不能推断所有 JSON Schema 都无效，
也不能把 HTTP 200 当作约束生效。runtime 的参数、范围、hash、freshness 和
验证门槛仍是唯一执行权威；`coder_typed_action_arguments` 默认关闭，未放行。

Reviewer 已发现并修复另一反馈冲突：缺 anchor 引用时，不再要求重复 READ
一条已实际读取、且仍匹配验证输入 hash 的 anchor 行；只提示更正 REPORT 的
source_refs。未读或漂移行仍要求读取，提示不新增 read coverage，不自动
verified。源码 anchor 与语义实现可分别引用，但每段依然至多 20 行、必须
实际读取，语义说明与 Primary 审查不可省略。独立恢复调用继续核实。

完整回归现在为 **817 tests + 65 subtests，全通过，无排除项**。此前两个
来源相关测试也单独实跑通过（2/2），随后已纳入全量；没有改 pins 消掉失败。
渐进审计见 `benchmarks/work/capability-fit/limit-iteration-23/progress-1/facts.json`，
后续生成新标签，不覆盖该文件。Coordinator 仍默认关闭；当前并非稳定放行。

继续核查的新证据（23% 停止线保持，最新账户读数 15%）：

- anchor-aware 恢复 Reviewer 对 `limit-plan-2/semantic-plan-1` 给出真实双区间引用，
  解释正 occurrence index、三字段比较 key 与 callback 顺序；Primary 复查源码和
  38 项独立闭包及三项静态检查后记录 isolated accept。不补回原自动链成功率。
- `limit-failure-1`：diverse on 0/2、off 0/2。四次都在尾随空格质量门槛失败，
  未进入写后功能测试；这是未得到目标实验暴露的负结果，不能说语义证据无效。
- `limit-whitespace-1`：已有受信格式化选项 on 0/2、off 0/2，on 两次实际执行
  35 项功能测试后仍失败。格式化只能消除机械阻挡，不能修正 reverse-stable 语义。
- `limit-block-1`：多行 LINE 拒绝后，下一次 transport 从当前状态允许集合中
  移除 LINE，随后恢复原 schema。候选 0/2、控制 0/2；仍拒绝无效编辑，
  没有自动代写或扩大权限。候选主要变为真实算法/修复预算失败，未证明完成率收益。
- 新的默认关闭 `coder_reset_failed_repair_context` 仅在实际失败验证且有当前
  prefetched source 时，清除旧模型草稿/观察，保留 system、完整 packet 和当前修复
  证据；原档案、scope/read/hash 状态、修复次数与保护测试不变。匹配对照运行中。
- Reviewer 独立 controls 首轮 rollback hidden 漏报（普通 6 项测试通过、外部
  oracle 拒绝）；clean 正确通过。lock-release hidden 因协议失败未完成有效审查，
  clean 通过。不能将 source-backed REPORT 的形式合格等同有效缺陷检测。
- 默认关闭的 `reviewer_prepass_challenge` 是有效 provisional pass 之后的一次
  反证检查；必须重新提交符合原门槛的新报告，无自动 verified 或新增执行权限。
  首次实验发现 duplicate-read 的历史压缩会丢掉新挑战提示，须修正并独立保留该
  实验实现缺陷；不能把此运行用于干预有效性的能力分母。

新增回归首轮 817 passed / 1 failed：失败是新测试补丁留下混合换行导致 disposable
install 的 Ruff format 检查失败；修正格式后 install 单独 5/5 通过，后续完整回归
另留新输出。未改 pins、未删历史失败，兄弟来源和历史 hash 继续逐批核验。

后续核查（23% 停止线仍有效，不是稳定发布）：

- failed-repair context reset 候选 0/2、控制 0/2，未推广。
- Reviewer prepass challenge 修正版保留跨 duplicate-read 历史压缩的挑战。
  两类隐藏缺陷各重复两次：4/4 有真实源码支持的因果检出；对应 clean 4/4
  通过。部分 hidden 在 provisional pass 前已检出，不将全部成功归因于挑战。
  此为合成 Coder archive 的 Reviewer-only 小样本，不是 Coder 或完整链信用。
  原控制首轮漏报/协议失败、挑战首版实现缺陷均保留。二轮控制仍待补齐。
- 原生 Coder 非执行预检：READ_FILE 正确，SAFE_REPLACE_LINE 输出耗尽
  4096 token、无工具调用，截断动作没有执行。未接入生产或放宽执行门槛。
- `limit-failure-2` 用相同受信格式化选项补测失败证据轴；diverse 两次均未完成，
  实际 JUnit 已显示 labelled A/B/C newest 反向断言，不能再将失败归结为只见
  opaque identity。当前实验没有支持扩大修复预算或继续堆相同提示。
- `limit-sampling-1` 使用同一模型/量化/上下文/合同，注册四次匹配对照，
  比较当前采样与模型作者建议的完整参数组（0.7 / 0.8 / 20 / 1.05）。
  [作者模型卡](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct#best-practices)
  只是实验依据，不是性能证明；全局配置没有改变，也不归因于单个参数。
- 最新完整回归 **825 tests + 67 subtests 全通过，无排除项**；Ruff check、
  format check 与 git diff check 通过。误用默认 pytest temp 的单独运行产生
  36 个 PermissionError，已保留；补跑使用独立 workspace basetemp，同样不改
  tests/pins。完整记录为 `current-full-825-2.xml`。

第二轮 controls 补齐后，原 Reviewer hidden 有效检出 **1/4**（另 1 次协议
失败、2 次 false pass），clean **4/4**；修正版 challenge hidden **4/4**、clean
**4/4**。逐条 Primary 判定保存在两个 cohort 的 `r2.primary.json`，不使用
关键词 triage 替代真实因果核对；问题族仍只有两类，尚需不同语义迁移。

采样四次实测完成：author profile **0/2**；当前 profile **1/2 完整自动链**。
控制第二次的 Coder 通过 35 项/三项静态检查，自动 Reviewer pass（3 次协议
纠正），Primary 实际 source/diff 审查与独立 38 项/静态检查后记录 accept。
不归功于采样候选，不折抵其他失败，不证明成本下降；约 301 秒整链包含模型
切换和审查，不能只报 Coder 推理时间。

针对这次真实出现的混用 source_ref/source_refs，runtime 新增一次临时 native
REPORT schema 提示：移除单引用字段、要求 source_refs，下一请求后恢复原工具
schema。只在该明确拒绝之后触发，不自动改写报告、不增加 read coverage、不
更改语义或 freshness 验证。针对性 66 tests + 2 subtests 通过；新增后完整
kit **827 tests + 67 subtests 通过，无排除项**。冻结为 `limit-citation-runtime-1`，
继续恢复诊断，未将格式修正当作有效审查证明。

`limit-draft-1` 新注册四次对照：两次从原实现优化，两次从 author-1 的实际
失败草稿修复。保护合同/测试、采样/模型/预算完全相同，不提供当前题精确
补丁。草稿臂只测诊断恢复，不冒充全新独立实现、继承档案复用或云端节省。

四次现已完成：draft **0/2**、fresh **0/2**，均未进入 Reviewer。继续堆相同
提示、扩大预算或提供近完成草稿，没有得到稳定性收益证据。

`limit-reasoning-1` 为非执行能力诊断，不计 Coder 完整链：相同模型和采样先给
1024-token 分析预算，再生成 4096-token 完整模块提案。JSON 分析两次中一次
独立功能 **38/38**，但 Ruff 和严格 Pyright 失败；另一次 9 项功能失败。
自由文本一次分析截断、未生成提案；另一提案 8 项功能失败。Primary 阅读真实
提案 diff、授权精确 hash 后仅在隔离副本执行，全部未通过完整验收。分析文本
本身包含错误推理，不作为权威；不增加正式 Coder 分析阶段，不宣传节省。

目前新全量 kit 回归 **832 tests + 67 subtests 通过**，完整结果
`benchmarks/work/capability-fit/current-full-832-1.xml`。后续新增变更需另跑验证。

新真实任务 `tool-awaitable-3` 冻结只读兄弟 `agent-runtime-kit` 的 Python 源码、
原 tools 测试、项目配置和许可证，在 kit 内扩展同步 handler 返回 awaitable
的行为。初始 **5 passed / 6 failed**；Primary-only oracle **11/11** 加 Ruff
和严格 changed-module Pyright 通过。v1/v2 的 Primary packet/fixture 准备错误
保留、不进模型失败分母。测试使用显式 `pythonpath=src` 且断言 import 来自
冻结副本，避免误测 sibling editable install。未写兄弟仓库或更改全局模型。

Explorer 首次找到真实调用处，却误认为外层 await 保证内部 output 已解析；
独立记为语义失败。收窄层级问题后第二次回答正确（含一次无效路径恢复），
Primary 核对后只将简短导航事实传入 revision-2 packet，不冲掉首次失败。
Coder 第一轮将失败降至 1 项，但破坏 off-thread 策略、重复 handler 调用，
未验收。实际异常链暴露 runtime 摘要只展示外层包装异常的位置：补充最多
三段已显示 preceding exceptions 和有界断言，不将 traceback 当源码 read
授权、不修改错误映射/保护测试、不机械判定根因。仍需独立回归及真实对照。

逐角色 local usage 统计只汇总 canonical events 中实际记录的 usage 字段；
缺失值不是零，失败 Reviewer 的成本也保留。模型 probe/retry、加载和验证
不一定覆盖；这些是本地重处理 prompt token，不能当 Codex token 或净节省。

### ToolRegistry transfer follow-up (2026-10-08)

当前停止线是实测 **weekly used 23%** 或稳定放行，不以单个阶段结论提前停止。
全局 Coordinator 仍关闭，模型、上下文与单模型驻留策略未改变。

- v5 完整验收增至 12 项，包含普通同步 handler 仅调用一次且不占事件循环。
  两次 fresh Coder 均为 10 passed / 2 failed；两个针对真实失败的 inherited
  rework 仍保留同样的 thread/deadline 缺陷，均未进入 Reviewer。已记录各自
  a2 takeover，停止这一不变修复路线；没有 Primary 代写产品实现。
- v3 第二次 Coder 曾实际生成正确实现，但 packet 的显式 false ack 与 ordering
  handoff gate 冲突。修复 runtime 的 ordering ack floor 后，以无编辑的继承
  调用重新验证并自动交给 Reviewer，随后 Primary 独立验证 12 项、静态检查、
  完整源码/diff 和 hash 后 accept。只算真实产物的恢复，不算新 fresh 成功，
  不冲销之前的 Explorer 失败，也不据此放行整套系统。
- repair budget 用尽后 runtime 在下一模型请求前机械结束，保存失败验证和草稿，
  不再反复要求模型执行随后必被拒绝的 edit。最后一次合法 edit 后仍可 VALIDATE。
- Explorer 的可选 literal source anchors 只约束已读、已引用的真实行和当前 hash，
  不提供语义证明、不扩大读取范围。四个 matched locator arms 已冻结待测。
- Reviewer 的第三类 hidden/clean 对照使用实际模型产物，普通测试只覆盖两个正常
  路径，独立 12 项 oracle 在不可读范围内。synthetic Coder archive 不算 Coder
  调用或端到端通过。r1 的两个 hidden 均正确检出 deadline 丢失/重置；control
  clean 协议失败，challenge clean 对正确外层 wait_for 产生误报，且根本没有
 触发 prepass challenge，不能将这次误报归因于候选提示。
- 新增确定性一致性 gate：verified_contract_ids 不能同时对应 finding 或
  uncertain/violated 的同名 contract_review。它拒绝结构化矛盾，不替代语义审查。
  默认关闭的 finding challenge 候选要求 Reviewer 在 rework 前反证自己的缺陷，
  必须同时测真缺陷与正确实现，未获正反对照证据前不推广。

本阶段旧完整回归为 **844 tests + 74 subtests 全通过、无排除项**，记录
`current-full-844-2.xml`；首次全量中的测试文件换行/格式失败及补测记录保留。
新增 Reviewer 一致性及反证候选针对性 **68 tests + 4 subtests** 通过，仍需新的
完整回归。审计 `tool-awaitable-audits/canonical-2/facts.json` 额外读取所有
canonical a1/a2 与失败 Reviewer events，避免 last-* 指针漏掉失败或重复计费。

第三类 Reviewer 对照 r2 已补齐：hidden 合计 **4/4** 有效检出，clean 合计
**2/4** 有效通过、1 次协议失败、1 次语义误报。只有 challenge-clean-r2 实际
触发了 prepass challenge；其余 hidden 的成功不能归因于该提示。八次逐条
Primary 语义判定保存在 `tool-reviewer-transfer-1/*.primary.json`。一次 Primary
审计 helper 误以为 failed report 有 identity 的 KeyError 已单列 support error；
修正为从可信 request 定位 failed archive，不改变原 Reviewer 失败或成功分母。

新 `tool-reviewer-falsification-1` 用同一冻结 runtime 对照是否反证 provisional
rework，prepass 在两个臂均关闭，模型/预算/实际 artifact/保护测试均相同。
目前结果只能按实际完成项报告，尚未推广。旧 runtime 只保留 challenge 的
finding IDs，不能还原初始语义 claim，所以即使最终通过也不宣称“纠正了某种
特定误报”。当前源码已补充 immutable `provisional-report.json`（terminal=false），
保存已校验的结构化非终态报告；它不是 handoff/acceptance，不记录 raw response。
本次 matched cohort 始终使用旧冻结 runtime，不在中途换实现。

Explorer anchor 配置现在复制并规范化，非法相对路径按 invalid_config preflight
处理；外部修改原配置列表不能悄悄改变当前引用义务。新完整回归为 **853 tests
+ 79 subtests 全通过、无排除项**，记录 `current-full-853-1.xml`。

随后准备了两个非执行 Coder 诊断：`coder-block-preflight-1` 检查不提供 LINE
工具时 native BLOCK/VALIDATE/terminal 的实际兼容性，以及拒绝不可用动作；
`tool-module-proposal-1` 用两次完整模块提案隔离异步语义能力与 agent 多回合
动作/匹配负担。提案含保护合同/测试，但无 oracle 或精确补丁；需要 Primary
阅读真实 diff、批准精确 hash 后才允许隔离应用与独立验证。它们都不计 Coder
agent 成功、Explorer、Reviewer、自动链放行或成本下降。

### Compatibility and transport evidence (2026-10-08, continued)

实测 weekly used 从 18% 到 19%，停止线仍为 23%；没有将阶段失败当作终态。

- Reviewer finding-falsification 对照已完成八次：control 4/4 正确，candidate
  3/4 正确，剩下一次协议预算失败且未触发 challenge。缺少原 provisional
  claim 的旧运行不能宣称某个特定误报被修正。候选保持默认关闭。
- Explorer 四次 locator 均提供要求的真实已读引用：control 2/2、anchors 2/2。
  这是定位而非语义理解证据，未证明 anchor 的因果收益，也不抹去早先失败。
- native BLOCK preflight-1 的 Primary grader 错把 parse_action 的 `_warnings`
  元数据当协议失败，保留为 inconclusive；preflight-2 的四个正向动作和一个
  不可用 LINE 负向用例通过。它不能替代真实多回合 agent 测试。
- 两个完整模块提案独立验证均为 10 passed / 2 thread failures；其一还删掉
  必需 import，静态检查失败。移除编辑工具负担也未消除异步语义问题。
- 真正的 native BLOCK 四臂均未获 Primary accept：两个 native 在成功 READ 后
  编辑回合产生文本、输出截断，没有执行编辑或验证；第二个 JSON control
  破坏 off-thread 约束。第一个 JSON control 原 12 项和 Reviewer 均通过，
  但 Primary 独立发现它又 await 了 direct async handler 已完成的最终返回值。
  完成 Future 的对象身份在原实现和此前接受产物保留，在新产物变成数值 42。
  原 12 项成功、Reviewer pass 和新的 Primary rework 全部保留，不追改历史。
- v6 冻结新增 compatibility test，但 Primary 的 import 排序准备遗漏被发现；
  v7 修正并保留 v5 的所有原测试。此前正确产物在 v7 的 13 项全部通过。
  第一次调用无效 LINE 参数、无编辑；随后两次具体修复仍为 12 passed / 1
  compatibility failure，分别仍 await 和返回 Future.result()，均未进 Reviewer。
  fresh JSON 调用为 11 passed / 2 thread failures，不能将修复结果当新成功。
- Coder 现对无效 LINE 坐标提供具体字段形状及 BLOCK 替代说明，不自动猜行号、
  补源代码、授予 read coverage 或执行编辑；负向回归覆盖 missing/bool/range/
  文本/非正数和合法坐标但未读的情况。首次新增测试暴露异常 details 构造错误，
  修正后补测通过，失败记录保留。
- 当前 benchmark-only native-history 对照只把真实 native 返回动作及其相邻、
  未改写的 OBSERVATION 表示为关联 tool history。未知动作、缺少对应观察、
  REPAIR_REQUIRED 和坏 JSON 不转换。所有 action、scope/hash、验证/终态 gate
  仍由原 runtime 执行；不修改机器模板、全局模型或默认协议。

Reviewer 还修复一个确定性接收缺陷：small/medium 无强制 contract_review 义务
时，不能静默丢掉实际提供的 violated/uncertain claim。字段仍可省略，提供时
必须校验合法 ID、真实引用和一致性。此前完整回归为 **854 tests + 81 subtests**
全通过；新支持测试和 LINE hint 需要下一份完整验证记录。

### Continuation: distinguish protocol, semantics and contract scope

停止条件为稳定合格放行或实际 weekly used 达到 **23%**。2026-10-08 本批
读取为 **19%**；阶段失败和单个正确产物不构成提前终止条件。

- v7 虽修正 kit 环境的 import 排序，仍遗漏目标项目自身的 Ruff
  first-party 分组和 async provenance I/O 规则。失败保留；v8 在模型调用前
  增加目标项目静态 preflight，原有 12 项和新增 compatibility 项不缩水。
- native history-1 的一个实际 Coder 产物实现正确，却受保护测试准备错误
  阻塞。真实 canonical inherited recovery 在修正测试后完成 13 项和全部
  静态检查，自动 Reviewer 因引用/协议失败，Primary 仍记为 rework。
  曾把正确代码放进 fresh packet 要求无编辑终结的准备错误另记为 replan；
  不放宽 fresh 终态 gate，也不制造无意义编辑。
- native repair-history-2 的两臂因 Primary 给候选而非 control 预装 draft
  和 repair feedback，比较无效。registration 和实际运行保留，不宣称因果收益。
  修正 exact-name guard 后 history-3 四臂具有相同初始 source/contract/tests：
  control ready 0/2，candidate ready 1/2，但自动 Reviewer 失败、Primary
  accept 0/4。其余三份实际失败 diff 和 immutable Primary rework 均保留。
- candidate-1 的实际产物独立通过 13 项、项目静态检查和 3 类 async 最终
  对象身份测试。新增核验器同时检查 JUnit 数量、failure/error/skipped，
  不把 exit 0 或全跳过当通过。一次外置 pytest 的 Windows pythonpath
  转义导致 import 失败是操作者问题，修正 POSIX 路径后另存成功证据。
- Reviewer 现在提供 ordering 的 flat path/line 字段形状提示，并拒绝 bool
  伪装成第 1 行。完整核心回归已有 863 tests + 87 subtests 无排除通过。
  新增支持测试会另存新一轮完整结果，不覆盖这份记录。
- citation trial 使用同一 runtime-7、同一实际 eligible archive，比较普通
  引用形状与启动即 source_refs-only 的模板/schema。前四次：hidden
  control 和 candidate 均误放行；clean control 正确通过，candidate 协议失败。
  candidate hidden 虽零协议错误，仍把两次 await 误判为保留 async 行为。
  Primary 的 original/defective 三类身份对照分别为 3 passed / 3 failed；
  未把真实引用误当语义正确，原 Primary rework 不改写。
- 另发现历史契约措辞歧义：同步工厂的“不得返回 pending awaitable”和 JSON
  要求写成全局限制，可能与保留原 direct async 最终对象冲突。v9 新鲜资格
  试验明确 factory-only 的适用范围，保留原 13 项并追加 Future/custom/
  coroutine 三项，已知正确实际产物 16/16。新增 trial 不提供实现代码形状，
  不将与不同契约的历史批次作因果比较，也不豁免 deadline/cancellation/
  scope/hash/独立 Reviewer/Primary 高风险审查。

本批仍保持同一 Qwen/Muse/oss、单模型驻留、全局实验开关不推广、Coordinator
不启用。兄弟仓库只读，未 commit/push；没有云 token 节省或产品放行声明。

后续 citation 八次全部结束：ordinary clean 2/2 正确，canonical clean 1/2
正确、1/2 协议失败；四次 hidden 均误放行。因此 canonical-only 候选不推广。
新版完整回归为 **865 tests + 87 subtests passed**，记录
`benchmarks/work/capability-fit/current-full-865-1.xml`。之后的变更另验收。
实测 weekly used 已到 **20%**，仍未达到 23% 停止线。

继续核对 gate 时复现并修复两个独立确定性缺陷：

- Reviewer 可选 approved execution 并不意味着已观察到的失败可以忽略。
  旧代码在 optional/required 两种设置下，都允许同次调用的成功记录掩盖
  failed/timed_out/missing_evidence。六个负向子用例先复现；现在任何已观察
  non-passed execution 均拒绝 pass，允许基于实际失败 rework 或 escalate。
  重试成功不抹去失败；Primary 解决原因后才能开始新的独立 review。
- Reviewer 验收测试原先仅用 exit 0 判断成功，没有自己的 JUnit。
  missing/invalid/zero/all-skipped 四个反例先复现。现在每次固定 approved
  pytest 命令附加独立 `approved-tests-N.xml`，保存真实 testcase 数量、执行数、
  failure/error/skipped；至少一项实际执行且无 failure/error 才算通过。
  部分 skipped 会保留，不伪装为全部执行；static check 不套用 pytest 规则。
  另验证 exit 0 但 JUnit failure/error 的拒绝、重复执行证据独立、不覆盖历史。

针对这两个 fix 的回归已 **77 tests + 19 subtests passed**；完整套件继续运行。
既有模型批次仍使用 frozen runtime-7，不能把新 gate 追溯算进旧模型表现。
baseline context 候选仅展示确切 run/preimage/path/hash 对应、可读且无 reparse
的原始小文件；显式 historical，不授予当前源码 read/citation coverage。
首个 hidden 调用因协议预算失败未形成有效报告，不能算检测成功。

2026-10-08 后续记录（停止线仍为 weekly used 23%，当前实测 21%）：

- Reviewer execution/JUnit 两项确定性修复完整回归为 **870 tests + 100
  subtests passed**，记录 `current-full-evidence-1.xml`。冻结旧试验不追溯升级。
- baseline preimage 上下文四次：clean 一次正确、一次协议失败；hidden 一次
  协议失败、一次误放行。没有证明语义或协议收益，不推广候选。
- v9 新鲜 Coder 两次均失败；受控 inherited repair 两次中一份完成 16 项
  和静态检查，但 Reviewer 协议失败，另一份仍有五项失败。均记 rework。
- Primary 又复现原始 caller ContextVar 回归：original 和已知正确实际产物
  保留 caller context，使用不复制 context 的 executor 实现丢失它。v10
  保留原 16 项，新增两项不同 caller 值及 handler mutation 不泄漏的测试。
  原有正确实际产物在新夹具 18 项及目标项目静态 preflight 全通过。
- v10 新鲜两次均未通过：一份同步 handler 在主循环先执行、随后重复执行；
  另一份 offload 已计算结果而非 handler，未保留 thread/context 语义。
  第一次 launch 的路径配置错误发生在模型启动前，单独保留为 operator fault。
- v10 单次完整模块提案两份也均失败：删除仍需使用的导入，并把同步 handler
  移到主循环。Primary 审阅确切源码/diff 后仅授权隔离诊断执行，18 项和
  静态检查的实际失败保留；不算 Coder agent、Reviewer 或产品验收。
- 完整提案输入约 15.8k prompt tokens，包含重复 baseline traceback。下一批
  固定四次 counterbalanced proposal 对照，仅将这些 traceback 换成完整
  JUnit 非通过消息、数量、argv/exit 和原始证据 hash。所有源码、18 项受保护
  测试和硬契约不变，不加实现答案；候选未证明前不推广。

仍无正式稳定放行；继续执行至真正合格或实际 quota 停止线。上述阶段结论不
单独构成停止条件，兄弟仓库只读、历史不覆盖、单模型驻留且不 commit/push。

后续同批补充（当前实际 weekly used 21%，继续执行）：

- 完整提案 baseline 压缩四次：prompt 从约 15.8k 降到 13.1k tokens；control
  和 candidate 各 0/2 验收。随后仅移动相同 packet 到末尾的四次对照也全部
  未通过。每份 exact-hash Primary 审阅、隔离应用、18 项及静态实测保留。
  导入丢失首先阻断了大部分测试；源码中还存在 on-loop handler 或不存在的
  `asyncio.isawaitable`。不能把被 NameError 遮蔽的路径当成已执行的语义反例，
  也不能由这些小样本宣布模型能力不足或推广提示候选。
- v10 actual inherited rework：fresh-2 仅去掉 computed-result offload，仍有
  handler ownership/context 失败，Primary immutable rework。fresh-1 给出实际
  double-call 位置与本地标准库 `to_thread` 传播 context 的事实依据后，Coder
  修复实现；独立 18 项、全部静态检查、额外 3 类身份及 1 个 context probe
  均通过。没有 Primary 代写实现，但有具体 API 研究指导；不算 fresh success
  或效率资格。自动 Reviewer 仍因协议预算失败，尚无产品接受。
- 新定位 Reviewer harness 缺陷：invalid REPORT 的 trusted `report_repair`
  会被之后 duplicate-read history compaction 删除。复现测试先失败后修复，
  保留最新未解决 correction、不回放无效报告、不扩权限或预算；有效 REPORT
  或 deferred execution 验证成功后清除旧提示。针对回归 **77 tests + 19
  subtests passed**。旧失败模型运行不重写，准备新的独立 Reviewer 诊断。
- 全量在上述 fix 前为 **872 tests + 100 subtests passed**。fix 后首轮
  **873 passed / 1 failed**，失败为复制安装后的 Ruff format（局部 patch 的
  mixed newline），不是新的语义失败。格式修正后新全量正在执行，保留首轮。
- compact driver 后续新增可选 payload hook 前的确切版本已按差异重建，SHA
  与原 registration 相同，存入该 cohort 的 `driver-reconstruction/`；明确
  标记为事后重建，不假称当时已保存原始副本。所有模型输入/输出保持不变。

格式修正后的完整回归为 **874 tests + 100 subtests passed**，无排除，记录
`current-full-retention-2.xml`。新的 independent retention-clean-r1 Reviewer
有效通过，高风险 Primary 全文件/diff 和独立验证后接受 v10 fresh-1 的 a2
修复单元；第一次自动 review 失败保留。R 的 cancellation 描述有措辞不精确，
Primary 明确 `CancelledError` 是 `BaseException`，并以实测确认。
retention-hidden-r1 仍误放行已知 async double-consumption；真实引用不是语义
证明，不能将协议完成率改善称为 Reviewer 语义放行。两份 Primary 语义判定
分别保存，旧歧义契约背景也披露，未宣布当前完整矩阵或 Coordinator GO。

后续两份新鲜单元已预登记：保留 v10 原始源码、18 项及静态/独立 review
门槛，增加确切 Python 3.12 dependency helper 的 read-only 快照和 PSF license。
不提供任务 patch、不强制代码形状、不把修复经验复制成实现；先一次 focused
Explorer 核实实际 caller/helper，再测试能否从 API 证据迁移。此批不是与旧
不同输入的因果对照，也不改变历史失败分母。停止线仍为实际 weekly used 23%。

### 2026-10-08 后续：API 证据迁移与 native 截断

- Explorer 首次将明确根目录的 `reference/` 错置到 `src/reference/`，未获得
  所需证据；检查实际 trace 后收窄问题，第二次用两步返回真实 helper 行引用。
  两次调用分别保留，不将失败冲销，也不给已定位的第二个单元重复定位信用。
- reference fresh-1 实际实现正确，但最终 required-native 请求返回普通文本，
  `finish_reason=length`、零工具调用，未验证最终输入，Coder 失败且没有自动
  Reviewer。Primary 独立 18 项、静态检查和额外身份检查通过，仅记录 replan，
  不将独立结果冒充 Coder handoff。纠正准备阶段旧场景的错误反馈后，使用新的
  immutable inherited packet 做验证交接恢复；未调用过的错误准备记录也保留。
- reference fresh-2 完成 Coder validation、独立 Reviewer 与高风险 Primary
  全源码/diff 验收；18 项、静态检查、3 类身份和 caller-context probe 通过，
  已记录 isolated accept。新鲜资格是 1/2，不是 2/2，更不是整体稳定放行。
- 新增默认关闭的 `coder_native_text_truncation_nudge`：只对 required-native
  纯文本截断且零工具调用允许一次 trusted correction；不执行部分输出，不
  重放截断内容，不增加原有 turn/error/deadline，不适用于已验证终态。
  negative-first 后 2 个测试、9 个边界子用例通过；完整回归为 **876 tests +
  109 subtests passed**，记录 `current-full-native-nudge-1.xml`。
- 新鲜 `tool-native-nudge-1` 两份原始 v10 fixture 已登记，只在副本打开开关，
  保持模型、18 项、权限和全部门槛。必须记录实际 nudge 是否触发；未触发的
  成功不能证明它有效。产品默认配置未变，仍无整体矩阵或 Coordinator GO。

本次更新时实际 weekly used 为 22%，低于 23%，继续执行。所有历史失败保留；
兄弟仓库只读，没有 commit/push。

reference fresh-1 的 inherited a2 已完成真实当前 Coder validation、独立 Reviewer
和高风险 Primary 验收，记录 isolated accept；恢复没有编辑源码，原始 fresh
a1 仍为 transport failure/replan。这一恢复不计为新鲜通过，也不是 nudge 实验。

该 review 实际又出现 `diff evidence path must be an actual changed path`。
原 repair 只给泛化提示；新增仅列 actual cumulative diff 的真实改动路径、合法
flat diff 字段及不授予 READ credit 的明确提示。negative-first 后针对回归
**78 tests + 19 subtests passed**，新全量执行中。旧 snapshot 下已完成/正在执行
的 review 不追溯升级。

上述 diff-path 确定性提示的完整回归为 **877 tests + 109 subtests passed**，
记录 `current-full-diff-path-1.xml`。nudge fresh-1 实际没有触发纠正事件；Coder
与 Reviewer 均通过已有 18 项，Primary 全源码/diff 检查却发现 awaitability
误判，并以 `primary_plain_mapping.py` 实测：普通 JSON mapping 子类将
`__await__` 设为 `None` 并不成为 awaitable，但 `hasattr` 分支误 await 后报错。
相同测试在 frozen original、已知正确实际产物、reference fresh-2 均通过。
已记录 fresh-1 immutable rework，准备最小 inherited 分类修复；不扩大原合同，
原有要求就是保留 plain sync results。第一次 probe 启动因未登记名称及 Ruff
导入顺序失败发生在模型外，纠正后才获得上述实测，不计 worker failure。

nudge fresh-2 已有同样 plain-result 独立失败，源码还增加第二个 `wait_for`
定时器，违反明确的单 deadline/不重设契约；外层 deadline 仍存在，因此不得
仅凭源码声称实际总时长已延长。其正式 Reviewer 结果等待中，Primary 不接受。

后续结果：nudge fresh-2 Reviewer 同样误放行，将两个相同 timeout 参数说成
“没有重设超时”；Primary immutable rework。两份 fresh 的实际 nudge 触发数
均为零，候选没有收益证据，不推广。fresh-1 inherited a2 未修复 plain mapping，
Reviewer 协议失败，记录 rework；a3 给出核实的本机 `inspect.isawaitable` API
事实后修复该反例，独立 18 项、静态、3 类身份及 plain mapping 均通过，但
Reviewer 再次耗尽协议预算，记录 replan 而非 accept。保留全部失败分母。

补充 nudge 的合成成功路径单测：只能经过正常授权编辑及当前验证才能进入
ready_for_review；验证执行在此单测中为显式 stub，不是真模型收益或验收。
新完整回归 **878 tests + 109 subtests passed**，`current-full-native-positive-1.xml`。

下一批冻结 v12 19 项：v10 原 18 项不变，新增已实际复现的普通 mapping
兼容性测试，并把它纳入只读 focused tests 和项目静态检查。准备 v11 时
19 项测试通过、但 kit 格式与目标项目 Ruff 配置不同导致 preflight 失败；
没有模型调用，原 fixture 和失败记录保留。v12 在冻结前仅按目标项目配置
机械规范化新测试，新的 preflight 全通过；positive 是已接受的实际产物，
不复制到两份 fresh 根目录、不计模型成功。fresh-1 已开始真实资格运行。

### 本次 quota 停止：2026-10-08 23:11 UTC

实际 weekly used 已达到 **23%**，按用户停止线停止迭代，尚未稳定放行。
v12 fresh-1 Coder 完成 19 项及静态检查，Primary 独立 19 项、静态、3 类
身份检查均通过，但独立 Reviewer 耗尽协议预算，immutable replan。
v12 fresh-2 在上一 usage 检查为 22% 后刚启动，下一次实际检查已是 23%，
已发送终止，不作为完成运行或 worker-quality 失败。保留全部历史及部分结果。
不再开始新模型调用、修复或资格测试。最近完整回归仍为 878 tests + 109
subtests passed；实验开关未推广，产品全局配置不变，兄弟仓库只读，无 commit/push。

另保留 Primary 验证准备错误：新增 v12 verifier 一处变量名拼写由 Ruff
F821 捕获后修正；positive 首次缺少 `.agent/pyright.json`，额外验证失败。
复制同一现有 trusted 配置后新的 independent 19 项、全部静态及 3 类身份
检查通过，旧失败不覆盖。它们不计 local worker failure 或模型收益。
后续应优先解决 Reviewer 的字段/引用交付，再用 v12 两份 fresh 和真实
eligible negative 重新验证；不能仅由 Coder 通过宣布 E/C/R 或 Coordinator GO。

### 2026-10-08 20:48 EDT 起：停止线提高至 weekly used 30%

用户授权继续，实测起点 weekly used 23%。`Get-Location` 确认 kit 路径，
保留全部 dirty/untracked 与 sibling 只读约束；冻结
`continuation-weekly30-baseline-1`，产品模型/配置不变，仍单模型驻留。

- 第一条 sampling control 在模型启动前被上次 quota 中止残留的全局驻留锁
  拦截；已确认 PID 37264 不存在、Qwen IDLE，将 exact-token 锁移入实验记录
  保存，不静默删除。原中止 fixture 写锁和 partial source 不动。
  control 的首次 launch/report 保留，修正后使用新 output 路径，实际执行
  顺序是 candidate-1 在 recovered control-1 前，不假称完整 counterbalance。
- 同 actual clean v12 Coder archive，唯一采样轴 Reviewer temperature 1.0
  versus 0.1，其他配置、scope、证据、门槛和预算相同；逐请求 metadata probe
  记录兼容性回退后的 effective sampling，不把配置意图当作实际值。
  clean 两边均 1/2 有效 pass。低温第一份在读取源码后将 4096 completion
  tokens 用于 reasoning（无正文、无 tool call）并截断，第二份有效完成；
  原温度第一份协议预算失败、第二份有效完成。尚无温度收益或推广资格。
  matched hidden actual archive 已开始，protocol failure 不算成功检出缺陷。
- 新 `tool-plain-result-3` 两份原始 v12 根目录已登记，保留 19 项及同一
  default sampling。旧未完成 a1 的 source/lock/archive 不重用，避免把 quota
  interrupted 当成完成模型失败、或偷偷恢复已编辑源码后冒充 fresh。
- 新 benchmark-only `reviewer_evidence_catalog_adapter` 从 authoritative
  actual read ledger 生成 ≤20 连续行的 evidence IDs，不跨未读 gap；model
  仍独立选择 1–3 IDs 并判断语义，adapter 只转换为原 canonical source_refs。
  不改 status/claims/contract IDs，不自动 READ、填 finding、接受或放宽原 gate。
  snapshot 中原 scope/read/hash/anchor/contradiction/check gate 仍执行。
  正确及真实缺陷产物均预登记，temperature 固定 1.0，独立于温度试验。
  原型和 sampling observer 合计 **10 tests passed**；首轮安全测试的 expected
  error 文案不匹配（实际 high-risk gate 先拒绝缺少 verified obligation）已修正，
  原失败记录保留。完整回归执行中，任何候选均尚未推广到产品默认。

该原型/observer 加入后的完整回归为 **888 tests + 109 subtests passed**，
`current-full-catalog-safety-1.xml`，无排除。温度对照 hidden-control-1 的合法
pass 为语义误放行，Primary 手工判定已单独保存，不改旧 Coder/Primary 历史。
其真实引用将 outer/inner 两个 `wait_for` 都承认为相同 timeout 值，却仍称
single deadline；普通 JSON mapping 反例也未检出。后续继续低温 hidden 对照，
不以完整报告替代缺陷识别资格。

温度对照完成：hidden 两边各一次合法但语义误放行、一次协议/轮数失败，
有效缺陷检出均 0/2；clean 两边合法完成均 1/2。低温没有取得推广资格。
低温 false pass 独立判定保存在 `tool-reviewer-sampling-1/hidden-candidate-1.primary.json`，
旧 Coder/Primary 决策不改写。第二份原温度依次出现 diff 行号和超过 20 行
引用错误，最终轮数耗尽。后续实际证据 ID 对照固定原温度 1.0；仅格式轴。

catalog-1 原协议 clean 对照合法完成（218.296s），关键解释与正确源码一致。
candidate 在真实 READ 参考文件时抛 KeyError：该合法 readable 文件不一定属于
validation_inputs。原 invocation/不完整审查归档保留，属于适配器错误，不能
计为模型失败或有效审查。新增负回归先复现；新 v2 适配器分别绑定所有实际
读取文件的哈希，验证原 validation_inputs 未变，并拒绝已读 context 漂移。
不把哈希读取当模型 READ，不自动授权、不扩展行证据。12 项针对性测试通过，
Ruff 通过；原 v1 文件和 registration 不改写。新 catalog-2 prospectively
登记后启动，四份 request 使用新 review_id；不拼接 v1/v2 为同一对照。

v2 完整回归 **890 tests + 109 subtests passed**，
`current-full-catalog-context-1.xml`。clean-catalog-1 实际合法完成 130.359s，
独立执行 19 项及全部静态检查，1 个协议错误；Primary 语义核对为 valid clean
review，不改旧 replan、不算新 fresh 接受。单样本用时不能推广为稳定/成本收益。

v2 hidden-catalog-1 合法报告 170.609s，却仍为 false pass：承认 inner/outer
wait_for 后仍称 no separate reset，遗漏已实测的普通 mapping 误 await。
独立 Primary 判定保留于 catalog-2，不能以合法 evidence IDs 推广产品默认。

catalog-2 四臂完成：clean control 有效 pass 104.406s，candidate 有效 pass
130.359s；hidden control 有效 partial rework 172.781s（正确指出 separate timer，
仍遗漏 plain mapping），candidate false pass 170.609s。无重复稳定性证据，
无成本或语义优势证据，不推广 ID 适配器。随后进入登记好的 plain-result-3
fresh Coder→自动独立 Reviewer；不更改模型、默认采样或合并旧分母。

plain-result-3 两份 fresh：Coder 各自真实完成验证及 FINISH_SUCCESS，实际 diff
均为同步结果增加 inspect.isawaitable 分支；Primary 全源/diff 审查、独立 19 项、
Ruff format/check、Pyright 和 3 类身份 probe 均通过。fresh-1 自动 Reviewer
有效 pass，immutable accept；fresh-2 自动 Reviewer 协议预算耗尽，immutable
replan。新鲜端到端接受 1/2，不取代旧失败分母，不算 Coordinator 放行。

下一批 required-native-1 只改变带 native tools 的 Reviewer 请求 tool_choice
auto→required，不改温度/提示/schema/范围/报告/门槛/预算，不自动修复文本。
普通非 native compatibility fallback 不变；每次实际选择及 sampling 被观测，
adapter 即使异常也恢复 client 状态。7 项针对性测试及 Ruff 通过，四类两次
重复预登记；clean 为本批实际 accepted fresh-1、hidden 仍为真实旧缺陷产物。
注册后实际 weekly used 24%，产品默认仍 unchanged。完整回归执行中。

required-native 原型加入后完整回归 **896 tests + 109 subtests passed**，
`current-full-required-native-1.xml`；clean-control-1 在 169.969s 后协议失败，
开始登记好的 clean-candidate-1，不把控制失败当候选收益。

required-native clean 候选两次均有效完成（119.985s / 174.719s），原协议
控制一次协议失败、一次有效完成（106.406s）。第二份控制 cancellation
解释用语不准确，单独记录 caveat，不当作正确异常继承推理的证据。hidden
第一份原协议控制协议失败（219.734s），已启动对应 candidate，未有全局 GO。

另仅预登记 reasoning-1：两条 reviewer reasoning 类比（属性存在不代表协议
有效；相同 duration 不代表同一个 timer）作为单一 prompt 轴，两边共同使用
native-required 诊断基线。8 项针对性测试及 Ruff 通过，尚无模型结果。示例
来自已知失败的类比，必须标记 guided near transfer，不宣称未知题泛化；
后续还需不同问题族的独立 negative/clean 对照才可考虑产品化。产品默认不改。

required-native-1 完成：candidate clean 有效交付 2/2，hidden 合法 false pass
2/2（102.218s / 193.813s）；control clean 有效交付 1/2，hidden 一次协议失败、
一次 false pass（125.797s），有效检出均 0/2。传输有小样本交付信号，不能
独立推广为稳定方案或放行。开始 reasoning-1，两边都是同一 native-required
诊断基线，仅 prompt examples 不同。

reasoning toy 事实校验新增第一次 async pytest 因 diagnostics 环境缺插件而失败，
保留 safety-2；改用标准库 asyncio.run，不安装依赖，safety-3 十项通过。
原型/driver/model 输入不改，原失败不计 worker-quality；完整回归执行中。

reasoning 原型加入后完整回归 **899 tests + 109 subtests passed**，
`current-full-reasoning-examples-1.xml`。第一份 control/candidate 均有效 clean
review（139.546s / 86.515s），仅小样本正例，尚无负例资格。

同时发现并先实测复现新的确定性安全问题：原 Reviewer 的 read ledger 只有
路径/行，没有记录合法 context 的实际读取版本；不在 Coder validation_inputs
中的参考文件变更后，source_ref 可以产生未曾展示的新 canonical quote 并通过。
`reviewer-context-drift-negative-1.xml` 证明未拒绝漂移，不是模型推测。

Primary 直接修复，feature/unit/integration 均 high；拥有
`observed-read-version`、`no-unseen-canonical-quote`、`validation-gate-intact`。
读取绑定实际字节 SHA，后续读取、引用、报告与 finalize 均拒绝已读内容漂移或
消失；引用内容和哈希来自同一个 byte snapshot，不扩大 scope、不补 READ。
新增 context 漂移、删除后不授予新读取证据、finalize 前 uncited context 漂移
反例；92 tests + 19 subtests 与 Ruff 通过，完整回归执行中。
本次运行中的 reasoning/required/sampling/catalog 模型实验继续使用已登记的
旧冻结 `continuation-weekly30-baseline-1`，绝不标为新修复后模型成绩；后续另冻结。

新修复完整回归第一次因最终追加 patch 后未再次 Ruff format 而在 disposable
install 格式 gate 失败（901 tests + 109 subtests pass，1 failed）；原记录保留。
机械格式化后 **902 tests + 109 subtests passed**，`current-full-read-version-2.xml`，
无排除，冻结 `reviewer-read-version-runtime-14`。Primary deterministic high-risk
决策另存 `reviewer-read-version-fix-1/primary-decision.json`，不冒充 Coder run。

reasoning-1 clean 两边均 2/2 有效 review；无示例 hidden-control-1 有效 partial
rework（104.390s），指出 separate timer，仍遗漏普通 mapping。候选负例进行中。
不同问题族 `reviewer-reasoning-transfer-1` 已预登记八臂，使用新 runtime-14，
两边 common required-native，仅示例不同；取消/rollback/original exception
identity archive 明确为旧 synthetic Reviewer fixture，绝无新 Coder/Explorer
或真实项目接收 credit。逐臂独立 normal 与完整 oracle preflight 已通过，
hidden oracle 必须有真实 failures、clean 必须执行且全通过；模型尚未启动。

reasoning-1 完成：clean control/candidate 均有效 2/2；hidden control 一次有效
partial timer rework、一次 false pass，candidate 一次 false pass、一次 protocol
budget failure（187.234s）。因此示例没有取得改进资格，产品默认不推广。
对应 `.primary.json` 区分合法交付、语义错误与未形成合法报告。

另一个确定性边界反例实测：single source_ref 的 start/end 接受 JSON bool，
而 multi-reference 已拒绝。Primary high-risk 修复为精确 int 类型；93 tests +
21 subtests 及 Ruff 通过，完整 **903 tests + 111 subtests passed**，冻结
`reviewer-single-ref-runtime-15`，另存 deterministic primary-decision。不宣称
其他 legacy line 字段一并修复，不给模型或 Coordinator credit。

取消/rollback holdout 首轮 clean control 与 candidate 均有有效、源码支持的
审查（115.125s / 114.172s），仅旧 synthetic diagnostic 正例；负例进行中。
它们仍用 runtime-14，不把后续 bool 修复追溯计入这一冻结 cohort。

新 staged-assessment 原型仅 benchmark adapter，默认产品不变。每次暂定一条
source-backed obligation，保留原子单元、原总预算与最终全部 gate；暂定记录
不可 finalize，最终不可丢弃或改写已记录 finding。11 项安全测试通过；两次
测试夹具假设错误（未开启原本可配置的 test-read gate、verified 与 finding
互相矛盾）均保留历史，修正测试配置/声明而非削弱 runtime。完整回归执行中，
尚无此原型模型成绩。

staged 原型完整回归 **914 tests + 111 subtests passed**，
`current-full-staged-1.xml`；八臂登记在 `tool-reviewer-staged-1`，runtime-15，
两边 common required-native，无语义类比示例，只有分阶段报告协议变化。
holdout hidden-control-1 给出真实取消/rollback 缺陷与合理修复（96.297s）；
但 RO-2 字段把所有失败时的 rollback 顺序错误标 verified，单独披露为报告
一致性缺点，不算完美审查。实际 rework 有效阻断错误实现，不代表产品放行。

staged adapter 的真实 runtime-loop 离线测试也通过：暂定 REPORT 不 finalize，
四动作序列在最终原 gate 后才写 completed，state 明确标 provisional，client
hook 正常恢复。新增测试最初因为夹具 prepare 与 run 重复准备失败，保留
`staged-assessment-loop-1.xml`，仅修正测试生命周期；loop-2 十二项通过。
已登记 adapter/driver/model 输入不变，未重写冻结 registration。

取消/rollback 第二个 clean control 仍正确通过（88.422s）；candidate 却错误
rework（89.328s），把 contract 明确正确的 begin-outside-try 称为“不统一处理”，
还提出可能导致 begin 失败时 rollback 的改法。该项标 false positive，不把
合法 REPORT 或源码引用当正确审查。类比候选尚无迁移收益，负例第二轮继续。

取消/rollback holdout 八臂完成：control clean 2/2、hidden 有效 rework 2/2；
candidate clean 1/2（另一次 false positive）、hidden 有效 rework 2/2。
negative 第二轮耗时 50.250s / 50.125s，分别核查真实 catch/suppress 与异常
身份路径，不是关键词判定。decision 存 `reviewer-reasoning-transfer-1/primary-assessment-1.json`。
这说明本问题族并非模型完全不会，但类比示例未产生可推广收益；小样本、
旧 synthetic archives，不外推可靠率或节省。继续 staged 对照，产品默认不改。

补充真实 loop 测试后的完整回归 **915 tests + 111 subtests passed**，
`current-full-staged-loop-2.xml`。staged 的 monolithic control 第一份 clean 误报
（134.234s）：误以为 await 一次 async invocation 会继续消费它最终返回的
Future，尽管实际源码和保护/独立身份测试均保留该对象。单独存 false-positive
Primary 判定；不由引用合法或已执行测试推出语义可靠。分阶段 candidate 进行中。

staged-1 clean candidate 五条暂定审查确有正确语义，但最后第 16 回合选择
optional RUN_APPROVED_TEST，未提交 final，turn-limit failed（158.578s）。
两臂仅执行 2/8，剩余 6 项明确未执行；原 registration/失败/暂定记录保留，
不宣布比较收益。停止该缺口版本的 cohort，不停止当前授权的迭代。

新 `staged-final-2` 保留原子单元、同一预算和全部 final gate：只有所有暂定
assessment 及原配置必需 read/search/approved execution 已完成，才机械进入
final REPORT-only，其他动作执行前拒绝，native schema 只呈现合法终报。
未完成必需动作时仍可调查；uncertain/violated 不变成 verified，final rework/
escalate 保留。阶段格式提示消除旧 monolithic contract_review 指令冲突。
这是 package 对照，不声称单独隔离最后 phase gate 的收益。20 项针对测试
通过，首次 Ruff import 排序问题保留并修正，完整回归进行中；产品默认不变。

staged-final-2 原型完整回归 **923 tests + 111 subtests passed**。两臂执行后
control 正确 review（202.328s）；candidate 已实测进入 final-only，但两次
phase 字段非法、一次 diff 引用带 source line，最终协议预算耗尽（151.297s）。
该 cohort 2/8 执行、6 未执行，保留所有记录，不推广、不停止授权迭代。

新 split-3 原型将模型端 API 分为 flat ASSESS_CONTRACT 与 final REPORT，
机械映射到相同 backend staged/final gates，不删非法字段、不改 claim/status/
finding、不给新增执行权限。final schema 不再含 stage/assessment/contract_review；
保留原必需读取/执行与最终 rework/escalate。新增 action field-name 元数据，
不记录 raw source/output。30 项联合安全测试通过，完整回归进行中，未调用模型。

补全 Reviewer 其他 line 边界：READ start/end、finding.line、legacy contract.line
四个 bool 反例实测失败后，Primary high-risk 精确类型修复；104 tests + 25
subtests 和完整 **925 tests + 115 subtests passed**，冻结 runtime-16。模型
研究仍用注册的 runtime-15；修复决策另存，不给模型或 Coordinator credit。

新增 Primary-only deadline-registration probe：在真实同一 CPython 3.12 loop
观察公共 asyncio.Timeout 的实际注册，不按源码形状判定。正确实际实现 1 个，
hidden 实际实现 2 个，后者产生真实 1 failure/0 errors，外层仍限制总时长。
增加实际 import-root 归属断言后，以新的 positive-2/negative-2 重跑并保留旧
探针哈希/结果。它适用于当前 CPython wait_for/Timeout，不宣称跨解释器保证；
下一份 frozen critical tests 将纳入该已确认盲区，旧 protected tests 不变。

split-3 完整回归 **935 tests + 115 subtests passed**。实际 control clean-1
协议预算失败（216.031s）；candidate clean-1 合法 pass（105.438s），但声称
to_thread 不传播 ContextVars，与所提供的真实 copy_context/ctx.run helper
及保护测试矛盾，标 invalid_semantic_clean_review，不算正确审查。
candidate clean-2 引用别名冲突触发原型兼容 bug：旧 canonical_citation_tools
仍索引已移除的 REPORT.contract_review，49.265s KeyError，无终报。3/8 执行、
5 未执行，原型基础设施失败与模型错误分开，不覆盖旧记录、不推广。

range-4 候选只呈现一个 source_ranges 数组，精确映射到同样 1–3 range 的
canonical source_refs；schema-only citation repair 支持 staged 形式，模型私有
stage 字段不能绕过工具身份路由。两边额外采用相同的 Primary 声明依赖证据：
caller-context verified 必须实际 read/quote 已在 packet scope 中的线程 helper，
包含 copy_context 与 ctx.run。此门槛更严，但仍不把引用自动当语义正确；缺证据
可 uncertain/escalate，不自动 READ 或编辑，不扩大 scope。9 项离线安全检查通过。

deadline fixture v13 准备遇到目标项目 Ruff ASYNC240（async test 内的 Path.resolve），
未调模型，保留不完整目录、原 probe/driver 与 failure.json。路径归属断言移到
同步 pytest fixture，既不删断言也不屏蔽 lint；新 v14 正例 **20 passed**，负例
**18 passed / 2 failed**（普通 mapping 与额外 timer），Ruff 及正例 Pyright 均
通过。原十九项测试 hash 未变。已准备 fresh C/R driver，模型尚未调用。

range-4 注册前新增 small-risk omission 负例实际复现依赖门槛绕过：可选
contract_review 未提交时，旧原型只检查已有 entries。修复为 pass 必须具有
每个声明 dependency contract 的 verified entry，并在 staged final 对选中
存档 entries 重新校验。缺证据的 provisional assessment 不得写入 archive。
历史 dependency-small-negative-1.xml 保留。11 项针对性检查通过；完整
**946 tests + 115 subtests passed**（current-full-range-dependency-2.xml）。
range-4 八臂及代码/config/source hashes 已前瞻冻结，开始串行 Reviewer 对照；
全局 config hash 未变，Coordinator 仍关闭，weekly used 实测 26%，停止线 30%。

range-4 clean control-1 failed（210.468s）；candidate clean-1 pass（105.515s）
零协议错误，实际引用 copy_context/ctx.run 并正确区分 direct async final value。
Primary 仍记录其对 returned completion context 隔离的一句过宽表述，不接受扩展
保证。candidate clean-2 escalate（82.359s）却未读 dependency，错误提议在
registry 重复 ContextVar capture，标 false_positive_clean_escalation。
hidden candidate-1 rework（158s）：真识别 inner/outer 双 timeout，但错误声称
单次 await async invocation 会消费其 final Future，且漏掉普通 mapping 的
__await__=None，记 partial_detection_with_false_positive_and_missed_defect。
所有逐臂 Primary 判定另存，既不重写旧 Coder acceptance，也不推广此候选。

准备 investigation-5：依赖调查必须在相关 assessment（包括 uncertain/violated）
或终报前完成；每个声明契约的条目无论 status 都须引用实际 dependency range，
解释必须同时考虑 application/library source。提示包含 pending read 导航，不
注入 source、不自动 READ、不自动 verified、不改原 final gates/budget；读后
uncertain/escalate 仍合法。6 项新安全测试通过，完整回归开始，尚未调用此候选。
fresh v14 driver 改用相同两种 prospective Reviewer，并在两边声明依赖证据；
离线准备检查覆盖新 run identity、原源码 hash、只读 critical test scope、独立
basetemp、检查命令及不可覆盖历史。首轮 test 错写 scope.write 的失败保留，
改为实际 modify/create 字段后通过；该 fresh 模型实验未注册/未执行。

range-4 hidden control-1 failed（137.516s），两次超过 20 行 citation、两次
漏 dependency citation；5/8 实测、3 未执行，primary-assessment-1.json 明确
do_not_promote。继续 investigation-5，不重播同一失败，也不将 cohort 收尾
当授权迭代结束。新调查门完整回归 **953 tests + 115 subtests passed**；
八臂、代码及输入 hashes 注册后，开始实际 clean candidate-1。

investigation-5 clean candidate-1 pass（90.422s），Primary 核查五条原契约解释
正确；hidden candidate-1 failed（152.547s），其未接受 provisional 条目仍将
两个相同 timeout 数值解释成共享单一 deadline，并漏 ordinary mapping；不能
把失败关闭算成功检出。clean candidate-2 failed（138.25s），引用超过 20 行
与漏 dependency 引用仍复发。clean control-1 failed（116.235s）；后续基线
负例进行中。依赖证据门未解决全部语义问题，不推广。

准备 catalog-staged-6：实际 READ 后生成 opaque evidence IDs（连续实际可见
最多 20 行、1–3 段），选择 ID 机械映射到 canonical ranges。不让模型计算
跨度，不自动扩大读取、裁剪非法引用、修改 status/finding 或接受语义。
混合/旧引用字段拒绝，未知/重复 ID、缺读及 source drift 拒绝；8 项离线
测试通过，完整回归进行中。两边用相同最新 runtime-16 和 dependency 调查门，
八臂及 hash 前瞻注册；仅模型端 citation mechanics 改进，不宣称负例已通过。

catalog-staged-6 完整回归 **961 tests + 115 subtests passed**；candidate 两个
clean re-review 均有效（114.531s / 104.047s）。hidden candidate-1 rework
（144.062s）真识别重复 timer，无 false direct-async defect，但 resolved-output
仍错误 verified，漏普通 mapping；只算 partial negative detection，不扩大放行。

fresh v14 的四臂原始源码/20 项保护测试/配置/packet/driver hashes 前瞻冻结；
两边启用相同 dependency investigation、evidence IDs 和实际 approved execution，
只比较 monolithic 与 staged report。先实际 candidate-1、control-1、candidate-2，
control-2 进行中，不声称随机试验或避免顺序效应。候选两次 Coder ready
（36.312s / 32.891s），独立 Reviewer pass（127.828s / 141.985s），每次实际
重跑 **20 tests / 0 failure / 0 error / 0 skip** 及三项静态检查。Primary 两次
完整源文件/diff review，额外公共 Native invoke/stream + 原 Native 回归各
**6 passed**，不可变 accept 已记录。只是这两个 frozen atomic units 验收，
不是整个候选、未知算法或 Coordinator 放行。control-1 Coder ready（26.844s），
Reviewer failed（120.531s），缺读 protected test 与审批执行门未满足，失败保留。

新 Primary-only public caller probe 实际验证工厂一次 off-thread 调用、一次
caller-loop completion、ToolResult 到 ToolResultContent 及 JSON round-trip，
invoke/stream 均覆盖。此探针在模型运行之后补充，不谎称预注册保护测试；
原始无 factory 支持源码 **2 failed**（真实未完成 coroutine），正确候选均通过。
从兄弟仓库只读复制 test_native.py，原/副本 hash 一致，4 项原回归通过；
未执行数据库相关 integration suite。首个 probe Ruff import 排序问题保留后
修正；不改保护测试、模型或全局 config，不宣称新 Explorer/Coordinator credit。

fresh v14 四臂现已完成：control-2 Coder ready（30.469s），Reviewer failed
（96.640s），先出现 diff/source line 混用，随后缺少实际 approved checks 与
protected-test READ。两个 control 的 Primary 不可变 replan 已记录；不能把
Reviewer 失败算作 Coder 失败，也不能据两次候选通过作普遍稳定性承诺。

protocol-reference-7 前瞻注册四个 Reviewer-only synthetic controls：两个
clean、两个只有 ordinary mapping 缺陷的 hidden，不再让真实 timer 缺陷掩盖
mapping 漏报。旧 eighteen-test suite、三项配置检查真实执行通过；单独 held-out
plain-result assertion 对 clean 通过、hidden 失败，绝不进入模型 read scope。
canonical archive 明确 synthetic_benchmark_archive / coder_invoked:false，
不计 Coder、Explorer、Coordinator 或整链成功。CPython 3.12 inspect/Awaitable/
_check_methods 原文摘录以 hash 和冻结完整 upstream 副本检验；模型只获得
readonly capsule，不获得 upstream 树、答案或保护测试。actual-read catalog
增加 anchor-centered 最多 20 行窗口，只从实际展示的行生成，不信任 line hint，
不扩大 read ledger、不判定语义；三项安全检查通过。重复 source READ 时原
runtime 可能显示真实 bounded protected-test prefetch，测试明确区分它与编造
证据；不把此前“adapter 不自动读 dependency”扩大成整个 runtime 从不 prefetch。
独立 preparation safety test 实际预检两种 archive 和所有验证结果，并确认
scope、无 upstream 暴露与 immutable inputs 均正确；后续结果另行记录。

protocol-reference-7 四臂完成：hidden-1 rework（196s）为错误 direct async
二次消费报告，漏真正 mapping；hidden-2 escalate（161.219s）对 hasattr 的
有效性产生部分合理怀疑，但无 bounded defect finding，并仍对现有 identity
语义缺证据。两个 clean 都 failed（92.828s / 173.719s）：缺 dependency 的
第二段 anchor 引用，第二次还重放已归档 assessment。有效 clean 0/2、完整
hidden 检出 0/2，四份 Primary adjudication 与 do_not_promote assessment 留存。
标准库原文可用不等于模型正确使用；不推广，不降低原验收要求。

test-consistency-8 是新冻结诊断：相关 provisional claim 前必须实际读取
Primary 指定 protected focused test 的完整 bounded 文件（最多 200 行），
不能仅读首行、把未读标读或在 uncertain/violated 时绕过。所有 final gates、
source SHA、独立判断及原预算保持；缺读返回合法 action，不自动判真。
依赖 citation 导航列出实际 read handles 的 anchor coverage，仍由模型选择
最多三段 application/dependency evidence，不代填、不裁剪、不修改 finding。
两项合并诊断，不做单轴因果归因。3 项门槛/导航安全检查及 2 项实际 prepared
archive 检查通过；完整回归 **970 tests + 115 subtests passed**。
模型和全局 config hash 未变，只驻留 Muse；新四臂已前瞻注册并预检，开始
hidden-1 / clean-1，尚不能作本候选的成功结论。全历史 audit 51 roots / 42
canonical Coder runs 与兄弟仓库 protected source hashes 均通过。

test-consistency-8 两臂实测 failed（hidden 48.953s / clean 76.734s）：各四次
在未读指定 protected test 时直接 assessment，即使给出合法 READ action
仍重复提交。2/4 executed、2 not executed；不会为凑次数重播相同失败。
不可变 do_not_promote 留存；取证门安全但仅提示未能收敛动作选择。

investigation-phase-9 保留该门及所有模型/采样/budget，增加 feasible native
tool schema：取证未完成不暴露 ASSESS_CONTRACT / REPORT，完成后仅给出
未归档 obligation IDs 的 enum；原 guard/citation/validation 仍检查实际调用，
并不信任 schema compliance。合法 rework/escalate 不被转换成 pass，不自动
read、不修改模型观点。导航补齐超过 100 行文件的后续窗口，避免重复前缀；
actual-read/source drift、不可修改输入 schema、状态选择及最终报告保留三项
安全测试通过。四臂独立快照/真实十八测试/三项检查/隐藏 oracle 前瞻冻结，
开始首对实际实验，weekly used 实测 28%，停止线继续 30%。

investigation-phase-9 首对完成：clean pass（150.031s），五项语义说明正确、
zero protocol error，实际先读完两个保护测试与两个依赖；hidden failed
（123.625s）亦 zero protocol error，但最终 assembled request estimated input
19813 > available 19456，被 client 本地拒绝、没有 HTTP 400。此确定性诊断
来自 wrappers 在 core 历史裁剪后继续加 state/schema；并非 LM Studio 请求
容量改变。负例 provisional 仍误把 hasattr 当完整 awaitability，未算检出。
两份逐臂判定、2/4 executed / 2 not executed 的 do_not_promote 保存。

wire-budget-10 在所有 prompt/schema adapters 之后、实际 client 之前预算
完整请求；保留 canonical contract、所有当前 controller state 和最新五轮
action/observation，必要时仅裁掉更旧的 pairs。canonical archive、read hashes、
引用 gate 不变；irreducible 仍由原 preflight fail closed，绝不扩大 context/output。
若启用原 context_recovery 则更新实际保留的 active context index，不伪造读取。
三项安全测试（schema 预算、不可约拒绝、保留近期证据及无输入修改）通过；
新四臂前瞻注册/验证，开始 hidden-1，尚无本候选的资格结论。
phase wrapper 另加异常时 tools/client restoration 与不改写模型响应的检查，
4 passed；初次 import-order lint 问题修正后 Ruff format/check 通过。此前完整
**973 tests + 115 subtests passed** 尚不含这一新增 wrapper test 与 wire tests。

wire-budget-10 首对完成：hidden pass（169.844s）是明确 false pass，仍将
hasattr 与真正 awaitability 混同；clean pass（122.5s）五项说明正确，保留
2 protocol errors。2/4 executed、2 not executed，逐臂 verdict 与
do_not_promote 存档。该负例本身没有 assembled_wire_context_trim event，
不谎称重现并修复相同 oversize request；预算分支另有离线安全证据。

boundary-analogy-11 仅增加一个冻结、实际 Python 执行的通用 Sized 类比：
__len__ 属性存在与 Sized protocol membership 在 explicit opt-out 时不同。
不含 ToolRegistry、__await__、inspect.isawaitable、PlainMapping 或目标补丁，
说明明确“类比不是当前缺陷证据”，必须比较实际 application/dependency
接受和拒绝分支。JSON snippet 与独立 .py 的 AST 一致、四个 observed booleans
实测匹配；不执行模型生成代码。首次临时 test 使用 exec 被 Ruff S102 拒绝，
保留日志后改为导入冻结 module；Ruff 和 fidelity test 通过。四臂输入/代码/
example hashes 前瞻注册，真实 blind suite/三项检查/oracle 预检完成，开始
hidden-1 / clean-1；仍不能做模型无关或 Coordinator 资格结论。

boundary-analogy-11 clean pass（107.891s）语义正确、zero protocol error；
hidden failed（126.047s）虽已正确记录 __await__=None 的 provisional 推理，
仍未终报，不能算有效检出。查明 wire adapter 自身安装顺序错误：first-installed
runtime wrapper 的 client wrapper 实际先执行，后续仍加 prompt/schema。
原冻结代码与错误注释不重写，新 assembled-12 把预算 wrapper 最后安装，使
其在真正 client call 链上最后执行。离线组合测试实际跑两个 wrapper 顺序，
旧顺序超限、新顺序裁剪后合格；主入口 AST 检查防止顺序回归。第一次测试
synthetic schema 体积未真正超限的失败留存，校准到超限后 **2 passed**，
不改真实预算。此前完整 **978 tests + 115 subtests passed**。

assembled-12 首个 hidden 完成 escalate（122.687s）：final high finding
awaitable-detect-protocol-mismatch 在 registry.py:100，准确指出 hasattr 接受
__await__=None，而实际 read CPython _check_methods 拒绝该 opt-out，建议移除
裸属性存在检测。Primary 对照 held-out mapping assertion 核查有效；无 false
direct async finding。另三项契约过度 uncertain，保留质量/效率 caveat，建议
替代谓词不直接作为合格补丁采纳。2 protocol errors 保留；只算这一个
synthetic hidden 的有效检出，不算 Coder、整链、Coordinator 或完整 matrix。
四臂全部输入先冻结；余下两个 clean 和第二个 hidden 开始串行执行。

assembled-12 四臂完成：clean-1 failed（211.469s），caller-context 引用真实
helper 却错误认为 application 应内联 helper internals，先 uncertain 后两次
请求 pass，被 verified dependency gate 正确拒绝；不是 archive citation loss。
clean-2 pass（197.937s）五项解释正确、1 error；hidden-2 false pass
（113.954s），未应用显式 opt-out 拒绝分支。有效 clean 1/2、hidden 1/2，
全部逐臂判定与 do_not_promote 存档。full regression **980 tests + 115 subtests
passed**，不据部分语义进展宣布稳定。

explicit-boundary-14 将已知 plain mapping opt-out 写进 public required_behavior
及稳定 acceptance scenario，强调原对象、一次调用、成功且无 spurious error；
不规定具体 predicate/patch。此后只算 contract-guided qualification，不能计
blind/未见边界发现。首对 hidden failed（63.219s）为反复漏 dependency 第二段
citation，不算缺陷检出；clean pass（145.641s）待完整逐项判定。四臂冻结，
未执行臂保留，不为凑次数重复同一机械失败。fresh-13 新真实单元准备检查
通过，原 v14 source、二十 protected tests、三项 checks、high 风险与实际
Reviewer approved execution 均保留；模型尚未执行，无 fresh Coder credit。

citation-bundle-15 改为模型选择一个 citation_bundle_id：每个 bundle 是 1–3
个实际 read handles，包含 changed implementation，并按声明规则覆盖所有
dependency anchors。source window 每段仍最多 20 行，不能跨未读 gap；scope/
SHA/原 canonical citation gates 继续检查。status/explanation/findings 不变，
无自动 verified/Source READ/补丁。每个 bundle 写只含引用 metadata 的独立
不可变 record；未知/错 contract/mixed fields 拒绝，不能把引用合法当语义
正确。未读 source 时不暴露带空 enum 的 assessment schema。transport-only
catalog 提示移除已由 runtime 验证的 hash 重复，但底层 hash guard 不变。
四项安全检查通过（缺 source/dependency、陈旧 Source、三种状态及 finding
不改写、坏 bundle 拒绝）；Ruff pairwise lint 问题修正后检查通过。新四臂
前瞻冻结/预检，开始实际 hidden-1，仍不进入产品默认配置。

citation-bundle-15 四臂完成：hidden-1 rework 192.593s、clean-1 pass
125.625s、clean-2 escalate 112.250s、hidden-2 rework 134.453s。有效缺陷
检出 2/2、正确实现 verdict 1/2；clean-1 的取消传播解释仍错（实际是
CancelledError 属于 BaseException，绕过 except Exception），因此严格
五项因果审查 0/2。clean-2 已读 exact inspect/ABC 拒绝分支，却仍误报
正确 predicate 不确定；本轮实际触发 wire trimming（移除八条旧消息）。
引用 handles 合法并不等于原证据持续可见或推理正确。逐臂判定及
do_not_promote 记录保留；full regression 985 tests + 115 subtests passed。

retained-evidence-17 前瞻冻结四臂：将实现、两份 protected tests、两份
真实 CPython reference 的五个 bounded reads 放入不会被裁掉的初始输入。
实际提供约 11.5–11.7K 字符，仍受原 aggregate 16K 字符上限、最多六段/
每段 160 行限制；范围、禁读目录、reparse、源码版本检查沿用原 runtime。
默认关闭；九项安全测试通过。它是框架提供的真实证据，不计模型自主
READ/navigation 成功，不提供期望 verdict 或 target patch，也不提升模型
context/turn/error budget。不把 synthetic archive 当真实 Coder 或 Coordinator
链，本轮正在执行；产品默认配置仍保持原样。

retained-evidence-17 四臂全部因本地 input_too_large 预检失败（111.047/
93.375/118.359/94.641s）；未发送超限请求，非服务 HTTP 400，也不计有效
判定。固定证据加最近五轮交互仍过大。新三轮历史窗口保留全部初始证据/
当前 controller state，不能裁掉来源或降低引用约束；两项窗口测试通过，
combined safety 15 passed。cohort-19 准备后发现 adapter import-order lint
失败，冻结源不改写且不启动模型；cohort-20 使用新 lint-clean adapter，
同样语义前瞻冻结，开始 hidden-1。最新 full regression 995 tests + 115
subtests passed（随后新增两项窗口测试另行通过，不能虚报 full 997）。
历史 audit 51 roots/42 canonical runs 通过，兄弟仓库源码、protected tests
及 global config hash 均未改变。

cohort-20 首三臂：hidden-1 rework 106.922s，clean-1 pass 103.141s，
clean-2 pass 144.938s，均零协议错误。两条 clean 的五项因果解释已核对：
正确识别 opt-out、单次 invocation 与 final identity、单 outer deadline、
CancelledError 的 BaseException 继承关系，以及真实 to_thread helper 的
copy_context/ctx.run。仍待 hidden-2，不能将部分矩阵作为稳定放行。
最新 full regression **997 tests + 115 subtests passed**；随后新增 fresh
profile 准备参数另测 3 passed。fresh-retained-18 两个原始源码真实单元
前瞻冻结，保留二十 protected tests、三项 checks、high 风险和实际
Reviewer approved execution，未启动 Coder。不降低 canonical handoff、
Source SHA/read/scope/citation gates，也不预填 verdict/target patch。

cohort-20 hidden-2 rework 159.719s、零 error；有效 clean 2/2、有效 hidden
2/2，全部逐臂分开判定。然而 hidden-2 的修复建议写了不存在的
asyncio.isawaitable（真实 reference 定义 inspect.isawaitable）；因此建议
不可直接采纳，不能宣称全部报告 claim 正确。新增 canonical synthetic
assessment 只允许进入真实链诊断，不是产品推广/Coordinator 放行。

fresh-retained-18 candidate-1：Coder ready_for_review 42.797s，原二十测试
及三项检查通过；真实 Reviewer 88.297s 因本地 input_too_large 失败。
真实 handoff 初始输入约 38K 字符，不能用 synthetic 成功代替真实链。
Primary 全量 source/diff 检查和新增 Native caller 六项 probes 通过，但
新 generator-coroutine probe 失败：types.coroutine 产生合法 awaitable，
无 __await__ 属性，手写判定漏掉它而返回未消费的 generator。标准协议
判定的 control 通过。canonical review.json 记录 rework，不将 Reviewer
infrastructure failure 当 Coder 失败；Coder 的新边界缺陷有独立真实失败
证据。旧二十测试不能证明完整的合法 awaitable 支持。

fresh-generator-21 保留 v14 原始源码/全部二十测试，并新增只读 generator
边界测试、公开描述该已有契约的合法输入；不给 predicate/target patch。
新测试可独立重放：portable preflight positive 21/21，negative 20/21，
零 error/skip，source-root assertion 通过。原历史和未执行 candidate-2
仍保留。新的历史裁剪允许退至最近一个 action/observation exchange，
保留初始实际 source/契约/current state，仍由原 preflight fail-closed；
三项窗口安全检查通过。新两条真实单元前瞻冻结，开始 candidate-1，
仍要求真实二十一测试/三项 checks、canonical handoff 和独立 approved
Reviewer execution。没有模型更换、turn/context/error 预算扩大或产品默认
升级；建议中 nonexistent API 问题仍保留，不能自动拿报告建议当补丁。

generator-21 candidate-1 初始失败 39.922s；a2 窄化继承修复只删 duplicate
return，仍失败，canonical rework 分别保留。candidate-2 二十一测试全过，
但 Primary-owned readonly 新夹具违反 target Ruff（I001/ASYNC240），记录
replan 而非 Coder semantic quality failure。后续 v2 夹具把路径检查移动到
同步 fixture；checked-23 实际目录预检仍检出 I001，零模型调用。v3 按目标
项目 first-party import 分类修正，verified-24 两条预检全部三 checks 通过；
portable positive 21/21，negative 20/21。旧保护夹具/失败不改写。

verified-24 candidate-1 Coder failed 28.828s（非法 async yield from，仍 bare
hasattr），canonical rework；candidate-2 Coder ready 25.500s，二十一测试及
checks 通过，但真实 Reviewer 71.078s 因 input_too_large 失败，canonical
replan。v5 presentation 只压缩 OBSERVATION 中与初始实际 source 逐字一致
的重复 canonical/source_quote，保留初始全文、source refs/hashes、模型
status/evidence/findings 及原始 canonical artifacts；非匹配/未显示/assistant
claim 不压缩。两项安全检查通过。新 readonly quote-d1 诊断 pass 156.062s，
实际批准执行四 checks/actions 完成；这是既有真实 Coder archive 的诊断，
不得将旧 replan 改成 accept 或计为 fresh chain。

guided-26 是 navigation + 已执行的 unrelated Sized analogy，而非 target
patch。candidate-1 Coder blocked 44.250s：报告原因是 identical replacement，
非有证据的 contract revision；实际代码破坏 off-thread 且有错误 flags，
不能算有效契约阻塞/通过。candidate-2 Coder ready 36.625s，但 Reviewer
208.421s turn limit：先提交 pass 才补 required approved execution，额外
回合耗尽。最新完整 regression **1001 tests + 115 subtests passed**。

execution-d1 把 required approved checks 放到 assessment 前，未自动执行；
但与旧 report-only nudge 组合产生空 native tools，35.078s 实际 HTTP 400
（required tool choice without tools）。v2 从原 trusted native schemas 仅
恢复 pending approved commands/ids，不恢复任意执行或编辑；无可用 schema
本地 fail-closed。失败实际执行释放 rejection/escalation 阶段，原 pass gates
仍拒绝失败结果。三项初版 + 两项组合安全检查通过。execution-d2 readonly
诊断 pass 216.172s，第 13 回合有效最终 REPORT，实际批准检查执行完成；
独立旧失败保留，没有回填 Primary 接受。

evidence-28 新鲜真实单元把 Coder generic analogy 替换为其 scope 内、带
真实 SHA/行号的 readonly CPython source evidence；不是目标实现/patch，也
不计模型自主 read。使用 v7 Reviewer 阶段控制。两条原始源码/二十一测试
及 target-directory static preflight 前瞻冻结，开始 candidate-1。这是组合
guided profile，不是 factorial causal test 或 unguided baseline。模型、单模型
驻留、context/turn/error budget、protected tests 和全部旧档案保持不变。

evidence-28 最终停止点：实际 weekly used **30%**，达到用户上限，停止
新增模型/测试迭代。candidate-1 Coder ready 48.094s，二十一测试及三 checks
通过；真实 Reviewer pass 230.657s，实际二十一测试/三 checks、零 protocol
error。Primary 全部实际文件/diff 审查及额外 Native caller 六测试通过。
但 Reviewer failure-cancellation 因果解释仍错：实际 CancelledError 属于
BaseException，绕过 except Exception；不是 ToolTimeoutError 分支保证它
不被包装。故源码功能正确仍记录 canonical replan，不作严格 Reviewer
qualification 或产品接受。candidate-2 Coder failed 38.891s，Reviewer 未启动；
原始失败保留，触及上限后不进一步诊断/运行。功能链 1/2，严格 Reviewer
因果质量 0/1，未稳定放行。完整 regression **1006 tests + 115 subtests
passed**。停止索引为 evidence-28/quota-stop-30-1.json。产品默认配置及
Coordinator 开关未改、兄弟仓库只读、无 commit/push。

后续须先获新的 usage 授权：补充真实 exception hierarchy 依赖证据，独立
检查 candidate-2 的失败，再以前瞻冻结的新单元复测；不要把已结束的
replan/失败改写成接受。通过完整真实链和负例后，仍需可移植 opt-in
产品封装与受控 Coordinator 集成，不能直接将 benchmark adapters 当
产品默认或以 synthetic/diagnostic pass 代替正式放行。
