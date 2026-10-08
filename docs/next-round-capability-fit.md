# 本地模型能力与运行协议下一轮执行交接

本轮目标是判断现有本地模型在合理的接口、信息和示范下，能否可靠完成受限开发与审查。先修已证实的流程冲突，再通过受控实验定位主要瓶颈。实验结果用于确定可交付的能力范围；小样本通过不能直接宣布完整 v2.1 放行。

交接日期：2026 年 10 月 3 日，America/New_York。接手 Primary 由用户切换为 6.1sol。本次只整理交接，下面的实现和新实验尚未执行。

## 工作范围和预算

- 仓库：`F:\ChatGPT\local-worker-kit`；当前分支：`codex/v2.1-dev`。
- 保留当前所有未提交文件。现有工作包含未发布的 runtime 修复、混合题库和 Reviewer 对照工具；不能用 HEAD 覆盖工作区来建立基线。
- `F:\ChatGPT\agent-evaluation-harness` 与 `F:\ChatGPT\agent-runtime-kit` 只读。运行、生成文件和修复全部在 kit 内隔离快照进行。
- 本轮不 commit、push 或发布 main。工程计划留在 dev；不重新安装真实项目中的 runtime。
- LM Studio 地址：`http://127.0.0.1:12345/v1`。一次只驻留一个模型，串行模型调用。模型加载慢应等待既有进程结束，不重复启动相同任务。
- 基线继续使用 Explorer `openai/gpt-oss-20b`，上下文 32768；Coder `qwen/qwen3-coder-30b`，上下文 24576；Reviewer 和 Coordinator `meta/muse-glimmer`，上下文 24576。
- 本轮先评估现有模型，不把更换模型当作默认补救。模型 ID 不等于精确量化版本；预检记录实际文件/量化元数据，无法取得则标记未知。
- 沿用先前停止线：weekly **usedPercent 达到 20%**，即剩余约 80%，不是从本轮再使用 20%。交接时实测 usedPercent 为 14%。开工及每个实验批次前后读取实际值；若已达线，不启动新工作。预算不可读取时先完成本地记录，暂停新的云端密集迭代并说明原因。
- 达到本轮实验结论并完成下面的回归、交接记录后可以结束；若仍有额度且结果支持，进入已有 v2.1 gate 验证。原放行条件以 `docs/improvement-plan-v2.1.md`、`docs/v2.1-execution-implementation.md` 和发布检查单为准，不由本文降低。

## 已有结果和当前阻塞

1. 最近完整确定性回归：496 passed、28 subtests passed、2 deselected。两个排除项依赖漂移的外部源码 pin，见后面的命令。该结果不代表模型成功率。
2. `atomic-evidence-publish` 首轮 Explorer 返回 5 条核验后的引用。Coder 获得两个文件权限，部分修复后失败，并请求已拥有的权限。
3. a2 继承式修复通过 6 项测试及 Ruff，runtime 自动启动 Reviewer，Reviewer 返回 pass。Primary 独立探测发现 rollback 抛错会覆盖原始 write 异常，记录 rework。
4. a3 旧测试在编辑前通过，终态 gate 拦截后续修复；最终无有效 diff。Reviewer 在具体反馈帮助下检出缺陷，不能计作首次独立检出。
5. a4 新增受保护边界测试，3 次验证仍有 2/8 失败，最终源文件哈希与初始相同。观察到的上下文利用率低于 50%。这支持存在语义修复问题，但尚不足以认定模型能力上限。
6. 独立 synthetic Reviewer 试验，旧提示和增加 cleanup 错误路径提示各测一组：隐藏缺陷均漏报，正确实现均通过。每格只有一次；不能据此计算可靠的总体成功率。
7. Reviewer 新增的通用错误路径提示已在工作区，但尚无实测收益证据。后续的 current 基线必须包含它，不得把旧结果当作 current 的同版本对照。
8. SQL fixture 已改为真实 SQLAlchemy Result，tuple 与 mappings 两种合法访问方式通过 Primary 参考实现验证。v1 recipe 未改写。
9. 两道 SWE-bench Lite Flask 题已冻结，但本地依赖预检未完成，Docker daemon 未运行；不把它们算作已测题。当前阶段优先复用本地诊断，避免把环境准备与模型能力混测。

关键证据入口：

- `benchmarks/COMPLEX-COVERAGE-V2.md`
- `benchmarks/MIXED-FEATURE-PILOT-V1.md`
- `benchmarks/work/mixed-v1/complex-v2/coverage-1/atomic-evidence-publish-round-1/`
- 上述目录 `.agent/tasks/mixed-complex-v2-coverage-1-atomic-evidence-publish-r1/runs/` 下 a1 至 a4 的规范档案。
- `benchmarks/work/mixed-v1/reviewer-controls/` 下四份 `challenge-result.json`。
- 早期 `sample-identity` 合理拆分后的两次集成成功：`benchmarks/SAMPLE-IDENTITY-SPLIT-COMPARISON.md`。它说明任务组织可能有帮助，不能据此拆散事务原子性。

