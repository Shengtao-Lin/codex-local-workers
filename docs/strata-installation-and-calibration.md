# 自动安装与环境校准

2026-11-03最新：**0.3.0-supervised.2已发布，真实GitHub到新项目完整链复验通过**。
见[固定发布身份与分层证据](strata-release-0.3.0-supervised.2-verification.md)：
干净clone重建一致、59项支持控制；安装READY后3Coder+4Reviewer请求，
11配置/15独立合并测试通过并canonical accept；任务后重复setup保留全部任务历史。
weekly观测28%/上限50%。以下“待授权/待发布”是原准备阶段记录，已由本段结果更新。

2026-11-03补充：[0.3.0-supervised.2发布准备](strata-release-preparation.md)已完成。
builder不再依赖忽略的实验目录，三次构建（含干净源码导出）ZIP逐字节一致。
新包仅更新文案/资格元数据及VERSION，全部功能文件延用已验收字节；59项支持控制通过。
尚未commit/push或发布，真实远程复验仍待授权后完成。下述rc1是保留的前一候选及证据。

当前结论：**本机候选路径通过，真实新版GitHub Release全链仍待发布后复验**。
批次`strata-bootstrap-20261101-1`。本轮没有commit、push、上传或创建Release；weekly最新观测25%，上限50%。

## 用户需要做什么

已有Windows Strata/iq3_s和项目Python依赖时，用户开启Strata并给Primary目标即可。
Primary负责下载固定版本、校验、选择已有Python、检查真实项目CI/测试、写一次可信检查映射，
再执行包内SETUP.md；用户无需手工编辑机器config或逐步指导Worker。
权限、任务合同和最终接受仍由Primary负责，安装不会自动批准任意shell、联网、递归或Coordinator。

这条支持范围是可信Python项目，不承诺替空机器安装Strata/模型/依赖或适配所有语言。
路径不明确、依赖缺失或项目检查有歧义时由Primary明确处置，不能跳过检查来标READY。

## 本轮补齐的流程

入口：[tools/strata-setup.py](../tools/strata-setup.py)，用户向操作说明在[strata-product/SETUP.md](../strata-product/SETUP.md)。

1. `fetch`：固定GitHub repository/tag/asset和SHA256，不使用漂移的latest；下载后核对大小和hash。
2. `unpack`：创建新缓存目录前核对完整manifest、大小写重名、Windows路径别名、逃逸和展开大小。
3. `project`：核对精确task.34包；新安装或逐文件一致时复用；其他旧安装不合并、不覆盖。
4. 自动发现现有Strata根目录及iq3_s实际tokenizer目录（含非默认模型存放位置）；
   Primary可用`--strata-home`/`--tokenizer-root`解决歧义，不移动模型或改安装。
5. 自动生成项目级配置，只选择包内已有支持profile。可信检查映射由Primary读项目后产生，
   输入含`input_roots`、`focused_tests`、`commands`；不把检查标准交给Worker或盲猜CI要求。
6. 服务未开时保留安装和独立pending记录，返回WAITING_FOR_STRATA，**不生成可用config.json、不启动模型**。
7. 用户开启后重执行setup；doctor核对iq3_s/并发1/上下文；当前纯计数器与后端6种请求计数一致，
   漂移负控拒绝；完整项目基线通过且输入未变；READY前再复核指纹，才写出config.json。
8. 安装短AGENTS指引时保留原字节并保存preimage；重复setup不重复追加。每次状态/校准/检查独立归档。
9. Primary取READY配置准备正式任务；任务仍走原安装入口、宿主检查、fresh Reviewer及独立最终验收。

仅READY不代表任务已验收。Strata之后更新也不会使旧READY永久有效：实际每次请求仍检查绑定，
发生漂移重新校准，不直接替换hash绕过。现有凭据仅用于同一驻留后端的count-only请求，未存档或提供给Worker。

## 可核查的实际证据

