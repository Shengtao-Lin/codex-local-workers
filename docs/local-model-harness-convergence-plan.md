# 本地模型 Harness 适配研究与收敛执行计划

## 2026-10-23 当前授权与 Strata 独立评估

最新用户停止线为 **weekly used 40%**，覆盖下文历史30%等停止说明。
用户已授权对新安装的 Strata IQ3_S 做独立测试及模型适配；本阶段允许的
模型变化限于这个显式实验，不更改生产默认或兄弟仓库。优先单 Strata
常驻、角色 fresh context；LM Studio 混用与切换须另有实测优势和驻留控制证据。
执行细节见 `docs/strata-evaluation-plan.md`；新记录在
`benchmarks/work/harness-convergence/strata-*-20261023-*`，旧成绩不改写。
初始输出4096的批次为基础设施HOLD；适配配置四格全部通过配置检查，最终
散列2/2接受、消息ID0/2接受（Primary发现falsey int子类边界、Reviewer漏检）。
原 Reviewer/生产/Coordinator 放行结论不因新模型通过局部检查而升级。

编制日期：2026-10-13；执行状态修订：2026-10-18。对象：接手本仓库的 Primary Agent 与结果复核者。

## 2026-10-22 历史阶段结论（预算已被上方2026-10-23更新覆盖）

**当日用户预算：weekly used 达到30%时停止；当前已由上方40%更新覆盖。**
这条当时覆盖下文“无上限”或旧停止线；已关闭实验的原预算记录不改写。
保持模型、单驻留、兄弟仓库只读、不commit/push、生产默认不变及历史保留。

**本日自主执行历史（预算已被顶部30%停止线覆盖）：** 当时用户授权持续自主迭代，
当时没有 weekly used 停止线；当时实测22%，仅作账户观测。生产默认、模型、单驻留、
兄弟仓库只读、不commit/push、独立验收和全部历史保留不变。

- `receipt-routing-20261022-1`离线42控制通过：紧凑回执不再把已完成Reviewer的单元
  导航为再次local_review；保留原Coder阶段字段，不影响模型输入、派工或接受。
- `project-identity-chain-20261022-1`提案正确但两单元都分给Primary，两个下游NOT_RUN。
  已知路由资格表没有送给模型；独立`coordinator-route-evidence-20261022-1`固定A/B
  分解均2/2正确，原输入A本地路由0/2、附真实目录B2/2，但条件链`-2`相同请求再次
  选择Primary，HOLD、两个下游NOT_RUN。不能把目录传递的窄收益当稳定路由证明。
- `coordinator-host-route-20261022-1`为新的默认关闭实验：模型只提议职责/依赖，
  宿主以绑定完整brief的Primary目录建议owner；不匹配仍归Primary，不自动派工。
  41离线控制及Ruff通过；两次live提案均正确、一请求、无协议纠正。这个确定性owner
  是宿主职责，不算模型能力。仍需Primary核对语义、不确定性、权限与最终接受。
- 条件链`project-identity-chain-20261022-3`上游Coder一编辑完整配置检查通过、fresh
  Reviewer一请求PASS，但独立完整项目149通过/2失败：实验复制器漏带alembic迁移
  文件，测试runpy报FileNotFoundError。无Primary接受、下游NOT_RUN；这是夹具故障，
  不是已证实的实现语义错误。原模板/reference169通过没覆盖安装工作区的完整依赖。
- `project-identity-chain-20261022-4`已接受1条受监督链、2个单元：完整复制及保护清单
  修复后，安装离线上游151/组合169测试通过；live两Coder各一请求/编辑/写后检查，
  两fresh Reviewer各一请求PASS，Primary逐个完整审查后接受；最终169项非数据库项目/
  私有/调用方/跨单元测试及Ruff/Pyright通过、保护清单零漂移、接受的上游原字节传递。
  本地单元合计约119秒，Primary无运行中语义提示/代写；准备及审查成本仍未测量。
  真实数据库并发/已持久化旧散列迁移未验证。前三批HOLD与所有NOT_RUN不变。
- 新增显式安装API`coordinator-routing.py`，不改旧probe或默认开关。
  `coordinator-routing-install-20261022-2`安装41控制、5脚本化精确请求/结果等价控制、
  Ruff及diff检查通过。首轮40过/1失败为测试夹具把a*64哈希“改”为同值，历史HOLD
  保留；修正为真变化且加断言，runtime候选未改。没有把离线成绩当live新增成功。
  `installed-identity-repeats-20261022-1`两条固定安装重复均完整接受，四单元各一编辑/
  写后检查、fresh Reviewer各一请求，零no-op/协议恢复/Primary运行中语义提示或代写，
  每条最终169项非数据库完整项目/私有/调用方/跨单元测试及静态检查通过。仅重复资格，
  不新增任务族或holdout信用；全部旧HOLD保留。当时usage观测26%，当时尚无停止线。
- 固定批次闭合后，`routing-preflight-20261022-1`确认并修复Primary验收配置错误延迟
  到模型协议恢复的问题：8负控原先消耗脚本化调用，现在全部调用前拒绝；复用旧schema，
  合计54控制和Ruff通过（含重叠旧控制及安装请求/结果等价，不相加为live成绩）。
  有效请求/模型/预算/权限/验收均不变，未增live。新API仍默认关闭。
- `routing-cli-20261022-1`离线安装入口通过：现有`coordinator-limited.py propose`
  新增显式`--routing-catalog`选项，调用同一宿主路由API；不加选项保持旧协议。
  66安装控制及13已有等价/前置控制通过，Ruff/格式/diff检查通过；零live新增。
  只方便生成提案，不自动批准、派工或接受，旧approve/dispatch没有新快照链资格。
  最近实测weekly used27%，当前停止线30%；之前已关闭记录不改写。
- `current-archive-controls-20261022-1`正控复制归档因实际执行路径绑定被拒绝，
  实验准备HOLD、六负控NOT_RUN，不能算Worker失败；不放松路径验证。
  独立`read-only-archive-controls-20261022-1`原归档只读正控通过，配置/合同/
  任务族/符号/run/依赖字节六种变化被拒绝，历史清单未变；不是审查语义检出成绩。
- `proposal-drift-evidence-20261022-1`修复新提案入口在源码并发变化时丢失已完成
  模型结果的诊断缺口：两离线负控红转绿，67安装控制及Ruff通过。失效结果只存
  为不可批准的独立诊断，同身份不可重跑；成功/旧协议与派工验收权限不变。零live。

**2026-10-22 较早自主迭代记录（预算已被顶部30%停止线覆盖）：** 用户当时取消 usage 上限，
要求持续自主判断、修改和受限实验，直到用户叫停；当时实测 weekly used 16%，
只是历史账户观测。模型、单驻留、兄弟仓库只读、不commit/push、默认关闭、
历史保全和独立验收边界不变。不能再把下文60%或“阶段闭合”当当前停止授权。

- 安装入口反馈已修复两处确定性遗漏：flat适配丢失静态定位回调，以及pytest失败时
  已实际执行的supplemental静态检查未进入当前源码绑定的定位反馈。离线负控通过；
  已暴露静态与混合故障对照均A/B全通过，**没有证明完成率提高**。
- `checked-research-20261022-1`已暴露frame恢复1/1完整接受，但有引用错误；同策略
  identifier迁移0/2、`checked-static-research-20261022-1`类型修复0/2。
  后者两格25行为测试及Ruff均过，但Pyright仍失败，Reviewer均NOT_RUN；
  一格采纳Explorer建议后修掉原错误又引入冗余条件，一格诊断指错变量而no-op。
  当前证据不支持把因果Explorer恢复当通用产品功能。
- `reviewer-input-observation-20261022-2`原/增补输入观察两臂各2/2正确裁决，
  新臂增加调用/耗时且一次观察账目冲突；无裁决增益，**不采用**。
- `usage-completion-transfer-20261022-1`原新任务重复0/2：首次实现各过25行为测试，
  两处Pyright可选类型错误后连续原样提交。源/hash/真实错误已送达，不能继续归因于
  反馈缺失，也不能把通过行为测试说成全部验收通过。

下一窄对照为`host-block-trial-20261022-2`：复用历史片段诊断正证据，在当前宿主自动
检查/交接底座比较整函数提案与模型选择1–3个精确非重叠片段；只变输出接口/内存拼接，
不变合同、事实、权限、3有效编辑/3写后检查、12请求、原Reviewer和最终验收。
两份已暴露失败草稿×两次×两臂=8格，普通失败保留且继续固定配对；安全/基础设施/
漂移/总时限或用户叫停则停。没有新题信用；有可核查收益才进入未暴露任务迁移。
无收益则不为“像Agent”保留复杂度，不继续同题加提示。候选仅benchmarks显式入口，
生产默认不变。`-1`因实验源码lint清理在零live时闭合，全部准备历史仍保留。

**该对照现已闭合：** `host-block-trial-20261022-2`实际8/8执行，整函数A0/4、片段B2/4；
frame为A0/2、B2/2完整独立接受，usage两臂均0/2。B一次先加casts再撤回原失败版本，
后三提案全为重叠且原样的文本块，机械拒绝，没有正确改法被挡住的证据。旧记忆候选
`execution-memory-20261020-1`曾A6/6、B5/6，不因这次回退就默认启用。
严格B4/4门仍HOLD；不把窄收益写成全通过。按预登记条件分支，仅作固定候选的诊断迁移：
`host-block-transfer-20261022-1`两份真实兄弟源码的新行为合同（请求散列忽略顶层易变字段、
URL绑定参数校验并保持编码），两题×两次×两臂8格，模型、预算和Reviewer不变。
这是新行为任务，不是陌生整个项目；未执行格不计失败，不用结果替换旧HOLD。

迁移现8/8执行：两臂Coder各4/4一编辑通过完整检查；严格完整链A3/4、B4/4。
A唯一未接受是Reviewer把`dict.items()`取得引用视为“检查忽略值”，与冻结参考实现及
同AST的另一次PASS存在解释冲突；Primary记录contract_revision/replan，不改代码、
不重抽Reviewer。B仅通过该窄迁移门，不证明Coder增益、一般可靠性或云成本节省。
下一候选默认关闭：连续两次原样提案且当前检查失败时，由宿主在**同一调用剩余额度内**
只切换一次整函数→精确块输出。检查/编辑/总请求/时间不重置，原Reviewer不变，
先负控再固定live。正常单元不增加调用；未确认Reviewer意见不触发自动修复。
旧类型修复失败族仍未合格，不把此恢复策略当R4全放行。

`noop-block-recovery-20261022-1`现8/8执行闭合：A2/4、B3/4完整独立接受；
旧失败草稿A0/2、B2/2，原始起点A2/2、B1/2。原B4/4门仍HOLD，不提升安装资格。
两次同调用自动恢复真实成功，预算未重置；但另一次实现后留下Python 3.11不支持的
f-string反斜杠表达式，3次编辑各有检查，最后回到旧失败版本。15行为测试过、静态检查
失败，Reviewer未启动。发现Ruff `invalid-syntax`规则未进入精确定位解析（原始错误仍有），
下一步只修复此确定性遗漏并做独立重放/对照，不把它宣称为唯一根因，不放宽版本/验收。
本批前usage观测从54%变2%，原因unknown、未请求reset，不能据此推断节省。

`ruff-syntax-focus-20261022-2`4/4执行：原解析A2/2、修复解析B1/2完整接受；
B一次准确定位仍两次原样提交。离线解析修复保留，但**无完成率增益证据**，该live门HOLD。
`-1`只是夹具准备被故意保留的坏语法拒绝，零live历史不删除。不再围绕此已暴露题调提示。
下一步改善可选Primary紧凑执行回执：完整档案不变，直接列停止原因/检查/实际恢复次数/
Reviewer状态及证据路径；不变模型输入、验收、预算或重试授权。先离线同输入等价，
再安装验证；不能把输出变短算作已证明节省云usage。

`primary-receipt-20261022-1`现2/2安装smoke完整独立接受；两格各一编辑/写后检查和
一次fresh Reviewer，没有新题信用。显式`--compact-output`保留完整报告和审查进程日志，
只缩短返回给Primary的导航信息。另经8个失败负控修复Reviewer返回绑定：非零退出、
旧身份、篡改/缺失canonical或未完成记录不能借方便路径的旧PASS返回成功；最终接受
仍由独立record-review门把关，不声称发现历史最终误放行。14个绑定控制、13个安装
等价控制、67个集成回归通过（有重叠不相加），之前比较夹具失败也保留。
下一步固定当前安装候选，把已通过真实源码切片的行为置于完整隔离项目及实际调用方
测试中，区分局部实现与项目集成，不再围绕旧语法题堆提示或扩大默认资格。

`project-callers-20261022-2`完整项目调用方批次4/4执行、2/4接受，整体HOLD：
散列2/2各过165独立测试及全静态检查/fresh Reviewer；消息整数零ID两次都是一编辑后
两次no-op，5失败/157通过，静态检查过，Reviewer未启动。**准备阶段资格描述更正：**
此消息行为在`prepared-slice-live-20261022-1`本就0/2未合格，不能与已通过的
make_sample_id revision归一化混淆，也不能当精简输入到完整项目的退化因果证据。
原注册/分数不修改，更正在该批provenance-correction.json；第一批零live E402准备失败
也保留。停止重复同题调提示，保持任务族路由边界；继续修正安装使用与证据导航的
确定性问题，不能以功能开关或一句“单函数”授予未验证能力。

用户批准按分支计划自主处理普通阻塞，weekly used 上限 **60%**；本轮开始32%，
最新实测35%。本阶段已闭合，停于**限定范围受监督试用门通过**，不是预算耗尽。
生产默认配置、模型及单驻留不变，兄弟仓库只读，不commit/push；历史失败不改写。
执行入口与完整边界见 [本轮证据交接](packaged-supervised-trial-20261022.md)，
机器裁决见 `packaged-release-20261022-1/decision.json`（位于统一实验目录）。

- 已安装产品profile的三题重复回归6/6；完整真实项目快照的已暴露改动2/2，
  每格151项独立测试及全部静态检查通过。两种分母不合并成新题成功率。
- Reviewer正控1/1、真实退化负控2/2：检出空白revision错误归一化、严格True退化为
  truthiness；先前两次准备失败保留。不能由此推出未知缺陷检出已解决。
- Explorer叙述调查仍HOLD；实际诊断中语义结论对但引用错一行，runtime success
  未算资格成功。复用已有宿主摘录的定位模式，两道不同定位题2/2，零协议错误；
  **只授予已知路径/符号锚点下的证据取回资格**，因果判断归Primary。
- 当前flat-v1安装profile与既有受限Coordinator快照链兼容：正确拆分、2/2单元独立接受、
  6项最终集成及全静态profile通过。不是同工作区自动调度或模糊需求自主设计资格。

本轮修复的是可核实机械问题：真实strict schema的旧union仍返回数组，改用显式默认关闭
的flat tagged输出；CLI加载超时只有通过原生API全部原驻留不变量才可继续；Explorer
任务证据义务可由Primary显式指定，缺证据报告给实际补读路径，既有一次报告恢复也可处理
显式source-only任务。类型/范围/hash/签名/完整检查/独立审查和最终接受门均保留。
宿主调度修复不等于模型语义能力修复；ASCII修复等旧失败任务族仍未合格，
未确认Reviewer意见不能自动当修法交给Coder。后续只在已授予范围试用；扩大范围需单独
资格证据，不把不断补题变成这次有限门的新隐含要求。Primary准备与审查成本仍显著，
云用量节省未知。没有正在运行的live批次。

**2026-10-20 当前有效入口（优先于下方所有历史状态/预算）：** 用户批准按上下文分层、
宿主恢复调度方向自主迭代，weekly used 停止线更新为 **50%**。本轮实际从0%开始，最近24%；
不能拿上轮30%或旧预算计算本轮消耗。保持原模型、单模型驻留、生产默认关闭、兄弟仓库只读、
不commit/push、全部历史与现有改动保留。未授予通用/生产稳定或默认Coordinator启用。

**最新固定矩阵结论（优先于下方旧停点）：** `bounded-chain-matrix-20261021-1`
原候选/模型/预算/合同不变，两类任务各两次，4/4受监督快照完整链、8/8单元独立接受。
实际Coder10次请求/有效编辑/写后检查：两次URL生产者被UP032拦住后自主修复，其余
6单元一次完整通过；早期“一次编辑”进度误报已纠正，原失败及账本保留。
Reviewer8次fresh PASS，Primary逐单元/累计独立验收，无运行中语义提示/代写。
限定任务形状的快照试用门已通过，见本批`trial-eligibility.json`；不再把无穷补题当该有限
门的隐含要求。仍不等于同工作区自动调度、通用任务/Reviewer检出或经济性放行。
Primary仍准备合同/测试/定位/分类并每链作四次审批/审查决定，成本收益未知。
下一步优先限定试用与降低/测量重复协调成本，不继续无失败证据地改C/R。

**此前2026-10-21执行补充：** 用户批准显式桥接下一步后，
独立`coordinator-bounded.py`的同版本完整离线门128项＋16子测试通过。旧验收器/状态/
单元Coordinator开关不改；只读桥要求完整当前host事实、fresh Reviewer及报告绑定的
Primary接受，不派工或自动接受。`bounded-dependency-smoke-20261021-4`一条已暴露
编码器→路径追加器快照链已完整独立接受：Coordinator正确分解及依赖，2/2单位，
最终全公私测试和静态profile通过；精确只读传输、两个不可变归档复验通过。
三个零模型准备失败保留，不改旧HOLD。该成绩只是一条受监督快照smoke，不能宣称重复
可靠性、新题迁移、同工作区自动调度或节省Primary云成本。详见受监督阶段文档。

