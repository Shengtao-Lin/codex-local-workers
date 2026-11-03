# Strata发布准备：0.3.0-supervised.2

最新授权：用户已明确批准commit/push当前dev分支、发布该预发行版并做真实GitHub到新项目复验。
以下“尚未发布/待授权”保留为准备阶段状态；实际结果以后续发布复验记录为准。main不改，历史不重写。

2026-11-03，本机发布候选已准备，**尚未commit/push、创建tag或上传Release**。
当前分支codex/v2.1-dev，HEAD仍为96202471caf62f010921eec5c61c0dd0fcbd9731。
weekly最新观测27%，上限50%。用户此前“不commit/push”约束仍有效。

## 本次补齐

发布审查确认旧builder依赖被忽略的benchmarks/work配置与资格记录。
现在4份已测试profile原字节保存在strata-product/examples，资格摘要与VERSION也作为正式产品输入。
builder只需要可纳入版本控制的源码，不再读取实验目录。
ZIP使用固定元数据；两次当前源码构建和一次不含benchmarks/.git的干净源码导出构建，SHA256完全一致。
干净导出不是已经提交的Git clone，不能混称远程源码验证。

包内版本为0.3.0-supervised.2，建议tag为strata-v0.3.0-supervised.2（尚未创建）。
对比已独立接受的setup候选，仅README、release-evidence.json变化，新增VERSION；
setup工具、profile、合同说明和全部119原发布runtime/install文件字节不变。
因此复用已有安装/校准/20项独立验收的完整smoke证据，不重新刷模型题目。
当前59项支持控制及Ruff/format通过，无新增Worker或模型调用。

## 可审阅产物

- [版本包](../benchmarks/work/strata-release-prep-20261103-1/strata-supervised-0.3.0-supervised.2.zip)
- [SHA256](../benchmarks/work/strata-release-prep-20261103-1/strata-supervised-0.3.0-supervised.2.zip.sha256)
- [面向用户的发布说明](../benchmarks/work/strata-release-prep-20261103-1/RELEASE-NOTES.md)
- [核对记录](../benchmarks/work/strata-release-prep-20261103-1/decision.json)

SHA256：`eaecbe9d7365265a09ce26eb998c5b069a607065ed4feebfe44616a8e49e95e7`。
旧候选、旧成绩、原始工作区改动及本次相关preimages均保留。

## 获得发布授权后的固定动作

1. 复核将纳入提交的Strata源码/产品说明/支持测试与已有改动，保留全部本地历史；不强推、不重写历史。
   提交并push当前dev分支；本轮准备不表示允许改main。
2. 创建固定tag/prerelease，上传上述已核对ZIP及checksum，使用已准备的用户向发布说明。
3. 从真实Release下载校验，在另一干净可信Python项目执行setup及一次有界smoke。
   先核对usage<50%、实际单模型驻留及当前环境；不开/关模型、不换模型、不放宽验收。
4. 远程下载、安装READY、Worker独立结果和最终验收分别记录。普通失败保留，不能更新旧成功。

GitHub当前仍仅有旧preview，新版远程全链仍是NOT_RUN_UNPUBLISHED。
发布是跨越此前明确保留边界的操作，需要用户一次集中确认；没有因“继续”而自动解除该限制。
