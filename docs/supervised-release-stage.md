# 受监督版本收敛（2026-10-19）

> 2026-10-22更新：最新用户停止线为weekly used60%，不是下文历史50%；最新实测35%。
> 当前阶段已完成限定安装profile回归、真实项目快照对照、Reviewer正负控、
> Explorer证据定位及一条当前安装版本的Coordinator快照依赖链。
> 有限受监督试用PASS，通用生产HOLD；叙述型Explorer、困难语义修复、
> 未确认Reviewer自动返工不在资格内。旧失败和分母保持。
> 详见[本轮交接与使用边界](packaged-supervised-trial-20261022.md)，不是默认启用通知。

当前用户授权：自主迭代 Explorer/Coder/Reviewer，条件成熟才测试 Coordinator；
weekly used **50%** 停止（2026-10-20用户更新）。本文件初始阶段起点15%是历史；
新窗口本轮实测0%起，最近24%。不 commit/push，兄弟仓库只读，单模型驻留。
旧 R4 HOLD、旧失败及 Reviewer 漏检记录保持；本阶段不是追认旧批次通过。

**最新批准执行顺序：** 用户批准按“安装入口对齐→固定自修→真实切片→条件Coordinator”
自主迭代，weekly50停止；下文旧审批/阶段停点不覆盖本授权。

### 最新阶段结论：固定重复/迁移矩阵PASS，可进入限定快照受监督试用

`bounded-chain-matrix-20261021-1`固定交错顺序：URL重复、新字符串列表去重/渲染、
新题重复、URL重复；模型、安装候选、bridge、预算、检查/接受门全程不变。
每链两单元，**4/4完整链、8/8单元独立接受，两种任务各2/2**。
此前单条smoke不并入本分母；本轮只新增benchmark适配、实验记录和文档，不改生产runtime。
四个参考完整profile、各生产者/消费者负控及八次无模型安装handoff均在live前通过。
Coordinator四次fresh提案都保留正确依赖/范围/风险，可信宿主复制完整验收合同；
这不等于Coordinator从模糊需求发明合同/测试或自行定位代码。

**实际恢复账本：** Coder10请求/10有效编辑/10完整写后检查，另有8次独立起点检查；
6个单元首编辑完整通过，两次URL生产者首编辑被Ruff UP032拦住，均在宿主真实反馈后
自行将`.format`改为f-string再通过。失败attempt和第二次编辑保留，无Primary语义提示/
代写。中途曾仅凭终稿误报为全一次编辑，闭批已明确纠正；以不可变账本为准。
因此本批支持两次该静态错误的自主修复，仍不证明复杂语义恢复。0no-op/协议恢复。
fresh Reviewer8请求/8PASS，0协议或输出失败；Primary逐单元和累计完整审查，
最终URL公私集成5测试、新题6测试及Ruff/Pyright全部通过，源/归档/传输无漂移。

新题第二个消费者`separators=(",", "")`对注册的`list[str]`数组域输出合规，
独立转义/回环检查通过；对象key separator在该域不使用，不临时引入字典要求或强制参考
代码形状，也不把本次资格扩展为任意对象JSON兼容。Explorer本批未调用，不能由C/R推断其成绩。

记录单位窗口共474.311秒（约7分54秒，不含准备/Coordinator/Primary停顿）。
每链仍有分解审批、两次单元审查、最终累计验收，加上Primary合同/测试/定位/分类准备；
云token和主动时间unknown，无Primary-only对照，weekly22→24不是精确成本节省估计。

`trial-eligibility.json`绑定本批decision，授予的只是上述两任务形状的显式受监督快照
试用资格；本有限门已通过，不再无限补题作为隐含门槛。默认Coordinator/同工作区自动调度、
任意repo/复杂任务、Reviewer未知边界检出、旧R4/D2/C4与经济收益仍未放行。
下一步优先在此边界内试用并减少/测量Primary重复准备协调，不无依据地再次改Coder/Reviewer。
完整证据见本批`handoff.md`、`metrics.json`、`observations.json`及每链`integration.json`。

### 前序安装与smoke证据（不覆盖最新矩阵结论）

- `installable-bounded-20261021-1`：从冻结实验抽出runtime-only共享包到`.local-agents/bounded/`，
  新显式`local-bounded-unit.py`/`local-bounded-review.py`使用现有Worker编辑、检查、锁及canonical
  归档，默认正常入口/配置不切换。移除历史sealed观察文件fallback，仍要求确切可信profile与
  canonical capture；Reviewer仍是同一contract-first方法，未换成旧正式Reviewer。
  安装副本无benchmark目录/历史任务目录依赖。旧实验源保持冻结比较，不改旧成绩。
  原LMStudioClient只新增默认None的reasoning_effort传输，原默认payload不变。
