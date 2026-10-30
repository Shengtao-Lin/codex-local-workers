# 当前试用合同与配置

合同描述目标、行为和权限，不描述逐行修法。以下仅是schema形状，路径、anchor、
身份、合同和检查必须由Primary针对真实项目修改；prepare通过也不代表任务已验收。

```json
{
  "schema_version": 1,
  "task_id": "project-local-change",
  "feature_id": "project-feature",
  "kind": "implement",
  "goal": "在已批准模块中完成一个明确的行为单元，保持列出的兼容行为。",
  "deliverable": "实际源码与补充测试、当前完整检查、独立审查和最终Primary验收。",
  "scope": {
    "read": ["src", "tests", "pyproject.toml"],
    "readonly": ["tests/test_existing_contract.py", "pyproject.toml"],
    "modify": ["src/example.py"],
    "create": ["tests/test_worker_supplemental.py"]
  },
  "risk": {"feature": "medium", "unit": "medium", "integration": "medium"},
  "required_behavior": [
    {"id": "behavior", "text": "替换为可观察的正常、异常和边界行为，以及必须保持的原有语义。"}
  ],
  "owned_contract_ids": ["behavior"],
  "dependencies": [],
  "acceptance_criteria": [
    {"id": "checks", "text": "保护输入不变，完整项目检查与有意义的补充测试通过，最终结果绑定当前源码。"}
  ],
  "implementation": {
    "edit_targets": [{"path": "src/example.py", "anchor": "def existing_function("}],
    "focused_tests": ["tests/test_existing_contract.py", "tests/test_worker_supplemental.py"],
    "supplemental_tests": ["tests/test_worker_supplemental.py"],
    "validation_profile": "project-strict"
  }
}
```

高风险兼容、并发、事务等任务不能因为这个示例写medium就降低实际分类。
保护测试应列真实精确路径，不将整个tests目录声明readonly后又允许在其中创建新测试。
缺失依赖或不清晰需求先修订合同，不要求Worker猜测或暗中扩大权限。

调查任务将kind改为`investigate`，只批准read材料，删除implementation和写入权限。
required_behavior与acceptance_criteria仍必填。缺少证据可诚实回答unknown，不能编造
运行效果、未读的上游保证或“未显式调用等于绝不会发生”的保证。

## 配置不是权限本身

复用本机已校准Strata配置：iq3_s、显式localhost端点、Node/harness绝对路径、
observed-v1版本引用、真实tokenizer路径和hash。保持Coordinator关闭与单模型驻留。
项目自己的Python、Ruff、类型检查及完整回归命令必须加入可信profile，不能只跑小测试。
模型不选择自身权限、检查标准或预算，也不能通过新attempt获得新额度。

统一入口需要`experimental_strata_task: true`。普通只读精简报告另外显式选择：

```json
{
  "experimental_strata_report_receipt": true,
  "experimental_strata_report_binding": "observed-line-v1",
  "experimental_strata_investigation_delivery": "investigation-v1",
  "experimental_strata_report_repair": "finalize-v1",
  "experimental_strata_answer_transport": "compact-v1",
  "experimental_strata_continuation": "task-v1"
}
```

这些是普通调查profile开关，不要复制到Reviewer或能力工具组合；实现任务也不需要它们。
可选能力遵守独立的任务授权和资格，不能为取得更多预算而填写不需要的能力。
Skill只是批准范围内的可读指引，不替代宿主硬门槛；当前实现任务不接收approved_skills。

## 反馈与接受

Primary保留完整输出和第一次失败。实现的每次有效修改由宿主自动检查；首次绿色不
代表最终接受。fresh Reviewer不能运行代码，也不能替Primary批准功能。
普通调查若需一次原合同内证据争议续作，必须绑定前次结果、当前源码和原任务总账，
不得将隐藏测试或参考答案改造成运行中提示。新事实/算法/代写另记assisted。

已暴露数据库并发调查的失败不会因为普通调查通过而撤销。尚未验证通用语义权威、
任意终端、模型生成脚本执行、网页与可写代码执行组合、深递归或Coordinator拆解。