**前一阶段补充：** 用户批准“安装入口对齐→固定自修→真实迁移→条件Coordinator”。
`installable-bounded-20261021-1`显式可安装入口的同版本离线门已通过：最终controls-5为
29项+2子测试，包含真实安装器、新旧模型实质输入/账本对照、Reviewer原正负控、三次编辑
与三次完整写后检查及驻留错误负控。默认入口/配置不切换；不fork Worker编辑/验证/归档核心。
固定四格自修`installed-repair-20261021-3`前保留`-1`driver序列化和`-2`驻留锁拒绝的零模型
记录；不删除实际锁，不中断其他批次。`-3`现4/4严格及受监督独立接受，无运行中语义提示或代写；
四格均一次有效修改，不能据此证明多轮困难恢复。真实兄弟源码迁移四格也已独立接受4/4，
其中一次Reviewer输出耗尽后在原预算内恢复，失败原样保留。随后Coordinator四次任务分解
提案均经Primary审批，未给预分解units，未派工；72项离线控制通过。
阶段结论：受限安装入口获正证据，但依赖链仍未准入。现有Coordinator只认旧ready状态，
新候选为pending-review协议且显式拒绝Coordinator启用，离线边界控制已确认。
不能改状态名绕过门；需要单独冻结、负控验证的可信协议桥，尚未更改该信任边界。
详见`docs/supervised-release-stage.md`及`installed-brief-20261021-2/integration-boundary/`。

**最新自主推进结果（优先于历史“下一步需批准”等句）：** 用户明确要求边界内的小修复、
离线控制和受限实验自动推进，不逐项请批；不扩大权限、不降低验收、不启用Coordinator。
`limited-family-20261020-2`三道新合成小任务各两次，完整C→检查→freshR→Primary终验6/6，
各题2/2，6Coder请求/6编辑/6写后检查，494.547执行秒，0语义救场/代写。原准备失败`-1`
保留。`limited-explorer-20261020-1`两道原样兄弟源码/真实测试定位各两次4/4，单独计分。
仅支持上述受限任务族与路径约束定位；一次编辑成功不证明复杂恢复，正例Reviewer通过
不证明未知缺陷检出，不恢复旧难题holdout或改旧HOLD。详见`docs/supervised-release-stage.md`。
尝试真实`_datetime`UTC迁移时，在无模型阶段发现datetime观察包装器不等于被编辑函数，
被canonical capture严格target绑定拒绝；`limited-time-transfer-20261020-2`记NOT_ADMITTED、
零live，不算模型失败。这是本次实验事实采集适配范围的限制，不能泛化为Worker runtime不能
处理datetime。无需用户决定小修复，但不把扩大事实表示协议混作本批同一候选。
不为强行运行而放宽绑定或临时改Reviewer。生产默认及已冻结候选不变，
实验性完整链通过不等于可安装入口或任意项目产品放行。

**最新授权补充：** 用户已批准独立实验验证一次Reviewer→Coder返工，以下旧“未批准”
仅是上一阶段历史停点，不再表示本次实验被阻止。仅隔离副本提供显式permit入口，
生产逐finding Primary disposition规则不改，不伪造Primary缺陷确认或接受记录。
`reviewer-bounded-rework-20261020-2`固定四格：真实JSON缺陷两次、已知parse_message
误报两次，均已暴露，不是holdout。12项离线资格/负控、四次默认拒绝/授权继承控制及
真实缺陷参考完整链通过；13项独立参考测试另计。父证据在原目录只读核验，子验收在
隔离目录重新执行；-1准备失败（绝对路径绑定）及零live记录保留。
父子Coder合计12请求/3有效编辑/3写后检查/900执行秒等额度不补满；只给一次子调用。
建议原文不经Primary语义筛选，不等于缺陷已证实；新代码仍须完整检查、fresh Reviewer
及Primary独立终验。误报允许安全拒绝/无修改，不算修复成功，不重抽相同代码Reviewer。
普通失败保留并完成固定顺序，安全/设施/漂移/时限/weekly50停止。
该四格现已完成：宿主检查4/4绿，但4/4实际语义退化，最终接受0；fresh Reviewer三次
正确返工，一次因报告协议错误及两次输出耗尽而未完成，无最终错误放行。
JSON两格修复tuple却照建议过度遍历set/frozenset；误报两格引入dict/list兼容差异。
旧四项兼容探针未纳入固定13测试，是准备/覆盖缺口；另存探针结果，不改原分母。
原样报告候选不采用，父失败及全部子结果保留。

下一窄候选`reviewer-locator-feedback-20261020-1`：同四起点、顺序、模型、预算、
权限和检查，仅Coder看到的反馈机械投影为finding/contract ID、路径/行号/类别；
移除解释与修法，不由Primary判断哪条真。canonical packet仍保留原文，fresh Reviewer
的方法及收到的原始反馈不改。15项离线控制与四次继承入口控制通过，实际请求已验证
投影字段、硬合同和原报告保留；原父归档及起点hash一致。四格已闭批：两真缺陷均
两次相同提案、零编辑，旧tuple漏检仍在；两误报也零编辑，独立检查和历史兼容探针
确认原正确源码未变。这是安全不修改，不是修复成功；fresh Reviewer全NOT_RUN。
真缺陷严格接受0/2、误报新退化0/2，仍未达到采用门槛。
这是顺序进行的已暴露诊断对照，不能宣称随机因果、新题迁移或放行。

随后仅做现有Explorer调查，不给旧解释/修法、隐藏测试或正确补丁：

- `reviewer-causal-evidence-20261020-2`：两任务各一次；运行success2/2，核心结论
  正确1/2（兼容任务无已证实缺陷正确，JSON漏判tuple）。运行成功不算语义正确。
- `reviewer-dependency-evidence-20261020-1`：只补实际Python3.12.10原始json依赖，
  并要求读取；两次都在必需依赖未读时被report-only门锁住，实际依赖读取0/2，
  因而不能判断“补依赖是否有效”。两次原失败保留。
- `explorer-read-prerequisite-20261020-1`：只在隔离副本修复前置读取与终态报告阶段
  顺序，保持模型/输入/问题/16turn/8read/6error/600秒不变。5项离线正负控通过；
  实际依赖读取变为2/2。有效报告1/2，而该报告仍错误断言JSON无缺陷；另一格未完成
  引用报告，语义不计分。两次都实际读了encoder1–200行，其中84行明确list/tuple→array；
  最后有效报告请求7121tokens/32768上下文。无上下文满的证据，不能将剩余漏判归为
  尚未读到文件或patch失败，也不能泛化成模型永久无能力。
- 怀疑过“typed citations与校验矛盾”，核对现有代码及测试后排除：已有逻辑会将
  已验证typed citation机械加入findings，无需再实现。该假设已另存，未改引用门槛。

没有启动后续Coder转移：因果证据门槛未通过。最终同版本离线回归49项通过，分别覆盖
实验permit、前置读取、默认宿主路径、反馈交接和剩余额度，不与live分母混算。
原R4 HOLD、Coordinator未准入、生产默认及兄弟仓库边界不变。

**最新产品入口决策，已授权并完成机械迁移：** 不再围绕旧两题叠提示或自动转发语义建议。
沿用既有能力路由及Primary最终裁定，Coder内的可信检查→有界修复继续自动；
未被独立证据确认的Reviewer语义意见不自动成为修法工单。用户随后“继续吧”已单独批准
将确定性机械修复迁入可安装入口（不改变默认启用状态），先安装级回归再做限定任务族验收。
这不是降低旧R4门槛、追认失败或放行Coordinator；批准不包括自动语义返工或全局启用。
`explorer-install-20261020-1`现已闭批：
仅`.local-agents/explorer-runtime.py`前置读取门和对应测试变化，其他生产文件及配置hash不变；
136项离线测试与38子测试通过，其中包含真实安装器完整自测。另一次安装副本Explorer82项
通过，两组重叠不相加；JUnit174计入38子测试，不是174项互不重叠测试。
首次沙箱临时目录权限失败、新增测试错用预算键导致的首次宿主/安装失败均保留。
只修测试键名为现有`max_explorer_turns`，未扩大真实预算。原始保全记录包含Ruff缓存变化，
`preservation-final.json`另列缓存与交付源码，未隐藏原始记录。
本批零Worker调用；当前仅Muse驻留（24576、parallel=1）。机械安装PASS，语义仍HOLD，
Coordinator未准入。`decision.json`、`handoff.json`、`metrics.json`及前后diff在该批目录。
运行经济性与云用量节省仍未证明，Primary主动时间/精确云tokens未知。

新证据分层记录：

- `execution-memory-20261020-1`：17项离线控制通过；固定12格 Coder 对照全部完成。
  A6/6、B5/6独立配置/保护检查；B请求10→8但漏tuple遍历，未达到采用条件。
  仅最近三次宿主观察历史的候选保持可选，不作为默认，不再围绕该失败调提示。
- `evidence-loop-20261020-5`：33项同版本离线控制、三题合规参考与六次无网络完整链通过。
  新隔离parse_message/mapping/sequence，固定12格全部完成；A/B注册检查各6/6，但B读取0次，
  取证能力未被实际运用，不能归因或默认启用。Primary事后源码复核及独立反例确认
  mapping-A-1/A-2/B-2用truthiness跳过FalseMap非法键检查；原注册成绩不改，
  Reviewer未运行，不能称Reviewer错误放行。四个离线准备失败目录保留，均0模型调用。
- `supervised-explorer-required-20261020-1`：已暴露两问/各两次4/4，仅已知路径的引用定位，
  不代表未知仓库自主定位或Coordinator合格。
- `static-focus-matched-20261020-1`：当前版本绑定的真实静态定位A2/4、B4/4，窄诊断通过。
  `supervised-repair-phase-20261020-1`完整链5/6仍HOLD；不与Coder-only成绩合并。
- Reviewer实际请求过去未发送reasoning_effort，宿主探针确认默认high，显式low能够生效。
  `reviewer-wire-20261020-2`执行3/20：负控17输出耗尽，正控18/19完成PASS；
  原14400秒批次时限已到，关闭HOLD，17格NOT_RUN，没有重置时钟。
  `reviewer-output-6144-20261020-1`只增加每响应输出4096→6144，已完成条件首对：
  负控17两次耗尽输出仍无报告，正控18完成正确PASS。其余18格条件NOT_RUN，HOLD。
  负控的源盲预测六项均正确；后续source review的medium/low都将输出用于reasoning，
  没有content/tool call。实际输入约6383 token，不是已证明的上下文溢出；不继续加输出上限。
- `mapping-recovery-20261020-1`：同合同增加已确认FalseMap反例为保护测试，固定四格0/4，
  每格两次相同提案/0编辑；不是重复验证有错代码直至PASS。
- `failure-source-20261020-1`：A/B各0/4；B机械提供批准失败测试当前源码和hash，
  实际包含`__bool__`定义仍未恢复。缺源码不是唯一原因，不继续扩大窗口或叠提示。
- `initial-repair-20261020-2`：两臂都得到完整失败源码，仅改变初始任务标题；
  首四格A0/2、B0/2，另四格条件NOT_RUN。B的一格曾将迭代改成`.keys()`，
  但保留错误truthiness guard；不能笼统写成全部0编辑，原decision措辞另有纠正文件。
- `explorer-trace-20261020-1`：原locate-only协议成功定位但禁止模型写因果解释，
  因果资格不可评价，属于Primary模式选择不匹配，不是OSS诊断失败。
  `explorer-trace-20261020-2`复用现有investigate模式后，OSS正确解释bool→跳过检查的因果链，
  引用/当前hash和只读边界经Primary核对。单个已暴露案例，不代表通用诊断放行。
- 发现精简Coder入口遗漏已有`implementation_guidance`字段，已在实验入口仅非空时传递，
  明确标为不可信建议、不是硬合同。`explorer-assisted-repair-20261020-1`固定匹配输入四格完成：
  无诊断A0/2；同一冻结本地Explorer因果笔记辅助B2/2通过检查、fresh Reviewer与Primary严格终验。
  不是两次独立Explorer调查或Coder独立诊断；8项离线控制与两次无模型完整链另计。
  以`scoped-decision.json`为窄实验结论，不覆盖旧HOLD，不转授产品资格。
- `inherited-feedback-fix-20261020-1`：精简实验入口也遗漏了已有`review_feedback`和
  `_inheritance`，已仅对非空字段恢复传递。三个离线继承控制验证当前检查和历史区分、
  父归档未变；零模型，不据此声称自动返工有效。生产runtime/默认配置未改。
- `reviewer-effort-compare-20261020-1`固定四格：默认参数1/2、显式阶段参数2/2。
  显式负控与此前失败source输入字节相同，输出完成仍不同，不能将偶次失败归结为
  某一个上下文或配置因素。无错误PASS，样本不足以单独采用参数变更。
- `reviewer-json-recovery-20261020-1`已完成原冻结20条Reviewer控制；13项离线控制和
  一次完整REPORT JSON格式兼容探针通过。新增候选只在两次输出耗尽、尚无完整判断时，
  从原16请求/4错误/600秒/4096输出池内允许一次改格式恢复；这是新恢复策略，不是旧预算原样。
  16/16原控制与4/4已暴露真实切片判断正确，当前引用已核对；无误拒或错误PASS。
  共24次实际请求，约901秒执行时间，全部原生完成，JSON恢复0次。
  窄控制通过，不证明新恢复分支的live收益，不默认采用，不给Coder/完整链/R4或生产信用。
- `explorer-inherited-recovery-20261020-1`：29项宿主/预算/交接控制、6项路由控制及
  两次无网络继承完整链通过。固定两份已暴露mapping错误起点，各调用一次新鲜Explorer，
  原样传入不可信研究笔记，经现有继承包再调用Coder、检查及fresh Reviewer。
  仅零编辑两次no-op父调用可自动进入；父+子Coder共享12请求/3编辑/3写后检查/
  12格式化/2协议恢复/900执行秒，父已用额度扣除。两次起点检查显式另计，
  Explorer600秒、Reviewer600秒独立沿用。两格已完成且严格完整链接受2/2，子调用各
  1请求/1有效编辑/1写后检查/0no-op；中途Primary语义反馈与代写均0。
  fresh Explorer主因解释均正确，但一条混入相矛盾陈述、另一条自由文本行号不准，
  完全准确研究报告0/2，不能由Coder成功覆盖。父失败和原始笔记均保留。
  结论仅是已暴露单任务的恢复机制成立，不代表迁移、稳定E/C/R或Coordinator放行。
  下一处权限边界：若要宿主自动将Reviewer语义返工送回Coder，会改变现行逐finding
  Primary disposition要求；当前未批准，不自行改变。当前weekly4%/上限50%，非预算停点。

前述Coder-only诊断的Reviewer与最终完整链接受均NOT_RUN，不是产品放行。
原始证据、registration/metrics/decision/handoff位于各独立批次，模型未收到隐藏验收修法。
完整原始档案归宿主，Primary看全局与异常；Worker仅看当前工作集的方向仍是待验证设计，
不能把“增加记忆/工具已实现”写成稳定性收益。Coordinator未准入。

**历史2026-10-19/20执行入口：** 用户授权自主收敛受监督
E/C/R，条件成熟才进入 Coordinator，weekly used 上限40%。见
[受监督版本阶段](supervised-release-stage.md)。`supervised-release-20261019-4`完整六格
受监督4/6、严格3/6；一条真实 Reviewer 误报经 Primary 源码/已有检查裁决，严格 replan 不改。
后续 literal-feedback 批次遇到 Windows cp936 读 UTF-8 报告的实验入口故障，停止且保留。
`supervised-bounded-20261019-1`修复显式 UTF-8 读取及安全两种源格式后，六格全部完成，
严格/受监督均4/6（ids2/2、raw2/2、json0/2），整体仍HOLD。
`supervised-reference-20261019-1`增加完整本地API参考的六格正在执行；JSON两格行为10项通过，
但类型检查失败且未有效恢复，不能接受。其余未闭批前不得宣称最终成绩。
Explorer独立四格已冻结，尚未执行；Coordinator未准入。生产默认/模型/验收未放宽。
旧失败、已暴露身份、设施中止与NOT_RUN均保留，不能合并为一个成功率。
实际 weekly used 最近26%，不是停止线；以下旧20%/15%与停止说明仅代表历史阶段。

**2026-10-19明确批准后最新结论：** `function-normal-repeat-20261019-1`固定四格全部执行，
Coder4/4一次提案/一次编辑通过宿主及独立检查，严格完整链仍2/4。
request_keys两次Reviewer PASS并Primary接受；single_content两次同源误报rework：
将要求保留的旧list转换行为当新缺陷。Primary源码/4项隔离探针确认误报并作hash绑定裁决，
仍守原PASS门槛记replan，不强行接受、不重抽Reviewer。见该批live-handoff/live-diagnosis/
live-metrics/live-decision；早期authorization-hold与decision是历史准备状态，不是当前停点。
weekly used14→15%，上限20%，停止于Reviewer硬否决/Primary证据裁决的关键设计选择。
未改门槛，R4 HOLD/R5未准入，无Coordinator、生产启用或commit/push；历史漏检保持。

**2026-10-19最新执行：** `normal-task-repeat-20261019-1`已闭批2/4，request_keys2/2、
single_content0/2（函数输出与模块协议不符，零编辑），旧失败不改。离线重放两种唯一函数：
一份行为13通过但Pyright失败，另一份嵌回原模块后原全部检查通过，零模型/零live信用。
Primary曾误读JSON转义，已追加primary-evidence-correction，原review不可变。
新`function-normal-repeat-20261019-1`函数输出/宿主嵌回候选12离线控制通过并冻结，
但主机审批拒绝新live，要求明确授权；4格全NOT_RUN，不得绕过或计模型失败。
见 [函数输出阶段](function-output-stage.md) 和该批authorization-hold/handoff。
weekly最新观测14%/20%，停止原因是主机授权边界，不是预算或能力结论；R4 HOLD/R5未准入。