- `controls-3.xml`原27项+2子测试通过；实际启动发现新CLI漏写驻留错误结构化报告后，
  仅补typed catch，保留真实reason_code；`controls-5.xml`29项+2子测试通过，含真实安装器
  自测、新旧三题对照、Reviewer原正负控/共享预算、三有效编辑各有写后检查、忙锁与加载
  失败两条负控。首轮回放数组接线错误、controls-4新增测试构造/临时cwd问题均保留。
- 自修批次固定静态F821及first/last-wins行为错误各两次，原合同/保护测试不变；这是已暴露
  合同上的受控错误草稿，不是新holdout。`installed-repair-20261021-1`driver在Popen前因Path
  JSON序列化失败，零模型；`-2`首格被PID18064持有的Muse驻留锁拒绝，零模型，其余NOT_RUN。
  只读复核时进程与锁已自然消失，未删锁或中断他人。修driver/报告后`-3`重新固定，
  **4/4严格及受监督完整链接受**：每格一次有效编辑、一次完整写后检查、fresh Reviewer，
  Primary独立核对全部源码/diff及公私测试、Ruff、Pyright，无运行中语义指导或代写。
  这些受控草稿均一次提案修正，尚未证明多次失败后恢复或未知边界检出。
- 条件真实切片为`application_binding_path`空字符串拒绝与原编码兼容、`request_hash`忽略
  单一顶层调试字段并保留只读canonical_json/输入/嵌套语义。只复制隔离，不改兄弟仓库。
  两题各两次，4/4独立终验且无运行中语义救场才通过；不将准备/接口失败计模型失败。
  `installed-real-transfer-20261021-1`参考完整profile、失败起点及两题离线完整链已通过，
  四格已闭批：**4/4严格及受监督完整链接受**，每题2/2，476.640执行秒，
  Coder四次请求/四次有效编辑/四次完整写后检查，0no-op/协议恢复，无Primary运行中
  语义指导/代写。hash-1的Reviewer首请求4096输出全部耗于reasoning、无报告，第二次
  在原共享错误预算内恢复并通过；原截断证据保留。不是上下文装不下，也不是语义
  不通过后反复抽PASS。其余三格Reviewer各一次请求；Primary逐格检查全部实际diff及
  独立公私测试、Ruff和严格Pyright。小型已定位真实函数，不是上游完整项目部署。
- 只有前述门槛通过才准备Coordinator任务包生成dry-run，不只测调度；分类仍Primary，
  不启用默认Coordinator或自动Reviewer语义返工。未知经济性仍明确unknown。

### 2026-10-21 新阶段：显式协议桥与一条受监督快照依赖链

用户批准继续后，新增独立默认关闭的`coordinator-bounded.py`；不改旧Coordinator验收器、
正常单元入口或新旧状态语义。完整复用host handoff验证，另要求精确fresh Reviewer、
当前已读源码、报告hash绑定的Primary disposition、live来源及逐编辑检查。未知协议、
过期/串错/缺失证据、未合格任务族及无显式opt-in均拒绝，不直接派工或自动接受。
`coordinator-bounded-bridge-20261021-1/controls-6.xml` **128项＋16子测试通过**，
含真实安装器、旧Coordinator、原Reviewer正负控及新桥。早期夹具锚点、导入路径和临时包
缓存污染导致的失败全部保留；修的是新测试隔离，不改旧测试语义。此离线数与旧批不相加。

`bounded-dependency-smoke-20261021-4`固定一条已暴露行为：编码器→路径追加器。
Coordinator从无预分解units的brief正确拆成两单位并保留依赖，Primary审查批准；
两次Coder各一次有效修改/完整写后检查，各一次fresh Reviewer并独立Primary接受，
**2/2单位、1/1受监督快照完整链接受**，单位执行窗口共120.766秒。
生产者快照保持不变；消费者受保护文件精确复制其字节，分发前和闭批时都验证归档与传输。
最终消费者快照全公私测试5项、Ruff格式/lint、严格Pyright通过。无运行中语义提示/代写。
未调用Explorer（路径和问题已明确），分类与最终验收始终归Primary。

