# Strata 受监督稳定性增量（2026-10-31）

本轮有可用的窄改进，通用正式版仍未放行。模型仍iq3_s、单驻留；task.34安装和生产默认不变，无commit/push。

1. 新任务的Ruff检查显式加 `--no-fix`；格式检查使用 `--check`。Click原先由fix=true引起的自动改写冲突不再出现，但修复不保证代码语义正确。可选[本机示例配置](../examples/strata-preview/config.current-machine.readonly-checks.task34.json)只改变Ruff检查开关，路径/检查范围仍须按目标工程调整。
2. [Primary返工准备工具](strata-primary-return-preparation.md)自动绑定机械字段，减少手填hash/缩进错误；13离线控制含冻结宿主兼容通过。该工具仅生成待Primary核对的新文件，不派工、不判断语义、不充值。开发侧工具未纳入发布包。
3. 已知事实提取任务可显式采用简洁事实+证据的deliverable；保持工具和调查自主性。三对新问题A2/3、B3/3，B摘要字符少30.19%，但多1次本地请求。这是小样本受监督使用依据，不是通用准确率或云节省证明。源码题B仍有范围延伸，完整报告仍须审查。

本轮[混合六题及辅助返工报告](../benchmarks/work/mixed-stability-20261031-2/report.md)：初始3接受/3不接受。gcd给出真实失败反例后用原保留预算自行修好，独立接受；Click即使完整1259项通过和Reviewer PASS，仍在原封存语义探针失败，辅助返工又因证据额度耗尽停止。旧失败均保留。

[三对报告格式对照](../benchmarks/work/compact-evidence-20261031-1/report.md)单列，不合并成总体成功率。共计本轮85次本地请求，模型及宿主流程约19分25秒，不含准备、Primary终验和加载。weekly最后观测19%，用户上限30%；Primary账单tokens/主动时间/净节省unknown。

下一项有证据支持的机械候选是超长读取窗口的有界处理：当前超过120行直接拒绝，且失败消耗证据动作额度；Click返工已实际遇见。但其语义探针仍失败，不能假定改窗口就能修好。若继续，应隔离候选先做真实轨迹重放/越界负控，再以新任务迁移；不给已耗尽旧任务充值、不放宽语义门槛。本轮未改动该权限/调度路径，也未启动联网、递归或Coordinator新live。

## 本轮后续隔离控制与迁移已完成

读取窗口试验见[独立结果](../benchmarks/work/read-window-20261031-1/report.md)：真实host证据适配层离线正负控通过，三道新算法题完整链3/3独立接受；**live截断触发0次**，仅说明正常路径smoke通过，不证明实际恢复收益。窄补丁已导出到[实验patch](patches/strata-task34-bounded-read-window.patch)，候选仅在benchmarks/work隔离区，未纳入发布安装或默认。旧Click失败及返工预算耗尽不改变。

三个独立批次合计109次本地请求、1376.734秒（约22分57秒），包括两次单列assisted返工，不包括Primary准备/独立审查和加载。不能把三批不同目的、重叠来源的成绩合成泛化成功率。当前实际观测weekly used19%/30%；未证明净云成本节省。

返工准备工具最终补充了可选create目标尚不存在的合法状态及意外创建拒绝，当前15项控制通过（此前13项为当时版本结果），Ruff/format和git diff --check通过。生成器仍不派工或批准语义。

## 2026-10-31 继续迭代：原生控制与跨来源结果

- [原124行动作完整原生重放](../benchmarks/work/read-window-native-replay-20261031-1/report.md)通过：候选第一次就交付120行，避免那一次协议拒绝，收费与禁读保持。仍不能证明旧Click最终可修好；旧任务未充值。
- [CPython/公开CSV新来源迁移](../benchmarks/work/compact-transfer-20261031-2/report.md)2题接受、1题回答不完整；引用均正确，缺陷是未完成跨段等价推理，未观察到新的捏造。11请求/100.734秒，不能与原3/3覆盖或合并为总体成功率。
- [明确文件的CSV/RST输入](../benchmarks/work/explicit-text-input-20261031-1/report.md)已做隔离候选，manifest负控和完整原生无HTTP读取通过。只收逐文件明确批准的输入，目录权限不增加；无脚本/网络/执行能力变化，未生产启用。
- 本阶段实测weekly used19%→20%，上限30%。无commit/push，旧历史与用户改动保留，兄弟仓库/Strata安装只读。没有净云成本节省证明。

当前适合继续受监督试用，通用正式版仍HOLD。接下来语义实验应区分必要推理与真正证据不足，避免把保守缺答当捏造，也避免用更多格式限制掩盖推理问题。是否需要修改交付契约必须用匹配的正负控判断，不把单题推导补充堆成全局提示。

## 已完成 skill 与推导对照

[skill-deduction-20261031-1](../benchmarks/work/skill-deduction-20261031-1/report.md)三道新问题×两臂全部完成：无skill组完整接受3/3，显式加载0.1.1组2/3；两组核心答案均3/3正确，B一题因附加结论超出已观察证据而HOLD。三次技能完整加载均核对成功，不再将主会话安装当作Worker加载。

A14请求/99.688秒，B16请求/125.234秒，B摘要总字符9771对A7870。仅三个配对、题目明确要求推导，不能证明技能有害或解决旧cache缺答；目前没有默认强制加载的收益证据。保留0.1.1为显式可选候选，不追加旧题重抽或扩大权限。普通任务包仍须清楚表达期望成果，完整报告仍由Primary核对。原发布包/安装/生产默认及旧资格不变；weekly最后观测20%，停止线30%。

## 真实源码的子代理协作试用

[subagent-handoff-pilot-20261031-1](../benchmarks/work/subagent-handoff-pilot-20261031-1/report.md)：
真实JSON校验函数深层支持由Worker自主实现并补15项测试，登记32项测试/Ruff/format及fresh
Reviewer通过；Primary独立35项行为检查通过。额外Pyright发现一处object不可迭代类型标注，
它未列入登记profile，单列准备/集成质量缺口，不追记成原检查失败。Primary保留原稿并在独立副本
补2行类型标注，最终35项及Pyright/Ruff/format通过；canonical为takeover、最终为assisted。
9次本地调用/233.672秒，未调用封存返工，不证明续作收益或净云节省。此例证明主要实现/测试
可以复用，不能将Worker未独立工程完整交付直接等同全部成果无用。未知任务族和通用资格不扩大。
