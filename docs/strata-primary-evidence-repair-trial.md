# Primary 独立发现后交回 Worker：单次辅助修复

2026-10-28，用户授权自主推进；weekly23%/50%。批次
`benchmarks/work/harness-convergence/strata-primary-evidence-repair-20261028-1/`。
父批新任务0/1 HOLD及Reviewer误放完整保留，不充值/重开旧任务。

## 证据与窄问题

原awaitable任务Coder通过两次Pyright错误自修后全检查绿，Reviewer PASS，独立425项
也绿；但Primary在原合同“Python awaitable”下核实合法types.coroutine生成器没有被
解析，原因是Awaitable ABC成员关系窄于真正可等待性。相同项目外探针参考通过，
Worker失败。Primary最终拒绝，未发生错误终验接受。不能把这归因于harness应用器。

旧注册的8/2预留只授权canonical Reviewer必修finding，本次是Primary独立发现，
所以原任务闭合后不调用resume。改为独立且明确assisted的新任务：从相同失败草稿
出发，保留原合同和所有旧公开/保护测试，提供已观察失败形式、输出与原位置，没有
给替代算法、参考补丁或私有验收。新增两个只读公开回归明确该反例及原生async
不能递归展开的原要求；这是新增Primary语义证据/测试准备成本，不叫自主成功。

## 固定执行

产品task.19/模型/读写权限/编辑器/格式化/全检查/Reviewer不变。只使用已存在普通
无续作入口：16请求/4编辑/4完整写后检查/16证据/24工具/1800秒，freshReviewer
10请求/900秒，总26真实调用上限；无8/2、无额外审查或继续充值。
此前实际72+最大26=98≤保守累计108，weekly50优先。仅1格/1attempt，失败闭合。

先0provider确认保留草稿公开回归1失败1通过，参考独立427passed/61integration
deselected及项目静态检查全绿；安装/doctor/prepare通过后冻结。记录助手在最终
核账时误从state而非TaskLedger.limits读取字段的0模型错误，只补记录未重复检查。

需当前全部检查+freshReview+Primary完整源码/diff+独立427及项目外原合同探针均
通过才记assisted1/1。原私有测试不输入模型；没有新算法提示、代写/接管计划。
普通失败不改候选/门槛或重抽审查；安全/漂移/驻留/usage停止，未运行另列。
无论结果，不据此取消父批Reviewer误放、不授予自主/通用资格。若辅助也不能完成，
闭合当前诊断，不继续围绕这题堆提示；若完成，只证明这种Primary反馈粒度可恢复，
还需解决发现成本，不能据此声称净省usage。

所有历史和改动保留，兄弟仓库/Strata安装只读，单iq3_s驻留，不commit/push、
不改生产默认。记录真实调用/有效编辑/检查/no-op/协议/本地时间与Primary额外介入。

## 闭合结果

PASS_PRIMARY_SEMANTIC_ASSISTED_REPAIR_1_OF_1，Coder10请求/2有效修改/2完整写后
检查，freshReviewer5请求PASS，独立427passed/61integrationdeselected与原同一
边界探针通过。第一次有效修改后Pyright指出多余cast，Worker自行移除；另一次
编辑触及未读当前行被拒，模型补读后完成，0no-op/0协议恢复/1编辑恢复。15真实
provider/26，任务377.375秒；weekly终点23%/50%。Primary没有代写或追加live修法。
父批原语义失败和Reviewer误放不改，不能用这次assisted成功证明自主能力、原任务
续作预算或云成本收益。材料范围修复与语义/覆盖漏检已区分，产品候选不继续改动。
