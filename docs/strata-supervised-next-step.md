# Strata 当前推进计划

更新：2026-10-30。用户当前停止线为 weekly used **20%**，每次启动新live前读取
实际用量；旧计划中的15%/50%等不再是本轮停止线。单模型iq3_s驻留，兄弟仓库与
Strata安装只读；保留所有既有修改和历史，不commit/push，不改变生产默认。

目标保持为通用、受监督的子代理：Primary给目标、合同与权限，Worker自主调查、
实现、补测试并有界修复，fresh Reviewer后由Primary独立验收。普通错误允许恢复，
以可靠最终成果、错误接受控制及Primary重复工作量评价，不要求一次正确。

## 当前证据

| 项目 | 有效结论 | 记录 |
| --- | --- | --- |
| 已发布/推荐入口 | 新隔离编码试用显式选择task.34；整体通用版/调查门槛HOLD，无生产默认升级或自动扩大资格 | [短操作说明](strata-quickstart.md) |
| 当前实验执行构建 | task.34冻结；629项宿主控制、真实错误合同0调用拒绝、118文件安装/doctor/拒绝覆盖通过；模型侧行为未改 | [候选交接](../benchmarks/work/harness-convergence/strata-binding-preflight-20261030-1/handoff.md) |
| 调度真实切片 | 两个单元及模拟集成受限接受；真实PostgreSQL未测试 | [交接](../benchmarks/work/harness-convergence/strata-scheduler-clock-20261030-1/handoff.md) |
| 畸形工具调用 | 恢复后原第一格受限接受；491独立检查通过，数据集错误分类对照通过；旧NOT_RUN保留 | [恢复结果](../benchmarks/work/harness-convergence/strata-malformed-tool-call-20261030-1/decision-resumed.json) |
| 二进制trace解析与自编测试 | 单元接受、526独立检查通过；模型自修静态问题；完整输入特性因内部过滤不一致HOLD | [单元结果](../benchmarks/work/harness-convergence/strata-binary-trace-20261030-1/handoff.md) |
| 序列化内部trace过滤 | 单元和输入特性受限接受；635独立检查通过，两个适配器/四种表示的模拟集成通过 | [decision](../benchmarks/work/harness-convergence/strata-serialized-internal-20261030-1/decision.json) |
| Primary接受记录绑定 | task.33完整620项宿主控制通过，含13项针对性控制；118文件安装及拒绝覆盖通过。同版本完整入口已接受 | [交接](../benchmarks/work/harness-convergence/strata-primary-review-binding-20261030-1/handoff.md) |
| 实际非变异测试修复 | 固定一格受限接受；6请求/1编辑，fresh Reviewer6请求PASS，独立613项目检查通过且变异被检出，接受记录绑定真实报告 | [decision](../benchmarks/work/harness-convergence/strata-nonmutation-test-20261030-1/decision.json) |
| 工具定义快照隔离 | task.33标准入口新单元受限接受；10请求/2编辑，真实静态失败自修；559独立检查和三种provider的mock序列化核对通过，无Primary修法 | [decision](../benchmarks/work/harness-convergence/strata-tool-snapshot-20261030-1/decision.json) |
| 搜索覆盖提示 | 两臂都正确限定搜索范围，未观察到新提示优势；task.32不推进默认 | [A/B](../benchmarks/work/harness-convergence/strata-search-scope-ab-20261030-1/handoff.md) |
| 新源码回答诊断 | 两题诊断2/2受限接受，分别5/4请求、0纠错；Primary核对完整回答与引用，无正式Reviewer；不满足完整调查迁移门槛 | [decision](../benchmarks/work/harness-convergence/strata-source-answer-transfer-20261030-1/decision.json) |
| 同安装连续使用 | U1 Coder9请求/3编辑后配置检查通过；Primary写了绑定器不支持的类引用，prepare漏拦，Reviewer无法交付；U1 HOLD、U2 NOT_RUN | [decision](../benchmarks/work/harness-convergence/strata-sequential-use-20261030-1/decision.json) |
| 正确绑定后的连续使用 | 编码U1受限接受：7Coder/7Reviewer请求、3编辑、一次引用纠错，574独立检查及NativeAgent集成通过。同安装U2执行完成但原回答过度延伸HOLD；旧档案和预算未变 | [decision](../benchmarks/work/harness-convergence/strata-sequential-use-contract-corrected-20261030-1/decision.json) |

这些测试有大量重叠，数量不相加推断独立规模或成功率。实现、审查报告和特性
集成分别判断。Coordinator未参与，不能由Worker成绩推断其分解任务能力。

## 不得被后续通过掩盖的边界

- 有限超时原2/2接受已追加更正为1/2 HOLD；异常消息断言越界同时被Reviewer和
  当时的Primary漏掉。SSE独立CR额外断言的HOLD保持。
- 聚焦审查能识别异常文案越界，却未正确判定SSE明确排除范围的断言；不给它
  通用语义资格，也不为此加常驻角色或以重抽PASS放行。
