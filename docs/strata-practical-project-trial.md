# Strata：可信项目内的受监督试用

这里的子代理不是逐条指令执行器。Primary给目标、行为合同、批准材料和检查；
Strata自行调查、组织步骤、实现、补测试并按真实失败修复。Primary读取完整成果，
独立决定是否接受。安装成功或`ready_for_primary`都不是最终验收。

当前候选和资格以`strata-practical-readiness-progress.md`及其指向的不可变decision为准。
不要用旧版本的PASS覆盖新失败，也不要把离线控制、公开小题、真实切片合成一个成功率。
尚未闭合的批次没有新资格；本页本身不授予生产启用权限。

## 安全起步

1. 使用可信Python项目的隔离副本；保留原项目改动，不把实验失败直接同步回原项目。
2. 使用有资格回执的冻结包，从包内安装器安装到没有`.local-agents`的新副本。
3. 使用本机已验证的Strata路径、tokenizer/hash与项目检查配置；不是复制一个通用YAML就能生效。
4. 保持一个iq3_s实例、并发1；不启动LM Studio模型。安装器不会下载、切换模型或安装项目依赖。
5. 每任务新身份，同一任务续作共享原预算；不得换task_id充值或覆盖失败。

```powershell
python -B install.py --target C:/work/trusted-project-copy
# 以下命令在该副本内执行，配置和合同由Primary核实。
python -B .local-agents/strata-worker.py doctor --config .agent/project-config.json
python -B .local-agents/strata-task.py prepare --contract .agent/task.json --config .agent/project-config.json
python -B .local-agents/strata-task.py prepare --contract .agent/task.json --config .agent/project-config.json --apply
python -B .local-agents/strata-task.py run --task-id example --attempt-id first
python -B .local-agents/strata-task.py status --task-id example
```

任务schema见[当前试用合同](strata-practical-contract.md)。其中占位路径必须替换，
配置须匹配本机校准数据和目标项目检查；不能把示例当作已批准的真实任务。

## 选择最小任务路线

`implement`适合目标明确、权限范围已知、有可信检查的局部Python行为单元。
可以跨文件，但不是整仓库架构重写。宿主自动格式化并运行完整配置检查，每次
有效编辑均有对应写后检查机会；通过后自动启动fresh只读Reviewer。
Primary仍核对真实diff、当前检查与Reviewer证据，不只看Worker自述。

`investigate`适合读取、比较和解释批准材料，不执行项目代码。普通调查可使用
显式compact-v1四字段报告，宿主绑定已观察引用并保留全文，不要求重复填finding索引。
正文仍可能过度推断；Primary必须核对结论和未知项。一次原合同内的证据争议续作
不等于首次自主成功；新事实、算法指导、扩大范围另记assisted。

实现预算：16次模型请求、24工具、16取证、4次有效变更、1起点检查加4写后完整检查、
1800秒；fresh Reviewer另计10请求/16工具/900秒。普通compact调查首阶段4普通请求、
共享8普通请求加每阶段至多一次机械报告纠错、总10请求/16工具/12取证/900秒。
总时间、权限、版本漂移和无进展机制仍会提前停止，不保证用完额度。

## 能力不是全局全开

- 公开资料：仅批准主机的公开HTTPS文本与已观察链接，没有搜索引擎、登录或上传。
- 操作：仅固定`json-summary`，不是任意shell或模型编写脚本的执行器。
- 子任务：最多两个串行、单层只读孩子，共享父预算，不能递归派孙任务。
- Skill：显式批准后可由只读调查加载；不是扩大权限或代替宿主硬检查的机制。

能力profile与compact报告profile不能随意混合；未验证组合保持关闭。
联网不能与可写实现一起启用。详见[按需能力与边界](strata-on-demand-capabilities.md)。
旧profile的固定题成绩不自动成为新产品的迁移证明；附带回执应分别注明版本与来源。

没有shell工具不代表OS隔离：测试会以宿主权限导入并执行修改后的Python。
本版本只适合可信本地项目，不能安全执行敌意仓库或网页诱导的任意代码。

## 真实项目试用如何评价

选择一个真实需要做的、有界行为单元。Primary给行为与验收，不给逐行修法。
保留起点、合同、全部请求、有效编辑、每次失败、检查和独立审查；未运行不算模型失败。
普通错误可在原预算内自修；保护输入漂移、越权或重复无进展应停止并交接。

记录Primary是否只审批和终验，还是还需定位、细化边界、语义提示或代写。
分别记录首次完成、监督恢复、assisted、接管和最终接受；不要反复抽样Reviewer直到PASS。
本地运行耗时与token可以观测，但没有Primary-only对照时不能声称节省某个云成本百分比。