## 启动检查

先执行 `Get-Location`，再检查 Git 状态、预算、现有进程与模型服务。不要启动旧 a4 的原样重试。当前交接没有已知仍在运行的模型任务，但接手时必须重新确认。

Python 已具备 pytest、Ruff、SQLAlchemy：

```powershell
$kitPython = 'F:\ChatGPT\local-worker-kit\benchmarks\work\stability-v1\.venv-diagnostics\Scripts\python.exe'
Get-Location
git status --short
git branch --show-current
```

默认命令沙箱在此环境曾出现 helper/写权限错误。遇到已确认的宿主权限问题，可按现有授权重跑同一限定命令的 elevated/unsandboxed 版本；不要扩大 packet 范围。

冻结当前工作区 runtime、driver、fixture、配置哈希与模型元数据作为 current 基线。复制到新的 kit 工作目录即可，不需要清理或 stash 用户改动。精确保留旧实验档案。修改 runtime 或题库后必须使用新候选快照；旧 `mixed_feature_benchmark.py step` 会拒绝 driver/runtime 漂移，不能绕过它接着跑。

## 单元划分与风险

实现前按 AGENTS.md 记录 feature、unit、integration risk 和 contract IDs。建议分为以下单元；不要把整轮实验交给一个 Coder。

| 单元 | 风险 | 拥有的契约 | 依赖 |
| --- | --- | --- | --- |
| 验证阶段状态机 | high | baseline 不终结、final 验证绑定当前输入、终态不再编辑 | 无 |
| Reviewer 中性示例与结果判断 | medium | 不预填通过结论、报告与证据规则保持 | 无 |
| 修复建议和证据窗口 | high | 启发式不扩权、不强制错误路径、新证据有界可读 | 验证状态机回归 |
| 实验 harness 与评分 | medium | 快照隔离、参考实现不可见、归因与评分可重放 | 基线冻结 |
| 少样本示范 | medium | 示例无答案泄漏、只注入相关示范 | harness 预检 |

整个 runtime 变更的 integration risk 为 high。Primary 最终检查每个变更文件、累计 diff 和集成行为；成功 Coder 仍须经过自动独立 Reviewer，不能省略标准交接 gate。

## 第一阶段 修正已确认的流程问题

### 区分基线验证与最终验证

重点位置：`.local-agents/worker-runtime.py` 的 `system_prompt`、`_validated_terminal_state`、`validate` 和主循环终态拦截。

现状：提示要求 fresh unit 先验证；任何通过的验证又可能触发只能 FINISH_SUCCESS 的终态。a3 已展示有待修复事项时过早结束的风险。

目标语义：基线和中途验证允许继续完成契约；只有明确请求最终提交、最终验证成功且输入未变，才进入终态并交接。具体 API 命名由实现决定，避免为此引入一整套新协调架构。不要靠“至少改一行”判断完成，避免无意义编辑解锁。

必须覆盖的行为：

- 绿基线加未完成需求或 review finding，不得自动结束。
- 已通过但未最终提交时，授权编辑仍可进行；修改会使旧验证失效。
- 最终提交的验证仍包含真实非零、非全跳过测试与配置检查。
- final 验证通过后继续动作应在执行前拒绝；one-shot nudge 与 runtime 终结继续有界。
- final 验证后输入漂移不得交接；缺失 JUnit、静态检查失败、保护测试被改写仍失败关闭。
- 兼容旧 packet；若确需 schema 变化，给出显式兼容规则和迁移测试。

### 去掉 Reviewer 的通过倾向

重点位置：`.local-agents/reviewer-runtime.py` 的 `report_template`、`initial_payload`。

现有示例预填 `decision=pass_to_primary`、空 findings、`status=verified`。模板偏置是待验证假设，不是已确认根因。

提供合法取值和字段形状，避免替模型预先选结论；如需要实例，平衡展示 pass、rework、uncertain/escalate 情形。保持现有决定枚举、引用核验、read-only 和风险审查规则。不要把默认 pass 换成默认 rework；正确对照也必须通过。

### 审计强制修复动作

重点位置：`_failed_test_repair_focus`、`_required_repair_focus`、`_compact_repair_payload` 与 repair supervision。

先按证据强度列出当前强制条件。真实缺失文件、陈旧哈希、保护测试不可写可继续强制；根据测试名匹配 anchor、唯一未修改文件等推断应作为候选建议。允许有新证据的少量有界调查，重复相同无证据读取仍停止。一次只调整一种启发式，先覆盖“正确修复仍在已改文件中”等反例。

