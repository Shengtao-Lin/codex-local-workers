# Strata 输出与宿主归因复核（2026-10-31）

本次复核已有档案，不启动模型、不补跑失败、不修改旧成绩或发布包。weekly used
观测为 20%，用户停止线 30%。当前适合受监督使用，尚不足以证明通用稳定或净云成本节省。

## 最新三题：模型回答不完整，不是宿主错误拒绝

证据批次：`benchmarks/work/compact-transfer-20261031-2`。

|题目|实际输出与检查|最终判断|
|---|---|---|
|cache/lru_cache 文档|宿主 ready_for_primary；14 个引用匹配；3 请求、0 协议恢复。范围、并发限定正确，但未完成必要跨段推导。|Primary hold_incomplete；无 Reviewer，非 runtime 拒绝。|
|penguins 数据|16 行、5 个缺失 sex、15 个非空质量之和 56025、最大 4675 及关联字段正确。|Primary 接受；2 请求。|
|textwrap 源码|空白正则、共同前缀、无 tab 展开、indent 的 isspace 区别正确；Primary 独立 4 项源码片段控制通过。|Primary 接受；6 请求；Worker 未执行代码。|

不合并此前三对格式实验的 3/3；此次 11 请求、100.734 秒不含 Primary 准备和终验。

文档题的 `runs/first/packet.json` 要求比较两种装饰器的参数可哈希要求，而非只摘抄各自小节。
`native-action-1-1.json`、`native-action-1-3.json` 与对应 host 观察确认 Worker 已读
1–120、151–270 行。它引用第 34 行 `Returns the same as lru_cache(maxsize=None)`，
也引用第 166–167 行参数必须可哈希，却说 cache 小节没有显式要求，将其列为 gap。
关键字顺序问题也承认等价关系可供推导，却继续将适用性列为缺口。

最早能确认的偏离发生在最终回答的证据整合：需要的两条前提已经获取，没有被工具拒绝或截断，
也没有用尽额度；模型未给出由它们支持的完整答案。它没有捏造“cache 不要求可哈希”这一相反结论。
因此保留“不完整”合理，把它称为代码失败、幻觉或宿主误拒都不准确。
`host-tool-result-4.json` 明确为 `report_recorded, acceptance:false`；最终语义判断来自
`cache-docs-decision.json`，采集脚本的 `primary_decision:PENDING` 不是最后决定。

任务交付要求同时写了 `Omit additional relationships, conclusions and background commentary`。
结合“exact observed source / evidence gap”措辞，可能强化了只摘录、不推导的倾向；这是提示设计
上的歧义和可验证假设，尚非因果结论。原文并未禁止题目必需的推理，单次失败也不证明模型没有该能力。
简洁输出曾减少无关错误，不能据此次不完整就全面撤销它。

## 已确认的宿主阻碍与尚未消失的模型错误

- `read-window-native-replay-20261031-1`：旧 Click 实际请求第 26–149 行（124 行），
  实现路径的原宿主直接拒绝并收费；候选首次返回 26–145 行及续读标记，禁读和收费不变。
  这是真实机械阻碍的修复证据，但仅为无模型原生重放，不能证明旧 Click 最后能修好。
  task.34 的只读 compact-report 路径原本已有长窗口裁剪；不要把实现路径限制泛化到所有任务。
- `compact-transfer-20261031-1`：明确批准的 CSV/RST 被输入 manifest 后缀过滤，准备阶段未调模型。
  字节相同的 txt 别名可以读取。`explicit-text-input-20261031-1` 隔离候选通过范围/数量/大小负控
  和原生读取控制，尚无原后缀候选的模型 live 成绩。这是输入适配限制，不是模型不会读 CSV/RST。
- `mixed-stability-20261031-2` 的 Click：完整 1259 测试通过、Reviewer PASS，原封存语义探针
  仍 6/8，两个空格被压成一个。语义偏离早于最后读取失败；不能将它全部归咎于宿主。
  gcd 则在暴露递归深度反例后，利用原保留预算修复并独立通过，表明有界返工有实际价值。

因此要分开统计任务语义、不完整交付、宿主阻碍、Reviewer 漏检和实验准备错误。
此前采集脚本曾用 CRLF/LF 常量比对误报；已根据 canonical 字节核对同一次结果，非 Worker 失败。
最新文档题无同类误报证据。跨路径的能力不一致是维护风险，但不是上述文档缺答的已证实根因。

## Skill 实际参与情况与窄更新

逐一查看三题的所有 `native-model-request-*.json` 和动作：只有
`kit_block/kit_read/kit_report/kit_search`，没有 `kit_skill`、技能名称或正文。
不能把这批成绩称为“已加载技能后的效果”。

复核发布代码 `releases/strata-task34/product/runtime/.local-agents/strata/task_contract.py`：
第 101–103 行已向只读入口传递 `approved_skills`；实现分支仍拒绝非空列表。
`readonly_host.py` 要求显式开关、固定正文并计入证据动作；原生入口只在目录非空时暴露加载工具。
故应复用现有只读接入，不能根据过时手册重新实现。未审计或声称当前 UI 安装副本自动更新。

仓库 skill 从 0.1.0 更新为 0.1.1，只有两项方法提示：沿可核实关系作有条件推导、精简不省略
请求的答案。没有嵌入旧题答案、改验收或增加权限。该版本尚无 live 效果证据，不替换安装副本。
手册同步纠正入口描述；旧 skill 的 Git 历史与冻结实验记录保持。

## 下一步判断依据

优先核对实际加载，再在新注册的匹配任务中区分“明确关系足够推导”与“确实缺少前提”。
仅加载更新技能或仅澄清交付措辞应分开比较，避免同时改两处后无法归因。旧题只用于诊断。
不需要为此次只读缺答加编辑权限、角色或预算；也不能因此忽略 coding 的独立验收漏检问题。
当前最强结论是：有用成果、可修的机械阻碍、未稳定的语义整合同时存在，不能用一个总 PASS/HOLD
解释所有层级。Primary 能补完这道题，但这份额外推理成本不能回填为 Worker 独立完成。
