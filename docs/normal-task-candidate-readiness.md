# 当前候选的正常任务验证：准入核对

日期：2026-10-19。用户要求继续能力边界验证，weekly used13%，停止线20%。
此记录为新的离线准备，不是旧批次重开或新的live授权，不修改生产配置/runtime。

## 后续批准与实现（覆盖下文准备时状态，不改旧成绩）

用户已批准逐项自主分析和窄优化，关键设计问题或weekly used20%停止。
本批 `normal-task-repeat-20261019-1` 按下述四格实施，实际起点weekly14%。
通过make_runtime显式proposal_rules参数及入口--preserve-existing-imports接入新守卫；
不使用全局替换/加载拦截/新增runtime子类。旧入口默认保留旧守卫。
改变的两个原实验文件先按原哈希保存到本批candidate-preimages，registration保留旧/新哈希映射；
旧批registration和成绩不改，重放旧版时需使用该归档原文件，不把原路径新哈希当成旧冻结版本。
下文“尚未接入/待确认”是此前准备状态，现以本段和新批registration/decision为准。

## 已确认的新问题

冻结 consolidated 候选的全部 registration pins 实测无漂移。
`harness_protocol.shape` 却拒绝任何 `ast.Import`，并要求所有非future的
`ImportFrom` 都属于仅含 Iterator/Sequence/cast 的新增导入白名单。
这把“原有导入必须保留”混成了“原有导入也必须属于新增权限”。

因此即使输入与输出完全相同，request_keys 的 `import hashlib` 和
single_content 的原模块导入也被拒绝。传入完整旧 IMPORT_CEILING 仍被拒绝。
`Consolidated.context()` 调用此守卫发生在模型请求之前；不把它算作模型质量失败。
这解释当前候选无法直接覆盖这两个正常任务，不追溯解释原SSE/Iterator的0/4：
原任务使用的导入在原白名单内，仍是有效失败。

## 最小离线原型

新增 `benchmarks/preserved_import_guard.py`，**尚未接入 Worker 入口**。
原 `harness_protocol.py`、`consolidated_harness.py`、`consolidated_entry.py` 不改。

原型把所有未批准更改的既有导入保留在 AST 比较骨架中，新增/删除的导入仍限原白名单；
目标体内的导入单独固定，不能借函数体可写而引入新导入。
签名、其他函数、常量、future导入、别名和未批准导入的相对结构仍固定。
12000字符及禁止新增检查抑制规则不变；不是shell权限、动态代码安全分析或OS隔离。

16项离线控制通过：两个真实起点的旧守卫拒绝、原型原样/参考修改接受，
以及新导入、别名、删除、局部导入、其他定义、签名、抑制和权限上限负控。
参考补丁仅用于离线准入检查，未给任何Worker；guard通过不是语义正确或完整链通过。
首次XML保留，最终格式整理后结果为 controls-v2.xml，重叠不相加。

## 提交确认的单一候选及条件批次

候选：仅接通“既有导入固定”的守卫；明确形成新候选，不声称是consolidated原样复跑。
接入必须是显式依赖参数/窄入口，不恢复全局替换、动态加载拦截、类变换或多层适配。
旧入口默认行为保持，先离线CLI检查：两个起点、脚本正控、scope负控、canonical交接、
陈旧证据拒绝；不得只凭本次纯函数16控制直接启动live。

拟固定四格：request_keys-1 → single_content-1 → single_content-2 → request_keys-2。
两项均已暴露，只有当前新候选的精确任务重复信用，不称新题迁移、不与历史2/2合并。
源码、合同、测试、私有验收沿用 unified-transfer-20261018-1 的冻结起点，不使用成功后源码。
实测起点分别234与9478字符，均低于原12000上限；后者整模块输出仍可能带来负担，
不因“单函数”称其简单，也不为此增加4096输出预算。

共同预算沿用当前12请求、3有效编辑/3写后完整检查、1起点检查、12次格式准备、
2协议恢复、2no-op停止、900秒；Reviewer16请求/4错误/4096输出/600秒。
Qwen与Muse保持原配置、上下文24576、单模型驻留；实际加载配置在live前核实。
无需Explorer定位（路径/符号已知），Coordinator不参与，Primary不提供具体算法或中途语义救场。

资格门槛：四格全部经原可信检查、fresh Reviewer及Primary独立完整链接受，
无安全/保护漂移/代写/语义辅助，才记精确任务受监督重复证据；不放行R4/R5或生产。
普通失败使资格HOLD但继续剩余固定格；安全/基础设施/保护漂移/20%预算到线停止。
未运行单列，不替换题、不补跑冲失败；Reviewer旧漏检单列，不以本次clean报告取消。
单格总外层2220秒，批次10800秒；记录加载/检查/本地请求和Primary介入，可测项才报告。

## 当前决定

`BLOCKED_CURRENT_CANDIDATE_APPLICABILITY`，不是模型失败或预算到线。
模型0调用，拟四格0运行，R4 HOLD/R5未准入。新live前集中确认以上候选和条件批次；
当前仅保存可逆原型及对照证据，不静默改变冻结候选或导入权限。
