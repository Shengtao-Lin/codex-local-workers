# Strata 受监督试用：从这里开始

当前本机编码试用候选是 **task.34**。适用于可信Python工程中的有界实现和补测试。
源码调查可提供线索，完整自主回答资格仍为HOLD，需要Primary逐项核对、修正并整合。
Primary给目标、行为边界和权限，Strata自主查读、实现并按真实检查反馈修复；编码
成功后自动fresh Reviewer，Primary独立验收。不是通用无人值守或已发布的生产默认。

## 1. 使用配套安装包

已纳入版本控制的[试用zip](../releases/strata-task34/strata-task34-supervised-coding-trial.zip)
包含README、install.py、manifest和完整runtime。解压后保持目录结构。
需要已有Strata harness、iq3_s单驻留，以及目标工程可用的Python/pytest/Ruff/Pyright。
安装器不下载模型或依赖。当前doctor观察到服务context131072、并发1；客户端仍用
已测试的65536上下文/12288输出上限，不自动调大。

先使用一份新的隔离工程副本，保留真实项目原有改动；不能覆盖旧.local-agents。

```powershell
$projectCopy = "F:/work/my-project-trial" # 已存在的可信工程副本
$product = "F:/work/unpacked/product"
$python = "F:/work/my-project/.venv/Scripts/python.exe" # 已有工程解释器
& $python "$product/install.py" --target $projectCopy
```

不混用仓库根目录的LM Studio入口或旧preview配置；本入口不启动LM Studio。

## 2. Primary只准备任务输入，不逐步指挥

使用新身份，如`.agent/requests/change-001/contract.json`和同目录`config.json`。
合同写目标、风险、行为/边界、批准读写范围、现有符号锚点及保护/补充测试；
不要把算法或每一步编辑序列当作硬合同。配置写本机连接、版本绑定和工程原有完整
检查。初次以[实际配置](../releases/strata-task34/examples/config.current-machine.agent-runtime.json)
和[已接受合同格式](../releases/strata-task34/examples/contract.example.agent-runtime.json)
理解格式；它们针对agent-runtime-kit切片，不能跨工程原样使用。

- 核对工程的formatter/linter/typecheck和测试命令，绑定它们实际覆盖的输入目录。
- `strata_token_counter`是当前Strata/iq3_s的显式路径与文件哈希绑定，不是API密钥。
  本机可以复用已验证连接部分；安装或tokenizer变化时先核对，不删除绑定来绕过。
- 新补充测试放精确`scope.create`；已有文件用`scope.modify`和稳定anchor。保护测试只读。
- `implementation_ref`绑定具体函数、方法或赋值，不绑定整个class；定位编辑用的
  `edit_targets.anchor`可以是class。task.34提前拒绝已有类引用，task.33的原失败保留。
- 无新身份来充值旧失败、无Git权限、无任意shell或默认联网/递归。只读调查用其独立
  已有profile；编码配置不能随意改成调查配置或相反。

本开发快照已包含安装包；跨机器安装和未知工程族需要另外核对，不由本机成绩自动保证。

## 3. 检查、准备、运行

```powershell
$taskId = "change-001"
$request = "$projectCopy/.agent/requests/$taskId"
$entry = "$projectCopy/.local-agents/strata-task.py"
& $python "$projectCopy/.local-agents/strata-worker.py" doctor --config "$request/config.json"
& $python $entry prepare --project $projectCopy --contract "$request/contract.json" --config "$request/config.json"
& $python $entry prepare --project $projectCopy --contract "$request/contract.json" --config "$request/config.json" --apply
& $python $entry run --project $projectCopy --task-id $taskId --attempt-id first > "$request/cli-first-full.json"
& $python $entry status --project $projectCopy --task-id $taskId
```

无`--apply`的prepare是预览，不调用模型；apply绑定任务。run可能需要几分钟，
外层命令yield后继续等待同一进程，不能重新启动。运行前预登记profile；本机受监督
试用使用task-rework-v1：首段16请求/4有效编辑，每次实改自动完整检查；一次封存
14/4仅用于Primary核实原合同缺陷后的合法续作，不是失败后自动充值。

完整结果位于`.agent/tasks/<taskId>/workflow/runs/first/result.json`，实际diff、
每次检查和原始动作位于同任务`runs/first/`。stdout只是便捷输出。调查没有正式
Reviewer，Primary直接核对报告；不能把调查answered算作编码审查通过。

## 4. 失败和接受

普通测试/静态失败会在原额度内交回Worker；Primary无需每步救场。blocked、预算
耗尽或Reviewer rework时，先看真实原因、实际diff和当前合同。只有原合同内的
确认缺陷才使用原封存额度及有版本绑定的feedback/resume；新要求另作任务决定。
不重跑相同输入或重复抽相同代码的Reviewer直到PASS，不删账本“重置”。

`ready_for_primary`表示等待Primary审查。Primary核对新断言、源码、当前检查、
fresh Reviewer及风险相称的独立关键/整体验收，再明确记录编码接受：

```powershell
& $python "$projectCopy/.local-agents/record-review.py" --repo $projectCopy --task-id $taskId --run-id first --decision accept --summary "独立验收事实和限制"
```

task.34继承拒绝缺失/不匹配的独立PASS或已漂移输入；该门槛不证明语义正确。调查
结论单独记录Primary核对结果，不套用只服务编码交付的record-review。

## 5. 交付和下一个任务

Primary可以读取全部原始成果；不要只信模型总结。候选提供create-only成果导出：

```powershell
& $python "$projectCopy/.local-agents/strata-worker.py" export --project $projectCopy --task-id $taskId --output "$request/export"
```

导出是Worker diff/preimages及检查证据，不自动携带最终接受权，也不自动合并源码。
fresh审查和Primary记录仍在canonical档案。由Primary核对真实diff并决定如何应用，
此入口不操作Git或兄弟工程。

同一安装已验证“接受实现→不同身份只读任务”的连续执行、重复派发拒绝和旧档案
不变；只读任务原报告仍有过度延伸，整体回答门槛HOLD，不能因此取得通用资格。
见[交接](../releases/strata-task34/checkpoint-evidence/corrected-sequential/handoff.md)。
初次仍用隔离副本，不要把旧preview“只换run_id”当新任务。后续任务必须用
不同task_id、独立请求文件和当前源码重新prepare；不覆盖旧合同/config/档案。
不并行writer；后续源码改变不让旧验收自动覆盖新版本。

已记录的语义漏检仍保留。净云节省、通用调查、联网/脚本/递归组合和Coordinator
任务拆分没有由这些编码成绩证明。详细边界见[受监督使用](strata-supervised-usage.md)。

## 给真实项目Primary的启动提示

```text
使用本机Strata受监督候选协助完成下面的目标。先读local-worker-kit的
docs/strata-quickstart.md和当前候选交接，核对安装、模型驻留及工程原有检查。
目标：<用户要完成的真实需求>
可写工程：<本次批准的项目或隔离副本>
保留已有改动和历史，不安装依赖、不commit/push，不更换模型或启用未准入权限。
Primary负责目标、风险、行为边界、批准范围和关键验收；Strata自行定位、实现、
补测试并根据真实检查有界修复，不要逐步代写或给算法。使用独立task_id与请求目录，
不覆盖旧任务、不以新身份给失败充值。implementation_ref使用具体方法/函数。
配置检查通过后走fresh Reviewer；Primary读取完整实际成果，独立核对并整合结果。
普通原合同缺陷按已登记封存预算和canonical反馈续作，新要求另作决定。
记录真实请求/编辑/失败、自修、Reviewer、独立验收及Primary额外介入；不可测成本写unknown。
```
