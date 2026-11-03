# task.34 固定版本的三个实际源码任务

2026-10-30，批次 `strata-frozen-coding-pilot-20261030-1`。保持已提交的 task.34、
iq3_s、单驻留、原预算/审查/验收，不修改 runtime 或默认。停止线20% used，
本轮前后实际观测均17%；本阶段因固定批次完成而收尾。

这是三个在兄弟工程真实源码上设计的小需求，全部只修改隔离副本；不是上游issue
解决率或公开benchmark新成绩。前两项为新的具体需求；第三项取自已暴露的行为。
资格仅限这三个单元和此前已有受监督编码范围，不改旧成绩或通用门槛。

| 单元 | Coder请求/有效编辑事务 | fresh Reviewer请求 | Primary独立结果 |
| --- | --- | --- | --- |
| 确定性模型客户端reset接口 | 7 / 2 | 4 | 接受；564项工程测试、Ruff/Pyright、混合generate/stream及NativeAgent重放通过 |
| messages_input嵌套数据所有权 | 9 / 3 | 6 | 接受；558项工程测试、Ruff/Pyright、两个适配器的输入变异探针通过 |
| 工具失败路径hook测试 | 9 / 1 | 8 | 接受；557项工程测试、Ruff/Pyright；两个私有错误变体均被新测试检出 |

原始基线552 passed；各次均有72项真实数据库集成测试未运行。工程回归高度重叠，
这些数字不能相加当作独立测试规模。Worker分别编写12、6、5条新测试；Primary
检查了全部新增断言、真实diff及关键调用方，独立验收后记录有版本绑定的接受。

失败完整保留：reset的新测试含不合理的`assert cycle != 2`，模型根据真实失败删除
该断言并保留正确重放检查；这是自编测试修复，不是复杂生产缺陷诊断。输入所有权
任务先因缺少承诺的新测试文件被拦，再修复新测试中的Pyright错误。没有Primary
提供算法/修法或代写，没有动用返工预留、增加预算或重抽相同审查。

第三项源码只读，新测试对“异常后误触发after_tool”和“超时后误触发after_tool”
分别产生2和1条断言失败，收集错误为0；正确实现通过。该负控衡量测试敏感性，
不等于测了Reviewer对错误代码的检出率。三个最终审查输入均正确，不能据此
宣称未知缺陷检出或错误放行问题已经解决。

本地完整链合计43次模型请求，911.327秒（约15.2分钟），包含宿主检查及fresh
审查，不含准备、独立终验和Primary审查时间。从源码快照到metrics约21.3分钟，
更早的准备未计入。最大Coder输入29556/43120/28674 tokens，均在原65536客户端
边界内；12288是输出上限，不是实测输出量。未发生模型切换，加载时间未知。

Primary仍编写合同/独立探针、准备控制并逐项审查。本轮新建的可复用runner/变异
控制属于一次性实验成本，合同细化、选测试和语义终验属于反复发生的任务成本。
主动时间与云token未精确测量，没有Primary-only对照，不能声称净节省百分比。
weekly观测未跳变也不意味着本轮免费。

结论：已有证据支持使用**原样task.34进行有限受监督编码**，普通失败可在本地原
额度内闭环，不需要每次出错就改协议。当前没有证据要求新增harness候选。下一次
应承接实际待办的完整小需求，复用现有配置和检查，减少每题专用实验准备；不要把
这次的重准备方式变成正常用户流程。通用调查及旧完整回答门槛仍HOLD，Coordinator
和未测权限组合没有新增资格。

完整本地证据：[handoff](../benchmarks/work/harness-convergence/strata-frozen-coding-pilot-20261030-1/handoff.md)、
[registration](../benchmarks/work/harness-convergence/strata-frozen-coding-pilot-20261030-1/registration.json)、
[decision](../benchmarks/work/harness-convergence/strata-frozen-coding-pilot-20261030-1/decision.json)、
[metrics](../benchmarks/work/harness-convergence/strata-frozen-coding-pilot-20261030-1/metrics.json)。
接受成果已导出，未自动应用到兄弟工程；所有原始历史保留，本轮无commit/push。
