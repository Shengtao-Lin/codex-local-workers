# 官方小题正常入口验证：固定3格

2026-10-28。承接Worker实现+自写测试2/2；不改task.19产品、模型、权限或生产默认。
实际weekly窗口报告0%，停止线50%。新批
`benchmarks/work/harness-convergence/strata-humaneval-normal-20261028-2/`。

## 来源与目的

使用官方https://github.com/openai/human-eval 的MIT数据，固定commit
`b9453e8f1865df0a0057a1383767caa400acfbcf`，原始gzip、license、题目和哈希均封存。
它是历史公开题库，模型可能已训练见过；这里只作现有harness的公开任务兼容证据，
不报总分/pass@k，不当陌生仓库或无污染holdout，不据此取得通用生产资格。
本轮复用官方验收来减少继续自编题目oracle的需要，仍保留独立审查和最终核对。

固定顺序：HumanEval/1括号分组 → /18重叠子串计数 → /39第n个素数Fibonacci。
均不需要新依赖、Docker或外部执行环境。/40因参数l与原项目E741冲突未选择；/10
原prompt已给算法，本次选择无此额外算法指导的/18。所有选择在任何benchmark
Worker调用前完成，未运行项不是失败题换掉，也不纳入已注册分母。

## 输入、适配与可信检查

Worker只见原始prompt/示例、具有类型提示的待实现源码、一个callable测试脚手架、
批准的项目源码与既有测试。它实现函数并编写明确归它所有的补充测试；只有这两
文件可写，其他现有测试/config逐文件只读。函数参数名和调用形状保留，类型可完善。
不向Worker提供canonical实现、官方test body或额外保护，不在live追加算法提示。

原题及canonical逐字留档；集成源只做类型提示与格式适配：List→list、补素数题
返回/内部辅助类型、空列表类型，以及docstring换行。算法不改；官方断言不改，
仅把check(candidate)变为pytest入口并绑定当前候选。参考需通过原项目Ruff、
Pyright、完整回归及官方/独立验收，待实现stub需被私有验收拒绝，全部前置成功才live。

独立额外检查为：合法平衡括号长度≤8及插空格；二元字符串长度≤5、非空子串长度
1..3对照封存官方参考。素数Fibonacci采用官方n=1..10，不发明无效输入行为。
这些不是执行中修复提示，也不证明覆盖所有未知语义边界。

命名空间1在0provider时因原prompt文档行超过项目100列失败，原材料和lint收据
保留；命名空间2仅做源码文档换行，原始题目和Worker goal原文不变，不放宽lint。
同版本490runtime控制复用；不安装HumanEval、不启动其独立执行器，不宣称OS隔离，
沿用本项目可信本地检查的既有执行边界。

## 注册、判定与失败分支

三起点同时冻结后固定1格/题，3/3完整独立接受、0最终错误放行才本批PASS。
每格普通16请求/4有效编辑/4完整写后检查/16证据/24工具/1800秒，绿色后一次fresh
Reviewer10请求/900秒；总78新provider。无续作、旧任务充值或同代码重抽审查。
原项目全部配置检查不变；Primary读取实际源码/自写测试diff，执行官方+额外保护
和完整回归并验证当前输入绑定。测试数量/Reviewer PASS都不代替最终接受。

一格普通失败使门槛HOLD，仍完成剩余安全固定题；批内不改候选/预算/提示/门槛，
不补跑冲掉失败。安全/漂移/驻留/weekly50停止，NOT_RUN另列。保持单iq3_s驻留，
兄弟仓库/Strata安装只读，不commit/push、改默认或启动联网/脚本/递归Worker能力。

记录真实请求/写后修复/协议/no-op、本地时间/token、Primary准备和最终审查介入。
官方材料适配成本与任务重复发生的协调分开；无主动计时/云token写unknown，
没有Primary-only配对不推算节省比例。结果写registration/decision/metrics/handoff，
保留所有旧HOLD、Reviewer误放与assisted成绩。

## 闭合

PASS_PUBLIC_BENCHMARK_COMPATIBILITY_3_OF_3。三格分别独立429/428/426passed，
各61integration排除；每格包含重叠419项目回归，不累加。Worker自写8/7/6个测试，
Coder4/3/3请求，Reviewer4/4/3请求，总21provider/78；任务529.234秒，不含准备/
独立验收/Primary，冷加载unknown。没有live算法提示或代写，失败未补跑。

he39 Reviewer将12-base和13-base确定性阈值混淆，Primary依据
https://arxiv.org/html/1509.00864v1#S1 的定理1.1及整数乘积/实际helper探针勘误；
原报告不改。64位范围说明未被反证，但更大数没有普遍精确保证；探针数不是
Fibonacci，未证明prime_fib公共入口反例，不改本批官方有限case成绩，也不把
benchmark接受说成任意大整数数学库合格。he18引用未提供参考也不当作证据。

已形成资格范围结论，未通用放行。当前单模型、原改动/兄弟源码/候选完整性通过，
weekly1%/50%，无活动live，不commit/push或改生产默认。下一步优先复用既有
同任务Primary反馈入口，明确24/6审查预留与普通task-v1的区别，避免又从头造harness。
