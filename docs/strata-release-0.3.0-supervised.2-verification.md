# 0.3.0-supervised.2：真实 Release 安装复验

2026-11-03，批次 `strata-release-remote-20261103-1` 已完成。
[GitHub 预发行版](https://github.com/Shengtao-Lin/codex-local-workers/releases/tag/strata-v0.3.0-supervised.2)
已发布；从真实 Release 下载到新项目的安装、校准和完整编码链通过。
这证明本机支持环境中的分发路径成立，不新增通用模型能力或无人值守资格。

## 固定发布身份

- 发布源码：`93a095bd3fbfadb93d5a06b342ca7a63fdfc8885`，分支 `codex/v2.1-dev`。
- 固定 tag：`strata-v0.3.0-supervised.2`；预发行版，不设为稳定 latest。
- 资产：`strata-supervised-0.3.0-supervised.2.zip`，443801 字节、136 个文件；另附 `.zip.sha256`。
- SHA256：`eaecbe9d7365265a09ce26eb998c5b069a607065ed4feebfe44616a8e49e95e7`。
- 实际 GitHub 干净 clone 重建得到相同 ZIP；其中 59 项包装、安装和续作支持控制通过。
- 发布 tag 和 ZIP 不因本篇事后验证说明而移动或重建。包内 pending 文字是构建时快照。

## 分层结果

| 层次 | 实际观察 |
|---|---|
| 远程获取 | 下载发布 ZIP 和 checksum，均与固定 SHA 一致；未用本机包替代 |
| 服务不可用 | 用本地不可用端口模拟，返回 WAITING_FOR_STRATA；安装保留，无可用配置，不启动模型 |
| 服务可用 | 发现既有 Strata/tokenizer；计数校准、漂移拒绝控制及项目完整基线成立后 READY |
| 安装后任务 | `release-install-smoke-20261103-1`，从仅 trim 扩为 trim + whitespace collapse；只改源码和新增补充测试 |
| Coder | 3 请求、1 编辑、0 协议恢复；新增 8 项有效测试；11 项配置测试及 Ruff/no-fix、format-check、严格 Pyright 通过 |
| 独立 Reviewer | fresh context，4 请求，`pass_to_primary`，无 finding；实际读取当前源码及测试 |
| Primary | 阅读完整 diff/源码/补充测试，独立合并测试 15 项通过并记录 canonical accept；包含前述 11 项，不能相加为 26 |
| 任务后再次 setup | READY、逐文件一致安装复用；源文件、项目 AGENTS 和整个 canonical 任务树保持原样，无生成请求 |

Reviewer 单列了 Unicode whitespace 的文字解释疑问。Primary 按合同“每个 whitespace run
变为一个 ASCII 空格”接受 `" ".join(value.split())`，保留的是非空白 Unicode；
未向 Worker 补语义提示，也未新增用例来改写该批成绩。不声称已穷举 Unicode 边界。

本轮任务链 7 次本地请求、154.343 秒，不含下载、环境准备、加载和 Primary 主动时间。
Primary 无源码/测试代写、无运行中语义指导；准备合同、可信检查和最终审查仍是其职责。
云端精确 token、Primary 主动时间与净节省 unknown；weekly used 观测 28%，停止线 50%。

## 可用范围与操作

已有 Windows Strata/iq3_s、可用项目 Python 依赖时，用户开启 Strata，
Primary 从固定 Release 校验下载并遵循包内 README/SETUP，审阅项目检查映射后生成 READY 配置。
不要复用别的项目的机器配置，也不要把 setup READY 当作任务接受。
本次服务观察 iq3_s、并发 1、server context 131072；client context 65536、output 12288。
没有启动/卸载模型、增加权限、修改生产默认或改写 main。

本版仍是可信 Python 项目的**受监督试用版**：任务走宿主检查、fresh Reviewer 和 Primary 最终验收。
不会安装缺失依赖；未知语言、未知任务族、调查报告的全面正确性、任意联网/脚本/递归和 Coordinator
不因安装成功而获准。先前 HOLD、失败与 assisted 结果均保留。

## 本地完整记录

相对目录 `benchmarks/work/strata-release-remote-20261103-1/`：
`release-published.json`、`registration.json`、`acceptance.json`、`post-task-verification.json`、
`decision.json`、`metrics.json`、`report.md`、`handoff.md`。
原始下载在 `download/`，实际安装在 `unpacked/`，新项目在 `new-project/`，
其中 `.agent/tasks/release-install-smoke-20261103-1/` 保存原请求、响应、检查和 Primary 接受。
这些本机历史未纳入发布包；本页提供可在 GitHub 阅读的结果摘要。
