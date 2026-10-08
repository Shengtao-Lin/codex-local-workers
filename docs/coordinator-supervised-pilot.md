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
