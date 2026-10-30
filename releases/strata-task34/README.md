# Strata 受监督编码试用版 · task.34

用本机iq3_s处理可信Python工程中的有界实现与补充测试。Primary给目标、行为边界
和批准范围，Strata自主读取/搜索、编辑、补测试并有界修复；宿主运行完整检查，
fresh Reviewer后由Primary独立验收。不是无人值守通用版，也没有自动接受。

## 使用

需要已经安装的Strata和可运行的工程Python/pytest/Ruff/Pyright，保持单模型驻留。
解压后不要拆散product内的安装器、manifest和runtime。在新的隔离工程副本安装：

```powershell
& $python "$bundle/product/install.py" --target $projectCopy
```

目标必须存在且没有.local-agents；安装器不覆盖、不下载模型或安装依赖。其他工程
应由Primary核对原有检查和批准范围。examples是本机agent-runtime切片的实际格式，
包含当前机器路径及tokenizer绑定，不是跨工程默认，不能直接复制任务原样重跑。
模型连接和tokenizer变化需核对；不要删除版本/输入绑定来绕过错误。

为每个任务准备不同的.agent/requests/<taskId>/contract.json和config.json：

```powershell
$request = "$projectCopy/.agent/requests/$taskId"
$entry = "$projectCopy/.local-agents/strata-task.py"
& $python "$projectCopy/.local-agents/strata-worker.py" doctor --config "$request/config.json"
& $python $entry prepare --project $projectCopy --contract "$request/contract.json" --config "$request/config.json"
& $python $entry prepare --project $projectCopy --contract "$request/contract.json" --config "$request/config.json" --apply
& $python $entry run --project $projectCopy --task-id $taskId --attempt-id first > "$request/cli-first-full.json"
& $python $entry status --project $projectCopy --task-id $taskId
```

prepare预览不调用模型。run可能需数分钟，等待同一进程，不重启同一任务。结果在
.agent/tasks/<taskId>/workflow/runs/first/result.json；实际diff和每次检查在runs/first。
Primary能读取全部成果，而非只能读模型总结。ready_for_primary不等于接受。

当前显式task-rework-v1首16请求/4编辑，每次实改触发宿主写后检查；缺测试、零测试
或失败均不能交接。一次封存14/4仅供经Primary核实的原合同缺陷按canonical反馈
合法续作，不是失败后充值。无实改不重复抽相同审查直到PASS，不删旧账本重置。

Primary审查源码与新断言、核实当前完整检查/fresh审查并做独立验收后，明确记录：

```powershell
& $python "$projectCopy/.local-agents/record-review.py" --repo $projectCopy --task-id $taskId --run-id first --decision accept --summary "独立验收事实和限制"
```

接受记录会核对当前输入、完整检查及真实独立PASS。implementation_ref只绑定具体
函数、方法或赋值；编辑定位anchor可以是class。task.34将已有类引用在prepare阶段
提前拒绝，不等到模型调用后失败。它没有放宽审查或增加模型权限。

新身份可以在同安装准备后续任务，保持旧档案；已验证实现→只读任务顺序与重复
prepare/run拒绝。不并行writer，不覆盖旧合同，不把旧版本检查当新代码的接受证明。
需要导出时使用现有strata-worker.py export；导出是Worker事实，不转移最终接受权。

## 证据与边界

同版本629项宿主控制（含9项新前置校验控制）和118文件安装核对通过；实际错误
合同在0模型调用时被拦。正确绑定后的已暴露生命周期任务：Coder7请求/3编辑，
Reviewer7请求/一次引用纠错后PASS；Primary独立574项项目检查及实际NativeAgent
展示/旧名拒绝/新handler调度核对通过，没有Primary生产代写。不是盲benchmark。

后续调查核心追踪有用，但原报告把正常完成/after hook过度推广，按固定口径HOLD；
Primary用实际反例纠正后另列。整体通用/自主调查门槛仍未通过。此包提供受监督
编码试用，调查只作需要核实的研究线索；不能把“已执行完”当“每句话可靠”。
旧HOLD/失败保持，无净云节约百分比。联网、任意脚本、递归与Coordinator拆分
没有由这些编码成绩准入。未发布、不改生产默认；examples含本机配置路径。
