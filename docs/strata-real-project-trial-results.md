# 真实项目改动试用：task.10

2026-10-26。三项任务来自兄弟仓库实际工作树，不是toy仓库或重复HumanEval。
其中一项是已观察的协议兼容缺口，两项是Primary设计的新增功能需求，不冒称GitHub issue。
全部在本仓库隔离副本中执行，原仓库源码及既有改动未变。

## 冻结结果

| 真实任务 | 实际执行与结果 | 判定 |
|---|---|---|
| runtime-kit：SSE支持CR/LF/CRLF及跨chunk边界 | 10模型请求，914.500秒；精确替换目标失配，0有效编辑、0写后检查，未进Reviewer | Worker失败 |
| runtime-kit：AllOfGuardrail＋公共导出＋Hook集成 | 5Worker请求、一次有效变更，fresh Reviewer7请求；独立435passed、61integration deselected；完整链559.922秒 | 独立接受 |
| evaluation-harness：导出每scorer的score_count/min/max | 完整检查输入137文件超过准备器125限制；Worker0调用。原项目452passed，参考实现与独立测试通过 | 基础设施阻塞／NOT_RUN |

注册3项，实际模型执行2项，接受1项，Worker失败1项，基础设施未运行1项。
不能写成“1/3模型成功率”，也不能忽略未运行项声称整个批次通过。
本轮总体`HOLD_REAL_TASK_BATCH`，旧批次成绩不改写。

实际本地调用22次，报告输入483102、输出43782 tokens；两个完整执行过程合计
1474.422秒（约24.6分钟），不含全部准备、Primary终验、离线诊断及加载时间。
同一个iq3_s驻留、并发1，候选没有逐格修改；没有Primary运行中指导或接管生产实现。
本轮未单独评估Explorer或Coordinator，不由Coder成绩推断其能力。

## SSE到底失败在哪里

任务契约基于WHATWG允许的三类换行及空行交付规则，范围只是换行兼容，不是完整
EventSource实现。[官方规范](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream)

原始源码不支持lone CR，保护用例有3项失败。隔离参考实现能通过项目原回归、类型、
lint/format及独立验收，说明题目有合规解，不是把不可完成的合同给模型。

实际Worker首次两段替换都收到`target block was not found`，宿主返回当前文件hash和
源码位置。第二次整函数find文本只比真实源码少一个词：

```text
真实旧代码：Provider stream event exceeded the size limit
模型的find：Provider stream exceeded the size limit
```

版本引用正确，但精确文字不匹配，因此没有写入。这是已确认的编辑传输适配失败；
不能把0编辑解释为“已实现但测试不过”。最终报告仅给budget_exhausted、reason=null，
Primary需要再读归档才能定位，说明失败摘要也缺少直接可用的原因。

另外做了**辅助离线反事实**：在新的副本只修正find里的这个词，不改模型提议的新实现，
不调用模型、不回传结果、不重算成绩。新实现仍有2failed、427passed：

- 旧的未结束事件大小限制测试被破坏：模型新代码也漏掉了错误信息里的event。
- 完整CR-only事件在网络不再给新chunk时无法及时产出：模型显式暂存末尾CR并等待
  更多数据，独立用例超时。这个行为违反原合同，不是验收时新增的要求。

因此不能只说“换patch就好了”，也不能说“模型必然做不对”：当前草稿同时有编辑
适配和实现语义问题；若先让写入成功、再给真实失败反馈，Worker能否自行修复，尚未测试。
这项没有进入Reviewer，所以不是该次Reviewer错误放行。

## 通过的跨文件真实功能

AllOfGuardrail需要改已有guardrails.py、hooks公共导出，并增加有意义的补充测试。
Worker实现了规则列表快照、顺序await、首次拒绝短路、返回原拒绝对象、异常和取消
传播，以及与已有GuardrailHook和phrase/length规则的组合；原有行为与依赖未改。

Primary读取全部实际源码diff和209行补充测试，核对fresh Reviewer、完整项目检查，
再独立运行435项验收。保护输入和运行时不变。这证明此类跨文件增量功能可以由
本地独立完成，不代表所有协议修复或安全判断已稳定。

已导出`patches/guards.patch`，包含实际实现和Worker补充测试，未应用回兄弟仓库。
应用前仍须核对原版本及重新验收，不能将它当成已合并功能。

## 评估仓库为何没进入Worker

模型可读来源已经收窄，但`general_prepare.build`对`check_input_roots`仍调用同一个
`manifest()`，套用125文件限制。现有模型展示本来只暴露initial_hashes/create；
宿主检查绑定与模型读取权限已有分离，容量判断却未分开。

137文件只是完整项目检查所需的源码/测试等输入，不是要求把137份源码直接喂给模型。
本轮不删除检查根、不减少回归、不提高限制绕过门槛。原始及收窄后的blocked packet
均保留。这是Harness的真实项目适配边界，未提供任何模型实现能力的负面证据。

## 成本与边界

Primary写了合同、保护测试及隔离参考实现用于可行性验证；这属于实验准备成本，
不是“免费”工作。准备时还修正了临时目录父路径和补充测试可读范围遗漏，全部保留。
无运行中代写不等于没有大量Primary工作，本轮没有Primary-only对照，净节省unknown。
末次weekly used1%，停止线仍50%；本批结论是HOLD，不是预算耗尽。

下一步应分别处理宿主检查清单容量、精确块失配的有效恢复/失败摘要，再测试有界
写后反馈能否修好真实协议草稿；不需要靠放宽正确性、刷旧小题或直接换模型解释结果。
本次只完成任务创建与固定测试，没有修改已冻结生产运行时、commit或push。

## 权威记录

`benchmarks/work/harness-convergence/strata-real-project-changes-20261026-3/`中的
registration、metrics、decision、handoff、逐格Primary记录、实际request/actions/diff/checks。
SSE辅助诊断单独位于`cells/sse/diagnostic-anchor-only/`，不计正式成绩。
准备失败namespace1/2及namespace3的blocked packets均保留。兄弟仓库内容hash、
主仓库HEAD和原有tracked diff、冻结候选及单驻留在闭合时已核对。
