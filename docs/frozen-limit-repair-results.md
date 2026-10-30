# 冻结候选：历史 limit 修复的两次对照

2026-10-10（本地日期）。weekly used 起点及最后实测均为 48%，上限 60%。
两次预注册运行已完成，阶段结论 **HOLD：不能把正常路径成功推广为算法修复稳定**。
未改产品候选、模型、提示或保护测试；没有 commit/push、兄弟仓库写入、
失败调用重试或中途 Primary 修复指导。全部原有改动和历史保留。

## 本轮固定输入

选取 `limit-recovery-3/control-1` 的真实历史失败调用原始前镜像，而不是
复制已完成实现或兄弟仓库当前工作树。源码 SHA-256：
`59d7f5b1de2d468ab4acd9e93c93f8649c60b3b20817b1a88f7243ab1491c66c`。
每个独立副本都先复现原有 **35 项 focused tests、8 项失败**。

复用 v3 保护文件、五项合同、acceptance scenarios、medium 风险和既有
review_feedback，无新增 few-shot 或语义指导。合同要求精确 legacy 顺序及
对象身份、回调顺序/异常身份、比较成本、非二次方位置记账、其他策略及
真实 dataset JSON round-trip 不变。历史正例预检为 38 passed，记录原样保留。
本轮是已有反馈下的失败草稿恢复，不是盲测或从原始功能代码实现新需求。

使用 `noop-primary-complete-1` 的固定产品候选；每次运行/审计核对 live kit
及 `transfer-candidate-runtime-1` 全部冻结文件哈希。全局模型、presentation
和预算来自此前正常单元配置，验证使用原 `project-strict` profile：Ruff
format/lint、原 selection 模块 strict Pyright，唯一目录适配是 basetemp
重定位到新副本。没有继承旧实验适配器或提高预算。它不是对历史 runtime
的随机配对因果实验，不能把差异单独归因于某条候选修复。

每个副本只允许一次 Coder 调用，成功后自动 Reviewer，再独立 Primary。
两个均通过才算本批通过；失败计入结果，不另起 run 冲掉失败。

## 实际结果

| 项目 | repair-r1 | repair-r2 |
| --- | --- | --- |
| Coder | failed | failed |
| 写后实际验证 | 3 次 | 3 次，另有 1 次预编辑验证 |
| focused 失败序列 | 6 → 6 → 6 | 8（基线）→ 24 → 24 → 6 |
| 独立完整夹具回归 | 32 passed、6 failed | 32 passed、6 failed |
| Ruff lint / format / strict Pyright | 均失败 | 均失败 |
| 协议纠正 | 2 | 2 |
| Reviewer | 未启动 | 未启动 |
| local-unit command window | 36.0 秒 | 28.5 秒 |
| Primary 不可变裁决 | rework | rework |

第一轮实际写入三版源码，失败集合为：**newest → oldest → newest**。
去掉反复 `list.index` 后，模型把排序 key 的位置符号改来改去，修一个分支
却破坏另一个，最终仍将 `-index` 用于 `nlargest`。对同 timestamp/identity
的记录，负位置会优先取较早位置；legacy newest 必须反向稳定，优先取
较晚位置。第一轮另把已推断为三元组的列表原地换成四元组，导致类型错误。

第二轮预编辑基线验证失败后仍可编辑，说明未错误触发成功终态 gate。
模型随后扩展 tuple，却一度未同步所有解包（24 项失败）；追加 arity assert
不能修复解包问题。最后修好 tuple 解包，但 `nlargest` 仍使用 `-index`，
所以与第一轮剩下相同的 6 项 newest 顺序失败。

两轮都消除了原有位置查找成本失败，也都执行了真实写后验证。因此不能
说“完全没有进展”或“没有 VALIDATE”；准确结论是：**局部进展未转化为
同时满足全部不变量的修复**。最终真实 diff 均只改授权 selection 文件，
保护文件、配置及 packet 哈希不变，未发现 scope escape。

runtime 实际发出了 repair_focus：第一轮 3 次、第二轮 4 次。第一轮 delta
明确列出了 resolved、remaining 和 new failures，但模型仍发生分支反复。
调用按既有两次修复预算失败终结，未无限循环或误交接 Reviewer。没有触发
重复无变化编辑 gate，因为这些是实际不同编辑，不是相同 find/replace。
验证未通过时 Reviewer 不启动是正确安全行为，不能算 Reviewer 失败或通过。

两轮最大模型实测 input 为 15,570 / 14,838 tokens；runtime 记录的最高
context utilization 为 0.8002 / 0.7704。没有观测到 context overflow、HTTP 400
或模型加载失败；不能仅凭这些数字排除上下文呈现/注意力对推理的影响。
两次协议错误均留在 canonical handoff；最终失败不是协议预算耗尽。

## 可核查结论及下一步边界

本批 **Coder 0/2、端到端 0/2、Reviewer 0 次（未评估）**。此前两个简单
单元的 4/4 仍有效，但不能合并解释成复杂算法已稳定。尤其“修好一边又坏
另一边”的确发生在本地模型草稿中；它不是 Primary 来回改 runtime，
因为本轮产品代码和规则始终未变。

故不扩大真实项目/Coordinator 放行，也不靠增大 turn/context、强制启动
Reviewer 或再加一句目标补丁提示去补分。当前候选能安全验证、阻止错误
交接和有限终结失败；没有证明它能让这个复杂修复成功。Reviewer 16 项
语义矩阵仍是独立 HOLD，14/16 历史不变。Explorer 没有新的定位问题，
未调用/不计成功；单模型驻留配置保留，但未独立测量 GPU 驻留。

下一轮若继续，应先把“旧错误草稿的局部修复”与“从正确 legacy 基线实现
优化”分别登记为独立能力，检查是否存在旧补丁/注释锚定影响；保留相同
硬合同和保护测试，并明确标注起点及历史反馈差异，不能假装是单变量对照。
这比继续重放同一个错误草稿更能判断是修复路径问题还是算法任务能力边界。
任何新候选都须另起版本并复验已经通过的正常路径，不能覆写本批失败。

停止原因是两次固定调用产生了明确失败结论，不是预算用尽。云 tokens、
Primary 主动时间及直接 Primary 成本未测量，不声明节省成本。未执行新的
完整 kit runtime 回归，因为产品 runtime 没变。

## 产物

- `benchmarks/frozen_limit_repair_batch.py`：冻结、运行、独立审计驱动。
- `benchmarks/work/capability-fit/frozen-limit-repair-1/registration.json`：
  模型调用前固定两个副本及判定标准；`registered-driver.py` 保留原驱动。
- 两个 `repair-r*` 的 `.agent`：原始基线、实际模型调用、全部 validation
  attempts/JUnit、diff、独立 38 项及静态检查输出、independent-audit.json。
- canonical run 的 `review.json`：Primary 不可变 rework，部分改动不撤销。
- `stage-decision.json`：本批 0/2 / HOLD；全部历史目录未修改。