前三个准备失败均零live并保留：公私pytest同名冲突；只读消费者起点F401使生产者无法
通过全局静态检查；参考whole-module导入间距I001。只修夹具/参考封装，新批重注册，
不降低合同/检查、不补跑覆盖模型失败。最终live候选与门槛冻结不变。

这是显式Primary监督、独立不可变快照的smoke，不是同工作区自动调度放行；
`coordinator_enabled`每单元仍false。Primary仍准备合同/测试/定位并审批和完整审查，
云token/主动时间unknown，无经济节省结论。旧R4/D2/C4和漏检历史不改。
本批已完整闭合；下一候选应先固定小规模重复与新任务迁移门，再考虑更广入口。
当前停止是注册smoke完成，不是weekly预算耗尽（最近22，上限50）。

### 前一阶段结论：安装限定入口可试用；当时Coordinator执行存在可信接口边界

`installed-brief-20261021-2`复用现有`coordinator-brief.py`，单单元及两独立单元各两次，
**4/4提案经Primary语义审批**，四次请求、约27.72执行秒、0协议纠正、0Worker派工。
未给预分解units，Muse自行选择单元/归属/合同/路径/依赖；宿主从可信目录复制验收条款。
Primary仍准备了详细合同、已定位源码、公开测试及验收目录，经济性尚未证明。
同版本72项离线brief/contract控制通过；`-1`因pytest默认临时目录权限失败（55通过、
17 setup errors），零模型，保留并在新批使用明确workspace basetemp，不降低门槛。

离线`integration-boundary/result.json`证实：现有Coordinator档案验收只承认
`ready_for_review`，新版候选输出`validation_passed_pending_review`；实际真实切片的
Primary已接受记录也保留该新状态。仅变状态的合成控制：旧状态可接受，新状态被
`unit lacks accepted Coder evidence`拒绝；bounded构造器也明确拒绝Coordinator启用。
这是可信接口尚未接通，**不是已测出Coordinator不会分解**。没有改名、伪造旧状态或
绕过守卫；依赖链live **NOT_RUN/未准入**。当前停在明确阶段/信任边界，而非预算停止。

下一步需要单独冻结显式协议桥：验证完整host manifest、当前输入、检查、fresh Reviewer、
Primary接受及plan绑定，保持旧默认行为和未知协议拒绝；先离线负控再谈依赖链。
不以本轮提案通过替代实际执行验收。旧R4/D2/C4和漏检历史不变，生产默认关闭。

### 前期证据（不覆盖上述最新阶段结论）

用户随后批准窄范围产品入口迁移。`explorer-install-20261020-1`已完成：只迁入已验证的
Explorer“必读依赖未读时保留受限读取机会”，未改变默认配置、权限、模型、预算或报告验收。
136项离线测试及38子测试通过（包含真实安装器自测），另一次安装副本Explorer82项通过，
重叠不相加。首轮沙箱拒绝、测试键名错误及首次安装失败全部保留；零Worker调用。
只有Explorer源码及其测试相对本批冻结基线变化，Ruff缓存另列。
机械安装PASS不等于语义/迁移放行：自动语义Reviewer→Coder返工仍未采用，Coordinator仍未准入。

**当前自主执行补充：** 用户明确允许边界内的小修复、离线验证和受限实验自动推进，
不再逐项请批；关键设计/权限/正确性门槛变化才需用户决定，weekly50停止不变。
`limited-family-20261020-2`固定三道新合成局部任务、各两次：labels配置覆盖、unique保持
首见顺序及对象身份、route只读依赖与编码/错误传播。每格同一bounded-source/focused-repair/
static-focus候选、原Qwen/Muse/预算/检查/Primary终验，Reviewer contract-first与显式
请求传输沿用，不新增语义返工。参数澄清：配置seed为low，但实际contract-first首请求
是medium，进入fallback才low；以各格request_profiles为准，安装候选未改变该行为。
此批仅限定任务族试用验证，不冲掉旧难题HOLD或恢复其holdout。
三题参考实现完整profile通过、六格preflight及三次零模型完整链后冻结，live现已全部完成。
每题2/2、共6/6无语义救场与保护漂移才通过该批门；普通失败保留并完成固定顺序，
设施/漂移/安全/时限/weekly50停止，未跑记NOT_RUN。Explorer无实际定位必要，明确未参与，
不从本批推断Explorer或Coordinator能力。Primary准备合同与公/私测试成本单列，经济性未知。
`-1`为准备失败、零live：依赖注解与严格Pyright的合法类型检查冲突；只在新批改注解，未降检查。

