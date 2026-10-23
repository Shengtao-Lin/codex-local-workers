# Strata 实现子代理（受限预览候选）

它在本机实现一个已明确合同的 Python 函数：按需读源码/测试、提交修改，宿主
自动格式化、运行检查，并把失败交回同一个有界会话。Primary 负责计划、权限、
保护测试和最终独立验收。当前不是通用自主编程产品，也没有测出云端用量节省。

这是与旧 E/C/R 并列的执行入口，共用编辑、验证和归档底座；不启动 LM Studio、
Explorer、Coordinator 或 Local Reviewer。不要求安装 LM Studio。源码中保留的
旧传输模块是共享宿主依赖，不会由此入口加载其模型或调用 lms。

**工作区限制：本版每个单元使用一份新的隔离项目副本。** 准备材料和便捷输出
仍是 create-only 的固定路径；仅换 run_id 不代表可以在同一副本连续接新任务。
不要删除旧 `.agent`/policy 来“重置”预算。Primary 在隔离副本完成独立验收后，
再审查是否把那一份实际 diff 合回真实项目；本版不自动同步或操作 Git。

## 安装

需要已有的 Strata、其 harness `0.2.1-alpha.3`、Node，以及目标项目已经可运行的
Python/pytest/Ruff/Pyright 环境。安装器不下载模型、运行包管理器或修改依赖。

在 kit 根目录运行（替换目标路径）：

```powershell
python -B tools/install-strata-preview.py --target C:/work/my-project
```

只创建目标的 `.local-agents`；该目录已存在则拒绝，不合并、不覆盖。升级请先在
新的隔离副本试装，不能直接覆盖现有项目的 Worker 文件。原生 SDK 默认 profile、
shell、网络搜索、skills 脚本、Git 和递归子代理均未开启。

## 准备任务

Primary 准备 schema-2 packet，明确风险、一个目标函数、合同和真正可执行的保护
测试。现有文件须提供稳定 anchor。`readonly` 是可读不可写；`forbidden` 完全
不可读。模型不决定自己的权限，不能修改保护测试、签名、其他函数或任意导入。

根据 [配置示例](../examples/strata-preview/config.example.json) 填写实际路径、
目标函数与项目原有检查。三条静态检查必须真实运行，不能为了放行换成空命令。
当前 profile 固定包含 Ruff format、Ruff check 和 Pyright，并运行 packet 的所有
focused tests；最终仍由 Primary 运行完整项目/私有验收。

准备 `.agent/spec.json`，显式列出允许补读并绑定版本的真实文件（最多125个，含
目标、focused tests、依赖及已有包的 `__init__.py`）：

```json
{
  "schema_version": 1,
  "source_paths": ["src/your_package/__init__.py", "src/your_package/module.py", "tests/test_module.py"],
  "target": {"path": "src/your_package/module.py", "module": "your_package.module", "symbol": "target_function"},
  "family": "pytest-source-v1",
  "cases": []
}
```

packet 还须把生成的 `acceptance/source-policy.json` 放在受保护的只读范围。
这不是某种函数类型的观察器，不需要为每个任务另写 typed capture producer。
显式清单不代表自动发现了所有依赖；Primary 必须保证合同与检查覆盖充分。

在目标项目根目录先预览，再创建运行材料：

```powershell
python -B .local-agents/local-bounded-prepare.py --packet .agent/packet.json --config .agent/config.json --capture-spec .agent/spec.json
python -B .local-agents/local-bounded-prepare.py --packet .agent/packet.json --config .agent/config.json --capture-spec .agent/spec.json --apply
```

预览不写文件、不跑命令、不调用模型。apply 仅创建缺失材料，已有输出则拒绝。
以实际回执 `next_inputs` 指定的 packet/config 为后续输入，不要误用未绑定的原稿。

## 运行与验收

Strata 先保持一个 `iq3_s` 驻留模型、并发1、context至少65536（当前实测131072）。
该入口不加载/切换模型；本机还运行其他服务时，由使用者保证它们没有另驻留模型。

```powershell
python -B .local-agents/strata-worker.py doctor --config .agent/prepared/RUN_ID/config.json
python -B .local-agents/strata-worker.py run --packet .agent/prepared/RUN_ID/packet.json --config .agent/prepared/RUN_ID/config.json
```

doctor 检查安装哈希、显式 Node/harness 路径、受支持版本和当前本地驻留状态，
不证明任务正确。run 每次须唯一 run_id；重复运行同一身份会拒绝，不能借新调用
隐式重置失败预算。模型变更、旧源码 hash、越权、保护输入漂移都应停止。

有界资源：宿主动作≤12、实际模型请求≤8，两者共享≤18；补读/搜索≤6次；
每次读取≤120行、搜索≤10条。最多3次有效编辑、1次起点检查+3次完整写后检查、
900秒总时限。单请求最多12288输出 tokens（含请求的 thinking4096），声明64K
上下文，固定当前已测试采样。不能自动续跑、自动提权或同证据反复抽审直到PASS。

进程退出0和 `validation_passed_pending_review` 只表示宿主检查及前端收尾完成，
**不是最终接受**。Primary 必须核对当前 canonical archive、实际 diff、完整独立
检查和保护输入；高风险任务完整审查。任何后续修改会使旧验证失效。没有 fresh
Local Reviewer 时，不能按旧 E/C/R 的小风险简化审查政策自动接受。

证据：`.agent/tasks/<task_id>/runs/<run_id>/` 下保留请求、响应、native session、
每次验证、前后 diff/preimages、预算与 `native-settlement.json`。便捷 report 不
代替 canonical gate；`native_http_requests` 才是实际模型请求计数，不把内部
`model_requests:0` 的离线形状宿主传输误报为零模型调用。

## 已知边界

- 只有已记录的单函数任务族可受监督使用。新任务先隔离试用，不自动获得资格。
- 多文件、测试编写、自动架构分解、Coordinator、Web/skills、跨调用恢复未开放。
- 同版本离线失败草稿→修改→检查恢复已测；若 live 全部一次改对，不声称证明了
  自主语义恢复。准备合同/测试和最终审查的 Primary 成本并未消失。
- 这不是操作系统沙箱：测试、插件及应用导入具有本机 Python 的实际权限，仅适合
  可信本地仓库。不要对不可信项目提权运行。

具体发布判定以对应冻结批次 decision/handoff 为准；未通过前不得称稳定正式版。
