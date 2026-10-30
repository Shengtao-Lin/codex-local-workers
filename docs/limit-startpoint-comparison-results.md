# limit 任务：旧草稿修复与 legacy 起点实现对照

2026-10-10（America/New_York）。固定四次调用全部结束：旧草稿 **0/2**，
legacy 起点 **0/2**，阶段决定 **HOLD_ALGORITHM_WORKFLOW**。
weekly used 起点和最后实测均为 48%，授权上限 60%。停止是因为预注册批次
已产生明确结论，不是用完预算。没有 commit/push 或兄弟仓库写入。

## 固定条件与有意差异

产品候选保持 `noop-primary-complete-1`，每次运行/审计核对 live kit 及
runtime snapshot 的冻结哈希。保持 Qwen Coder、Muse Reviewer、OSS Explorer、
既有上下文/turn/修复/协议预算、单模型驻留配置和原验证 profile 不变。
全局配置未修改，也未引入任务专用适配器。

两组都复用前一批 limit 修复的五项硬合同、medium 风险、owned contracts、
scope、edit_targets、acceptance criteria/scenarios、保护测试和 strict Pyright
配置。两个包逐字段核对，只有 task/feature/run 身份及 `review_feedback`
不同；源码起点单独记录。每组两次，顺序 draft-r1、legacy-r1、draft-r2、
legacy-r2。每调用最多一次，不中途修包、提示、改标准或重试。

| 差异 | draft 组 | legacy 组 |
| --- | --- | --- |
| 源码起点 | 历史失败调用原始 preimage | v3 原始正确 full-sort 实现 |
| 初始 source SHA-256 | `59d7f5b1de2d468ab4acd9e93c93f8649c60b3b20817b1a88f7243ab1491c66c` | `4c337d46d8a1c82b5ad7954f482545282477195c20eae7fd5de2a922b431a0ab` |
| 历史反馈 | 原样保留 `newest-equal-key-order`、`preserve-passing-behavior` | 移除这两条只适用于旧 heap 草稿的反馈；不另加策略、few-shot 或补丁 |
| focused 基线 | 35 项、8 failed | 35 项、2 failed（比较成本）；其余功能测试通过 |

这是**两个工作流的对照**，源码和反馈同时改变；不是源码起点单变量实验，
不能把任何差异完全归因于源代码或历史反馈。legacy“正确”指既有功能语义，
不指已符合新增性能合同。所有任务都已暴露，不计陌生题/盲测成功。

每组必须两次都通过原 focused/static gates、自动 Reviewer、独立完整夹具
检查和 Primary 审查才算通过。失败不会被成功替换；两组都未达标准。

## 四次实际结果

| 调用 | 独立完整夹具（38 项） | Ruff lint | format / strict Pyright | 协议错误 | local-unit 秒 | 终止原因 |
| --- | --- | --- | --- | ---: | ---: | --- |
| draft-r1 | 32 passed、6 failed | fail | fail / fail | 1 | 25.7 | 两次 failed-validation no-op |
| legacy-r1 | 17 passed、21 failed | pass | fail / fail | 1 | 35.5 | 两次本地修复预算耗尽 |
| draft-r2 | 14 passed、24 failed | fail | fail / fail | 3 | 20.5 | 两次 failed-validation no-op |
| legacy-r2 | 22 passed、16 failed | fail | fail / fail | 4 | 18.5 | 协议错误预算耗尽 |

所有单元 Primary 不可变判定为 `rework`，实际 diff 都只涉及授权 selection
文件；保护文件、packet、config、Pyright 配置哈希不变。部分修改未撤销。
Coder 0/4；Reviewer 0 次（验证失败，不能算通过或失败）；端到端 0/4。
Explorer 已定位，不重复调查、不计成功。Coordinator 保持关闭。

### 错误草稿组

- draft-r1 去掉反复 `list.index`，仍把负位置用于 `nlargest`；因此 newest
  重复键顺序的 6 项测试失败。末版四元组解包已更新，但算法符号仍错误。
