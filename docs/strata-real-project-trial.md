# Strata受监督版本：三项真实源码试用

最新完成结论：用户授权先修复后执行；当前环境经7组count-only校准和4负控通过，
只更新新隔离副本的3个源码指纹，原合同/模型/runtime/预算/验收不变。三题**3/3独立接受**，
共29请求/556.830秒；tags首稿失败后自主修复保留，0Primary代写/语义指导。weekly最后观测25%/上限50%。
见[最终报告](../benchmarks/work/real-project-trial-20261101-1/calibrated-environment-v3/report.md)及该目录decision.json、metrics.checked.json。
原包和修复前环境阻塞全部保留，无活动批次，不commit/push。下方“环境阻塞/等待开启”均为阶段历史。

最新执行补充：用户已授权三题live并将weekly上限更新为**50%**。开始/结束实际25%。
当前因外部Strata计数器源码3项指纹不符停止；unregister在模型前conflicted（0请求/0编辑），
tags/logging为NOT_RUN。原冻结输入/成绩保留，未改绑定绕过检查，无活动批次。
见[本批报告](../benchmarks/work/real-project-trial-20261101-1/report.md)及decision.json。
下方“等待开启/30%”是原准备阶段记录，已被本段和最新用户授权更新，不代表当前预算。

准备日期：2026-11-01。**仅离线准备，等待用户开启Strata；三题NOT_RUN**。
weekly used停止线30%，准备开始实际23%；后续以实际查询和最新用户更新为准。
固定批次`real-project-trial-20261101-1`，不是模型A/B或正式公共benchmark成绩。

## 目标与起点

观察同一受监督版本能否交付真实、有用的实现或调查，Primary是否仍需反复细化和纠错。
允许原额度内自主探索、自修；最终正确性和独立验收不降低。不要求一次做对。

- 候选`0.3.0-supervised.1`，原样task.34；runtime、生产默认、skill和权限不变。
- ZIP在`benchmarks/work/strata-supervised-v1-20261031-1/strata-supervised-v1.zip`，SHA256：
  `5cef7b3e28bb9d224d37292e29bac32e66ebcd26a5407a3236476037e985c381`。
  本批从该ZIP重新解包、逐项核对manifest并在三份独立工程中安装。
- 来源为兄弟仓库agent-runtime-kit，HEAD `bc3f59e4b9e03d5e16ae89223f66239f79c70a5b`，准备时干净。
  源码原字节复制；兄弟仓库和Strata安装保持只读。
- kit HEAD `96202471caf62f010921eec5c61c0dd0fcbd9731`及既有改动hash已保存。
  保留全部历史，不commit/push。本轮只新增准备材料，在当前计划入口追加本批状态。
- 每份工程含完整Python源码，保持真实导入；Worker只读合同授权的少量文件。
  隔离pyproject继承上游Ruff规则及严格Pyright，检查全部复制源码和本题测试。
  不复制.env或启动数据库/服务，不宣称这些切片等于原仓库全部集成测试。
- 复用已有Python/依赖，不安装依赖。保持iq3_s、单驻留、客户端65536上下文/12288输出。
  **未连接端点、未doctor、未核实实际驻留**；用户表示Strata未启动。

这里baseline指原始代码、原有检查和安装起点，**不是Primary-only配对用量基线**。
旧通过/HOLD/assisted原样保留，不能由本批计算精确云端节省百分比。

## 三题需求与验收

|顺序/ID|目标|Worker可写|独立验收|
|---|---|---|---|
|1 unregister|AgentRegistry新增移除注册：返回原对象、缺失与get同错误、其他注册不变、可重新注册、排序正确|registry.py和一个新补测文件|原2测试、完整静态检查、封存5项验收、fresh Reviewer、Primary全diff|
|2 tags|工具定义与注册/发现增加可选标签，JSON往返、精确筛选，保留调用/错误行为|tools/models.py、tools/registry.py和一个新补测文件|原4测试、完整静态检查、封存8项验收、fresh Reviewer、Primary全diff|
|3 logging|队列日志操作说明：上下文捕获/字段优先级、序列化/隐私边界、异常和依赖不确定性|无，只读logging.py及correlation.py|原3测试和静态基线、Primary持有8项行为探针、核对完整报告；无正式编码Reviewer|

前两题是新增真实功能，不是人为植入坏补丁。tags是两个源文件拥有同一合同的完整单元。
新tags字段有意加入序列化结果，其他字段/无标签调用保持；大小写、空串、空格按合同精确匹配。
验收包含实际定义的JSON往返、注册/发现与调用。unregister按注册键操作，descriptor后变不重命名注册项。
三题按public兼容/隐私边界登记high风险，Primary不只凭Reviewer或测试摘要接受。

源码不是新holdout：Registry/correlation曾用于旧调查，新功能目标和日志两模块综合问题未作为本题运行。
模型预训练暴露unknown。本批无skill，不在失败后换skill；不启用联网、operation、孩子或Coordinator。

## 已完成的离线准备

1. 三份工程安装相同ZIP，实际入口prepare预览全部通过，未apply/派工。
2. 原测试分别2/2、4/4、3/3；每份全部源码/现有测试的Ruff no-fix、format check、严格Pyright通过。
   实际导入来自隔离副本；检查前后输入hash不变。
