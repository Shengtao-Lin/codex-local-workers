# Strata Primary return preparation

## 自动绑定返工证据（开发侧辅助工具）

`tools/prepare-strata-return.py` 仅为 Primary 已确认的原合同缺陷生成 feedback，
不派工、不裁决语义、不修改安装或默认。Primary 提供一个 JSON 数组，例如：

```json
[{"id":"boundary","contract_id":"existing-contract-id","text":"已核实的原合同反例及真实观察","path":"src/module.py","line":42}]
```

```powershell
& $python tools/prepare-strata-return.py --project $projectCopy --task-id $taskId --findings findings.json --output feedback.new.json --assistance assisted
```

生成器读取当前 canonical result/ledger，核对输入未变，自动绑定 **host latest_check**
（不是外部反例文件的hash）及精确保留缩进的源码引用。输出使用独占创建；来源过期、
任务活动中/已返工、越界引用或非本合同finding会拒绝。生成后仍须Primary核对，再按
现有resume入口使用；宿主依然独立验证权限、反馈、原保留预算和fresh审查。工具不
决定反馈是否确属缺陷，也不把assisted变成自主成绩。暂未纳入发布安装包。

## 已预选只读续作的证据反馈

同一工具也可为**新任务启动前已选task-v1的investigate**绑定一次证据核实问题。
Primary提供`{"contract_ids":["原有行为ID"],"text":"原合同内需要核实的问题"}`：

```powershell
& $python tools/prepare-strata-return.py --project $projectCopy --task-id $taskId --evidence-request question.json --output feedback.new.json --assistance unassisted
```

工具核对任务已settled/ready、仅执行过首段、原profile/角色、当前来源hash、合同ID和完整结果hash；
拒绝已用续作、漂移、活动任务和新增字段。它只生成feedback，不调用Worker，也不调整权限或预算。
宿主在`strata-task.py resume`时再次独立核对。`--findings`旧用途保持；两种输入互斥。

预先登记、不含答案的同范围核实问题可按实际标unassisted；Primary若给新语义解释、具体修法或缺陷
诊断，必须如实标assisted。不能为了变成unassisted而改名。不支持给已运行的普通独立调查换配置充值。
新工具控制26项通过，覆盖实际冻结宿主feedback_shape兼容；live资格见当前计划的独立批次记录。
