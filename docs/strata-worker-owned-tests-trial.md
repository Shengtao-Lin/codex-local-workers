# Worker 实现与自写回归：定义输出隔离固定重复

2026-10-28。用户要求继续自主推进。实际weekly used窗口现为0%（重置时间
1793798400），停止线仍50%，助手未消耗reset。旧闭合87/108不续费、不复用余额。
新批`benchmarks/work/harness-convergence/strata-worker-tests-isolation-20261028-1/`。

## 为什么测这一项

材料清单故障已能修正，但awaitable新题中测试和Reviewer一起漏错，Primary发现后
交回的新辅助任务才完成。继续修改patch协议没有直接证据。这里保持task.19产品
逐字一致，观察Worker能否同时实现行为、生成有检错力的测试，并减少Primary逐例
编写公开测试/语义反馈的需要。不是成本A/B，也不预设测试通过就证明代码正确。

## 唯一行为单元与两格

从只读兄弟runtime源码复制，ToolRegistry源码此前暴露，输出隔离需求首次live。
register返回值、每次definitions返回的ToolDefinition及嵌套JSON schema必须互相
独立，修改外部值不影响注册状态、旧快照/其他工具/未来输出。保持原始内容、排序、
空结果、重复/timeout验证、handler/input-model身份与原invoke语义，不冻结公开模型。
两处发布边界属于一个不变量，同一单元覆盖，feature/unit/integration均high。

Worker可写registry.py与一个明确归它所有的supplemental测试文件；该文件只提供
7行“新registry输出为空”的脚手架。Worker需补充有意义的register/definitions嵌套
隔离和正常调用回归。其他已有测试和配置逐文件只读，隐藏保护在项目外。只读材料
批准src/agent_runtime、tests、pyproject，既有范围与版本绑定保留；不新增工具权限。

repeat-1、repeat-2起点均在live前冻结，顺序固定，不向第二格转移第一格补丁或报告。
不提供算法/参考/隐藏测试/变异器，不在live补语义提示或代写。普通失败HOLD但完成
另一个安全格。不能把旧失败冲掉，也不把该行为说成陌生repo benchmark。

## 离线控制和独立验收

起点现有普通检查可以绿，这不是完成新需求的证明。封存保护必须拒绝原始别名
实现；参考完整静态检查和独立全回归必须通过。复用同版本490产品控制，不改runtime。

宿主独立将已注册行为的两种错误分别注入一个额外进程：register返回内部定义，
或definitions返回内部定义。只跑Worker-owned测试，Junit确认有执行的真实断言
失败；不把import/收集错误当检错。原始7行脚手架两种均不能检出，参考测试必须
分别检出。运行时同样核查Worker自写测试，两种变异均被检出才满足测试交付。
变异器不进Worker，不改变原任务源码、检查收据或历史，不作为运行中修复反馈。

每格完整配置检查→一次freshReviewer→Primary完整源码/测试diff审查→独立全回归
含封存保护→两个自写测试变异控制→当前源码/检查/审查绑定，全部通过才接受。
2/2、0最终错误接受为该任务族固定重复门槛；无自主写后失败则恢复指标未触及。
这不解决所有未知边界，也不等于通用生产资格。

## 预算、失败和成本

每格普通16请求/4有效修改/4完整写后检查/16证据/24工具/1800秒；freshReviewer
10请求/900秒，最多52新provider。无续作/充值/相同代码反复审查。保持iq3_s单驻留。
安全/漂移/驻留/weekly50停止，未运行另列。批内不改候选/门槛/提示；普通失败闭合
后按真实原因选择另一次窄设计，不能在两格间调参或增加公开验收来帮助第二格。

记录Primary脚手架与保护/参考/变异控制准备，和每格协调/完整审查分别列出。
准备wall time不冒充主动时间，后者/云tokens不可测写unknown。本地请求、检查、
有效编辑、协议/编辑恢复、no-op、时间、输出token和测试检错证据分别保存。
没有Primary-only配对，不能声称节省百分比。结束写registration/decision/metrics/
handoff；兄弟/Strata安装只读，保留全部历史/现有改动，不commit/push或改默认。

## 闭合

PASS_WORKER_IMPLEMENTATION_AND_TESTS_2_OF_2。两格各独立428passed/61integration
deselected，freshReviewer均PASS；各自6个自写测试分别检出两种别名错误，0收集错误/
0跳过。首格12Coder+7Review请求、2有效修改（一次Pyright失败后自修、一次协议
恢复）；次格8Coder+5Review请求、一次修改全绿。合计32provider/52，任务合计
832.688秒，Primary无live语义提示/0代写。它只证明本任务族的重复实现及测试检错力，
不证明通用/未知边界或经济收益；完整准备、独立验收和Primary最终审查成本另计。
旧awaitable0/1、Reviewer误放及assisted1/1保持。下一步固定3个官方benchmark小题。
