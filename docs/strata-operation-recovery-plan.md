# 已批准文件的操作类型纠错

2026-10-29。独立批次`strata-operation-recovery-20261029-1`。推荐资格仍是task.22；
本次机制基线是实验task.23，候选task.24仅改变general_host的一个create拒绝分支，
其余上下文、角色、编辑器、预算、检查与权限保持匹配。旧四格A1/2、B0/2保持。

## 目标和窄边界

已有可写文件误用create时，仍原子拒绝整份提案。只有observed-lines-v1、路径明确
在modify、文件实际存在且所有绑定仍有效，才复用现有EditTargetError纠错通道。
反馈要求read当前内容并使用version_ref+replace；不发新版本凭证、不自动覆盖、
不增加scope或重置任何额度。原edit_recoveries和重复提案停止机制照常计数。
非该profile、只读/越权/缺失/漂移/reparse路径仍按原边界拒绝，不改变报告与审查。

## 离线准入

冻结旧真实create提案与材料，在新副本重放：旧宿主终结、新宿主返回有界纠错，
均零写入；后续必须按现有读取、版本绑定、原子事务与完整检查完成合法替换。
控制覆盖保护文件/新路径/漂移/旧profile、部分应用、伪版本、重复提案与纠错额度。
真实native控制通道必须证明一次拒绝后可继续修改/验证/submit，且恢复确实记账。
保留所有失败控制，不修改旧运行或根据假定正确补丁改旧分数。
通过后冻结task.24，运行同版本完整回归；不得夹带task.23之外的上下文/换行/预算修订。

## 固定live回归

只运行两个已冻结旧题各一次：先完整回合归属（旧零修改失败），再SSE字段兼容
（旧版已完整接受的回归）。复用上批合同、配置、完整HEAD源码、owned stub和私有
验收；相同目标模型、采样与task-rework-v1额度。新task身份/新安装独立，已暴露题
不恢复holdout身份、不将新成绩覆盖原失败。无需新参考实现或新语义提示。

两格共同登记候选/输入/私有hash及顺序后才live，每格最多50 provider、全批100。
初段16请求/4实改/4写后检查/16证据/24工具/1800秒；一次符合原正式规则的返工
14/4/4/14/24/900秒；fresh Reviewer每次10请求/900秒，最多两个不同实改版本。
普通失败保留并完成剩余安全格，不能逐格改候选、补跑或给未交付旧任务充值。
无Primary算法、生产代写或追加修法；有介入则标记assisted并与自主成绩分开。

## 结论和停止

两格均通过全部工程检查、fresh Reviewer、Primary实际diff与原私有验收，且离线
权限/原子性/预算控制通过，才取得该窄修复的受监督回归依据。真实是否触发操作
纠错另外记录；若未触发，只说明现场兼容，机制依据仍为零模型重放，不刷题制造错误。
旧题成功不能赋予未知任务族、通用、Coordinator或生产默认资格。
任一格未接受则HOLD并指出是模型工作内容、工具操作、恢复或基础设施故障；不再
在本批新增候选。控制失败先在live前修正；重大信任边界变化或weekly50%停止。

## 成本和保存

保留iq3_s单驻留，兄弟仓库/Strata安装只读，无commit/push/default变更。
记录实际调用、输入/输出、检查/修复、上下文与停因；云用量和Primary主动时间
不可测则unknown，不由weekly推算节省。当前weekly4%，停止线50%。
registration、逐格结果、decision、metrics和handoff写入新批次；上批记录不覆盖。

## 当前执行记录

task.24最终预live冻结目录为批次`candidate-v2/product`，manifest
`7b00d997b0b58c7de99603a36b068ac32dbde6ae1568c2772286d0b053fab87b`。
仅general_host.py语义改变，安装清单同步生成。最初隔离副本漏复制.ruff.toml造成
无关折行，已恢复最小diff；首版candidate/product保留，未进行live。两版运行时AST
相同。一个新测试索引未初始化的可选pending_transaction键失败，改为.get后新11项
通过；首次1failed31passed完整收据保留，原相关21项也通过。

旧真实proposal原内容和范围在两边保持，仅epoch版本引用重绑到真实同版本读取。
旧StateError、新EditTargetError，均零实改/写后检查；原生控制另证明纠错计入原额度，
随后合法替换、完整检查与submit可完成。两格正式安装/准备通过，同版本完整569项
回归通过（956.67秒）。正在冻结registration，固定顺序evaluation-B→runtime-B，
weekly最新4%/停止50%；尚无live结果。

## 阶段结论

固定两格已完成并完整接受2/2：回合题Coder11/Reviewer7请求，独立179通过；SSE
题12/7请求，独立468通过、64integration排除。两格均包含原私有16项，未给予
Primary算法、语义修法、代写或预留返工。所有中间失败保留。

共37provider、1040.234秒任务活动。新create纠错在live触发0次，机制依据仍是
无模型原提案对照+原生负控；不把现场成功因果归于该分支。新候选通过窄工程控制
和已暴露题回归，可进入冻结的新任务迁移；尚不能宣称未知任务/通用/生产资格。
SSE Reviewer的一条diff来源归属错误由Primary核对原始请求及preimage后记录，
未修改报告或据此否定实际正确产物；独立终验是接受依据。

本批无活动单元，weekly最新4%/上限50%；原task.23 HOLD不改。详见
[本批交接](../benchmarks/work/harness-convergence/strata-operation-recovery-20261029-1/handoff.md)。
接续保持task.24最终manifest、权限、模型和预算不变，选择真正新任务迁移；
继续保留失败，不为回归成功扩展资格或为普通错误逐个叠加提示。