- draft-r2 也把 tuple 扩为四元组，却保持结果三元组解包，产生 24 项失败。
- 两轮实际模型都在失败后提交两次无变化替换，固定候选机械停止。
  这是候选 gate 的真实生效证据，不是修复成功，不能回填通过。

### 从正确 legacy 起点实现组

- legacy-r1 新写手工 heap，错误地给 datetime/字符串取负；newest 分支的
  替换方向错误，相同 key 时可能比较 payload。逐项取 key 并立即比较，也
  不满足先完成全部回调再比较的不变量。并非复制旧草稿的负索引错误。
- legacy-r2 用另一种 heapify/pop 实现，仍给 datetime/字符串取负；每个
  item 的 key_func 被调用两次，违反各回调一次的合同。
- legacy-r1 的 runtime focused 证据是：基线 2 failed；第一次编辑的
  validation 因 diff-quality 失败未跑 pytest；后两次为 26、21 failed。
- legacy-r2 runtime 只实际执行了预编辑的 2-failed 基线；末版 VALIDATE
  在 diff-quality（新增尾随空白）阶段就拒绝，focused tests `not_run`。
  本文的 16 failed 来自 Primary 后续独立执行，不能说模型对末版成功
  执行了测试。之后无变化替换耗尽协议预算，未触发成功交接。

两个组都产生了真实不同实现；四次失败不是只缺测试执行或模型没启动。
同时存在算法推导、tuple 编辑一致性和失败反馈后无进展等问题。

## 结论和下一阶段选择

**“只是旧草稿锚定，换正确起点就能解决”没有得到支持。** 去掉旧草稿反馈
后，两次 legacy 实现仍失败且引入另一类基本算法错误。但样本只有每组两次，
两个因素同时改变，所以不能证明不存在锚定影响、不能比较两种工作流的
总体成功率，更不能证明任何模型或整个计划必然失败。

当前证据更支持：这个 bounded Coder 在该算法任务上，尚不能可靠地同时
维护排序、泛型 key 类型、回调副作用及复杂度约束，并从验证错误收敛。
候选能阻止错误验收并有限终结，无证据表明放松安全 gate 就能修好语义。
第一批两个正常单元的 4/4 结果继续保留，不与本批合并成产品稳定指标。
Reviewer 原 14/16、语义 HOLD 仍是独立阻塞，不能用没有启动的 Reviewer
掩盖或补足该矩阵。

不再为该工作流重复相同包、增加 turn/context、强行触发 Reviewer，或通过
删掉复杂题宣称全面放行。此类优化暂由 Primary 负责算法/不变量设计与
最终接管；如继续研究，另行登记“Primary 给出已审查策略、Coder 实现”的
辅助模式，与本轮自主算法选择分开计账，仍保留相同硬合同和保护测试。
这属于能力分工对照，不是证明原工作流已经修好；应同时记录 Primary 的
策略准备成本，避免局部模型省时掩盖更大的云模型工作。

本轮所有 model request 均正常产生返回，未观测 HTTP 400、context overflow
或模型加载失败。最高 reported input/context utilization 分别为：
draft-r1 12,646/0.6812；legacy-r1 14,627/0.7618；draft-r2 13,490/0.7156；
legacy-r2 13,295/0.7076。不能据此排除提示呈现或注意力影响。GPU 驻留
未独立测量，配置不当作实测证明。
local-unit 总窗口约 100.2 秒，不是全部端到端主动时间。Primary/cloud token
成本和经济对照未测量，无节省成本结论。产品 runtime 未变，本轮未重跑
完整 kit 回归，不把历史回归伪装成新执行。

## 可核查产物

`benchmarks/work/capability-fit/limit-startpoint-comparison-1` 包含预先冻结的
`registration.json`、`registered-driver.py`、四个隔离目录和 stage-decision。
每个 `.agent` 保留独立基线、live 输出/计时、canonical packet/preimages/diff、
全部 immutable validation-attempt/JUnit、Primary 38 项与原静态检查输出、
independent-audit.json 和 immutable review.json。前两批历史目录未修改。
驱动为 `benchmarks/limit_startpoint_comparison.py`，复用已冻结的独立审计器，
执行期间两者都没有修改。
