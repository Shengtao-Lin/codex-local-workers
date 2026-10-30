# Strata续作证据可用性：窄修复验证

2026-10-25；新阶段，不重开已闭合的autonomous批次。
授权：用户“继续吧”。weekly used实测4%，停止线50%。

## 起点与假设

task.6原结果不变：只读续作0/2，实现续作1/1；通用版HOLD。
C1/C3在fresh续作中重读三个历史范围，第三次原文尚未返回即触发判重。
历史来源覆盖不等于当前上下文已持有源码。只验证：按可信新attempt建立的
证据交付窗口能否解除该阻塞，同时保持同一窗口的重复读停止机制。

## 唯一代码差异

仅隔离开发区的普通task-v1 continuation：历史coverage/引用仍累计；
进展判定另用当前host attempt的已交付覆盖和搜索key。在成功绑定并开始
新attempt时重置当前窗口计数；普通模型请求不能重置。所有读取照常计费。
不调整其他profile、Reviewer、预算、提示、权限、版本或验收。
同attempt的native协议恢复及context rebuild不重置此窗口；该保守限制另列，
本次不声称修复任意上下文重建。编辑仍沿用原版本失效与检查流程。

## 离线与冻结

先保全task.6开发源码/根Git/状态、驻留及旧decision，后改代码。
控制覆盖：历史范围可在新attempt重新交付；同窗口重复三次仍终止；
正/负搜索、重叠行、当前hash变化、越权、预算累计、取消/失效反馈不派发；
默认及Reviewer仍用旧规则，实现链及同输入review复用不退化。
复用现有测试，不造新平台。离线失败先修夹具或实现，不启动live。

## 固定live批次

候选task.7在任何live前冻结。顺序C1→C3→C4，每题首阶段及一个预封存
合同内反馈；C1/C3完全复用task.6冻结源码/合同/反馈，只变候选。
C4是新合同：canonical usage解析及相关测试的证据调查，属于熟悉仓库的新目标，
不是陌生仓库holdout。先冻结，不能注入答案或成功旧补丁。
只读两阶段共享8requests/16tools/12evidence/900s/2recoveries，
首阶段仍4/8/6/450s/1recovery；max output12288、host context65536，iq3_s单驻留。
不需要Reviewer的调查路径由Primary全文核实，绝不称为ECR完整链。

首阶段不ready则续作NOT_ELIGIBLE；普通失败保留并继续下一固定格。
任何安全/保护输入漂移即停止，usage>=50%不派发后续。每题仅一次固定反馈，
不因结果不利补跑；本阶段不再安排live修订，得到结果即总结。
判重修复控制及C1/C3通过才可说该阻塞解除；三题全部独立接受才记
“本小批只读续作PASS”，不自动通用release-ready，不覆盖原A1/A4问题。

## 交接

独立目录strata-context-evidence-20261025-1记录baseline、registration、
逐格result/Primary判定、metrics、decision及handoff。记录实际重复读取、
请求/时间和未测云成本。无commit/push/默认启用，兄弟仓库及Strata只读。
