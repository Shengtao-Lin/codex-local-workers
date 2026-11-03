# Primary如何选择并传递Strata技能

技能是按任务选择的可选方法。Primary决定给哪些技能，Strata在可用目录中按需加载，
再自主决定具体步骤。同一个subagent可以承担不同任务，不必为每个skill新增常驻角色或模型。
此目录供Primary选择；不要把整份目录或AGENTS.md注入Worker。

## 选择表

|当前任务需要|选择|当前状态|
|---|---|---|
|目标清楚，工具与合同已经足够|不选skill|正常选择，不代表功能缺失|
|追踪调用、分支、包装/委派关系，解释实际行为|[trace-behavior](../strata-skills/trace-behavior/SKILL.md) 0.1.0|一项真实调查完整加载；核心顺序正确，附加对象修改断言错误，完整报告HOLD；无收益对照|
|核对有限表格中的过滤、计数、汇总与缺失值|[summarize-structured-data](../strata-skills/summarize-structured-data/SKILL.md) 0.1.0|ZIP安装后18行新切片任务正确接受，正文实际加载；单题无技能收益对照|
|跨材料整理证据、完成必要推导并交回紧凑结果|[source-backed-handoff](../strata-skills/source-backed-handoff/SKILL.md) 0.1.1|实际完整加载已验证；小批对照未证明默认加载有收益|
|实现、修复、补测试，或自动fresh Reviewer|当前不传skill|task.34实现入口拒绝非空approved_skills；自动审查链没有本目录的传递约定|

通常选零个或一个；只有方法互补、确实必要时才选多个。专项skill无需再附加通用交接skill。
这是减少重复上下文的选择原则，不把它冒充宿主硬上限：当前接口最多四个。
例如“解释某选项如何影响调用路径”选trace-behavior；“按地区汇总缺失记录”选数据技能；
“修改该选项的行为”仍走现有实现合同与检查，不因它是代码任务就加载调查技能。

Primary可在授权任务内自主选择，不必逐项询问。新技能不能代替任务族资格、权限审批或独立验收；
若实验已经冻结为无skill，保持原样，新的选择只能进入新注册输入。

## 怎样给：使用现有接口，不依赖UI继承

1. 选择前读取所选SKILL.md全文。它应提供可复用方法，不含任务答案、隐藏验收、任意执行指令或新权限。
   冻结文件版本、原始UTF-8字节的SHA256与实际content。已准备或运行中的任务不原地换技能。
2. 当前统一入口只在`kind: investigate`传递技能。在**新任务的独立配置副本**设置
   `experimental_strata_skills: true`；在合同中加入`approved_skills`。不改生产默认配置。
3. 每项字段严格只有`name`、`description`、`content`。名称与文件frontmatter一致，description使用
   对应描述，content为该SKILL.md完整UTF-8文本，包含frontmatter。不要仅给路径、名称或摘要。
   当前description为1–500字符、content为1–12000字符；最多四项、名称不能重复。
4. `prepare`先不带`--apply`核对入口与范围，再按正常流程绑定运行。运行时模型先看到获准技能的
   name/description；调用`kit_skill`后才收到完整正文。Primary可以只提供选择，也可以在任务说明中
   明确要求使用某个已选技能；后者是任务输入差异，比较实验时必须预先登记。
5. 从实际工具观察核对是否加载和内容是否匹配。加载会消耗工具/证据及上下文资源，相关请求照常计入
   总预算。未调用不等于加载失败，也不能记成“使用了skill”。不为强制加载补跑任务。

下面是给现有**新任务草稿**赋值的结构示例，变量`skill_text`必须来自全文读取，
`skill_description`来自对应frontmatter；这不是一份完整合同，也不写入旧档案：

```python
skill_text = skill_path.read_text(encoding="utf-8")
contract["approved_skills"] = [{
    "name": "trace-behavior",
    "description": skill_description,
    "content": skill_text,
}]
config["experimental_strata_skills"] = True
```

版本/hash、选择理由、实际加载与否写入Primary准备记录或registration，
不要往严格的三字段skill对象或顶层合同添加未知字段。可以记录：
`trace-behavior@0.1.0 / source sha256 / behavioral trace / offered / loaded或未加载`。
其他必需任务信息仍在合同，不藏在可选技能里。

不选时省略`approved_skills`或使用空数组，配置保持原已验证值即可。
UI安装只影响其对应会话，不能证明独立kit Worker自动继承。完整手动安装与历史证据见
[加载说明](strata-skill-manual-loading.md)。选择/可用、实际加载、效果改善是三个不同事实。

## AGENTS.md与产品交付

本仓库[AGENTS.md](../AGENTS.md)已加入上述选择路由。它的其余部分仍包含旧LM Studio工作流，
不要把整份文件当作Strata项目的安装模板。外部项目保留自身规则，可合并以下短段；
将目录位置替换为该项目实际可读、已审阅的skill目录和选择指南位置：

```text
Optional Strata task skills
Primary chooses optional method skills by task needs, usually none or one.
Consult the reviewed skill catalog; offer only relevant, frozen content through
the installed entry's supported approved_skills interface. Strata may load an
offered skill when useful and chooses its own execution steps.
Record the skill version/content hash and actual loading separately. Do not
inject the whole catalog, task answers, or overlapping instruction stacks.
Skills never grant tools, scope, budget or acceptance authority. task.34 supports
this through investigate; implementation and automatic Reviewer skill routing
are not enabled. Preserve the existing contract, checks and Primary acceptance.
```

本目录与新增skill未改入旧task.34安装包；另有隔离的[可携带RC](../benchmarks/work/strata-portable-20261031-1/report.md)
已包含技能并完成数据技能实测。行为技能实测见[两项协作结果](../benchmarks/work/supervised-cooperation-20261031-1/report.md)，
不宣称稳定性收益。未来若接通编码或审查技能，应复用相同的显式批准、
内容绑定与加载记录，作为独立运行时改动验证，不通过把方法正文塞入goal/read范围绕过当前限制。
