# Strata受监督v1

版本：0.3.0-supervised.1；运行时仍为原样task.34。按当前新subagent设计，已达到受监督使用门槛。
Primary给目标/边界，Strata自主调查、实现、补测、自修；Primary核对完整产物后接受、合法返工、补完或replan。
这里的稳定是这条有界协作与验收路径可复核，不是保证每个Worker报告首次正确。
通用自主调查、Coordinator、任意脚本和更深递归没有因此放行；历史成绩不变。

本地发行物：[strata-supervised-v1.zip](../benchmarks/work/strata-supervised-v1-20261031-1/strata-supervised-v1.zip)。
解压后从README.md开始；包含用户向的AGENTS.strata.md、配置profile、技能与反馈工具。
旧包保留，生产默认未改变，不包含实验计划、私有验收答案或完整历史。

## 完成证据

|设计要求|实际证据|
|---|---|
|自主实现与本地修复|[ZIP编码完整链](../benchmarks/work/packaged-coding-20261031-1/report.md)：6请求/3编辑/2本地修复；13配置测试/严格Pyright/Ruff与fresh Reviewer；Primary18项独立验收，0代写|
|非纯编码与可选技能|[ZIP数据任务](../benchmarks/work/strata-portable-20261031-1/report.md)：实际加载包内数据skill，18行分组/缺失/汇总准确；3请求，无Primary提示|
|有界反馈与原任务连续性|[两题续作](../benchmarks/work/evidence-continuation-20261031-1/report.md)：首段1/2，固定一次核实后2/2；原HOLD保留，8累计请求，无权限/预算重置|
|部分成果利用与Primary补完|[JSON任务](../benchmarks/work/subagent-handoff-pilot-20261031-1/report.md)：原稿takeover，Primary独立副本2行类型补完、35项终验；最终assisted，未回填自主成绩|
|能力激活与共享子账|[当前能力复核](../benchmarks/work/capability-refresh-20261031-1/report.md)：真实公开web+固定operation正确；真实只读孩子计入父账；父报告错误被拒绝，整体报告1/2，不当作全语义放行|
|权限与方法分层|显式approved_skills与能力合同；10权限正负控；不会由skill、网页或孩子扩大权限|
|可携带安装与交付|[最终审计](../benchmarks/work/strata-supervised-v1-20261031-1/verification.json)：119原发布文件hash不变，完整ZIP核对，新安装/拒绝覆盖/真实合同预览/doctor通过；原RC另有4profile预览与create-only导出|
|支持工具可靠性|26反馈绑定+5包装控制，共31项及Ruff/format通过；旧结果不相加造总准确率|
|成本诚实与用户边界|实现和补测实际复用，无Primary代写的成功任务成立；净云节省、主动时间仍unknown。保持iq3_s单驻留、兄弟仓库/Strata安装只读、不commit/push|

## 使用时的必要边界

编码是可信Python仓库中的行为完整单元；继承实际工程检查，fresh Reviewer后仍由Primary终验。
调查是可复核的研究产物，不能把引用正确或父子一致当作推理正确。需要核实时按预选task-v1续作；
不能给旧独立调查临时切profile。小缺口可由Primary在保留原稿后补完并独立重验。

技能是Primary可选方法，目前只读入口支持，真实加载与收益分开。网络、固定操作、孩子按独立profile
和任务批准范围使用。web+写入、web+孩子、continuation+capabilities、任意生成脚本/深递归仍拒绝或未准入。
没有shell工具也不代表OS隔离：项目检查执行可信Python，使用宿主权限。

本版不需要增加角色或继续刷已暴露题。后续优先在实际任务中观察Primary准备/审查负担；
具体新故障保留证据后做窄修，新的权限或组合需要自己的准入，不把这个版本当通用正确性保证。