3. 新功能验收在原起点分别5失败、8失败，原有检查仍绿色，能够识别尚未实现。
4. Primary在private副本准备小型可行解，原回归/静态及新增验收5/5、8/8通过。
   **这不是Worker成绩**；只验证批准范围内有可运行解。可行解不回写Worker起点、不提供给Worker。
5. 日志8项独立行为探针通过，留作审查依据，不转为运行中答案提示。
6. 上游源码/配置/Git状态不变；三份任务起点保持原字节，参考解和独立验收不在批准读范围。

保留所有命令、stdout/stderr、退出码和耗时；重叠回归不相加，三题均未调用模型。

- [registration](../benchmarks/work/real-project-trial-20261101-1/registration.json)
- [离线控制](../benchmarks/work/real-project-trial-20261101-1/offline-controls.json)
- [交接](../benchmarks/work/real-project-trial-20261101-1/handoff.md)
- [基线与已有改动](../benchmarks/work/real-project-trial-20261101-1/baseline/git-and-worktree.json)
- [任务输入索引](../benchmarks/work/real-project-trial-20261101-1/setup.json)

## 开启Strata后的固定执行

先核对实际weekly<30%、iq3_s唯一驻留/并发1、doctor ready、无活动writer和冻结hash。
tokenizer/harness变化不静默删除绑定：保留原登记，先决定是否需要另行校准。
依次unregister→tags→logging，各一个first，不并行writer；使用已安装入口和合同/config，
先prepare --apply再run，yield后等同一进程。不擅自启动服务、加载模型或修改安装。

编码用原task-rework-v1：首段16请求/4有效编辑/4完整写后检查/1800秒；
一次封存14请求/4编辑/900秒，仅限canonical资格满足的原合同返工。
fresh Reviewer每个实改版本至多10请求/900秒，最多两版本；整任务provider上限50请求。
首次检查与写后检查按现有宿主分账，首段失败不能借封存预算，不用新身份充值。

调查预选task-v1：共享10请求/12证据/16工具/900秒；首段4普通请求，原任务至多8普通请求，
另有有界协议报告恢复。最多一次原合同证据续作，仅确有未核实材料且状态符合时使用。
问题封存在sealed/logging-question.json；不对相同回答重复抽样直到PASS。Primary核对完整调查。

|结果|预定处置|
|---|---|
|完整正确|记录自主修复/失败，当前版本独立接受；不人为制造反馈|
|确认原合同缺陷且符合返工资格|最多一次绑定feedback；原结果保留，实改后完整检查/fresh Reviewer|
|首段失败、不具资格或低进展|记阻塞/耗尽和可复用成果；小缺口可Primary另副本补完并完整重验，标assisted|
|普通题失败|保留并继续其他独立题；NOT_RUN不是模型失败|
|核心有用但附加断言错|原报告HOLD，Primary纠正整合单列，不改成自主接受|
|两题连续需Primary重写主要实现|停止扩题，分析协作价值，不无限加题/预算|
|安全、输入漂移、错误/多模型驻留、weekly达30%|停止新派发，保存实际状态，不中途换候选|

固定三题结束后区分：独立完成、部分成果复用、合法返工、Primary补完和最终正确性。
全部顺利也只支持受监督使用，不放行通用推理、任意终端或Coordinator。

## Primary成本与发布分支

Primary准备已实际包含选题/合同、定位范围、检查映射、保护验收、私有可行解和离线控制。
这些不是“只审批计划”；一次性试验设计和日常重复合同/审查工作分开说明。
后续每题记录是否给语义/修法、定位缺失依赖、修代码/测试，还是只核对最终成果。
从canonical提取请求、编辑、自修、no-op/协议恢复、检查/Reviewer/总时间；加载单列。
无法可靠计量的Primary主动时间、分题云tokens写unknown，不凭weekly反推精确成本。

三题顺利、成果可靠可复用之后再决定发布；**本次不commit/push、不创建GitHub Release**。
如果Primary经常重做，先给结论，不为发布抹平失败。

未来“给Codex一个GitHub Release、自动设置本地、用户只开启Strata”的发布验收清单：

1. 固定tag、用户向ZIP与独立SHA256；不包含机器日志、私有答案或实验计划。
2. Codex在授权目标副本下载固定版本，核对校验值及manifest；继续拒绝覆盖旧.local-agents。
   保留现有规则/改动，升级不能静默覆盖。
3. 自动发现并核对本地Python/工程检查、Strata Node/harness/tokenizer路径和版本绑定。
   当前示例含本机绝对路径/hash，**尚无经过验证的跨机器全自动配置器**；复制示例、删hash或API可达不足以证明完成。
4. 合并短AGENTS指引，保留工程原规则，不整份覆盖旧LM Studio说明。Primary仍负责需求、风险、
   文件权限和实际工程验收，安装本身不授予任意权限。
5. 服务没开时停在“安装/离线检查完成，等待Strata”，不开服务/换模型；开启后doctor、单驻留、
   合同预览与一个有界smoke通过才称ready。

已有验证为本机干净安装、防覆盖、合同预览、完整实现/调查工作流；未验证远程新Release到另一工程
的一次完整自动配置、跨机器迁移和缺依赖处理。本批只准备清单，不混入安装平台开发或新能力组合。
