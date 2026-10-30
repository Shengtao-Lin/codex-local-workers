# 冻结task.24的新任务迁移：规范化评估证据

2026-10-29。批次`strata-evidence-order-transfer-20261029-1`。同一iq3_s、单驻留，
task.24 manifest `7b00d997b0b58c7de99603a36b068ac32dbde6ae1568c2772286d0b053fab87b`。
复用绑定相同的569项宿主控制及两题旧回归2/2，不再改runtime/提示/额度。

## 新单元

起点为agent-evaluation-harness已冻结完整HEAD969f197，不复制未提交改动。
新需求：evaluation_evidence自身保证规范化数组顺序，使同一批已提交记录的不同
排列得到相同证据和数值指标，并能通过现有MlflowEvaluationWriter重放同一run。
现有Worker调用方已按这些字段排序，但纯函数本身不保证，直接使用或不同读取
顺序可能改变证据hash。此任务新增函数级保证，不声称现有SQL正常路径必然出错。

可写仅evaluations/export.py与一个owned补充测试。输出顺序是行为合同：scorers按
scorer_id/version的字符串字典序，results按sample_id/scorer_id/version/字符串UUID。
所有字段、条目数量、JSON深拷贝、现有指标及错误策略保持；不能通过丢记录、修改
输入、改writer匹配策略或降低有限数检查实现。已有规范输入兼容，旧远端非规范
artifact不做迁移或静默改tag。Primary给目标和不变量，不给排序实现或参考补丁。

feature/unit/integration均high：版本化证据影响远端digest与幂等兼容；完整单元不拆。
现有MLflow工程测试和所有原文件保护；独立验收在Worker可读范围外，覆盖普通排列、
版本排序、空/重复条目、值与lineage保留、输入与输出互不污染、无效JSON/非有限数
及现有writer的查找/指定run_id重放。使用现有依赖和测试client，无外网或新增环境。

## 准备和注册

先验证源/hash、已有工程检查和私有正负控。规范输入的golden仅从原函数原有行为
冻结，给独立验收用，不向Worker提供；不写新生产参考实现。错误/兼容正控须通过，
原非规范输入应证明新需求尚未实现。准备错误留痕，live前修正，不记模型失败。
确认合法解在批准范围内、保护输入隔离后冻结registration与全部hash，再派发一次。

## 相同完整任务额度

保持task-rework-v1：首段16请求/4有效修改/4写后完整检查/16证据/24工具/1800秒；
一次符合原canonical门槛的返工14/4/4/14/24/900秒；fresh Reviewer每次10请求/
900秒、最多两个不同实改版本。每单元最多50provider，未交付不能借返工。
不逐步提示、不把私有失败变成修法、不重复抽同一报告直到PASS。

## 判定和失败分支

工程全部检查+meaningful owned tests+fresh Reviewer+Primary全部实际diff及冻结
独立验收通过，才算新单元完整接受。一次新题成功是有限迁移依据，不宣称总体稳定率。
普通失败保留原分母，先判工作内容、协议/恢复、检查/报告还是基础设施；本批不改
候选/任务/门槛、不补跑。仅使用已预登记的合法一次返工；提供新语义则标assisted。
验收自身若有错，原格INVALID保留，相同产物纠正验证另列，不改成原格成功。

停止于本新单元明确结论、关键设计/信任问题或weekly50%。兄弟仓库/Strata安装只读，
无commit/push/default变更；保存registration、结果、metrics、decision和handoff。
记录Primary准备/最终审查与Worker工作，无法可靠计量的主动时间/云tokens写unknown。

## 已执行结论

新单元完整接受1/1。Coder14请求/15取证/2实改；第一次写后5个自编测试预期失败，
自行修正后全部通过，生产函数hash在修复前后相同。Fresh Reviewer8请求合法PASS，
Primary完整diff和独立验收172通过（148原项目、11 owned、13私有），无语义指导、
算法、业务代写、接管或预留返工。所有中间失败与准备lint错误保留。

task.24及全部模型/范围/预算不变；复用相同manifest的569项宿主控制。22provider、
515.109秒任务活动，净云节约仍unknown。一次新需求成功是有限迁移证据，不改旧
任务分数或宣称总体稳定率。当前无活动单元，weekly5%/停止50%。
下一步保持冻结候选，在同类有界Python局部任务上小规模受监督试用；新模块或仓库
继续做独立终验，不为普通失败自动追加提示或修改runtime。详见
[本批交接](../benchmarks/work/harness-convergence/strata-evidence-order-transfer-20261029-1/handoff.md)。
