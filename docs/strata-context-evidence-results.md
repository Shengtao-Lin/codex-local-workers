# Strata续作证据窗口：本轮结论

2026-10-25；候选task.7，固定三任务已闭合。**通用版仍HOLD。**
完整记录：`benchmarks/work/harness-convergence/strata-context-evidence-20261025-1/`
的`handoff.md`、`decision.json`、`metrics.json`及逐格归档。

## 真正修好的部分

在隔离开发区分开“任务历史读过哪些行”和“当前attempt已交付哪些原文”。
保留历史引用与版本；读取仍收费、同窗口重复仍停止。没有加预算、换模型、
加提示或改变Reviewer。70项相关离线控制通过。

旧C3续作的三个历史范围现在全部返回，且没有触发旧判重；随后模型自主搜索四次。
这证明一个实际宿主阻塞已解除，不代表整个任务自动正确。
旧C1此次在更早的报告错误处停止，没有进入续作，不能算它的重读回归通过。

## 三题为何仍未验收

|任务|结果|
|---|---|
|C1 HTTP/SSE旧题|answered带info findings被拒，首阶段4请求用完|
|C3 settings/provider旧题|首阶段曾自主纠正无效报告；续作重读成功，但最终又出现answered+info findings，8请求用完|
|C4 usage新目标|确实生成报告，但unknowns数组写成字符串，被native bridge拒绝，首阶段4请求用完|

独立最终接受0/3；预登记6阶段执行4，另2为NOT_ELIGIBLE，不能当额外失败。
没有补跑覆盖，也没有报告改写或Primary救场。本轮只读，无Reviewer live。

C1/C3的精确机械拒绝已由零模型重放确认。
C4响应正常以tool_use结束、输出4887tokens，不是截断或没想写报告；
桥接层返回`Invalid bridge arguments`，此错误在Python宿主前，
因此host记录protocol_recoveries=0不代表协议错误不存在。
这些都是交付/恢复问题，不能直接归为模型不会调查；草稿语义仍未获独立接受。

## 当前最小下一步

另建窄候选，处理“调查完成”和“发现问题”的报告语义耦合，
不要继续把investigation的answered当成代码PASS；保留Reviewer及Primary验收边界。
同时准确呈现native桥接层的字段类型错误。先离线验证，不自动删finding、
转写草稿、扩大预算或更改本轮成绩；新live另登记。

实际16个本地请求、约16.6分钟执行窗口。weekly used4%→5%/上限50%；
停止因为固定批次已有明确结论，不是usage耗尽。
Primary主动时间/云token未测，无节省比例结论。原改动和历史保留，
无commit/push、默认启用、兄弟仓库/Strata安装修改；无活动Worker。