**2026-10-19正常任务准入核对：** `normal-task-readiness-20261019-1`确认当前模块守卫
拒绝正常源码已有的hashlib等导入，即使提案原样不改也失败；发生在模型请求前，非模型失败。
原冻结pins无漂移。新增独立guard原型16离线控制通过，尚未接入Worker，不改冻结候选。
详见 [正常任务候选准入](normal-task-candidate-readiness.md)：提交确认窄接入及条件四格，
真实CLI离线控制通过并冻结后才live。模型0调用，R4 HOLD/R5未准入，weekly实测13%/20%。

**2026-10-19能力边界核对：** 用户批准尝试受限能力路由；见
[能力路由边界](capability-routing-boundary.md)。本阶段只做离线证据核对和既有路由守卫控制，
没有启动新live/Coordinator。request_keys、single_content历史各2/2不转授当前consolidated候选，
messages_output仍1/2；limit正确legacy起点仍0/2，Primary算法辅助仍1/2。
当前候选未获得新增直接派工资格，R4 HOLD、R5未准入；不把目录整理称为稳定性放行。
本轮weekly used实测13%，沿用用户20%停止线。下文批次的旧状态/预算仍为当时记录。

**2026-10-19最新：** 用户已批准的实验Harness收敛完成，`consolidated-harness-20261018-1`。
单一Coder控制器直接复用WorkerRuntime，真实CLI离线17控制通过（模型0调用）；固定已暴露4格live0/4。
12请求/4真实编辑及4写后检查/8no-op，无协议或基础设施故障。T2两格仍3个Pyright错误，
后续提案重复，第三编辑/验证机会有余量；T1原样复制错误frame。旧Reviewer漏检保持，Reviewer本批0次。
R4 HOLD、R5未准入、生产不变。weekly used12%/20%，下一步是能力/产品边界选择，不再追加同题小变体。
当前统一实验入口、逐格证据及边界见该批handoff/decision和docs/consolidated-harness-stage.md。
以下“尚需批准Harness收敛”属于此前状态，已被最新授权与结果取代。

**最新阶段结论：** `behavior-unit-20261018-3`固定8/8完成，A0/4 B0/4；B9次文本编辑均有写后检查，
仅T2两单元最终AST变化，imports实际先删再恢复，类型错误5→4→3但仍未通过。Reviewer0次。
离线重放全部B安全提案的3种AST（含被协议拒绝payload），可信格式化后仍0个完整检查通过。
明确存在模块格式/协议噪音及实验适配耦合，但未发现被单纯机械门槛挡住的已观察正确补丁。
R4仍HOLD，旧Reviewer null漏检保留。weekly used12%/上限20%，固定方案未过，停于下一研究方向选择。
建议先收敛实验Harness而非继续追加暴露题live；尚未实施该更大调整。详见该批decision/handoff。

**最新用户已批准继续设计对照：** [受限行为单元与完整诊断](behavior-unit-diagnostic.md)。
仅实验允许目标函数体+精确stdlib import，补齐同版本可信静态诊断；Reviewer/模型/验收不变。
weekly used上限20%，本次起点11%，离线控制通过后固定8格；不改生产默认/旧成绩，不启动R5。
以下“需批准下一设计”是此前批次停止时状态，已由最新批准更新。

**当前追加授权：** 用户批准自主实验/迭代，weekly used停止线更新为20%（实测起点10%）。
按 [反馈修复与审查边界诊断](feedback-recovery-diagnostic.md) 单独检验no-op回执与Reviewer已知漏检。
不修改旧成绩/冻结候选；先离线控制后固定8格恢复诊断及2格Reviewer控制，不启用R5或生产默认。
下文15%及已结束批次停止说明为历史状态。

**本阶段已完成：** `feedback-recovery-20261018-3` 有效8格回执对照A0/4 B0/4，
16请求/0编辑/16no-op；B真实回执已核实。独立Reviewer正负控制各一次均PASS，
负控null退化由Primary两项探针拒绝，正控两项通过；不并入旧14测试分母。
无效入口批次3执行/5NOT_RUN和所有离线/启动故障独立保留，不能混入模型成绩。
当前weekly used11%/上限20%，停止于任务单元/审查责任的设计选择，不是预算到线。
下一步需审是否批准扩大当前单函数限定为有界行为单元及完整静态反馈；尚未实施或启动新live。
证据见该批decision.json、metrics.json、handoff.md；R4仍HOLD、R5未准入。

**最新已批准 live 结论：** `bounded-evidence-prep-20261018-1` 固定12/12完成，无补跑。
最终独立完整链接受 A0/6、B2/6，B 的 READ/SEARCH 使用0次；不支持将差异归因于实际取证。
17次编辑全部有写后检查，16次 no-op；Reviewer 三次 PASS 中一次 null 转换退化被 Primary 拒绝。
R4仍HOLD，R5未准入；无基础设施失败或最终错误接受。latest weekly used10%/停止线15%。
方法限制、逐格证据与成本见本批 `live-handoff.md` 和设计 §9。以下准备状态和旧授权保留为当时记录。

**此前准备阶段授权（2026-10-18）：** 用户授权聚焦核对、最小 A/B 设计和可逆离线准备，
没有授权新增 live。见 [预算对齐与有限证据交互设计](bounded-evidence-interaction-design.md)。
**离线实施现状：** 该设计 §7 S0–S3 已推进至可集中审批；结果与三道准确任务见 §8，
批次 `bounded-evidence-prep-20261018-1`，有效输入 `cells-v4.json`。
候选 18 项、运行停止边界 7 项离线控制通过，12 格尚无 live 成绩；不改变 R4 HOLD。
准备批次 `evidence-interaction-prep-20261018-1`，共同预算与受控读取先离线验证；
候选及协议冻结后再准备新题，准确任务、预算、门槛齐备后集中请求 live 批准。
接手执行按该设计 §7 的 S0–S3 顺序推进：核对 → 窄适配与负控 → 冻结后封存任务 → 集中审批。
本次交接修订未扩大 live 授权；准备完成不等于 R4 放行。
R4 仍 HOLD、R5 未准入，旧 5/6 与所有失败/NOT_RUN 保持不变。
weekly used 最新观测 9%，用户停止线 15%；以下旧批准、预算和“下一步”均按历史解读。

**最新追加结论（语义咨询已执行）：** `semantic-advice-20261018-1`固定9请求全部完成。
直接修复0/3、Muse咨询后修复0/3 all-check；行为分别21/21/20和21/17/23（每格25）。
6次提案全部实际应用，零保护漂移，无加载/长度/HTTP故障。Muse3/3指出核心原因，前两次附带判断
不完全准确（冻结源码独立核查已保留），完整诊断1/3。即使有可用建议，Coder仍未可靠落实类型域边界。
不将该咨询阶段接入生产、不追加补跑，不修改原候选或旧5/6正式迁移结果，整体仍HOLD。
actual weekly used结束6%/上限15%，登记5→派发6的元数据更正见usage-correction，非预算到线。
该批已形成明确结论；下一候选若开展，应先冻结同模型/同总预算的最小agent循环对照，
检验现有包装与跨回合测试修复的差异，不能预先认定是harness或模型唯一责任。
不再默认扩展提示变体。详见该批handoff/decision/逐格证据，以下保留历史计划与结论。

**最新收束决策：R4仍HOLD，目标未完成。** 本轮不再搜索小型格式/措辞变体。
`exception-reference-20261018-1/consolidated-decision.json`汇总所有新批次：正式恢复新3/3、旧0/3；
正式迁移新5/6、旧1条接受，11/12执行，最后一旧对照NOT_RUN。随后六个固定诊断批次共45次模型请求，
不是45个新题或独立成功率分母。上下文裁剪、先解释后编辑、前瞻合同澄清、错误块输出、坏体隐藏、
修改前基线参考均未取得各自3/3 all-check；块输出一例行为25/25但原B904仍失败，照实保留。
隐藏坏体会丢失已明确要求的旧兼容行为；基线参考也未解决错误类型/Message单例问题，均不采用。
当前actual weekly used5%，上限15%。停在下述角色流程的重要判断，不是预算耗尽，也不假称R4放行。
下方旧“下一步”属于各批次当时提案，以本段和consolidated-decision为准。

### 已批准的下一阶段：失败草稿语义咨询，不是验收Reviewer

2026-10-18用户“可以的 试试的”批准下述隔离九请求对照。当前actual weekly used5%，停止线15%。
本次只新增诊断，不改生产runtime/正式handoff；先无模型控制通过并冻结，再运行固定三轮两臂。
注册批次`semantic-advice-20261018-1`。以下“建议/尚未实现”保留为批准前的历史说明。

目前可确认：最后正式失败的JSON合法、实际编辑成功、错误反馈含预期ValueError与实际TypeError、
当前源码/hash正确，无HTTP400或长度耗尽。模型有正确首轮实现的证据，但对这份错误草稿的语义修复不稳定。
Primary的原输入域表达也不够明确，责任不能全归模型；前瞻澄清仍失败，故也不是唯一解释。
不再修改已冻结candidate、覆盖失败、放宽lint或选择更容易的题替换原分母。

建议需要用户作出的**角色流程选择**：是否允许使用同一Muse，在Coder验证失败后做一次只读语义咨询。
这不是普通机械改动，因为它把当前只在通过验证后介入的审查模型用于失败修复建议，并影响预算与审查独立性。
本轮尚未实现、注册或调用这个新流程。批准后才按以下顺序开展，不自动启动Coordinator：

1. 单独命名`semantic_advice`，绝不将failed Coder伪造为ready_for_review，不调用要求通过验证的正式Reviewer入口绕过gate。
   建议只是不可信研究/修复意见，不能生成pass、授权写入、降低风险或作为Primary验收证据。
2. 先做无模型正负控制：真实失败身份/源码/hash/测试输入绑定，假引用/陈旧源码/伪造验证拒绝；
   诊断产物与正式Reviewer报告隔离归档；所有原编辑、验证、不可变历史与Primary权限保持。
3. 固定暴露样例三轮两臂：直接Coder单提案与一次Muse咨询后Coder单提案。最多3次Muse、6次Coder，
   无probe、无补跑、同4096输出、同25测试及静态检查、单驻留。咨询内容由模型产生，不提供Primary算法/gold。
   Primary分别评咨询因果/引用与实际实现，不把“解释正确”当“代码正确”。零新题信用。
4. 只有咨询3/3正确且咨询后代码3/3 all-check才讨论正式候选。正式流程必须重新预登记：
   诊断请求计入原角色/时间总预算，不暗中在16次Reviewer预算之外另送请求；Coder仍6请求/3验证/3编辑/1格式化。
   如采用共享预算，先证明失败闭合与真实计数，再决定是否有正式live资格；不静默修改已冻结Reviewer配置。
5. 验证通过后仍需全新上下文的正式独立Reviewer及风险路由Primary审查。咨询不替代任何一关。
   使用同一Muse先咨询再终审存在相关性风险，必须明确记录并保留原16/16及真实4/4挑战；
   不因小样例咨询有效就宣称新增审查职责已合格。
6. 正式候选若通过新的固定恢复批次，才独立冻结未用于候选开发的三类任务×两次×两臂；
   原6/6、逐题2/2、无安全漂移、无Primary语义实现接管门槛不变。旧5/6与失败题永不恢复新题身份。

若不批准这个角色流程变化，则保持当前候选与R4 HOLD，不继续把同一语义失败包装成新的机械补丁。
模型替换、Primary提供算法、缩减能力目录或降低原门槛同样属于另一个需要用户决定的路径，未获授权。

2026-10-18后续结论覆盖下文“迁移进行中”：`unified-transfer-20261018-1`已闭批，
候选5/6接受（逐题2/2、2/2、1/2），旧对照1条接受，11/12执行、末条旧对照NOT_RUN。
最后一候选真实应用了错误实现：将Mapping校验错误转为TypeError，保护测试拒绝；不是JSON/patch/HTTP400/长度/派审故障。
第二请求有明确pytest.raises(ValueError)、实际TypeError、当前源码/hash，故不归因为缺失反馈。
随后固定上下文对照完整/依赖闭包均0/3；先解释再编辑对照直接/诊断后均0/3 all-check，
解释能指出错误转换，代码有部分进展但仍把缺字段Mapping当不支持类型。全部失败和逐项行为成绩保留。
Primary同时承认原合同把“所有Mapping属于新输入域”留在隐含等价关系中；前瞻文字澄清对照保持全部25项测试不变，
没有修改旧合同、旧分数或生产runtime，也没有恢复未暴露资格。相关独立批次均在harness-convergence下。
当前仍R4 HOLD，weekly used实测5%，停止线15%。下一诊断只考虑实际错误位置绑定的更小代码块输出，
不继续叠加解释/上下文/规则；若无改善，再提交任务能力/语义协助的重要边界判断。目标未完成。

2026-10-18 机械恢复正式结论：`unified-preparation-20261018-1`固定六格完成，
旧0/3、新3/3经原canonical验证、同一冻结Reviewer及Primary全量审查接受。
原18项独立行为测试与Ruff/Pyright/真实观测检查不变；每个新单元两次模型提案、
三次验证、一次既有受控格式化。旧普通格式失败耗尽验证槽的问题在新流程中消除。
这仅为已暴露题恢复资格，不是新题或产品放行；Reviewer输出耗尽与原预算恢复照实保留。
随后独立登记`unified-transfer-20261018-1`：request_keys、single_content两道原NOT_RUN题，
以及兄弟runtime的messages_output新合同，各两次两臂，候选原6/6及逐题2/2门槛。
三组原源码失败/参考通过/私有负控检出、12个安装入口及实际观测命令通过，
新注册测试首次缺省配置断言失败保留，纠正读取默认值后4/4通过，未改实际配置。
本批已冻结启动，模型和Reviewer不变、单驻留、生产runtime不改；当前weekly used4%，上限15%。
新批最终状态以其decision.json为准，旧矩阵不回填、不把准备过的题说成陌生仓库。

最新授权补充：用户明确要求同范围简单机械决定自主推进，不再逐项确认。
因此，在模型、角色、编辑权限、合同/验收、安全门槛和预算上限不变时，允许自主建立
独立机械候选并登记、负控、冻结和测试，继续向R4推进，weekly used15%停止。
旧批次与失败不重开、不改分母；兄弟仓库只读、不commit/push、不改生产默认。
仅当涉及模型/权限/安全或重大架构、语义取舍时再请求用户判断。
这覆盖下文“每个新增机械live候选均逐项授权”的旧流程要求，不覆盖重要边界变更。

2026-10-18后续正式结果：用户已批准正式候选及条件迁移。`static-span-formal-20261018-1`
17项控制通过，首个新单元实际完成编辑、三次验证和自动Reviewer（pass），
但Primary确认循环metadata异常兼容回归ValueError→RecursionError并replan。
因此固定6格只执行2格，其余4格NOT_RUN，迁移不准入。旧失败、Reviewer漏检和所有pins保留。
同一候选的普通隔离rework`metadata-cycle-recovery-20261018-1`补六项只读回归，
私有参考18/18通过；模型修好了这些行为，但新增RUF013/Optional错误，未获第二次模型请求：
普通Ruff格式失败仍走后置格式化复验，耗尽三槽。整体仍HOLD，不将恢复记成旧分数通过。
下一机械候选应统一受控格式化准备与源定位诊断，守住原命令/模型/权限/验收预算，
不继续逐错误堆提示；新live按计划授权、登记、负控、冻结。当前weekly used3%，上限15%。

2026-10-18最新状态：用户已明确批准的九次静态修复诊断全部完成，见§16及
`repair-representation-20261018-1/handoff.md`。相同输入：错误解释3/3正确、
整函数3/3修好类型错误但格式回退（all-check0/3）、最小片段3/3通过全部原检查。
仅为局部接口诊断，无Reviewer/完整链/新题信用，R4仍HOLD。下一建议为独立授权的
正式循环静态错误片段修复候选及后续原门槛迁移，不直接提升生产。weekly used当前3%，
上限15%；历史状态和预算数值以下保留，不覆盖本条。

2026-10-17 最新授权与状态：用户批准继续，预算窗口已重置，目标仍是 **完成 R4**，weekly used 新上限 **15%**，本轮起点 **0%**、最终收尾实测 **2%**。R3 PASS、R4 HOLD、R5 未准入。原模型、单驻留、原保护测试和门槛保持；兄弟仓库只读，不 commit/push，生产 runtime/handoff 不改。下文旧“当前”与50%/45%/30%停止线及旧停工说明仅保留历史意义，以本条与最新decision为准。

最新固定迁移批次 `capture-transfer-20261017-1` 已在首组失败后闭批：2/12执行、10条NOT_RUN，原候选6/6门槛不可达。旧Coder最终通过12项可见/私有测试及静态检查，但最后一轮仍发no-op编辑，终态拒绝后耗尽6轮；新Coder六次输出都因docstring引号附近的非法JSON被拒绝，**0次编辑**，后续5项失败属于未改的原源码，不能算已应用实现语义错误。Reviewer两边均未启动。所有响应正常stop、实际输入1698..1896tokens、上下文利用约24%，不是HTTP400/长度耗尽/patch失配。下一架构决策应单独注册Coder输出通道对照（原始函数代码与真正约束的字符串），冻结合同/预算/Reviewer不变；不在失败批次补跑，不把旧题重新算holdout。[本批交接](../benchmarks/work/harness-convergence/capture-transfer-20261017-1/handoff.md)。本次停在固定门槛失败及新输出协议决策点，不是预算耗尽。

最新离线进展：`capture-transport-20261017-2` 已封板，完整114项控制、另54项原语义引擎/输入等价回归通过（有重叠，不相加）。真实canonical消费者、旧20观测无损、完整bundle机械等价和安装入口序列化已验证；既有审查语义候选未改，不计新题或完整链成绩。下一步独立注册三道新题×两次×两臂，两臂相同合格Reviewer/观测准备，保留原6/6及逐题2/2门槛。[阶段交接](../benchmarks/work/harness-convergence/capture-transport-20261017-2/handoff.md)。

