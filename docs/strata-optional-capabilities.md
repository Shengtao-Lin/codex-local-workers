# Strata 可选能力：受监督试用边界

当前不是全功能自动启用版。核心实现仍使用已冻结 C3；新能力逐项实验，必须显式选择入口及批准范围，Primary 保留最终验收。

## 已完成与执行中

- 核心实现：C3 `0.2.0-observed-version.3`，可信 Python 隔离任务，最多4个源码文件和2个补充测试；宿主检查后交 Primary。原有真实 pilot 与其他实验成绩分开保留。
- 只读调查：C1 `0.2.1-capabilities.1`，固定4个问题的源码结论4/4核实通过。可做批准文件内 read/search/report；不能执行测试、修改、联网、递归派工。
- 独立审查：同一C1固定12格完成，6/6缺陷检出、6/6正确放行。严重度不校准，附带描述有准确性缺口；只作为 Primary 的审查建议，不是接受权限。
- Skills：C2 固定4格完成，两条启用格实际加载正文；核心答案4/4正确，整份报告严格门槛3/4，收益混合且未证实。保留默认关闭的受监督试用，不自动注入所有任务。
- 官方文档：两份批准页面实际获取，原2格仍HOLD：一份答案过度概括，一份引用纠正耗尽预算。C5补精确引用反馈后，另1个已暴露排序诊断通过，不能冲掉旧失败或证明通用联网能力。只批准固定 docs.python.org 文档ID。
- Coordinator：未启用。其他角色通过不证明它能从计划生成可靠任务包。

## 实际接口

显式只读入口为安装包内 `.local-agents/strata-readonly.py`，分为 `prepare` 和 `run`。
请求 mode 为 `investigate` 或 `review`；配置必须显式开启实验只读模式。
准备过程将合同、源码/运行时/解释器及允许读取范围绑定到同一任务。
审查请求需要真实 preimages 与宿主检查回执，不接受 Coder 总结代替 diff。

模型工具只有 `kit_read`、`kit_search`、`kit_report`、`kit_block`。
仅在单任务批准相应能力时，另提供 `kit_skill` 或 `kit_document`。
有效引用须来自当前实际显示的行；结构合法不代表结论正确。
所有工具、协议恢复、HTTP请求均有持久预算，重启不充值。

调查上限8次请求，审查10次；各12次取证、16次工具、900秒，0次编辑/验证执行。
每次输出12288 token；计数器在65536上下文安全界限内进行请求预检。
保持 iq3_s 单驻留；记录中的本机实例上下文131072不等于所有请求都可使用全部窗口。

## 证据与成本

最新能力阶段计划为 `docs/strata-capability-expansion-plan.md`，各批结果保存于
`benchmarks/work/harness-convergence/strata-*-20261024-1/`，以各批 decision/handoff 为准。
未运行不是失败，离线通过不是 live 成功，模型报告 PASS 不是 Primary 独立接受。
目前云 token、Primary 主动时间和对照经济收益 unknown；不从 weekly 百分比推算节省。

生产默认配置、已发布 C3、兄弟仓库和 Strata 安装不作修改；不自动发布或 push。

本轮22个固定单元及1个独立诊断已结算，另2格预检替换保留NOT_RUN。
最后完整离线套件161项，措辞/引用反馈修正后35/36项受影响控制通过，不能相加。
统一交接见 `benchmarks/work/harness-convergence/strata-capabilities-stage-20261024-1/handoff.md`。
weekly used末次27%，未达50%上限；停在本轮固定阶段的明确结论，不声称全功能稳定版。