保持：精确写范围、只读验收测试、当前内容哈希、无任意 shell/Git、真实验证、不可变档案。不要通过加大全局轮数、扩大写权限或忽略测试来改善数字。

## 第二阶段 区分模型能力和工具负担

先实现可重放的小规模诊断，不直接跑整个公开题库。当前 driver 尚无 direct-solver 和多组消融模式，需要接手者实现并独立预检，不能假称已有命令支持。

选择三个问题族：严格输入与边界、多文件证据隔离、异步聚合或异常清理。当前 rollback 题和历史 sample-identity 都已用于调参，只能算开发题。另写至少三个未用于提示设计的迁移题，提前冻结测试、正确参考实现、错误变体及评分规则。

每道题至少覆盖一个正常、错误和边界行为；参考实现先过全部保护测试与项目检查，错误变体必须被拒绝。正确实现允许不同合法 API 和代码结构。事务不可为降低单元风险而拆开。

| 条件 | 输入与调用方式 | 主要回答的问题 |
| --- | --- | --- |
| A 直接解题 | 同一契约与限定源码/测试，模型返回限定补丁，由可信 harness 应用到隔离副本并验证 | 无多轮工具负担时能否产生正确实现 |
| B current 工具循环 | 冻结的当前工作区 runtime，无新增 few-shot | 当前 harness 的表现 |
| C 修正后的工具循环 | 第一阶段候选，保持模型、参数与题目相同 | 修正流程后能否改善 |

直接解题仅用于诊断，不作为生产 Coder 接管，不授予任意文件或命令权限。对补丁检查路径、范围和基线哈希；无法解析单独记格式失败，不允许 Primary 代写正确答案。记录各组实际收到的信息及差异；单次输出与多轮工具的区别意味着这不是纯模型能力测量。

先三个开发题，每组两次：18 个 Coder/solver 试验。分批最多启动 6 个；先完成一批、检查预算和新信息，再继续。常规 Coder 的自动 Reviewer 是额外调用，需要单独计入时间；不得为了实验数字而关闭正常的成功后审查。

如果流程冲突已通过确定性重现，无需反复花模型调用证明同一处 bug。所有模型调用保持串行；尽可能按角色分组诊断以减少模型切换，但生产式 Coder→Reviewer 交接顺序保持。

判断方式：A 能做而 B 常失败，优先检查工具/上下文负担；C 比 B 有重复改善，说明流程修正有价值；三组都失败则继续调查题目契约和语义能力，不直接宣布整个计划失败。样本小，只报告逐题结果与失败模式。

## 第三阶段 少样本和参数对照

先比较 C 与 C 加少量 few-shot，暂不同时改温度、推理配置或模型。

- Explorer 示例：文件名查找与内容查找；返回证据时明确搜索范围与未知项。
- Coder 示例：替换失配后定位当前块；验证错误的最小有效修复；保持独立分支及副作用。
- Reviewer 示例：隐藏错误路径的具体反例、合法实现的通过、证据不足时的明确不确定。必须平衡缺陷例和正确例。
- 每次仅注入一到两个相关短例，以源码片段、可观察结果、简短判断和动作/报告组成。建议总量上限约 800 tokens，记录实际值；这是初始实验参数，不是未经实测的最佳值。
- 示例只用于展示可迁移的方法，不能包含当前验收题的参考补丁、字段名组合或唯一答案。用资源关闭的例子测试未见过的锁释放/回滚情形，避免照抄答案算成功。
- 在迁移题上比较：3 题 × 2 条件 × 2 次，共 12 次候选试验。开发题结果单列，不与迁移题合并。

Reviewer 另设独立 hidden/clean 对照，不等待 Coder 成功。至少两个不同错误路径问题族，每族一份缺陷和一份合法实现，每个条件各一次作初筛；有改善后重复核实。两族 × 两变体 × 两条件为 8 个初筛调用。当前 `complex_reviewer_challenge.py` 仅有一个 rollback 问题族，仍需扩展。

当前 Reviewer 评分硬编码了缺陷行号 13/14/15，扩展前应改为从冻结 source/anchor 得到合法证据范围，避免移动行号影响评分。synthetic archive 永远标记 synthetic、Coder 未调用、feature 未接受；oracle 与参考实现必须在 worker 可读 scope 外。正确对照的静态检查预检失败属于 fixture 错误，不计为模型失败。

few-shot 有重复收益后才考虑参数试验。当前 Reviewer temperature=1.0，Coder=0.1；`reviewer_reasoning_strength=low` 只是提示文字，并未成为服务端推理预算字段。先核实实际 LM Studio 请求、模型模板与服务端支持。不要凭修改配置字符串声称启用了更强推理。

