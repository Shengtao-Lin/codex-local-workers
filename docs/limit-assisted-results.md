# Primary 策略 + Coder 实现：固定两次辅助模式结果

2026-10-10（America/New_York）。预注册两次调用结束，完整链 **1/2**，
阶段决定 **HOLD_ASSISTED_REPEATABILITY**。候选、硬合同、保护测试、模型、
配置及预算未改变。weekly used 起点和最后实测均为 48%，上限 60%。
没有 commit/push、兄弟仓库修改、失败重试或中途 Primary 修复提示。
全部历史与部分修改保留。

## 本轮唯一实验变化

相对于前一批 legacy 工作流，保留正确原始 full-sort source、五项 limit
硬合同、medium 风险、scope、edit targets、acceptance scenarios、35 项
focused tests、38 项完整夹具、Ruff 和原 strict Pyright profile。
两个副本都先复现 35 项中仅 2 项比较成本失败的基线。

只在 advisory `implementation_guidance` 中增加一次 Primary 已审查的策略：
先按输入顺序各取 timestamp/identity 一次；用枚举位置区分每个 occurrence；
对纯 comparable key 使用标准库 nsmallest/nlargest；两个方向均用正原始
位置，并保留 helper 的返回顺序。不提供源码实现、目标 patch、指定变量名
或 edit sequence；Coder 可选其他满足硬合同的方案。
旧草稿 review_feedback 仍为空，不追加 few-shot。

策略见 `docs/limit-assisted-strategy.md`。它明确建议了算法，不能计自主算法
设计成功。包逐字段核对，仅 task/feature/run 身份和 implementation_guidance
不同。产品 runtime 保持 `noop-primary-complete-1`，每次运行/审计检查全部
冻结哈希。每个副本一次 Coder 调用，成功后自动 Reviewer，再独立 Primary。
预先要求两次均通过；没有用首轮成功回填第二轮失败。

## 实际结果

| 项目 | assisted-r1 | assisted-r2 |
| --- | --- | --- |
| Coder 最终状态 | ready_for_review | failed |
| 独立完整夹具 | 38 passed | 29 passed、9 failed |
| Ruff lint | pass | pass |
| Ruff format / strict Pyright | pass / pass | fail / fail |
| 自动 Reviewer | pass_to_primary | 未启动 |
| Coder / Reviewer 协议错误 | 1 / 1 | 2 / 未评估 |
| local-unit command window | 210.0 秒 | 33.1 秒 |
| 不可变 Primary 判定 | accept | rework |

第一轮不是一次写对。保留六次 validation attempts：基线 2 failed、
第一版编辑仍有 2 failed；后续 functional tests 已过，但先遇到格式失败，
再遇到 Pyright 失败，最后两次 current validation 全部通过。
Coder 在原调用内修复，Primary 没有补提示、代写或修改 tests。
最终只改 limit 分支：预计算 `(timestamp, identity, index, item)`，selection
key 排除 item，通过正 index 处理双向稳定性，返回原 payload。

Primary 检查实际 cumulative diff、完整 selection 模块、真实 public caller
及已验证 SelectionPolicy 的 positive-limit invariant；独立 38 项、Ruff、
strict Pyright 通过。源码中的 `policy.limit or 0` 在合法 validated limit
policy 上不改变行为；不把绕过验证的 forged policy 对象纳入本合同。
Reviewer 读 changed implementation 和 acceptance tests，对五项 owned
contracts 提供实际引用，acknowledge 原三项 checks，返回 pass_to_primary。
它没有额外 approved execution，不能声称 Reviewer 重新跑了 tests/checks。
Reviewer 一次协议纠正和较慢请求等待均保留；未发生调用级基础设施失败。

第二轮采用了标准库选择，但 key 只含 timestamp/identity、遗漏原始位置；
后续又把已选结果统一升序 sort。对 newest，这既不能修复此前选错的 tie
occurrences，又破坏完整 descending 顺序。已有三版实际编辑并验证：
focused 失败为 **30 → 6 → 9**，最终耗尽既有两次修复预算。静态问题仍在。
保护文件/packet/config 哈希不变。Reviewer 因 current validation 未通过
不启动，这是正确 gate，不是 Reviewer 能力失败或通过。

## Primary 额外成本：实测和缺口分开

- 策略审查及写入的墙钟窗口：UTC 01:37:58–01:38:31，**33 秒**。
  这是初始环境/上下文检查之后的指定窗口，不含全部 Primary 主动工作。
- 额外指导文本：**3,219 字符/UTF-8 bytes、420 个空白分词**。不是实测
  LLM token 数；策略只准备一次，两份 packet 复用。
- 包/文件/hash 准备及两个基线命令的 script wall time：**1.657 秒**。
  不包含驱动开发、策略审查或 Primary 推理时间。
- 两次独立验收的 pytest/Ruff/Pyright 命令窗口：各 **2.141 秒**，合计
  **4.282 秒**。Primary 实际 diff/语义审查时间未精确测量。
- Primary 动作：审查策略、创建两个受限包、执行两次独立验收及两份不可变
  判定；模型调用期间额外修复指导 **0**，Primary 生产实现编辑 **0**。
- 精确云 tokens、Primary 总主动时间和直接 Primary 实现对照：**未测量**。
  weekly used 是账户级取整读数，不能代替单次成本测量。

local-unit 两次合计约 **243.079 秒**，包含 Coder、handoff 和首轮 Reviewer，
不是精确分离的模型加载耗时，也不是全部成本。它与失败基线的较短 command
window 不可直接作经济比较。不能把 33 秒说成“全部额外 Primary 成本”，
也不能据 1/2 或 usage 读数未跳变宣称减少了 Primary 工作。

## 阶段结论

这个已暴露任务的辅助模式出现了一个可审查的完整成功：此前 legacy 组
0/2 的历史仍保留，本批是独立的 1/2，不改旧分母。但样本小且非随机同期
对照，仅支持“该策略能够帮助完成任务”的可行性证据，**不支持稳定放行**。
第二轮表明，给出正确策略仍不能保证 Coder 保留全部语义和正确消费失败
反馈。既不能断言算法设计是唯一阻塞，也不能断言整套系统必然失败。

停止本批，不补第三次冲掉失败，不提高预算/放松 tests 或把 advisory 策略
改成必须照抄的硬代码模板来伪造成功。此类算法优化仍需 Primary 负责
策略和最终兜底，未获得独立或辅助自主放行。后续如要改进，必须另行登记
新的通用候选或能力分工，并复验正常路径；不要继续同包重试此题。
正式 Reviewer 16 项语义 gate 仍为 HOLD（历史 14/16），Coordinator 不扩大。
Explorer 没有新定位问题，未调用/不计成功。模型及单驻留配置保持原样，
GPU 驻留未独立测量。无新完整 kit regression claim，产品 runtime 未变。

## 可核查记录

`benchmarks/work/capability-fit/limit-assisted-1` 保留 registration（含额外
策略成本字段）、registered-driver、preparation-cost、stage-decision 及两个
隔离目录。每个 `.agent` 包含 baseline、live 输出/计时、canonical packet/
preimages/diff、所有 validation-attempt/JUnit、独立检查输出及 immutable
Primary review。驱动为 `benchmarks/limit_assisted_trial.py`，复用已冻结审计器，
执行中两者均未修改。全部先前试验目录及现有用户改动保留。
