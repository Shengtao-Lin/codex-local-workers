# 正常入口新修复迁移：同步工具返回 awaitable

2026-10-28。承接正常入口只读材料兼容1/1，不改旧六格5/6 HOLD或历史分母。
新批次`benchmarks/work/harness-convergence/strata-awaitable-entry-transfer-20261028-1/`。

## 单一问题与任务

已暴露hooks通过不等于正常入口能修新问题。本次只派一项此前未live暴露的真实
兄弟源码任务：ToolRegistry.invoke遇到普通同步函数返回awaitable时，应取得一次
await后的最终结果，同时保持同步工作在线程执行、调用恰一次、原单一超时覆盖全部
执行、外部取消传播、原错误包装与hooks顺序。原生async handler仍按原语义await一次，
不递归展开返回结果。范围一个真实源码文件，带现有工具/hooks回归；不引入新依赖。

Primary准备可观察行为合同、公开测试与项目外封存保护测试；参考实现不进Worker。
公开两例验证普通函数返回coroutine和async callable实例；保护验证custom awaitable、
失败cause/输入预验证、超时/取消以及成功/失败after_hook。参考全检查/独立测试
必须绿，原始兄弟源码公开测试必须红；否则不live。准备故障原样保留，不算模型失败。
这是新题迁移诊断，不是外部benchmark、无偏holdout或Primary低准备成本证明。

## 冻结和预算

task.19产品逐字相同，原490同版本控制复用；不修runtime、模型或默认，不给算法。
实际只读材料沿用src/agent_runtime和现有tests，pyproject.toml；只有tools/registry.py
可写，无create，私有验收不在项目读范围。现有正常安装/doctor/prepare/run入口。

保持iq3_s单驻留、正常review-rework-v1，首阶段16请求/4有效编辑/4完整写后检查/
16证据/24工具/1800秒；至多一次经Primary核实的原合同canonical审查必修缺陷
使用原预留8请求/2编辑，再freshReview，总Worker24/6、每次Review10请求/900秒，
最多44新provider。普通Coder不绿或审查未交付不因此充值；不重抽相同代码/证据。
此前六格46+正常兼容11=57，新最大44，合计101≤原保守累计上限108；weekly50优先，
准备时实测22%。未用预算不补齐；没有新要求/算法救场、代写计划。

## 固定判定与失败分支

注册1格/执行1次；必须当前全部检查、freshReviewer、Primary独立完整验收及当前
源码/测试/检查/审查绑定才1/1接受。任一普通失败/HOLD保留，不逐格修候选或补跑。
安全/输入漂移/驻留/预算停止，未运行单列。若有真正必修Review发现，逐条处置后
只用原一次预留；optional不变成硬要求。出现重大信任/架构问题再交用户。

记录有效修改/检查/协议/no-op/实际请求、本地耗时/token及Primary准备/审查；无
Primary-only对照不声称节省。若首改绿，二次语义恢复NOT_EXERCISED。成功只证明
此新任务正常入口可用，不扩大为通用放行；失败区分补丁语义、流程、审查与环境。
完成后写decision/metrics/handoff，保留全部历史/现有改动、兄弟/Strata安装只读，
不commit/push、不改生产默认。

## 原批闭合

HOLD_PRIMARY_DETECTED_AWAITABLE_BOUNDARY_0_OF_1：Coder8请求/3修改，前两次
Pyright失败后自修至完整检查绿；Reviewer7请求PASS。冻结独立425项也通过，
但Primary对原合同“Python awaitable”的独立探针确认生成器型coroutine被返回为
generator而非int37；相同探针参考通过。根因是isinstance(Awaitable)排除了这类
合法对象，属于模型语义与审查/测试覆盖漏检。Primary拒绝，最终错误接受0。
15真实调用/44，weekly终点23%/50%。旧8/2不用于非canonical Reviewer发现，
不补跑原任务；下一步独立assisted修复仅给已核实事实，不改本批分母。