|层次|本轮结果|边界|
|---|---|---|
|真实GitHub下载|固定旧tag `strata-v0.1.0-preview.1` ZIP真实下载，308631字节，SHA/manifest正确|旧preview不含当前完整链，明确拒绝安装；没有静默替换成当前runtime|
|离线控制|最终58项通过，Ruff/format通过|包括原反馈/包装控制，不能把重叠轮次相加成总分|
|候选新项目安装|最终ZIP135个文件，119原发布runtime/install字节不变；正常安装、防覆盖及重复复用通过|本地构建候选，未声称由GitHub下载|
|服务未开→ready|受控未监听loopback端口模拟不可达，之后恢复真实网关；不关闭/启动实际模型|不是一次真实卸载/重新加载Strata的计时实验|
|校准与基线|自动发现6组计数精确一致+1项漂移负控；真实pytest/Ruff/no-fix/format/strict Pyright基线通过|平台和模型仍限定现有支持范围|
|最终ZIP完整任务|Coder3请求/1编辑，Reviewer4请求，16配置测试，20独立合并验收，111.468秒，canonical accept|合并验收含配置测试，不相加；synthetic安装smoke，不是新benchmark能力资格|
|完成后再setup|再次READY，整个任务档案和AGENTS逐字节不变，已安装runtime复用|未产生新模型请求或任务额度|

此前候选还运行过一次接受的安装smoke：7请求、114.625秒、17合并验收。
两次使用同一安装功能fixture，分别验证候选变化，不能当两道陌生题或用成功覆盖失败。
第一次离线测试父目录缺失、最初harness正式安装布局识别错误、各开发/格式检查输出均保留，未计模型失败。
用户安装了三个skill；本批不自动offer/load，安装不会改变任务冻结方式。

## 当前发行物与剩余一步

本地候选：[strata-supervised-setup-rc1.zip](../benchmarks/work/strata-bootstrap-20261101-1/strata-supervised-setup-rc1.zip)
及[校验和](../benchmarks/work/strata-bootstrap-20261101-1/strata-supervised-setup-rc1.zip.sha256)。

SHA256：`7317b2bdcde470fd91813ae380f300cc47fe284d57fed082c24aa92aff8943a2`。
最终报告/状态：[decision.json](../benchmarks/work/strata-bootstrap-20261101-1/decision.json)、
[package-setup-verification.json](../benchmarks/work/strata-bootstrap-20261101-1/package-setup-verification.json)、
[metrics.json](../benchmarks/work/strata-bootstrap-20261101-1/metrics.json)。

真实远程存在的是[旧preview](https://github.com/Shengtao-Lin/codex-local-workers/releases/tag/strata-v0.1.0-preview.1)。
当前功能尚未发布，故“从新版GitHub Release下载→新项目→完整任务”仍为NOT_RUN_UNPUBLISHED。
不能用本地ZIP测试替代这一步，也不为测试擅自发布。

下一步在用户明确允许后，审查并提交源码/产品文档，将已验证候选及checksum上传固定Release；
之后从真实GitHub下载到另一个干净项目，重放setup与一次smoke，才宣称完整远程交付路径已验证。
Primary仍需读项目生成检查映射；净云节省/主动时间未测，工具研发/fixture准备与日常执行成本分开。

## 发布后的Primary启动提示

下面在**新版实际发布后**使用，替换唯一的Release链接即可：

```text
从我指定的Strata supervised Release安装到当前可信Python项目的隔离副本：<固定Release URL>。
先核对实际tag、asset和官方记录SHA256，阅读包内README、SETUP、AGENTS.strata.md。
保留项目现有规则/改动/历史，不覆盖旧.local-agents，不自动安装依赖，不commit/push。
你负责定位已有Python、检查项目CI/formatter/lint/typecheck/tests，生成可信checks.json，
调用包内tools/strata-setup.py自动发现、安装、校准并验证项目基线；不要让我手写config。
我负责开启Strata和iq3_s。服务没开时保留WAITING记录并说明，禁止替我load/unload模型。
遇见旧preview、不兼容安装或漂移，不删hash/记录绕过；普通路径/映射问题自主核实处理。
只有READY配置才用于新的有界任务，Primary给目标/合同/权限，Worker自主执行自修，
完整读取实际产物并独立最终接受。安装READY和任务接受、辅助成果与自主成绩分开记录。
```