预算收尾：`r4-observation-transport-20261017-1` 完成严格命令封套、显式源码清单及真实子进程边界44项，另一次真实无模型canonical重放1项通过（不是单次合并45项）；首次Windows测试参数名错误保留。发现readonly范围本身不自动进入验证输入epoch，重放通过显式读取绑定生产者/配置。新组件尚无已认证Reviewer消费者与家族DTO/新题迁移，不能接入生产或算R4通过。[离线阶段交接](../benchmarks/work/harness-convergence/r4-observation-transport-20261017-1/handoff.md)。恢复前先取得新预算授权；继续同一候选的认证传输/旧20输入等价及安装控制，不重跑已结束诊断。

本日后续批次（原控制 / 已暴露真实回归，完整报告质量计分）：原策略恢复 `r4-canonical-policy-20261017-1` 为 **16/16、1/4**；固定事实 `r4-observed-facts-20261017-1` 为 **15/16、2/4**；扩展事实与一次预算内恢复 `r4-fixed-observation-recovery-20261017-1` 为 **15/16、2/4**（原判断标签16/16，一条错误替代修复建议不抹去）；条件 low 恢复 `r4-conditional-recovery-20261017-1` 为 **16/16、3/4**；逐观察判断 `r4-observation-accounting-20261017-1` 为 **16/16、2/4**（顶层判断3/4，一条观察把真实结果事件误说成不存在）；完整类型化输入 `r4-typed-observations-20261017-1` 为 **16/16、2/4**。全部 HOLD，旧失败不回写，无新 Coder/holdout 成绩。

关键证据：完整输入下模型仍能准确描述“存在 ToolResultPart(None)，实际状态 requested”，却用“符合实现”支持合同 verified。因此事件摘要损失不是唯一原因；单纯加报告字段或恢复动作完成率不足。另有恢复后漏观察条目、纠正请求回到 medium/auto 再次输出耗尽的流程成本，不能混作 HTTP/context 失败。尚不能从这些样例断言模型完全没有语义能力。

窄诊断 `r4-contract-status-20261017-1`：同合同/输入/schema，唯一差异为是否附实现，两臂各 **4/4** 正确预测六种结果的合同状态，actual wire 匹配；只是 `PASS_NARROW`，所有样例均应 succeeded，尚未排除常量预测器，也没有观察到该任务下的源码负面效应。下一步先补可区分负控，不继续 DTO/措辞/采样微调：`r4-discriminating-status-20261017-2` 从原保护测试机械提取明确断言 requested 的重复请求序列，另加被忽略的未知 call_id，两个条件都提供原可见测试及明确 target_call_id。准备批次 `-1` 因初始状态规范不充分、零 live 关闭保留。负控完整通过后才考虑“先推导合同要求、再对照实现”的独立候选；模型预测仍是不受信任判断，不得当 gold 或自动验收。R4 仍须原16/16、真实回归4/4及三道新题两次两臂的完整链门槛。

最新完成：有区分力的诊断 `r4-discriminating-status-20261017-2` 两臂各 **4/4**，正确区分六个 succeeded 与两个 requested；只取得窄子能力证据。独立两阶段候选 `r4-contract-first-20261017-1` 已完成固定20/20，原控制 **16/16**、真实回归 **4/4 PASS**。共26次真实请求（含4次合同推演及2次保留的输出耗尽），全部共用原16请求/4错误/600秒预算。两个坏实现均正确定位 None/status 缺陷；一条附带措辞疑虑保留，按原“确认缺陷优先阻止接受”规则仍为 rework。新阶段不是R4放行，也没有新Coder/holdout成绩。下一步先做验证命令实际观测的受信传输与离线安装控制：当前事实提供者仅认八个冻结源码版本，不能直接迁移到新草稿，不能绕过其 guard。[本阶段交接](../benchmarks/work/harness-convergence/r4-contract-first-20261017-1/handoff.md)。

**当前有效状态：R3 PASS，R4 HOLD，目标仍是 R4；weekly used 上限 45%，收尾实测 43%。** `r4-review-medium-formal-20261016-1` 已完成 20/20：原控制 **15/16**，已暴露真实切片 **2/4**，候选 HOLD。三个失败都是误放行，不是本批传输/截断/未提交报告；两条真实报告已提到 None 合同风险，却仍 verified/consistent。简化 medium 的 4/4 未迁移到正式流程，不能升级生产。下一步是需要确认的新审查职责设计，见 §16 与 [本批交接](../benchmarks/work/harness-convergence/r4-review-medium-formal-20261016-1/handoff.md)。没有启动新 live；此处停在关键架构判断，不是预算耗尽。下文带 30% 或旧“最新”字样的段落保留历史意义，以本段、§0、§16 与最新注册为准。

最新授权更新：用户批准继续证据观察接口阶段，并将 **weekly used 停止线上调为 45%**。本阶段实际启动 29%；旧批次 registration/decision 的 30% 历史上限保持。新批次 `r4-review-evidence-20261016-1` 独立冻结，不修改 DTO 已关闭批次；生产 runtime 保持不变。目标仍为 R4，不以一个局部候选通过替代整体放行。应用 Goal 卡片仍含旧 30%/blocked 文本，工具不支持直接更新 objective 或恢复，实际执行以本条用户授权及新 registration 为准。

最新进度：用户已批准独立 Reviewer 简化报告阶段，目标仍为完成 R4、weekly used 上限 30%。新批次 `r4-review-dto-20261016-1` 固定 16 条全部执行，实质正确 **15/16，HOLD**；旧批次也是 15/16，但失败机制不同，不能据此声称稳定性改善。新失败没有提交 REPORT，因重复读取完整五行测试而终止；报告字段精简未解决证据导航到裁决的流程。实际 used 从本阶段 24% 至收尾前 28%，最终值见新 decision。**R3 PASS、R4 HOLD，R5 未准入**。旧迁移候选 2 接受/1 拒绝/3 未运行、旧 Reviewer 15/16 均不改写。新交接：[Reviewer DTO 阶段](../benchmarks/work/harness-convergence/r4-review-dto-20261016-1/handoff.md)；原语义失败：[R4 迁移阶段](../benchmarks/work/harness-convergence/r4-transfer-20261016-1/handoff.md)。

本轮修复记录：serializer 批次关闭 HOLD（3 个 Coder all-check，只有 1 条合格完整链）；presence 的旧 Primary 过早记分用新增 correction 留痕。独立 readiness 阶段只对齐报告就绪与既有完整阅读门槛，并给两臂 presence 绑定原目标实现，不换提示、模型或预算。修复前负控 3 fail/3 pass，修复后 6 pass；新批次通过不改变旧失败分母。

2026-10-16 最新执行目标：**自主按阶段推进，完成 R4；actual weekly used 达到 30% 停止**。用户授权自行安排可逆、证据驱动的阶段优化，不需逐步询问；固定门槛、模型、单驻留、保护测试与历史保持不变，兄弟仓库只读，不 commit/push。遇到语义/架构取舍、能力范围调整或必须放宽门槛等关键判断再交用户。serializer 与 readiness 机械阶段已完成，R3 完整链达标后进入 R4。每批 live 仍冻结候选，失败闭批，不覆盖失败或现场修改。新的机械缺口可先独立登记和离线修复，不把已失败批次补成成功。应用 Goal 卡片最新读取仍为此前的 blocked，objective 已是 R4/30%；用户已批准继续，不能把旧卡片状态解释成缺少本阶段授权，也不能把目标误标 complete。当前工具不支持主动恢复该卡片。

2026-10-15 用户要求继续按计划执行，并将停止线上调为 **30% weekly used**；实际启动 0%，整合期间复核 1%。R3 开始默认关闭的离线整合，批次 `r3-host-20261015-1` 已保存 110375 路径基线与现有源码副本。以下旧批次的历史上限、成绩和 decision 不回写。

目标是分清代码生成、补丁应用、流程控制和语义审查的失败来源，再验证一个面向当前本地模型的简化执行候选。不是继续追加提示直到旧题通过，也不是直接移植别人的完整 agent。

R0/R1 已完成；**R2 当前接口候选已通过**：literal 输入 + strict whole JSON + 宿主终止换行归属，在固定批次 owned 3/3 all-check，raw 0/3，见 §8.9。R3 的起点装配、CLI 字段丢失及后续 readiness 失败都是保留的历史，不再代表最新 R3 状态；当前 R3 PASS 不回写这些旧分母。R4 已准入并执行，但迁移语义和 Reviewer 控制均未达门槛，见 §10.3。当前证据不等于生产或通用模型能力放行。

本轮阶段轨迹（2026-10-16，45% 授权）：证据观察候选原固定 **16/16**；真实档案 **1/2 HOLD**；八格术语对照两臂各 **2/4**；简化 auto/required 报告各 **3/4**；匹配正式 low 指令 **3/4**；强度对照 medium **4/4**、high **2/4**；medium 正式入口原控制 **15/16**、真实回归 **2/4**。各批次独立计数，不合并成成功率，不计新 holdout 或 Coder 成绩。原模型、生产 runtime、预算与历史未改变。

## 0 当前执行索引

| 阶段/批次 | 已核实状态 | 接手证据 |
| --- | --- | --- |
| R0/R1 | 完成冻结；修正已确认的 CRLF 守卫不一致，正负控制通过 | [R1/R2 分析](../benchmarks/work/harness-convergence/r1-r2-20261013-2/analysis.md) |
| 原 R2 十二格 | 原始精简 3/3；原始正式、失败精简、失败正式均 0/3；HOLD | [原 decision](../benchmarks/work/harness-convergence/r1-r2-20261013-2/decision.json) |
| R2 结构化定位三格 | 0/3；一次部分修复、两次 no-op；HOLD | [逐格结果与结论](../benchmarks/work/harness-convergence/r2-localized-20261013-1/handoff.md) |
| R3 离线原型 | 14 条新无模型控制通过；没有接收器、安装或 live 资格 | [原型 decision](../benchmarks/work/harness-convergence/r3-proposal-20261013-1/decision.json) |
| R2 输出表示对照 | 已完成：exact 0/3、whole 0/3；HOLD，见 §8.3 | [六格交接](../benchmarks/work/harness-convergence/r2-output-20261014-1/handoff.md)、[decision](../benchmarks/work/harness-convergence/r2-output-20261014-1/decision.json) |
| R3 readiness | PASS；候选 6/6、baseline 2/6 | [完整链 decision](../benchmarks/work/harness-convergence/r3-readiness-20261016-1/decision.json) |
| R4 transfer / Reviewer | HOLD；迁移候选 2 接受/1 拒绝/3 未运行，独立控制 15/16 | [R4 交接](../benchmarks/work/harness-convergence/r4-transfer-20261016-1/handoff.md) |
| R4 独立 compact REPORT | HOLD；固定原 16 条仍 15/16，失败改为未提交报告的重复读；生产 runtime 未改 | [独立阶段交接](../benchmarks/work/harness-convergence/r4-review-dto-20261016-1/handoff.md) |
| R4 证据观察候选 | 原 16 控制 **16/16 PASS**；仅阶段资格，不是 R4 放行 | [观察阶段](../benchmarks/work/harness-convergence/r4-review-evidence-20261016-1/handoff.md) |
| R4 真实档案诊断 | **1/2 HOLD**；已暴露 None 语义反例仍漏报，零 Coder 调用 | [真实诊断](../benchmarks/work/harness-convergence/r4-real-review-20261016-2/handoff.md) |
| R4 术语对照 | 固定 8 格完成；两种措辞均 2/4，均漏掉两个错误实现 | [交接](../benchmarks/work/harness-convergence/r4-review-terms-20261016-1/handoff.md) |
| R4 简化语义 / required 输出 | 各 3/4；输出耗尽失败保留，不算传输故障或补跑成功 | [简化诊断](../benchmarks/work/harness-convergence/r4-review-semantic-probe-20261016-1/handoff.md)、[required](../benchmarks/work/harness-convergence/r4-review-required-probe-20261016-1/handoff.md) |
| R4 匹配 low / 强度对照 | low 3/4；medium 4/4、high 2/4；只提供正式对照资格 | [low](../benchmarks/work/harness-convergence/r4-review-matched-low-20261016-1/handoff.md)、[强度](../benchmarks/work/harness-convergence/r4-review-strength-20261016-1/handoff.md) |
| R4 medium 正式入口 | **HOLD：原控制 15/16，真实回归 2/4**；3 个语义误放行；0 新 Coder/holdout 成绩 | [结果与下一阶段提案](../benchmarks/work/harness-convergence/r4-review-medium-formal-20261016-1/handoff.md) |
| R4 逐义务语义处置 | HOLD：候选 13/16、真实回归 4/4；同期 formal 15/16、2/4 | [独立对照](../benchmarks/work/harness-convergence/r4-semantic-disposition-20261017-1/handoff.md) |
| R4 机械位置/路由修复 | HOLD：15/16、3/4；机械失败消除，保留语义误判和输出耗尽 | [机械修复](../benchmarks/work/harness-convergence/r4-semantic-transport-20261017-1/handoff.md) |
| R4 唯一温度 0 对照 | HOLD：14/16、4/4；20 格首次 wire 除温度外完全相同；不再扫参数 | [解码对照](../benchmarks/work/harness-convergence/r4-semantic-greedy-20261017-1/handoff.md) |
| R4 原策略定义恢复 | 准备固定 20 格；只恢复正式策略原定义，原输入/门槛不变 | [注册](../benchmarks/work/harness-convergence/r4-canonical-policy-20261017-1/registration.json) |
| R5 | 未准入 | 不以原型/诊断成绩替代完整链 |
| R2 约束解码对照 | schema 0/3、plain 0/3；HOLD，见 §8.5 | [六格交接](../benchmarks/work/harness-convergence/r2-decoding-20261014-1/handoff.md) |
| R2 输入表示对照 | json 0/3、literal 0/3 all-check；literal 三次有效修复，仅格式失败 | [六格交接](../benchmarks/work/harness-convergence/r2-rendering-20261014-1/handoff.md) |
| R2 终止换行候选 | **PASS：owned 3/3、raw 0/3**；未启动 R3 | [放行交接](../benchmarks/work/harness-convergence/r2-boundary-20261014-1/handoff.md) |
| R3 宿主整合 2026-10-15 | 离线 809 测试及 302 子测试通过；live 2/12 已执行但起点失配、余 10 格 NOT_RUN；不是模型能力失败 | [R3 交接](../benchmarks/work/harness-convergence/r3-host-20261015-1/handoff.md)、[起点审计](../benchmarks/work/harness-convergence/r3-host-20261015-1/origin-audit.json) |
| R3 纠正起点批次 | 新增 15 控制、十二格起点预检通过；2/12 已执行。候选修复 1/1 all-check，CLI 序列化断开派审，余 10 格 NOT_RUN；R4 不准入 | [纠正批次交接](../benchmarks/work/harness-convergence/r3-origin-fixed-20261015-1/handoff.md)、[无模型边界复现](../benchmarks/work/harness-convergence/r3-origin-fixed-20261015-1/handoff-boundary-audit.json) |

§8.8 新批次已结束并满足 R2 门槛，达到用户本轮停止条件。后续从 §8.9 接手 R3 设计，不能重跑已完成批次或合并失败分母来凑 3/3。

核心判断：保留严格的权限、证据和验收底座，减少模型负责的机械状态转换。是否有效必须用同期对照与未暴露迁移题回答。

## 1 约束与接手检查

- 工作仓库：`F:\ChatGPT\local-worker-kit`。编制时分支 `codex/v2.1-dev`，HEAD `ebf20e27f17604dcdf2c418393c0e33ae71e8360`，有大量 tracked 和 untracked 改动；这不是干净 baseline。
- 两个兄弟仓库 `F:\ChatGPT\agent-evaluation-harness`、`F:\ChatGPT\agent-runtime-kit` 严格只读。只向 kit 内新建隔离目录复制指定源码；不在兄弟目录运行可能写缓存或日志的测试。
- 不 commit、push、stash、reset 或覆盖历史。不能为了让回归通过更新旧 pin、修改保护测试、删除失败目录。
- 模型保持：Explorer `openai/gpt-oss-20b`，Coder `qwen/qwen3-coder-30b`，Reviewer 与 Coordinator `meta/muse-glimmer`。Explorer context 32768，其余 24576；单模型驻留、并发 1，允许正常加载等待。
- 服务为 `http://127.0.0.1:12345/v1`。实际量化、模板、采样、KV cache、服务版本与加载参数须读取并记录；读不到写 unknown，不凭历史截图推断。
- 当前停止线为 **45% weekly used**，来自最新用户更新；本轮证据观察至正式 medium 阶段观察为 29% → 43%。旧批次 15%/30% 历史注册不回写。启动、每批 live 前后、阶段结束都重查；读不到时暂停新 live；达到上限不启动新调用，已有写入安全收尾。用户新指令优先。
- 不安装外部 agent、Docker、依赖或模型，不启动额外云代理。本轮研究不等于授权在用户项目运行第三方程序。
- 安全状态机、交接协议、保护验收由 Primary 实现和审查；不让本地 Coder 决定自身权限或修改自己的验收门槛。

## 2 本仓库事实与尚未证明的解释