保持任务/权限协议模型无关；采样、native tools、structured output、推理控制使用可核验的模型适配配置。相同能力模型可替换不意味着所有模型使用同一组最优参数。

## 记录与验收

每次保留唯一 task/run/revision、角色与模型元数据、源与测试哈希、runtime/config/prompt/示例哈希、实际工具动作、验证次数、JUnit、静态检查、协议错误、模型/验证/加载耗时和 Primary 决策。云端 tokens 无测量则写 unknown；账户 usage 百分比不能替代单任务 token 成本。

至少分别报告：Explorer 有效定位率、Coder 首次成功与修复转化率、Reviewer 缺陷检出与正确对照误报、完整 feature 接受、基础设施失败、Primary 是否写实现以及投入时间。未到达 Reviewer 不进入 Reviewer 分母；提示了具体答案的复审不能算独立发现。

本轮候选进入下一步集成的最低证据：

1. 第一阶段状态机和权限回归通过，未引入越权或陈旧验证接受。
2. 开发题上的改善至少重复出现，迁移题无新增确定性回退；原始逐题记录可核查。
3. 每个 Reviewer 错误路径问题族能同时检出缺陷、通过合法对照。持续漏报的类型不能宣称合格，也不能靠删题完成 gate。
4. 至少一个完整的两单元 mixed goal 在新快照中跑通两次：真实 Explorer、受监督 Coordinator、Coder、独立 Reviewer、Primary 接受与全量集成测试。原子事务仍归一个单元。
5. 这些结果只支持进入既有放行验证；未解决外部 source pin、公开题预检或其他已有 gate 时，明确保留缺口。

若预算不足，按阶段优先完成结论：先确认流程修正，再完成一组可比较的 Coder 结果，再完成 Reviewer hidden/clean 对照。不要为了数量留下一堆未完成子实验，也不宣称未测阶段通过。

连续同类失败且没有新证据时停止该分支，保留诊断并形成下一步决策。预算未到线且还有独立有效实验时继续，无需每一步询问用户。模型调用 timeout/yield 不等于失败，必须轮询同一个进程。

## 现有命令与回归入口

以下命令是现有接口，不代表其已支持上述新实验组。使用前完成对应新快照准备；新路径不能覆写已有目录。

```powershell
& $kitPython -B benchmarks/mixed_feature_benchmark.py prepare --suite complex-v2 --case atomic-evidence-publish --round 1 --batch capability-fit-candidate-1
```

准备完成会打印 root。正式 step 使用该 root、批准的 unit，并且只能在独立 Primary 接受依赖单元后进入下一单元。当前 Coordinator 测的是 Primary 批准的 unit 提案与路由；不能把它写成自主拆解复杂 feature 的证据。

```powershell
& $kitPython -B benchmarks/mixed_feature_benchmark.py step --root <prepared-root> --unit atomic-publish --authorize-step
```

现有独立 Reviewer 诊断参考命令：

```powershell
& $kitPython -B benchmarks/complex_reviewer_challenge.py --source-root benchmarks/work/mixed-v1/complex-v2/coverage-1/atomic-evidence-publish-round-1 --variant hidden
```

该历史 source-root 仍是缺陷对照种子，不能原地修成正确实现；工具会复制到新独立目录。不要把此命令当成推荐再次原样重跑，下一轮应先完成计划内变化与冻结。

修改后先跑相关测试与各目录的 Ruff 配置检查，最终再跑完整回归；不要对无代码变化重复整套回归。

```powershell
& $kitPython -B -m pytest .local-agents/tests tests -q -p no:cacheprovider --basetemp=benchmarks/work/mixed-v1/pytest-capability-fit-final-1 --junitxml=benchmarks/work/mixed-v1/capability-fit-final-1.xml -k 'not test_static_fixture_baseline_is_lint_only and not test_sample_identity_protected_metadata_boundary'
git diff --check
```

这两个排除项必须在报告中披露，不可只更新 source pin 消掉失败。真正放行前，恢复/重建隔离的正确冻结来源并执行对应检查，或依照已有 gate 明确记录未满足。

## 接手后的首个动作

读取本文件、仓库 AGENTS.md 和对应核心实现，确认预算与 dirty 状态；冻结 current 基线；实现并验证“绿基线不能提前终结修复”的最小状态机单元，然后开展上面的分批对照。不要先换模型、增加轮数或重写整个 kit。

最终提交给用户：根因的证据与剩余不确定性、候选实际改动、按条件分开的实验表、失败与基础设施记录、完整回归结果、可承担的任务范围，以及进入既有 v2.1 gate 还缺什么。