- Reviewer曾把限定搜索说成唯一调用方；Primary必须核实完整调用方或明确缺口。
- 宿主检查/引用/哈希证明事实与版本，不证明完整语义。模型自写测试也是交付，
  Primary按风险审查断言依据；不能把与当前实现一致当作合同授权。
- 15%停止时的NOT_RUN、准备错误、外层GBK解码、私有测试同名和导入绑定错误等
  均保留，不能算Worker失败，亦不能隐去Primary准备成本。

## 本轮固定顺序和分支

1. 序列化内部trace已完成，接受只限登记特性；旧解析单元曾发现的集成HOLD不改写。
   保留全部源码、测试、真实请求和独立验收。不得把后续通过变成旧批次原本通过。
2. task.33离线回归及安装完成。旧task.31档案被task.33拒绝的原因是安装哈希不同，
   属于正确跨版本负控，不绕过、不重新绑定旧记录，不算正向资格。
   以新登记的test-repair-v1实际测试修复验证同版本完整入口；原预算/门槛不变。
   实际测试应检出调用方bytearray变异，生产源只读；fresh审查和Primary独立终验
   后才记录接受。准备时误将测试路径绑定为生产实现引用的错误已原样归档，
   仅修正未注册packet，没有改变候选。若错误拒绝合法同版本流程，只按证据窄修。
3. 以上成立后，整理一个可直接审查的受监督候选及安装说明，明确支持能力、
   未准入能力、固定预算、真实调用和一次返工路径；仍不发布或改生产默认。
   下一次新任务须验证完整行为单元及跨单元不变量，优先复用已有工程检查，
   降低逐任务参考实现/专用runner的准备负担；不因普通成功扩成大benchmark。
   此项已形成task.33试用zip及配套manifest，解包哈希核对通过，尚未发布。
4. 编码与调查分别判断。保持task.33/普通只读协议不变，完成已冻结的ownership、
   http-error两个新源码问题；无新权限、技能或提示修订。按预登记事实清单与实际
   原文独立核对，普通错误继续第二格，安全/漂移/驻留或usage停止新格。失败不
   反复问到正确；通过也只是本批诊断，不满足完整调查迁移门槛，不补写通用资格。
5. 最新用户要求继续趋近可用版。同安装链已暴露一个确定性Primary输入/prepare缺口。
   保留原HOLD；只做task.34类引用前置拒绝，先9条负控和宿主回归，不给类声明新增
   PASS能力。控制通过后，正确绑定的已暴露需求以新registration复测；旧账本不充值、
   原Reviewer不重抽、不把复测当盲迁移。之后再验证同安装后续任务与重复派发拒绝。

## 本阶段结论

继续推进后，task.34已整理成可使用的**有限受监督编码试用版**：配套zip、实际本机
配置/合同格式、短操作说明、安装/doctor和成果导出均核对。class引用的Primary输入
错误现可在模型前拒绝，原HOLD/未运行不改分。正确绑定后的代码单元接受，原预算
内自修，不由Primary代写。不是通用正式版或净云节约证明。

同安装实现→调查执行和去重/档案机制通过，但要求原调查回答全部准确的整体门槛
仍HOLD。调查中的正常完成/after hook过度延伸已用实际反例核实，Primary纠正整合
单列assisted；不能以代码通过掩盖调查问题，也不能因后续报告问题撤销正确代码。
这次不再为措辞问题追加提示/新角色或重抽答案。通用目标仍未完成。

此前四项完成时，task.33作为显式、隔离、受监督的试用候选：完整宿主控制和
安装通过，同版本实际测试修复及新源码单元均接受，后者在原预算内完成真实提案/
静态错误恢复；两个只读新问题也分别接受。zip和每批decision/handoff均已落盘。
冻结候选继续保持，不因后续题目不通过就来回改协议，也不把本阶段当通用正式发布。

下一步应使用该原样包承接一个真实需求，以现有工程检查为主并记录准备/协调/
终验工作，而不是继续为每个单元先写完整参考实现。超出已记录族先隔离；通用调查、
联网/脚本/递归组合、Coordinator分解及净云收益仍分别未证明，须沿原门槛登记验证。
普通模型语义错误先保留并确定是否在原合同内，允许的返工只用原封存预算；确认
机械故障才离线修复并另冻候选。不能用新成功覆盖旧HOLD或为成功而补刷。

权限、安全或合同重大变化需要用户决定。其余实现与可修复问题自主处理。
达到20%停止新工作并交接；执行中的批次保留真实终态，不将未运行标成失败。

## 计量与历史

记录本地请求、实改、协议恢复、检查/审查/独立验收、真实介入和耗时；Primary的
合同/测试/定位/语义反馈/代写分别注明。未量测的主动时间、云token、加载时间
写unknown。没有Primary-only配对和完整用量，不能报告净节省百分比。

设计职责见[架构](strata-architecture.md)；未完成的总体能力门槛见
[完整资格计划](strata-practical-readiness-plan.md)。
此前完整行动文档已逐字节归档并记录sha256：
[历史计划](history/strata-supervised-next-step-through-20261030-15pct.md)。
历史记录中的预算和“当前”是当时快照，当前用户指令及最新有效decision优先。
