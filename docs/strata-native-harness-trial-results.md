# Strata 原生文件工具对照结果

2026-10-24，按 `strata-native-harness-trial-plan.md` 完成N0–N3及唯一允许的live后修订。
结论：当前受控原生文件工具可完成所测单元，尚未达到替换现有入口的收益门槛。
已发布核心 `0.2.0-observed-version.3` 与生产默认保持不变。

原12格在第6格遇到真实harness故障而停止：5接受、1基础设施失败、6未运行。
一次可恢复的原生编辑拒绝没有扣工具计数，下一动作因此撞上不可覆盖的同名归档。
在隔离DEV修复记账与动作编号后，零模型重放验证了恢复路径，再运行两道新题的8格。
旧失败没有被重跑或改成成功。

| 最新固定8格 | 当前kit工具A | 原生文件工具适配B |
|---|---:|---:|
| 最终独立完整链接受 | 4/4 | 4/4 |
| 每题重复接受 | 2/2、2/2 | 2/2、2/2 |
| Coder请求 | 22 | 19 |
| fresh Reviewer请求 | 21 | 22 |
| 总模型请求 | 43 | 41 |
| 累计Coder+Reviewer宿主秒数 | 991.657 | 1126.969 |
| Primary语义救场/代写 | 0 | 0 |

总请求减少4.65%，没有达到预登记20%；接受数相同，B累计角色执行时间约多13.64%。
所以保留当前入口，`0.2.2-native-fs-trial.3` 作为默认关闭的受监督实验候选。
有界恢复实际发生：T4-r1-B在编辑被拒后自行补读、修复并通过独立验收。
Reviewer也在一次新题中自行纠正错误状态和精确引用；这类机械负担仍增加耗时。

双方都已经使用原生AgentLoop。本轮差异是原生read/edit/write及宿主适配，搜索、
检查、上下文、安全范围与Reviewer保持共同底座。A支持批量修改集，B按单文件操作
计集，因此不是完整原生profile的性能结论。新建文件仅有离线控制；没有启用网络、
shell、递归或Coordinator，未验证长上下文native重建，也没有云用量节省对照。

完整证据与边界：
`benchmarks/work/harness-convergence/strata-native-stage-20261024-1/handoff.md`。
逐格registration/metrics/decision位于 `strata-native-revision-20261024-2/`；
旧 `strata-native-pairs-20261024-2/` 的HOLD与未运行记录保持原样。
关闭审计核对所有冻结产品、发布ZIP、兄弟源码及单模型驻留通过。
private oracle内容仍匹配初始规格，其SHA首次在关闭时记录，未伪称预登记绑定。
weekly used末次30%，上限50%；按固定阶段结论停止，无commit/push。
