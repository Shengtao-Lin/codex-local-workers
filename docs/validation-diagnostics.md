# 失败测试后的静态诊断

默认情况下，focused tests 失败会跳过后续 configured checks。可信配置维护者可为适合失败诊断的单个命令开启 `run_on_test_failure`：

```json
{
  "id": "ruff-check",
  "argv": ["{python}", "-m", "ruff", "check", "src", "tests"],
  "run_on_test_failure": true
}
```

该对象放在 `.local-agents/config.json` 的对应 `validation_profiles` → profile → `commands` 数组中。省略或设为 `false` 保持默认行为；必须是真正的布尔值。不是 Coder 的 VALIDATE 参数，也不允许模型提供新命令。

只有失败测试具有可用、非零执行数的 JUnit，且验证输入未变化时，才会继续这些显式标记的诊断。没有标记的命令不会顺带执行；某个诊断改变输入会阻止后续诊断。缺失 JUnit、零测试、全跳过或输入漂移仍不能得到有效提交。

诊断结果不会覆盖测试失败，不计编辑进展或修复周期，也不允许 FINISH_SUCCESS。即使 Ruff format 检查报告格式问题，失败测试分支也不会自动格式化或自动重跑验证。测试通过后的原有检查/格式修复流程不变。

优先用于 Ruff `check`、`format --check` 等只读检查。该标记是可信配置维护者对执行时机的明确授权，不是隔离机制：命令、pytest 和导入代码仍拥有宿主 Python 进程的实际权限。不要给有副作用的脚本盲目开启。

更完整的诊断不等于模型已能正确修复语义缺陷；自主能力和 Reviewer 能力仍需各自的冻结验收证据。