该批结果：**6/6严格及受监督接受、每题2/2**，累计494.547执行秒，Coder共6请求/6有效
编辑/6写后检查，0no-op/协议恢复；fresh Reviewer均PASS，Primary核对全部实际diff和独立
公/私测试及完整profile，无运行中语义指导或代写。全部一次提案完成，不能据此证明困难任务
的有界恢复能力或Reviewer未知边界检出能力。来源是新合成小题，不能当真实项目迁移。

`limited-explorer-20261020-1`另计：复制兄弟仓库原样八个源码/测试文件，两问各两次，
**4/4独立核实正确定位**（Agent重复注册、Tool超时）。均fresh非cache命中，真实READ及引用
hash/quote核对；Agent首格未读额外测试引用被拒后自主补读，另一次Tool协议纠正也保留。
这是已有路径约束下的源码/测试定位，不是因果诊断、广域未知仓库探索或Coordinator能力。

随后实际兄弟仓库`_datetime`的新UTC合同迁移，**live全部未运行**：`limited-time-transfer`
`-1`参考测试8项过但fixture lint/private-use失败；`-2`修夹具后参考完整profile通过，
无模型Coder检查通过，Reviewer handoff因`capture target differs from trusted function binding`
拒绝。观察包装器不等于被改函数，严格绑定正确生效；不放宽绑定、不伪造事实、不临时改
Reviewer。该datetime任务暂不属于现有证据接口已支持范围，不记模型失败，不冲掉旧分母。
这是实验事实适配层的范围，不是已经证明生产runtime不能处理datetime；本阶段没有借题
重写表示协议。新fixture的准备故障也说明Primary准备成本尚未解决，不能只报模型成功率。
以上给出的是“JSON可表示、合同完整的小型单函数任务 + 受限定位”的独立正证据，
尚不是可复制到任意真实项目的稳定产品版本。当前候选仍显式实验入口，生产默认未改。
闭批后只读观察到兄弟仓库errors.py外部追加两个类，未影响冻结副本或所引行；来源writer
unknown，另存`upstream-post-batch-observation.json`，不刷新旧输入或改分。

2026-10-20进度：宿主短期执行记忆固定对照A6/6、B5/6，未采用；受控补读固定对照
注册检查A/B各6/6但读取0次，未证明取证收益。后者Primary反例另发现3条Mapping语义缺陷，
不覆盖注册检查成绩，也不是Reviewer漏检（两批Coder-only）。离线控制分别17/33，不合并分母。
Reviewer4096输出批次执行3格后原时限关闭；6144条件首对负控输出耗尽、正控正确PASS，
其余18格条件NOT_RUN，仍HOLD。FalseMap恢复、机械补源码和初始阶段标题均未完成修复；
实际已提供源码，不应继续把失败全部归咎于上下文缺失。既有Explorer的locate-only无法产出
因果解释，切到原investigate模式后单例解释正确；冻结该本地笔记的E→C辅助对照
已完成A0/2、B2/2严格完整链接受，仅证明该已暴露案例的团队辅助效果。
实验入口遗漏的指导/继承反馈字段已恢复，三个离线继承控制通过，生产默认未改。
Reviewer阶段参数四格对照默认1/2、显式2/2，不足以判定唯一根因；
`reviewer-json-recovery-20261020-1`固定20条控制全部判断正确，24请求/约901执行秒，
均未用新增JSON恢复；不能据此宣称恢复分支或稳定版本已经合格。
`explorer-inherited-recovery-20261020-1`在35项离线控制和两次无模型完整链后，
开始测试每格fresh Explorer→继承Coder→检查→fresh Reviewer，不由Primary中转语义指导。
仅零编辑普通no-progress允许恢复，父调用已用预算扣除；两格现已严格完整链接受。
每格fresh研究、子Coder一次编辑和完整写后检查、fresh Reviewer、Primary独立终验；
中途Primary未补语义指导或代写。仍是一个已暴露任务的两份错误实现，不算新题迁移。
Explorer主因2/2正确但完整报告均有事实/行号瑕疵，不能宣称E/C/R整体放行。
用户随后批准独立Reviewer→Coder实验（不含生产启用）。原文转交四格均产生语义退化，
fresh Reviewer三次正确拒绝、一次未完成，无最终错误放行，候选不采用。
只给Coder定位字段四格均零编辑：真缺陷未修复，误报未造成退化；不能算完整链接受。
本地Explorer的跨库JSON因果诊断仍漏判；隔离终态前置读取修复使依赖读取0/2→2/2，
但有效报告1/2且该次语义仍错，不能算角色放行。49项同版本离线回归通过，不混入live分母。
生产逐项disposition规则、默认及Coordinator状态未改；安装入口机械迁移已单独批准并完成，
不是继续围绕旧题叠提示或把报告格式成功当能力合格。
详见主计划最新入口与独立批次记录。无生产默认启用、无Coordinator放行。