| 事实 | 证据 | 解释边界 |
| --- | --- | --- |
| E501 四组实验中 minimal code、minimal JSON、full JSON 各 3/3，full code 0/3 | [四组结果](harness-factorial-results.md) | 上下文与表示存在交互；只覆盖一个已暴露任务，不是一般成功率 |
| 真实 presence 切片行为正确，初次迁移卡格式；宿主格式化后通过 | 同上 | 机械格式可由工具承担，不代表可修正跨文件语义 |
| 评分与 cache key 迁移两次均 12/15 | 同上 | 存在真实类型与跨文件不变量错误；每次仅一个块、总三次提案也限制了修复机会 |
| 正式单函数终态候选 presence 完整链 3/3，repair 0/3 | [终态结果](single-function-terminal-results.md) | 修复了流程障碍，但未解决 repair 能力 |
| 后续 repair-state 候选仍 3/6 | [该阶段结论](../benchmarks/work/system-convergence/single-function-repair-state-20261012-1/stage-conclusion.json) | 当前失败证据保留不等于模型能使用它 |
| 最新 patch-only 阶段 repair 三次都是当前源码无变化替换；presence 三次未进入 patch 阶段、未验证、未启动 Reviewer | [收尾](../benchmarks/work/system-convergence/single-function-patch-phase-20261012-1/closeout.json)、[动作证据](../benchmarks/work/system-convergence/single-function-patch-phase-20261012-1/live/phase-exposure-analysis.json) | 最新 0/6 不支持把所有退化归因于 patch-only 分支 |
| 原诊断方法 395 字符，后续中间草稿 648 字符 | 同一收尾记录 | 起点、历史和协议不同，历史成功不能充当同期 baseline |
| 有限正式入口曾完成 2 个 Coder、2 个 Reviewer、1 条依赖链 | [入口资格](../benchmarks/work/system-convergence/integration-delivery-20261011-3/stage-decision-1.json) | 仅有限能力资格；没有普遍真实项目稳定性或成本收益证明 |

待验证假设：

1. **流程负担**：模型能生成正确源码，但需要自行选择 VALIDATE、填写机械字段和结束动作时失败。
2. **草稿锚定**：失败中间草稿比原始草稿更难修，模型重复已有实现。
3. **上下文适配**：完整合同不必等于完整 packet；重复状态、历史错误示例及冗余字段可能降低有效修复率。
4. **编辑接口**：定位、换行及版本约束可能拒绝本来可用的改动；必须与真正的 no-op 分开。
5. **语义能力**：即使移除流程负担，当前模型对某些修复和跨文件不变量仍达不到稳定要求。

不得把假设写成结论。特别是：没有 HTTP 400 不证明上下文无影响；不执行 Reviewer 不说明 Reviewer 能力好坏；模拟回归通过不说明模型成功率提高。

2026-10-14 证据更新：旧失败草稿六个实际请求均包含两条 E501、完整当前函数与正确 hash；新的结构化定位三格仍 0/3。三格输入各 1242 tokens，均正常 stop，未见截断；有效 patch 正常应用。因此该批没有证据支持反馈丢失、过期源码或应用器误拒。输出复制负担仍只是待测假设。R2 起点的 11 项行为测试原本就通过，它测量单提案静态修复，不能代表整个 Coder agent 的新功能实现、多轮修复或 Reviewer 能力。

## 3 外部项目研究与可迁移机制

以下为 2026-10-13 读取的一方文档与部分源码。链接到 main 的内容会变化；如后续采用具体实现，先记录 commit、文件 hash 与许可证。这里没有安装或复现第三方 benchmark，也不使用其成绩推算本地 Qwen 或 Muse 的表现。

### 3.1 Aider

Aider 支持多种编辑表示，明确指出不同模型适配不同格式；whole 简单但输出较长，diff 使用搜索替换。它的 architect 模式把方案与具体编辑分成两个请求，允许同模型承担两阶段，也明确增加延迟与成本。[编辑格式](https://aider.chat/docs/more/edit-formats.html)、[两阶段模式](https://aider.chat/docs/usage/modes.html)

自动 lint 与可配置的改后测试由宿主触发；源码中 `apply_updates` 后进入 `auto_lint` 等路径。它不必等待模型为每一次已应用改动再发一个自定义 VALIDATE 动作。[检查文档](https://aider.chat/docs/usage/lint-test.html)、[base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py)

repo map 提供相关符号、签名和受预算约束的依赖概览，而不是一律塞入整仓源码。[repo map](https://aider.chat/docs/repomap.html)

官方故障页也讨论编辑格式不遵从、无关上下文和本地量化模型的编辑困难。该页的经验判断不是我们当前模型的测量，尤其不能将其某个 token 阈值当作普遍规律。[编辑故障](https://aider.chat/docs/troubleshooting/edit-errors.html)

采用：宿主检查、语义任务与编辑表示分离、按实际任务提供上下文。暂不采用：增加第二个设计模型、自动提交、宽松模糊 patch。前两项会增加成本或改变本轮归因；后两项与本仓库边界不一致。

### 3.2 mini SWE agent 与 SWE agent

mini-SWE-agent 的公开说明强调简单循环、线性历史和 bash 接口；`DefaultAgent` 源码把 query 与 execute 分开，并有时间、步数、连续格式错误的限制。它适合作为“较少编排是否更易诊断”的参考，不是“给 shell 就一定更强”的证据。[设计说明](https://mini-swe-agent.com/latest/)、[循环源码](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py)

较早 SWE-agent 的 ACI 设计则使用专门文件窗口、简洁搜索结果和编辑时语法检查。两种路线同时说明：接口设计需要匹配模型与任务，工具越多或越少都不是充分条件。[ACI 文档](https://swe-agent.com/latest/background/aci/)

采用：把可见请求与实际轨迹对应起来；用简单循环做对照；让错误观察精确且简短。不采用：在本 kit 中给 Coder 任意 shell。受限 API 与操作系统隔离不是同一个保证，已有 scope/hash 边界仍保留。

### 3.3 Neal 与 Neal SWEbench

Neal 将运行编排放在确定性状态机中，按 scope 调用角色、保存可恢复状态；其原生 provider 可包装已有 agent SDK，OpenAI-compatible provider 则拥有自己的工具循环。兼容测试区分协议、结构化输出与行为。因此“支持某 API”与“该模型在某角色有能力”是两回事。[架构](https://raw.githubusercontent.com/navels/neal/main/docs/architecture.md)

Neal 的 coder 提交与最终 squash 不适合直接带入本轮。其 coder/reviewer 上下文策略也不能替代本项目要求的独立新上下文审查。[项目说明](https://github.com/navels/neal)

Neal-swebench 对任务确定性、隐藏答案隔离、基础设施故障与模型失败分别处理，并承认样本是刻意选择的困难子集，存在重复运行翻转。值得学习的是实验口径，不是其数值。其基础设施补测统计规则也不直接替换我们的“全部尝试留档、原分母保留”。[评测方法及限制](https://github.com/navels/neal-swebench#case-construction)

采用：角色能力与兼容分层、宿主状态机、明确 incomplete/blocked/failure、可恢复记录。我们已经具备其中很多机制；本轮不重复造一套，只查它们是否泄漏成模型必须理解的复杂协议。

### 3.4 其他用户指定项目

| 项目与一方来源 | 公开设计 | 对本仓库的意义及限制 |
| --- | --- | --- |
| [JcodeAgent](https://github.com/ShakenTheCoder/JcodeAgent) | README 描述 DAG、结构化记忆、验证与有限 Analyze/Patch 循环 | 可借鉴依赖摘要和失败记录；本次未核实完整执行源码及能力成绩，不把宣传中的自纠正当成已证明稳定 |
| [Local Multi-agent Orchestrator](https://github.com/JanithaIllankoon/Local-Multi-agent-Orchestrator) | README 将模型建议与 gated Executor 分离，描述逐个加载本地模型 | 与单驻留、宿主执行方向一致；不证明其具有我们的完整代码验收和补丁安全保证 |
| [codex-orchestrator](https://github.com/zm2231/codex-orchestrator) | 包装持续运行的 Codex/Claude agent，角色、HITL 与 worktree 隔离 | 可参考生命周期与交付物检查；它调度的是已有完整 agent，不是直接证明小型本地模型能跟随复杂工具协议 |
| [agent-orchestrator](https://github.com/Untrivial-ai/agent-orchestrator) | 当前链接重定向到 OrchestratorInc，管理 coding agent 会话、workspace 和反馈 | 主要是上层协调参考，不是本轮 Coder 内循环替换答案 |

### 3.5 Tenet 的模型适配与相似故障

用户补充的 [Tenet](https://github.com/JeiKeiLim/tenet) 是高度相关的参考，但主要处于 coding agent 的外层：编排、任务上下文、评估、恢复。此次源码核对固定到 commit `b05a84bba1f2597410472401960ae6e7b12e30c8`，不把 main 的后续改动混入结论。

已实现的可借鉴机制：

- `model_tier: local` 在分解阶段指导更细、单一职责、明确验收的任务；frontier 使用更粗的目标。这是规划提示策略，不是运行时自动证明模型能力。我们的替代是按已测任务族与依赖复杂度分类，不能简单以 local/frontier 二分推定质量。[分解规则](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/skills/tenet/phases/04-decomposition.md)
- 当前 `toInvocation` 调用 `buildWorkerContext`，adapter 再把 context 和 prompt 组合发给 agent；说明上下文准备、派发与下游接收需要端到端核对，而不是看一次 compile_context 返回。[JobManager](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/src/core/job-manager.ts)、[OpenCode adapter](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/src/adapters/opencode-adapter.ts)
- 独立 code/test/public-surface critics 区分合同符合性与测试是否只是在复述实现；但三名评估者不是三份可靠性保证，也增加调用成本。采用其审查维度，不在本轮增加三个 Muse 调用。[评估配置说明](https://github.com/JeiKeiLim/tenet#configurable-critics)

最有价值的是它也公开记录了类似困难：

| 一方记录 | 状态与事实 | 本计划的响应 |
| --- | --- | --- |
| [弱模型 critics 调查](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/.backlog/tasks/task-001%20-%20Weak-model-critics-investigation.md) | pinned 版本仍为 To Do；作者观察到较弱执行模型倾向全部放行，而强模型仍能找问题，原因尚待查 | Reviewer 必须保留 hidden/clean 语义控制，不能靠多个 PASS 投票替代 |
| [worker 上下文设计调查](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/docs/planning/18_model_tier_and_worker_context.md) | 历史设计记录指出 compiled context 当时仅到 orchestrator；当前 JobManager 已有 worker context builder | 历史 bug 不能说成现存 bug，但它证明应测试实际发出的请求 |
| [缩小 decomposition 上下文](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/.backlog/tasks/task-010%20-%20Worker-critic-context-size-%E2%80%94-narrow-inlined-decomposition.md) 与 [上下文过滤调查](https://github.com/JeiKeiLim/tenet/blob/b05a84bba1f2597410472401960ae6e7b12e30c8/.backlog/tasks/task-032%20-%20Context-filtering-what-to-send-to-worker-from-project-document.md) | pinned 记录仍为 To Do，讨论全 spec/DAG 对小任务的冗余、兄弟任务干扰与缺少上下文预算 | 当前单元完整合同加依赖接口，不默认塞整份计划；不能声称 Tenet 已证明此优化有效 |

不照搬：默认无限重试、并行 job、每 job commit、每次三 critic、全量文档内联。这些分别与固定实验预算、单驻留、无 Git 操作及精简上下文目标冲突。README 的长时间自治是项目定位，不是我们模型/机器的成功率证据。

另一个实现差异：当前 `safeReadArtifact` 对读取失败返回空文本，以便继续派工。我们对必需合同和保护信息不能采用此降级；必需上下文缺失应在调用前停止，只有明确标为可选的资料才允许缺省。这是边界选择，不表示发现了 Tenet 的越权漏洞。来源同上 JobManager。

研究结论是本计划的设计推论，而非外部作者共同验证的定律：**保留宿主底座，先简化模型接口，测量后再决定是否替换整个 harness。**

## 4 目标职责与不变量

### 4.1 对模型简单不等于对宿主宽松

| 内容 | 模型应做 | 宿主应做 |
| --- | --- | --- |
| 任务 | 理解行为与约束、提出实现或阻塞 | 绑定批准的任务、范围、身份、风险与能力目录 |
| 源码 | 使用当前源码与必要依赖事实 | 读取、版本绑定、限定范围、展示实际内容 |
| 改动 | 提出语义改动 | 解码、精确匹配、检查 scope/hash、应用和归档 |
| 检查 | 解释真实失败并修复 | 按可信 profile 执行、超时管理、记录不可变结果 |
| 合同 | 给出有证据的判断，不知道就未知 | 不把模型布尔值当证明，不伪造确认，不隐藏遗漏 |
| 完成 | 不必操作宿主内部终态协议 | 判断检查是否当前有效，调度独立 Reviewer，再交 Primary |

限定单函数候选的目标流程：

```text
Primary 批准单元与 profile
  → 模型提交 patch 或明确阻塞
  → 宿主守卫并应用
  → 宿主受控格式化与检查
      失败 → 当前源码和失败证据 → 有界修复
      通过 → 独立 Reviewer → Primary 处置
```

这是带宿主反馈循环的受限 agent，不是只调用一次 LLM，也不是让模型管理整个执行系统。

### 4.2 必须保留的底座

1. 原 scope/read-only/forbidden、路径及 reparse 检查、唯一 writer、哈希防过期。
2. 保护测试、固定 lint/type profile、非零实际测试、输入变化使旧验证失效。
3. 格式化仅授权源文件；保留格式化前后 hash/diff，单函数外变化按约定拒绝，不放宽 lint。
4. fresh Reviewer、真实源码/测试证据与既有 disposition；模型不直接接受 feature。
5. baseline green 不能当新实现成功；Reviewer 通过不能修复过期或缺失的验证。
6. 每次失败、补测、Primary 干预、infra 和未执行格都保留；原归档不可覆盖。
7. 无任意 shell、无自动 Git、无真实项目部署、无让 Coordinator 自批范围。
8. 缩小任务不能拆开原子不变量或降低 risk floor；细分只降低无关语义负担，不能把事务/生命周期的完整性切给互不负责的单元。

### 4.3 单独处理合同确认的兼容问题

现有 `WorkerRuntime._contract_check`、`_assert_submission_contract` 以及 `local-unit.py` 的 handoff gate 都依赖 Coder 确认。不能只删除其中一处，不能调用 template 后把 true 当模型判断，也不能把新的 host validation 冒充旧 `ready_for_review`。

R3 必须形成版本化设计：

- `validation_facts` 只记录宿主执行事实；`worker_assessment` 独立记录模型判断，允许缺失/unknown。
- 新状态明确表示“当前确定性检查通过，等待独立语义审查”，不是旧合同已确认。
- 自动检查不要求先取得模型确认；但交接新状态需要明确协议版本、已批准模式、源码与保护输入 hash、非零测试和全部 configured checks。
- 所有硬合同仍交 Reviewer；Primary 独立核对旧确认责任是否有遗漏。未被保护测试和独立审查覆盖的语义项保持待决。
- 不改 Reviewer 候选、提示或模型；若它不能安全接收新证据形状，就停在实验分支，不让 adapter 捏造旧字段。
- 旧模式与归档保持原有严格规则。新候选的资格名称单列，不能宣称旧 gate 已被通过。
- 初期只覆盖批准的单函数、小或中风险任务；事务、并发、安全、迁移及跨文件原子不变量仍归 Primary。

风险适用说明：上述限制指未来产品路由。现有 repair/presence 冻结 fixture 标为 high，不得降级以套用此范围。R2 可在隔离副本做高风险任务的诊断，不产生产品资格；若后续 R3 使用这些已批准实验题，每个成功单元仍必须 fresh Reviewer 与 Primary 全量 diff/合同审查，且单列为隔离受监督证据。未经相应风险验收不能借此开放高风险产品派工。

## 5 统一实验规则与失败分类

每个阶段在首个 live 前生成 `registration.json`：问题、唯一候选、输入 hash、合同/保护测试、顺序、调用与验证预算、失败停止条件、门槛和唯一下一步。以下数字为计划门槛，不能跑完后改。

- 独立工作目录、相同源码起点；baseline 与 candidate 交错执行。种子若服务支持则预登记配对种子，不能为了可复现擅自改变现行采样；不支持写 unknown。
- 不在 live 中改源码、提示、schema、formatter、fixture、预算或分类。发生 bug 则结束该注册批次，保留原结果；新 live 候选需重新授权。
- 纯采集器错误可从已有原始证据恢复，但不得重调模型冒充原调用。基础设施重试也新增 attempt，不能覆盖。
- 低温不等于确定性；三次重复不是三个独立题。报告逐题配对结果，不在小样本上声称统计显著或生产成功率。
- 不增加通用 few-shot，不在看过 holdout 后追加针对性例子。后续若专测格式 few-shot，使用无关业务示例并另注册。

| 分类 | 判断依据 | 不能混算为 |
| --- | --- | --- |
| infra | 加载、连接、HTTP、超时、环境/依赖、收集器异常 | 已证明模型语义失败 |
| protocol | 无法解析、schema 错误、非法动作 | 自动等同源码错误 |
| patch_apply | stale hash、定位缺失/歧义、换行适配失败 | 模型一定不懂修法 |
| no_effect | find=replace 或实际字节没有变化 | patch 引擎应用错误 |
| deterministic_fail | 实际测试、lint、类型检查失败 | 必然都是业务语义错误，须细分 |
| workflow_fail | 可用源码未验证/未交接、错误终止 | “不会写代码” |
| review_protocol | 引用、结构或证据绑定失败 | 漏检/误报能力成绩 |
| review_semantic | 有效报告漏检、误报、修法违反合同 | 引用成功即可抵消 |

同一次运行可以有多个事件标签，但唯一 terminal outcome 必须明确；不能为了总和好看强行选一个根因。根因说明使用 confirmed / supported / hypothesis / unknown。

## 6 R0 冻结现状与统一观测

目标：后续执行者能定位本次到底运行哪个版本，不再从几十个驱动的历史推断。

步骤：

1. 首命令 `Get-Location`，核对 usage、Git HEAD/branch/status、活动进程、LM Studio resident、writer lock。遇到 lock 不直接删除。
2. 新建一次性目录 `benchmarks/work/harness-convergence/<唯一批次>/`，记录 tracked diff 和每个需要保全的 untracked 文件清单/hash；重要改动做命名可恢复快照。不要反复 stash 整仓。
3. 冻结实际 `.local-agents`、配置、加载器、profile、fixture、驱动、解释器版本。记录哪些选项仅在 isolated config 启用，不把根配置与试验配置混用。
4. 核实 §2 原始证据、canonical archive/preimages、JUnit 和实际 diff。work 目录可能被忽略；缺失就报告，不从总结重造。
5. 做一份只读 `current-state.json`：已接受的有限能力、未接受候选、各角色最后一次真实调用、旧 D2/C4/I1 边界与当前安装版本。
6. 将新驱动做成显式传入 root/config/fixture 的薄 runner；不要再通过修改被 import 模块的 `BASE` 来选择批次。不清理旧驱动。

借鉴 Tenet 的上下文派发事故，新增 `context-delivery.json`：列出每项必需合同/依赖事实从 packet → renderer → client 实际请求的对应位置及 hash，区别“生成过”“实际发送”“被截断”。不靠模型复述来证明信息已送达。另列项目稳定事实、当前 unit 信息、历史事件三个层级；只把与任务有关且可核对的内容送给 worker。

观测协议：隔离试验中保存准确的发送 messages、schema、采样参数、响应与应用结果，过滤凭据。只保存合成/授权 fixture 内容，不扩大生产 diagnostics 的原文日志默认范围。每份请求带 hash，原文仅本地保存；无可核对请求时标记证据不足。

输出：`baseline.json`、`preservation.json`、`current-state.json`、环境记录和下一阶段注册。任一历史/保护输入意外变化、不可恢复现有改动、环境身份不清时 HOLD。

## 7 R1 无模型的状态与编辑重放

目标：先确认工具可以可靠处理正确响应，隔离 host bug。无 LM 调用。

至少覆盖以下 20 类正负控制，每类明确预期状态、文件 hash 和交接结果：

1. 正确单函数 patch → 应用 → 当前检查事实。
2. CRLF/LF/BOM 对齐；检查 single-function guard 与 SafeEditor 的换行语义是否一致。
3. 旧 hash、外部写入和重复请求拒绝。
4. find 缺失或歧义，返回当前范围，不擅自模糊匹配。
5. no-op 不记 edit、不消耗有效修复、不无限重复验证。
6. 修改签名、相邻函数、保护测试、禁止路径与 symlink 均拒绝。
7. baseline 全绿但无有效实现，不取得新单元成功。
8. 格式化修正机械问题，hash 更新后重跑检查。
9. 格式化触及禁止范围/改变不允许的 AST/命令失败，fail closed。
10. Ruff F821/E501、类型错误和 JUnit 失败保留实际路径、行、规则及当前源码版本。
11. 正确补丁后模型错误说 blocked，已有检查事实不被抹掉，仍不能直接接受。
12. 错误补丁后有效修复，旧失败保留，旧 validation 不复用。
13. 零测试、全 skipped、缺 JUnit、超时、检查后输入漂移均拒绝成功。
14. unknown/false 合同判断不能被适配器填成 true。
15. schema 临时切换在成功、解析失败、传输异常后都恢复。
16. 重启恢复不重复应用或重复启动 Reviewer。
17. fresh Reviewer 收到正确 packet、累计 diff、最新验证，不接受 Coder 摘要作证据。
18. 旧模式兼容且默认配置不变。
19. 必需合同/依赖事实在实际 client 请求中确实存在；缺失、读取异常或被裁剪即 preflight 失败，不静默继续。
20. 当前任务上下文不误混另一个 unit 的源码、验收和失败；模型的身份声明不能覆盖 host 绑定身份。

先对当前 baseline 重放并归因；必要的新控制可证明已有确定性缺陷，但 R1 不顺手改生产 runtime。若缺陷使 R2 实验不可信，只允许在隔离 runner 修复实验基础设施并重新冻结，不能边跑模型边修。

输出 `replay-results.json`、真实测试记录、根因表和 R2 preflight。所有必需控制通过才进入 R2。模拟响应不计模型成功。

## 8 R2 匹配输入的能力诊断

### 8.1 已完成的原注册

问题：不要求模型选择 VALIDATE/FINISH 时，是否仍修不动同一个失败草稿？

固定 **2 个起点 × 2 个上下文 × 3 次重复 = 12 个调用**，每格仅一次提案，无模型修复重试：

| 轴 | 水平一 | 水平二 |
| --- | --- | --- |
| 起点 | 原 E501 失败 preimage，目标约 395 字符 | 后期归档失败 draft，目标约 648 字符 |
| 上下文 | 当前函数、完整硬合同、必要依赖与当前真实错误 | 正式 packet/repair 信息的完整渲染，合同语义相同 |

输出统一为已有精确 JSON patch（或具体 blocked_reason），模型、采样、4096 输出上限及现行请求 timeout 不变。两组均由宿主执行相同验收，**不自动格式化**，避免新增变量；沿用原诊断的 pytest、Ruff format/lint、严格类型与保护检查。原验收若因当前环境不可运行先解决环境，不能删检查。

实现提示：优先复用 `benchmarks/repair_context_factorial.py` 的 `messages_for`、`apply_proposal` 与 `checks` 思路，但新 runner 显式选择快照；不要修改旧批次文件或直接运行会重用旧目录的 setup。395/648 只是校验提示，真实文件和函数 hash 才是身份。

每个起点都先实际运行检查获得属于该快照的错误，不能给短起点附上长草稿行号。最小上下文也保留全部语义要求，不能删条件换成功。两组使用同一错误事实，差别只在上下文包装；记录渲染差异。

顺序预登记交错，不先跑完一个臂。一个响应一条归档，分别计算 parse、apply、non-noop、行为、静态与 all-check。无 Reviewer，不计完整链。

固定决策：

- 至少一组在 **648 失败草稿 3/3 all-check pass**：支持进入 R3，但只支持该条件下可修复。
- 只有原始起点 3/3：支持起点影响；不认为正式修复已解决，保持该修复族 Primary-owned。
- 没有失败草稿组 3/3：结束本路线本轮 live，不追加提示/轮数。可报告部分能力，但不强行启动 R3。
- 同起点不同上下文的差异仅为小样本支持，不声称唯一因果解释或全局模型上限。

R2 的固定重复旨在观察重复性，不因前两次相同普通失败提前删除第三次；这与旧计划的连续失败停止规则不同，启动本阶段即明确采用这套预登记规则。安全、预算或环境异常仍立即停止，余格记 NOT_RUN。

### 8.2 已完成注册：输出表示同期对照

问题：在完全相同的失败草稿、硬合同和结构化错误输入下，减少原文/hash 的输出复制，是否使模型稳定生成完整修复？不是再次加强定位提示，不把结果解释为单一复制字段的因果证据。

固定后期 648 字符草稿，沿用结构化定位批次的 user 消息、模型、采样、4096 输出上限、context、timeout 和全部检查。两臂均无自动格式化、无重试、无 Reviewer，每格仅一次 completion：

| 臂 | 模型输出 | 宿主处理 |
| --- | --- | --- |
| A exact | 现有 path/expected_sha256/find/replace 或 blocked_reason | 现有精确 patch 守卫与 SafeEditor |
| B whole | 仅 replacement（完整替换函数，含原签名和缩进）或 blocked_reason | 使用请求时绑定的 path/hash/完整原函数构造精确 patch，再过同一守卫与 SafeEditor |

顺序固定 **A1 → B1 → B2 → A2 → A3 → B3**，共六格。B 的 system prompt 只替换输出格式相关语句，保持修复目标、合同、保护与阻塞说明；schema 随输出形状改变。必须在 live 前保存逐字 prompt/schema 差异，不能宣称 system prompt 完全相同。不得在 B 中加入修法、正确示例、算法或额外推理轮次。

宿主不得重读新版本后悄悄更新绑定、修复缩进/语法、补写遗漏、模糊匹配或自动改 docstring；这些都会把宿主能力算入模型成绩。只接受原始 JSON 字符串所含完整函数；允许的换行归一化仅沿用已有编辑语义。签名、装饰器、相邻源码、路径、当前 hash、唯一 writer 与保护验收仍严格执行。

live 前完成：正确函数真实应用并通过全部检查；部分修复仍失败；no-op、仅换行、stale/external write、签名、相邻函数/注入、错误路径、多余字段、混合 blocked、正文非函数、解析失败均拒绝；adapter 成功/异常后恢复 schema/parser；实际 HTTP 请求与冻结 messages/schema 一致。正控只在验收者目录，不发送模型。旧 R1/编辑控制复用，生产 runtime 和正式 handoff 不改。

决策仍为同一失败草稿 **某一固定臂 3/3 all-check pass**，且保护输入/证据无漂移；B 只有 1/3 或 2/3 不放行。B 达标才取得 whole 候选资格；仅 A 达标则仅 A 可供后续使用。两臂都达标只能证明可行，结合 tokens/时间评估采用理由，不宣称成功率提高。两臂均不达标则结束这一候选并给出证据边界，不能自动改提示开下一轮。普通失败仍完成固定六格；安全、预算、服务或采集故障停止并保留 NOT_RUN。

新结果不得回写原两个 HOLD。R2 达标只支持采用该输入/表示进入 R3 设计与完整链验证，绝不等同产品或 R4 放行。后续实现沿用获资格的模型输出与宿主绑定，不在 R3 同时再次改变表示。

### 8.3 输出表示结果与当前下一步

2026-10-14 固定六格完成：exact 两次只修第 90 行、一次 no-op，whole 三次 no-op；两臂均 0/3。六次实际请求与冻结版本一致，均正常 stop，保护文件无变化。whole 每次输出 157 tokens，exact 为 396/396/394，输出缩短没有带来全检查通过。720 项确定性测试、302 个子测试通过；不能把这些离线成绩计为模型资格。

该结果不支持把复制负担当成已经证实的根因，也不构成一般模型能力失败证明。两臂共同使用强制 json_schema，仍未分离约束解码与模型生成表现。下一步唯一建议是先设计“同一 whole 输入/同一 JSON 输出要求，只切换服务端 response_format”的对照；两臂仍使用同一严格 parser、guard 和验收，不自动容忍非法输出。此建议尚未注册或执行 live，不能在本批中追加调用、改提示或增加修复轮数。当前 R2 HOLD、R3 前置和 R4 门槛均保持。

本次 live 计划版本保存在批次 checkpoint 中；本节是全部调用和保全核对完成后的文档状态更新，不修改注册、候选或历史 decision。详见 [完整交接](../benchmarks/work/harness-convergence/r2-output-20261014-1/handoff.md)。

### 8.4 强制约束解码单因素对照（2026-10-14 注册）

用户已批准继续下一步；本阶段起始 weekly used 8%，停止线仍为 15%。新批次 `r2-decoding-20261014-1`，不覆盖 §8.3 历史。

- 固定输入为上一批 whole-1 未改动失败草稿、原 messages 和完整函数 JSON 输出要求。模型、采样、上下文/输出预算、parser、宿主绑定、保护测试和检查原样保持。
- schema 臂保留 `response_format: json_schema`；plain 臂仅省略这个 HTTP 字段。plain 仍须返回合法 JSON，不容忍 fence、不提取裸代码、不纠正响应、不增加调用。
- 固定顺序 schema-1、plain-1、plain-2、schema-2、schema-3、plain-3；各一调用，总六格。实际 HTTP 请求删除 response_format 后必须与旧 whole-1 完全相等。
- live 前完成实际 client 请求差异控制、相同严格解析负控、上下文管理器异常恢复及旧 R1/输出适配回归。全部通过才冻结；不改生产 runtime 或 handoff。
- 门槛不变：固定臂 3/3 all-check 且六格完整、wire/保护 hash 核验通过。普通失败完成六格；基础设施、安全或 usage 停止保留 NOT_RUN。旧 HOLD 不变，R2 资格不是 R3/R4 放行。
- 六格结束即提交逐格结果、decision 和 handoff。若未过，不在本候选追加提示/调用。只能对该已暴露静态修复归因，不能宣称一般模型能力或跨文件能力。

### 8.5 解码对照结果与下一步边界

固定六格完成，schema/plain 各 0/3；六条输出正文完全相同，均合法 JSON、no-op、正常 stop。实际请求只差 response_format，单次输入 1243、输出 157 tokens；没有 HTTP、截断、解析、应用定位或保护范围故障。734 项离线测试及 302 个子测试通过；104901 个预存路径保全核对无漂移。weekly used 起止显示 8%，非精确成本测量。详见 [交接](../benchmarks/work/harness-convergence/r2-decoding-20261014-1/handoff.md) 和 [decision](../benchmarks/work/harness-convergence/r2-decoding-20261014-1/decision.json)。

关闭服务端 schema 并未改善该输入。失败发生于有效修复提案生成，不是正确改动卡在 patch/验证/终态。但两臂都仍使用 JSON 转义的源码和合同，不能将这种输入下的单提案失败直接推广为模型整体无能力。

唯一下一步建议为输入表示对照设计：原 JSON 输入与逐字段无损的多行源码呈现，保留全部合同、错误事实及同一 whole-function JSON 输出。先离线验证事实等价，不加修法、示例或预算。该下一批尚未注册/执行；若仍失败，应报告当前配置能力边界，不无限扩展提示。当前 R2 HOLD，R3/R4 门槛不变。本节是本批结束后的状态更新，冻结计划仍保存在 checkpoint。

### 8.6 输入源码表示对照（2026-10-14 注册）

用户批准继续 §8.5 建议，起始 weekly used 9%，上限 15%。批次 `r2-rendering-20261014-1`，固定 json-1、literal-1、literal-2、json-2、json-3、literal-3，各一次模型请求；无补跑、额外提示、格式修复或预算扩展。

两臂均沿用上一批 plain-1 的完整函数 JSON 输出、同一 system prompt、无 response_format、模型/采样/预算/保护测试和严格应用器。唯一改动为 user 输入中 target.source 和两条 current_source_line 从 JSON 转义字符串变成有明确字段标签的原样文本块；其余 metadata/合同不删减，不加修法。宿主可逆还原必须与原 facts 逐字段完全相等，实际 wire 除该 user 呈现外与 plain-1 相等。两条错误与源码一起改变呈现，结论只归于这个输入表示组合，不区分其中单个字段。

前置：展示无损、缺块/重复/串位/多余内容拒绝、实际 client 请求控制、原编辑/解析边界及全套 R1 回归通过。先冻结再 live，不改生产 runtime/handoff。固定臂 3/3 all-check 且六格完整、wire 与保全核验通过才取得 R2 资格；不是 R3/R4 或产品放行。

普通失败完成六格；基础设施、安全或 usage 停止保留未运行格。结束提交原始请求/响应、逐格检查、decision 和 handoff。若仍失败，结束这组表示微调，报告当前输入/单提案/模型配置下的能力边界，不自动继续堆提示或开另一个候选。

### 8.7 输入表示结果：有用修复与拼接边界分开计分

六格全部完成。json 三次 no-op；literal 三次实际修复两条 E501，11 项行为测试、lint、Pyright 均通过，但 format 失败，因此两臂 all-check 均 0/3。literal 输出少了旧函数块的末尾换行，精确替换后移除了相邻 @staticmethod 前的空行；只读 Ruff diff 仅要求补回此空行。没有自动格式化、补跑或改分。

751 项确定性测试、302 个子测试通过；106722 个既存路径核对无漂移。实际 wire 仅 user 呈现不同，完整 facts 无损；没有 HTTP、截断或解析故障。weekly used live 起止显示 9%，上限 15%。[完整交接](../benchmarks/work/harness-convergence/r2-rendering-20261014-1/handoff.md)、[decision](../benchmarks/work/harness-convergence/r2-rendering-20261014-1/decision.json)。

本题已有输入适配影响的证据，不宜再笼统归为模型不会修；仍不能宣称跨题稳定。下一步结束表示微调，固定 literal，只设计宿主拥有函数终止换行/原始分隔边界的窄契约。先覆盖 LF/CRLF/EOF、装饰器邻接、尾换行差异、stale hash、签名/邻接源码、no-op 等离线控制；作为新候选重新注册固定批次，禁止把本批补空行后改成 PASS。格式检查、R2 3/3、R3/R4 门槛不变。该修复尚未实现或 live，本节只是保全结束后的状态更新。

### 8.8 函数终止换行归属候选（2026-10-14 注册）

用户要求自主推进到 R2 通过或 weekly used 15%，本次启动实际 10%。固定 literal-1 的 messages、模型、采样、预算、JSON parser 与全部检查；不改生产 runtime/handoff。

新批次 `r2-boundary-20261014-1` 固定 raw-1、owned-1、owned-2、raw-2、raw-3、owned-3，各一调用。两臂实际请求必须完全等于上一轮 literal-1；唯一差异在 host 绑定：raw 原样精确替换；owned 将函数文本的零或一个末尾换行映射到原绑定函数的终止换行，原源码其余前后字节保持。仅沿用 LF/CRLF 归一化，不修正文、缩进、语法或 docstring，不执行 formatter。

多个尾部空行、尾部多余声明/注释拒绝；签名、装饰器、相邻源码、stale hash、路径与 no-op 仍严格拒绝。输出正文与绑定后的参数分别归档，不把宿主补的行终止符算成模型生成。前置正负控覆盖 LF/CRLF、EOF、相邻装饰器、尾换行有无、多尾换行、签名/作用域/版本/no-op；旧模型响应仅离线重放，不回写旧成绩。

门槛仍是固定臂 3/3 all-check、六格完整、实际 wire 和保全一致。原 11 项行为测试、format/lint/Pyright 全部不放宽。取得 R2 资格只用于 R3 设计，不代表完整链、迁移或 R4。若未过，本轮用户已授权在预算内按新证据独立注册下一候选，但不能改本批分母或中途修候选；达到 15% 不启动新调用。

### 8.9 R2 放行结论与适用边界

固定六格全部完成：raw 0/3、owned **3/3 all-check**。六次真实请求完全相同，六条模型响应也相同，均修复两条 E501；owned 每次仅恢复原函数块已有的一个终止 LF，模型正文未改。原行为测试、format/lint/Pyright 全通过，保护文件和 108545 个预存路径无漂移。25 项边界控制、776 项完整回归及 302 个子测试通过。weekly used 10% → 11%，停止线 15%；因 R2 已通过停止，没有继续到 R3。

新决定只赋予 `literal + whole JSON + owned terminal boundary` 候选 R2 资格，不覆盖历史 HOLD。不是降低格式门槛、自动格式化、增加模型轮数或 Primary 代写；宿主边界归属变更已在 §8.8 前置登记，原始响应与变换参数分别可审计。[decision](../benchmarks/work/harness-convergence/r2-boundary-20261014-1/decision.json)、[完整交接](../benchmarks/work/harness-convergence/r2-boundary-20261014-1/handoff.md)。

后续只将这一组合用于 §9 的 R3 设计/离线整合，先完成版本化事实交接、独立 Reviewer 兼容控制与隔离安装回归，再完整链固定批次。不把旧不完整原型直接当正式入口。R3/R4、迁移、跨文件、产品接受和 Primary 成本收益都仍未验证。生产 runtime/handoff 本轮未修改。

## 9 R3 单一宿主流程候选

进入条件：R2 通过，用户批准本阶段及 §4.3 的新协议边界。先设计和离线测试，再 live。

只做一个完整候选：从第一次提案就使用受限 proposal 模式，不再等失败以后才切换 patch-only。继续使用 R2 通过的上下文、输出表示和受控适配；底层仍为精确 patch，不在 R3 再换编辑格式、采样、Reviewer 或模型。

### 9.1 状态机与上下文

- host 状态：PROPOSE → APPLY → CHECK → REPAIR 或 REVIEW_PENDING → PRIMARY_PENDING；另有 BLOCKED/FAILED/INTERRUPTED。
- 模型输出 patch 或具体阻塞；单函数试验的必要源码由 host 提供。若缺必要依赖，返回具体证据请求/阻塞，不能杜撰事实；本阶段不扩展通用仓库探索工具。
- 一次真实 patch 后直接进入可信格式化和检查；先有有效改动才有实现资格。全部通过不再要求 FINISH_SUCCESS，不再发无意义终态 nudge。
- 修复上下文保留完整合同、当前源码、当前错误、最近尝试是否产生实际改动和剩余预算。旧失败片段不当作当前源码；不把 rejected proposal 重放成成功示例。
- 不自动重试 identical no-op；同版本连续两次 no-op 即结束该调用。保留合法 blocked 路径，不强迫模型伪称能解决。
- 不将“只返回最新源码”误称为完整记忆；用确定性执行收据保留已做/未做事实，不引入额外摘要模型。

### 9.2 实现边界

优先新增默认关闭的窄适配层，复用 SafeEditor、ValidationRunner、archive 与 handoff 事实核验，不 fork 整个 WorkerRuntime。若这些部分无法独立复用，先形成最小提取方案与等价性回归，不用大规模重构混入 live 候选。

重点检查符号：`single-function-context.py` 的 `messages/guard/patch_messages`；`worker-runtime.py` 的 `_record_edit/_required_repair_focus/_contract_check/_assert_submission_contract`；`local-unit.py` 的 canonical handoff；现有 formatter、输入 hash、Reviewer request 生成及 `record-review.py`。

新状态/版本对安装器、CLI、task-policy、Coordinator 消费者影响须列出，未知版本 fail closed。classification 与跨文件任务不通过新模式派工。所有旧模式确定性回归、R1 反例、新 handoff 控制及隔离安装预检通过后冻结。

### 9.3 开发题同期对照

两个已暴露任务（匹配的 repair 起点、presence）× 三次 × baseline/candidate = **12 个 Coder 单元**。

- baseline 是 R0 冻结的当前正式单函数路径，不能偷偷换成历史最好版本；candidate 为本节唯一版本。
- 两臂相同源码、合同、保护测试和可信格式化权限；不把宿主自动检查记为模型动作。
- 每单元最多 6 次模型请求、3 次有效 patch、3 次完整检查、2 次本地修复；若旧冻结配置更小则两臂取更小值。请求/单元超时在 live 前登记，不能临场增加。
- 候选是流程与接口组合对照，不能将差异单独归因于提示长度或某一字段；R2 才负责上下文因素。
- 所有具备对应模式交接资格的单元自动启动同一 Reviewer；未具备则不调用，不得人工喂正确源码挽救。
- Primary 中途不代写、不提供算法答案、不纠正模型语义；最终按风险 review。干预例另记 assisted，不计自主成功。

进入 R4 要求：candidate **6/6 完整链接受**，两个任务各 3/3；零安全/过期验收错误；保护输入不变。若 baseline 同为 6/6，只能说候选可行，不能声称稳定性提升；需有更低协议开销才有采用理由。

任一 candidate 普通失败使本 gate 已不可达时，归档并停止剩余 live，保留 6 格注册分母和 NOT_RUN；不另开第二候选。不以 baseline 更差放宽 candidate 门槛。

### 9.4 本轮 R3 起点审计与停止（2026-10-15）

唯一宿主候选已实现、默认关闭：版本化 `host-proposal-v1`、宿主检查和未知 worker assessment 分离、独立派审与 Primary 核验、旧模式兼容。27 条新协议控制及完整 809 测试/302 子测试通过，安装与十二个入口无模型预检通过；三道真实依赖迁移题在 live 前封存。

但 `harness_r3_prepare.py` 的 repair 源目录选择有错误：复制了 R2 `raw-1` **运行后**工作区。冻结起点 hash 为 `7d75cbe0…`，复制到两臂的实际 hash 为 `73e760ea…`，后者恰是旧 raw 的最终结果；E501 已修，剩下的却是函数后分隔空行缺失。预检只比较两臂相等，没有校验上游冻结起点和预期错误谓词，因此错误地允许 live。这是 Primary 的实验构造错误，不归责模型或服务。

已执行 repair-baseline-1（4 次 no-op）和 repair-candidate-1（2 次 no-op）；两者均无有效编辑、Reviewer 0 次。保留全部原始请求、响应、失败与 12 格注册分母，余 10 格 NOT_RUN。能力有效样本 0，不能给候选“0/6 能力失败”或声称 R2 的 3/3 被推翻；R3 也没有通过。新协议无模型控制仍有效，但实际完整链尚未证明。

只新增离线 `harness_fixture_origin.py` 起点控制，不修改 live 冻结候选、驱动或既有结果。它会拒绝“两臂同错”，正确源码副本已通过 11 行为测试、format、Pyright，保留原两条 E501；没有修补它或调用模型。当前错误批次关闭。下一步必须以**同一个候选**另立纠正实验注册，先绑定上游 pre-run 全部源码/保护测试 hash，并验证预期失败类型，才允许调用；不是在原格上重跑覆盖失败。此新批次需单独批准，不在本轮悄悄启动，不增加提示、改变模型或放宽门槛。

### 9.5 同候选纠正批次：修复成功，CLI 派审接口失败

用户批准继续后，另立 `r3-origin-fixed-20261015-1`，不改旧批次或生产候选。每格源代码/保护测试绑定上游 pre-run freeze；复制前、复制后、调用前校验，并在十二格上实测预期失败：repair 11 测试通过、format/Pyright 通过、仅第 84/90 行 E501；presence 9 测试中四个指定参数例失败、静态检查通过。15 项起点/失败谓词正负控制通过；原 809 测试及 302 子测试是同哈希候选的既有证据，本次没有冒称重跑。

固定顺序执行前两格：baseline 4 次请求（3 次 no-op、1 次失败验证），没有有效编辑；candidate **1 次请求、1 次有效编辑、2 次宿主检查（含起点）**，11 行为测试与 format/lint/Pyright 全通过，独立复验一致。实际 diff 仅将两条 docstring 长行换行，执行逻辑、保护文件和其他成员未变。新模式本题修复有正证据，但不是重复稳定性或迁移结论。

正式入口随后在 `handoff_gate` 报 `Unknown host execution protocol`。canonical `handoff.json` 有 `execution_protocol: host-proposal-v1` 和显式 `worker_assessment: null`；`worker-runtime.compact_handoff()` 未保留这两个字段，默认 CLI 写出的 `coder.json` 因而缺失。`local-unit.verify_handoff()` 拒绝是正确的 fail-closed 行为，不应放松门槛。无模型重放确认：完整归档可验证；其 compact 投影与实际 CLI 简报完全相同并被拒绝；仅在内存恢复 canonical 协议字段可通过同一 verifier。此反事实没有写回报告、没有派审、不是补跑成功。

此前 27 项协议控制的正路径从 `runtime.run()` 直接传完整报告到 verifier，未经过真实 CLI 默认序列化；十二格入口预检也不执行完成报告往返，因而漏掉跨层字段传播。本轮 Reviewer 调用 0 次，不评估或归责 Muse。候选已执行 1 格，完整链接受 0；另 5 格 NOT_RUN。总注册 12、执行 2、余 10 NOT_RUN。停止原因是确定性集成失败使原 6/6 门槛不可达，不是 token 限额或模型能力总否定。weekly used 6% → 7%，停止线仍 30%。

唯一下一步：需单独授权一个 **serializer-only 机械修复**，显式透传协议/unknown assessment，不根据状态补造协议、不绕过 canonical 验证，不改变上下文、模型、编辑接口或 Reviewer。先补实际安装后 CLI/子进程的完整往返正控，以及未知/缺失协议、伪造 assessment 的负控；证明运行成功报告经默认 compact 路径仍能派审。随后另立固定完整链批次，旧失败不覆盖、不在本批追加第二候选。R4、提示调优和全局默认启用均不在自动范围内。

## 10 R4 未暴露迁移与 Reviewer 验证

### 10.1 三个迁移单元

在 R3 live 前由 Primary 冻结三道新题，参考实现与 mutation 控制只对验收者可见。候选作者不使用这些题调提示；执行环境只能读取题目、真实依赖和指定可见测试。这里的“未暴露”仅指未用于该候选开发，不声称模型预训练未见。

建议任务结构：

1. 同类机械错误但不同源码结构，避免只是重命名 get_many。
2. 单函数正常/空值/错误边界，覆盖 falsy 值和异常传播。
3. 单函数消费真实类型/依赖，包含分支交互，不能靠一条静态修复完成。

优先从兄弟仓库只读复制适合的切片。若采用公开 benchmark，固定项目 commit、issue 文本、许可证、环境和独立测试；禁止把 gold patch 或 hidden 测试泄露给 worker。没有匹配环境就不用该题，不在本阶段临时装 Docker。

每题 2 次 × 两臂 = **12 个 Coder 单元**，预算与 R3 相同；新旧失败都保留。保持 Reviewer 不变，合格 Coder 自动完整交接。

门槛：candidate 6/6 完整链、逐题 2/2、无新增 safety failure、没有语义接管；同时不低于 baseline 同期表现。失败停止扩展，不重新挑更简单的题补足成绩。

### 10.2 Reviewer 的独立资格

保留既有固定 16 条语义控制及其裁决标准，R0 必须定位准确文件/hash，不新造一个同名 16 条集。以同一 Muse/原预算做一轮，结果与新 handoff 来源分开记录。

R3/R4 的 clean 通过不能替代 hidden 缺陷检出。旧 16 条不能达原门槛，则旧 Reviewer gate 仍 HOLD；可以保留 Primary 全量审查的受监督模式，但不得称三角色自主放行，也不能边改 Reviewer 边解释 Coder 候选。

补做不调用模型的 handoff 负控：伪造检查、旧源码、合同缺项、模型拒绝/unknown 被偷换确认、重复派审均拒绝。若新协议产生缺口，停止产品集成。

### 10.3 2026-10-16 R4 闭批与关键判断

`r4-transfer-20261016-1` 固定候选未在 live 期间改动。三个已执行候选均完成编辑、配置检查和自动派审，证明这三次没有 patch/CLI/handoff 阻断；其中 `collect_tools` 仍把已有调用的合法 None 结果当作不应处理，状态错误地保留 requested。保护测试覆盖 False 和 0，却没有这个 None 分支。独立只读探针：冻结参考 6/6、候选 5/6。Reviewer 引用了该条件却仍声称全部 falsy 保留，属于真实语义漏检，不是报告格式问题。Primary 拒绝，剩余迁移格按原门槛停止，无重跑或语义代写。

原 16 条独立 Reviewer 控制完整执行并逐份裁决，15/16 正确。`required-coverage-r1` 的原始提案识别了必需测试缺失，但反复提交空 findings 或矛盾的 verified/violated 字段，耗尽原协议预算；不计通过，也不能把它误诊为没读懂合同。另一重复成功不覆盖该失败。合同冲突 2/2 正确 escalate；原缺陷控制均找到源码支持的因果问题。已暴露的简单控制正确，不推导复杂依赖切片也可靠。

收尾误用运行前的“不得存在 current-task”断言导致 10 pass/1 fail，记录保留。独立运行后审计 5/5：15 个成功报告的索引均是本次完成后生成、唯一 review_id；失败格无完成索引；冻结输入不变，模型请求未包含 Primary 答案或索引。没有改原断言来消除失败。

下一阶段建议见 R4 handoff：先将已暴露语义反例转为新回归，审计合同到类型边界/验收测试的覆盖；另立一个更小 Reviewer 报告 DTO 的离线候选，只让宿主推导冗余机械字段，不替模型推断语义；独立冻结新迁移题。原 R4 HOLD、6/6 和 16/16 标准不变。这涉及 Primary 测试准备职责及新的 Reviewer live 候选，需明确关键决策，不在此闭批后静默追加重试。Goal 仍未完成，停止不是因已用尽 30%。

### 10.4 已批准的独立 Reviewer DTO 阶段（2026-10-16）

候选只在 `benchmarks/reviewer_compact_dto.py`：模型输出 assessment/findings/contract_review/ordering_review/unverified_claims 五类语义信息；宿主从模型显式状态派生合同索引，从可信当前验证派生 check IDs，绝不自动判断合同正确、生成 findings 或绕过原引用/覆盖/权限门槛。生产 `.local-agents` 未修改，模型、上下文、16 turns/4 protocol errors、原 16 控制与实质裁决标准均不变。

离线 17 控制通过，含实际子进程入口和旧失败 REPORT 重放；原运行时相关回归 **704 tests + 302 subtests** 通过。重放只接受原本已给出明确缺陷的第二份旧报告，仍拒绝两份缺 findings 的报告，不算 live 成功。live 冻结后没有改候选、控制、输入或重采样。

新批次 **15/16**：六条正确实现通过、六条实际缺陷检出、两条合同冲突升级；两条必需覆盖缺口一正确、一无报告。失败格 `required-coverage-r1` 六次读同一测试、一次非 JSON 输出，无 REPORT 尝试；实际测试五行/94 bytes，原始动作又请求到 94 行。模型已观察必需负数测试缺失，但未形成有效审查输出。READ 返回范围和 truncated，却没有显式 total_lines/EOF；这是待隔离验证的接口假设，不能直接断言缺两个字段就是根因。实际最大输入 5635 tokens（全批），失败格 5258，context 24576，无 length 截断或 HTTP 400 证据。

全部 16 格：旧 79 次 chat completion、465.358 秒；新 74 次、416.828 秒。输入 tokens 347407 → 343834；减少字段没有显著减少总输入，且两批并非随机同期试验。Primary 主动时间与云 token 未测，不声称省成本或成功率提高。新收尾 7 条控制通过，并以全新子进程重现旧 reference 6/6、旧 candidate 5/6 的 None 语义反例；这仍是检测到失败，不是修复。初版收尾测试误比较动态时间戳，6 pass/1 fail 留档；只修新审计的时间戳值比较，保留类型/是否存在和全部语义字段，原验收不变。

阶段决策：该候选 **HOLD，不提升到生产、不启动新迁移或 R5**。下一步不继续微调 REPORT 字段或重跑旧题。应单独设计证据观察接口：明确完整文件边界、当前已展示/仍缺范围、与报告就绪一致的当前状态，先离线证明事实不增不减和陈旧输入拒绝，再决定是否值得一个新冻结候选。不得把宿主提供证据偷换成宿主提供语义结论，也不得自动把“已读”当作“理解”。原 None 漏检需继续作为显式已暴露回归；即使协议恢复，也还要新迁移题 6/6 完整链及独立 16/16 才满足 R4。

## 11 R5 Explorer 与 Coordinator 的条件推进

前提是 R4 范围内任务族可用；此阶段不负责拯救 Coder。模型与单驻留不变。

### 11.1 Explorer

不因为可选而跳过资格。预登记三个有真正未知定位问题的只读调查：入口到实现、错误路径到测试、两个候选符号的消歧，各两次，共 **6 次**。

分别打分：协议完成、文件/行证据真实性、回答完整性、结论与源码是否一致、Primary 收窄次数。目标 6/6 真实且完整；不能由 Coder 后续成功覆盖失败。已知路径给得过多的题只算 anchored locate，不扩大为自主仓库调查资格。

只评估当前 Explorer；若需要改提示、工具或上下文，另立阶段，不混进 Coder 候选。缓存命中不冒充新模型成功。

### 11.2 Coordinator

保留已批准能力目录，classification 归 Primary，未知族 fail closed。只调度通过本计划范围内的任务，不因“单函数”自动认为能力合格。

两条预先冻结小 feature：一条两个 local 单元的真实 producer-consumer 依赖；一条 local 单元与计划内 Primary 单元的混合所有权流程。每条做 Primary 编排与 Coordinator 编排各一次，最多 **4 个 feature**，最多 8 个 Coder 单元、相应 Reviewer，Coordinator 提案最多 2 次。

Coordinator 负责拆分提案与路由，Primary 仍批准风险/范围/依赖。消费者必须等生产者独立接受，最终执行 exact-input round-trip/rejection 集成检查。外部 rework 不补成首轮通过。

采用 Tenet 的能力适配思路，但不用“拆得越小越好”：每个单元记录任务族、交互不变量数量、所需依赖事实、预期工具负担和独立验收。相邻单元如果需要共享未完成状态或同一原子提交，应合并或归 Primary；不要为了让 local 接单牺牲行为完整性。给 worker 当前单元及依赖接口，完整 DAG 归协调层保存。

通过只代表该目录内受监督编排可用；任一合同或依赖错误阻止扩展。不得恢复旧 D2/C4 失败分数，不启用全局 coordinator 默认值。

## 12 成本与协议负担的测量

每格记录，不只记录成功格：

- 语义：实际行为验收、静态检查、完整链接受、有效修复率。
- 协议：parse/schema 错误、patch 拒绝、no-op、仅用于确认/终态的请求数、错误阶段切换、未验证退出。
- 上下文：实际输入/输出 tokens、各部分大小、裁剪与错误可见性、当前源码版本；不以字符估算替代服务实际 usage。
- 时间：加载、推理、验证、Reviewer、等待、端到端；耐心等待加载不等于删除加载成本。
- Primary：准备合同/测试、诊断、审查、修复/接管的主动时间分别计时；无法测量写 unknown。
- 云端：可取得的 tokens/计费独立记录；weekly used 仅停止线，不作为节省证据。

R3/R4 比较相同准备材料的稳态运行成本；一次性 harness 开发成本另列，不能抹去。R5 经济结论需包括失败和接管。若要推荐日常启用，预登记的最低目标是配对任务 Primary 主动时间中位数减少至少 20%，每题完整链均被接受，端到端时间不超过 Primary 对照的两倍。该阈值是本计划的初始产品取舍，不是事实；用户可在 live 前调整，不能事后改。

主动时间无法可靠测量时只给质量结论。相同 Primary 第二次处理同题有学习偏差，须交错顺序、保留逐题值，并将小样本经济结论标为试点结果，不作长期收益承诺。

## 13 总预算与阶段停止

| 阶段 | live 上限 | 放行含义 | 失败后的默认动作 |
| --- | --- | --- | --- |
| R0 | 0 | 基线可核查 | 补证据或报告阻塞 |
| R1 | 0 | 工具/状态控制可信 | 修实验，不烧模型重跑 |
| R2 | 12 次单提案 | 失败草稿在某固定条件下可修 | 保持该族 Primary-owned，交接分析 |
| R2 定位补充（已结束） | 3 次单提案 | 0/3，未取得资格 | 保留 HOLD |
| R2 输出表示（已结束） | 6 次单提案，两臂各三次 | 两臂 0/3；原 3/3 门槛不变 | 已结束该候选，交接证据边界 |
| R2 约束解码（已结束） | 6 次单提案，两臂各三次 | 两臂 0/3；六次 no-op | 不继续调整输出 schema；见 §8.5 |
| R2 输入表示（已结束） | 6 次单提案，两臂各三次 | 两臂 0/3 all-check；literal 三次修复 E501、format 失败 | 固定 literal，定位函数换行边界；见 §8.7 |
| R2 终止换行（已结束） | 6 次单提案，两臂各三次 | **owned 3/3、raw 0/3** | R2 资格已满足，停止本轮；见 §8.9 |
| R3 | 12 个单元，最多 72 次 Coder 请求；Reviewer 最多 12 次调用 | 开发题上的新模式可用 | 结束唯一候选，不补第二版 |
| R4 | 12 个单元，最多 72 次 Coder 请求；Reviewer 最多 12 次调用，另 16 条固定挑战 | 三个未暴露单元有限迁移 | 不启用产品默认，不放宽审查 |
| R5 | Explorer 6 次、Coordinator 2 次、Coder 最多 8 单元及相应 Reviewer | 受监督能力目录编排 | 保持人工编排 |

这些是条件上限，不是必须花完的预算。Reviewer 每次内部请求数/timeout 保持当前已冻结配置，不因本表增加。不得并行驻留模型节省墙钟时间。

优先停止条件：用户叫停 → 安全/保护漂移 → weekly used 达当前上限（现为 50%，已达到）→ 需要用户决定的架构/语义取舍 → 阶段明确 FAIL/HOLD/实验无效 → 阶段完成。R2 按各自注册完成固定重复后判断普通失败，R3 按 §9.3 的门槛不可达规则提前结束。infra、实验装配故障与质量失败分开；没有有效证据就给 INCONCLUSIVE，不做无边界重试。

若用户批准自主推进，只能沿依赖满足的阶段走；R3 新协议仍需明确授权。任何模型替换、全仓重构、新增角色、公开 benchmark 环境安装、真实项目写入、发布或新增 live 候选都不在默认授权内。

## 14 何时考虑替换 Harness 或模型

- 简化提案可用，正式循环不稳定：优先替换内循环的职责分配，保留权限/归档/验收底座。
- 正确提案在离线重放被拒绝：修编辑与上下文版本接口；不能归因模型。
- 同输入下简单与正式提案都语义失败：在这个任务/预算/模型配置下能力不足，收缩任务族；不是整个本地模型项目失败。
- 只有 Primary 给算法后成功：登记 assisted 模式和额外成本，不能计自主能力。
- Coder 可用、Reviewer 语义不合格：保持 Primary 实质审查，不用报告格式合法掩盖漏检。
- 现有 runtime 无法不破坏旧模式地支持新流程：提交小范围重构或外部 harness 对照提案，先列安全差异与迁移成本；不在失败现场直接整仓换框架。
- 新模型仅在独立授权后做同题同环境对照，先兼容再能力测试。model agnostic 指协议与安全逻辑不依赖具体模型，不意味着任意同参数规模模型无资格验证即可替换。

## 15 结果交接包

每阶段保存以下新文件，不覆盖历史：

```text
<batch>/
  registration.json
  freeze.json
  environment.json
  cases/<case>/<arm>/<attempt>/
    request.json
    response.json
    proposal.json
    events.jsonl
    diff.patch
    checks/
    archive-references.json
  metrics.json
  preservation.json
  decision.json
  handoff.md
```

原始请求响应仅在本地隔离 fixture 保存，凭据不进入归档。canonical worker archive 仍为工作流事实来源，避免新采集器成为第二套互相矛盾的真相。

`decision.json` 至少包含：stage、candidate/hash、registered/executed/not_run、各层成绩、逐题配对结果、Primary 干预、失败分类、适用能力边界、未知项、usage 起止、停止原因、下一步唯一建议。不给一个混合的 total_success 隐藏各层。

`handoff.md` 应直接回答：

1. 模型有没有产生正确且实际应用的改动？
2. 正确代码是否丢在验证/终态/交接上？
3. 改善来自哪个被控制的因素，哪些只是推测？
4. 新题是否迁移，Reviewer 是否真正被调用且有效？
5. Primary 工作有没有减少，测量缺口是什么？
6. 下一步继续、收缩还是停止？给唯一动作，不列无限备选实验。

## 16 可直接交给下一位执行者的指令

### 已批准并完成：静态错误理解与再生成负担的独立诊断

新批次`repair-representation-20261018-1`已按以下设计完整执行9/9，36项离线负控通过。
A错误解释3/3正确；B整函数3/3应用且类型错误修好，但全部Ruff格式失败；
C片段3/3应用且12项测试/Ruff/Pyright全通过。逐格裁决、wire、diff及全部失败保留。
三臂user message逐字节相同；相对前一批共同新增定位片段，不能把跨批改善全归给输出格式。
没有独立Reviewer或正式循环接受；下一步应单独授权/登记正式循环候选，而非直接产品放行。
原始设计及当时的待批准说明以下保留为历史，不代表仍在等待本九次实验的授权。

前置事实：`scheduling-live-20261018-1/post-close-feedback-audit.json`逐一核对三份真实第二请求。
失败检查的id/status/exit_code/output/diagnostic与当时validation-attempt-2完全一致；
当前源码、binding、source_sha256一致；Any导入可见；没有转发已解决的pytest失败。
generic diagnostics为空、通过pytest摘要与失败Pyright共存，但错误并未缺失；
不能凭这两个字段现象就宣称根因已确定。此审计零模型调用，不改变旧分数。

下一诊断在获得明确批准后独立登记，不重开旧批次：

1. 输入固定为`new-1`第二请求当时的完整事实和源码，保持原合同、测试、错误与hash；
   此任务已暴露，永久不算holdout。Primary只从实际Pyright文件/行定位唯一helper声明行，
   不提供修复后的代码或算法。绑定片段可同时展示给三臂，防止定位信息成为隐藏差异。
2. 三臂各三次、交错执行，总上限九次单提案，零额外兼容probe或失败补跑：
   A只解释错误（受约束的原因/受影响符号/所需变化，不编辑）；
   B整函数replacement；C当前错误行的受控片段replacement。
   只有输出任务/表示不同，不同时精简输入、加示例、改模型或提高采样预算。
3. C的path/hash/find由宿主从冻结快照绑定；模型只给replacement或blocked_reason。
   不让模型指定位置，不解析围栏、不修JSON、不自动补注解、不静默修改主体代码。
   重建结果仍过原outer-function签名/AST、SafeEditor、当前hash、原验收与全部静态检查。
   片段不得换helper名字、参数结构、增加语句或改非授权行；这只是隔离单个静态错误的诊断接口，
   不冒充一般单函数能力或扩大Coder任务族。
4. live前先做正确/错误/空/重复key/多行/围栏/错hash/错位置/外部源码变化负控，
   以及实际安装入口和序列化往返；冻结后不改。模型保持Qwen，context24576，
   并发1、单驻留，原温度/4096输出/请求超时沿用。每样本只允许一次提案，
   更低请求量不视为更严格的完整worker放行门槛，而是本诊断的固定观测单位。
5. A按预登记的源证据rubric由Primary裁决，不要求唯一术语/代码形状，不把判断当gold；
   B/C实际应用于独立隔离副本，原12项可见/私有测试、Ruff、Pyright不变。
   只计算提案可应用性与实际检查，不记ready/accept或绕过Reviewer。
   若后续要声称完整Coder单元成功，必须另走原canonical验证、独立Reviewer、Primary接受流程。
6. 解释界限：A正确且C正确、B失败，支持再生成粒度负担；A正确但B/C失败，
   支持理解到代码动作的转换仍有问题；A也失败不能直接推出模型普遍无能，
   仍需区分诊断输出协议及输入干扰。三臂不能混算总通过率。
   同一已暴露样例的相关重复只作窄诊断，不推断新题成功率或省成本。
7. 保存registration、准确wire、原始响应、绑定/拒绝原因、实际diff/检查、逐样本裁决、
   preservation、decision、handoff。weekly used15%停止，保留历史与现有改动，
   兄弟仓库只读，不改生产runtime、不commit/push。达到固定九样本结论即闭批，
   不扩大题库、模型或预算来填通过数。

此处只是下一实验设计，没有新模型调用或新片段接口实现。需要用户批准此新的live诊断；
已批准的旧/新调度六轮授权不能默认为批准第三个协议候选。整体R4仍HOLD，
必须继续达到未暴露三题两轮完整链及独立Reviewer等原放行标准。

### 2026-10-18 已批准的输出通道对照结果（覆盖下方待批准状态）

用户随后明确批准验证调度live对照，已在
`benchmarks/work/harness-convergence/scheduling-live-20261018-1/`闭批。
固定schema，旧/新调度各三轮，完整链均0/3，实际Coder请求旧每轮1次、新每轮2次，总9次。
新调度三轮都在第二次HTTP请求展示Pyright准确路径/行号、reportMissingParameterType及当前未注解函数源码；
模型第二提案仍保留缺失obj注解并引入Ruff格式回退。最终运行时先因格式失败，
独立检查确认类型错误仍在；不混淆最后运行时是否执行Pyright。行为测试各格12/12，Reviewer零次。
因此调度修复消除了“无修复机会”的阻塞，但当前整函数提案/反馈/模型组合下修复转化仍0/3。
不放行，不加预算、不补跑，不推断更小修复接口或其他任务也必然失败。
下一唯一建议是独立隔离报错理解与整函数再生成；原合同、保护测试、安全门槛不变，
新live须按计划登记授权。保留全部逐格wire、失败、canonical replan和历史；weekly used仍2%，整体目标未完成。

后续无模型调度候选已单独登记并封存：
`benchmarks/work/harness-convergence/prevalidation-format-offline-20261018-1/`。
7项不同离线控制通过，旧三次验证耗尽可复现；前移既有受控格式化后，
在相同三次验证上限内向第二脚本提案展示真实类型错误，最小注解修复后原canonical gate通过。
首次3通过/3失败及后续脚本夹具修正均留档；没有live、没有模型能力/产品信用。
实际pytest次数旧失败2次→新脚本成功3次，仍在原上限内，不能说实际执行成本未增加。
格式化越界、改语义、源码/保护测试陈旧、无opt-in及预算耗尽均拒绝。
下一live候选仍需按计划独立授权和预登记，不能把当前goal自动续跑当作新增live授权。

用户已明确批准独立输出通道实验并恢复推进。新登记批次为
`benchmarks/work/harness-convergence/output-channel-20261018-1/`，旧迁移失败批次未重开。
保持同一 Qwen、单模型驻留、逐单元六请求/三编辑/三验证/900秒，Reviewer及合同、
保护测试、hash/签名/AST/安全编辑边界不变；不修改生产默认配置或生产runtime。

25项离线控制通过，含两种通道真实host编辑、验证、canonical handoff重放。
第一次扩展控制为23通过/2个Windows默认临时目录权限错误，原XML保留；
使用新的仓库内临时目录后25通过。不是模型失败，也没有修改验收断言。

固定两臂各三轮已全部执行：原始文本三轮均含Markdown围栏，共18次请求全部在编辑前拒绝；
真正WHOLE_SCHEMA约束三轮均成功解码并应用，每轮12项可见/私有行为测试及Ruff通过，
Pyright因新增内部辅助函数参数缺少类型注解失败。schema每轮仅1次模型请求：
初始验证、写后空白质量检查失败、受控格式化后递归复验耗尽三次验证预算，
模型没有得到最后类型错误再做修复的机会。全部实际chat请求21次，Reviewer零次，
完整链0/6，不放行产品，不给新题迁移信用，不推断语义或错误修复能力不够。

独立阶段结论是：约束解码解决了观察到的JSON转义失败，原始代码通道仍有封装协议失败；
验证调度又阻止了后续修复。下一唯一建议是单独登记“既有受控格式化先于计数写后验证”
候选，先离线证明实际执行/请求/时间预算不增加、错误可见、旧源码拒绝和保护边界不变，
再决定live资格。不得在已闭批候选中现场修补、扩预算或恢复holdout身份。
本批weekly used 2%→2%，当前停止线15%；停止因为形成固定对照的明确结论，而非usage耗尽。
完整交接见该批registration、逐格结果、metrics、preservation、decision与handoff。

当前额外决策审计：`capture-transfer-20261017-1/output-channel-decision-audit.json`。没有新模型调用或新协议实现；11项既有边界/合法转义控制通过，冻结源码pins无漂移。现有Host构造器明确拒绝structured_output=true，而Client的默认schema是通用动作，不是whole-function replacement；不能仅改配置或隐式绕过构造检查就声称仍为已合格协议。待用户确认独立Coder输出通道对照（原始完整函数文本 vs 真正约束的replacement schema），沿用原模型、六请求、合同/保护测试、所有安全校验与Reviewer；关闭的迁移批次不能重开。此处只补决策依据，不视为用户已批准，也不把目标改为局部离线通过。

> 先读 `r4-contract-first-20261017-1/decision.json`、逐格裁决、预算审计及 handoff.md。R3 PASS，R4 HOLD；固定已暴露诊断原16/16、真实4/4通过，仅取得下一阶段资格，不是迁移或产品放行。先 Get-Location，核对 Git/未提交改动、actual weekly used（上限50%，用户新指令优先）及原模型/单驻留。保持已冻结语义候选不变；先实现默认关闭的实际观测传输离线候选，优先利用既有 VALIDATE 的受信命令、canonical检查输出与输入epoch，拒绝伪造/截断/过期/错误argv或生产者/越界，不提供gold、不在验收后另跑可改变输入的执行。原事实表只认八个旧版本，不能静默放行未知源码。须有真实无模型canonical重放、安装/序列化及原20格输入无损控制，再冻结三道新题两次两臂的12单元完整链。两臂同一合格Reviewer；原Coder预算/模型/门槛不变。保留历史和改动，兄弟仓库只读，不commit/push，不改生产runtime/handoff，不补跑冲掉失败。预测是模型的未审查语义主张，不是事实或自动接受；旧None反例永不恢复holdout身份。达到usage停止线则不启动新工作。

以下为历史 R2 → R3 授权模板，R3 现已完成，不应重复执行：

> 我已审核 R2 结果，批准执行同一计划的 R3，包括版本化地区分 host validation 与 worker assessment；不允许伪造旧 contract_check 或绕过独立 Reviewer/Primary。只做一个默认关闭的候选，先离线反例、回归与安装预检，再固定同期对照。保持模型、合同、保护测试和预算；完成或失败后交接，不自动启动 R4。

迁移阶段另行指定 `R4`；受限编排阶段另行指定 `R5`。每次先读上阶段事实与当前 usage，而不是从聊天里的旧 PASS 或旧上限直接接跑。