目标：显式启用、范围明确的受监督完整链。Primary 提供合同与最终验收，
Worker 可有界恢复；持续语义指导或代写计 assisted/takeover，不计自主完成。

## 固定顺序与决策

1. 保存未提交文件哈希和候选源快照；离线实现独立受监督验收入口。
   复用 canonical handoff 验证及逐项 disposition，不修改生产默认行为。
   必须绑定完成的 Reviewer、当前源、全部检查和 Primary 独立验收。
   漏 finding、过期/串错证据、真实缺陷、未解决争议、检查失败均拒绝。
   记录 strict 与 supervised 两种结果，禁止以反复抽样获得 PASS。
2. 冻结该入口与现有函数输出 Coder/Muse Reviewer；准备3个未暴露局部任务，
   每题2次，共6格，完整检查与 Primary 独立终验。任务不从旧失败改名。
   Explorer 对真实定位问题独立计分，失败不被 Coder 覆盖；若调查没有意义，
   不以虚构定位题充数，而另行注册具备真实搜索空间的定位控制。
3. 全6格无错误最终接受/安全漂移，且各题2/2受监督接受、无语义救场，
   才授予这些任务族有限试用资格；任何普通失败保留并完成诊断顺序。
   每格分析，冻结批次中不改候选/标准；后续修复另建版本并写清失效证据。
4. E/C/R 条件通过后才注册 Coordinator：从批准计划生成可执行包，
   不能只测试调度；分类及未合格任务归 Primary。暂不启动此阶段。

Coder保持 Qwen，Reviewer保持Muse，24576上下文、并发1；Explorer先核对现有配置。
沿用12请求、3有效编辑及3写后检查、900秒Coder、4096输出；Reviewer沿用
16请求/4协议错误/600秒/4096输出。单元总2220秒，6格批次上限14400秒。
停于40% used、安全/保护漂移、基础设施故障或需要用户判断的新架构边界。
普通质量失败不触发同格补跑，也不扩大预算或改变模型。

## 成本与可靠性

每格记录加载/执行/检查/审查可观测时间、请求/编辑/反馈/no-op、误拒/漏检，
以及 Primary 准备、定位、语义反馈、裁决、接管。不可测值unknown。
本阶段没有Primary-only对照，不声称节省百分比。
旧已暴露正反例仅作离线门控控制，绝不恢复holdout身份。
预期准备负担：一次性入口/任务/保护测试；运行中应仅审批及终验。
如果仍需频繁专门探针裁决，即使代码通过，也单独报告经济性未成立。

## 2026-10-20 受控恢复候选

已闭批：bounded-source 六格严格/受监督4/6；API参考六格仍4/6，JSON0/2。
后者两次行为10项通过，但未修复类型错误，不能接受。原 Explorer2/4，
同题只加真实路径导航仍2/4。全部旧失败保留，不合并分母。

`supervised-repair-phase-20261020-1`使用同一宿主与预算，明确区分实现和写后失败修复阶段；
失败证据仍为真实原始检查，没有给具体修法。17项离线控制与三题完整无模型链通过。
JSON两格都通过第二次有效编辑修复类型错误；第一格完整接受，第二格遗漏tuple，
Reviewer检出且独立验收复现，记失败。Reviewer建议递归set/frozenset的部分无合同依据，
Primary另记裁决，不送回Worker。本批其余格尚在执行，不能宣称最终通过率。

本批闭合后才准备组合候选：复用机械生成的完整API参考和显式修复阶段，
同组六格、同模型/预算/检查/Reviewer，检验两项已观察效果能否共同改善完整链。
这是额外信息和流程呈现的组合检验，不能单独归因；全部题均已暴露。
6/6门槛不变，仍须新任务迁移、独立Explorer资格及安装控制才讨论产品放行。

Explorer下一格试验直接复用现有`explorer_required_citation_paths`，将已给的导航路径
登记为证据义务；空搜索后的已有恢复会要求实际READ_FILE，不新增工具或运行时分支。
四格已冻结，三项离线控制通过（含两个子用例）；首次沙箱临时目录权限失败另存，
正常权限重跑同一控制通过。必须等当前C/R批次结束，遵守单模型驻留。
