# Strata 通用核心：执行入口与当前证据

## 可选能力扩展执行中（2026-10-24）

用户最新授权希望进一步试用Strata能力，另按`strata-capability-expansion-plan.md`推进。
稳定C3和旧成绩不改。新实验0.2.1-capabilities.1默认关闭，复用原生循环/读取与账本，
只读入口不授予写入/执行；新增17项控制和完整144项回归通过，类型/lint通过，
0模型调用。首轮账本初始化遗漏的13fail/4pass原记录保留。固定调查4格已准备，
尚无该能力live资格；fresh review/Skills/Web仍待各自门槛。weekly26%/上限50%。
阶段记录`benchmarks/work/harness-convergence/strata-capabilities-stage-20261024-1/`。

## 单项日常试用已接受，测量修正已披露（2026-10-24）

冻结C3新增DeterministicModelClient.reset到完整项目副本，432tests通过/61数据库跳过、
全静态绿、显式项目配置下private5通过。11HTTP/3编辑与3写后检查/1协议恢复，宿主
8.20分钟，无Primary运行中提示或代写。生产逻辑首轮正确，后续修模型自写测试。
Primary仍有明显准备/验收成本：旧实验适配器重写task/config于live前修正；独立夹具
随机ID和外部pytest未加载async配置两种测量错误均保留原始记录，另登记修正，0Worker
重跑，同一补丁最终独立接受。不能把原4fail/1pass称模型失败或称原测量始终正确。
权威：`benchmarks/work/harness-convergence/strata-daily-reset-20261024-1/`
中的decision/metrics/handoff及primary-disposition。C3 runtime未改，旧资格不变；
省云成本未证明，后续应复用正式CLI和项目config减少实验编排。weekly25%/上限50%，
不commit/push，兄弟只读，未启用独立角色；固定单项试用结束。

## 完整项目受监督试用已完成（2026-10-24）

冻结C3 `0.2.0-observed-version.3` 在完整agent-runtime-kit隔离副本完成固定3项：
catalog筛选、非有限工具超时修复、实际同安装catalog→HTTP依赖链，3/3独立接受。
各格438/450/447 tests通过、61数据库测试原规则跳过，private分别2/4/2；全部静态通过。
新组合副本478tests通过、61跳过、private8通过；26HTTP/5有效编辑与5写后检查，
合计宿主21.01分钟。两次恢复为自写测试/静态修复，无运行中Primary语义指导或代写。
Primary仍承担合同/保护测试准备及完整终验，尚无云成本节省证明。准备期三次问题
保留为0模型调用的夹具/预期契约修订，不计Worker失败。C3/模型/预算不变，旧core
资格与失败均保留，不启用独立角色/生产默认、不commit/push。weekly最新实测25%/上限50%。
权威记录：`benchmarks/work/harness-convergence/strata-core-real-pilot-20261024-1/`
中的`decision.json`、`metrics.json`、`handoff.md`。固定试用已结束，没有执行中Worker。

## 最终有效状态：CORE_STABLE_SCOPED / release-ready（2026-10-24）

本阶段已完成，停止原因是核心目标达成，不是预算耗尽。weekly used最新23%，上限50%。
权威结论：`benchmarks/work/harness-convergence/strata-general-version-stage-20261024-1/decision.json`
与同目录`handoff.md`。下方“执行中”均是保留的历史进度，不代表仍有批次在运行。

C3 `0.2.0-observed-version.3`：离线115；已知pair2/2、兼容6/6、保留回归12/12、
错误起点4/4；已暴露组合诊断2/2；新合同迁移transfer2-2为6/6、三类各2/2，
两个真实同安装依赖链。分层分母不合并。新六格52HTTP/14编辑与配对检查、2协议恢复、
1上下文重建、合计宿主39.36分钟；0Primary运行中算法指导/代写，0已知错误最终接受。

最终ZIP：`benchmarks/work/harness-convergence/strata-general-core3-release-ready-20261024-1/strata-worker-core-0.2.0-observed-version.3.zip`，
SHA256`2e3eb7086e7d603c1a966df7cc96e48efb151141b1906e0d09b8b2efea4905ba`。
真实CLI/取消/状态/导出/脏文件保护通过；resume为离线安装host API控制；最终ZIP/
文档链接/例子/inventory/91文件安装/doctor通过。包无开发计划/实验历史。

只放行受监督、可信隔离Python项目、固定iq3_s安装的有界实现核心；Primary仍终验，
不代表任意任务/模型、生产默认启用或云成本已降低。S5/S6及独立E/R/Coordinator未启用。
旧F3/6/HOLD、旧修复0/2、全部准备失败与messages负控测量修正原记录均保留。
新messages两格原API删除负控触发collectionerror；原false不删，另登记API-body负控
修正（0Worker重跑，真实断言失败/0error），不是原始测量一直正确。无commit/push。

## 最新接续：组合诊断关闭，准备第二套新迁移（2026-10-24）

`strata-general-core3-mean-composition-20261024-2`按冻结门槛2/2独立接受，
`PASS_COMPOSED_REPAIR_DIAGNOSTIC2`；两次均自主采用Fraction精确累加，未收到算法提示。
第一格73tests、第二格64tests，均全static与12封存私有验收通过；18HTTP、5编辑、
2协议恢复、1111.110合计宿主秒。此为已暴露合同配合Primary预先补强保护测试的诊断，
不是新任务资格；旧F3/6/HOLD与旧修复0/2不改。无Reviewer、无最终错误接受。

当前C3产品/模型/预算/提示均未改变。下一批`strata-general-core3-transfer2-20261024-2`
离线控制通过、前三格已独立接受，第二组三格执行中，整批尚无结论：
messages-1为34完整tests+2private；fake-1为44+3private，同安装依赖成立；
reuse-1为43+4private，全static通过，0Primary运行中语义/代码帮助。
messages-1原负控删去新API导致导入error，测量无效；单独amendment修正为保留API/
失效函数体，0模型重跑，原false/errors1保留，修正负控真实断言检出且0error。
后续同类测量遵循同一规则，非事后删掉失败分母；详见batch/sensitivity-amendment.json。
transfer2-1因私有测试别名断言缺陷在0live时封存，6NOT_RUN不算模型失败。
仍>=5/6、每类>=1/2、6格全执行、0已知wrong-ready，至少两条真实同安装依赖链。
weekly最新实测23%/停止50%。产品流程离线已通过flow-3，但核心尚未release-ready。
后续若新记录更新，以其canonicaldecision及本入口新增说明为准；下方保留历史进度。

## 最新有效状态（2026-10-24；持续执行）

冻结候选`strata-general-version-c3-20261024-1/product`，0.2.0-observed-version.3，
92文件；完整离线115通过，固定已暴露pair2/2、兼容6/6、保留12/12已独立接受。
三批不混合分母、不复用旧版本模型成绩；保留矩阵98HTTP/27编辑/0协议恢复，
local/preservation/crossfile各4/4。旧C1的11/12/HOLD、旧语义漏检和C2未运行记录均保留。
已真实消除clear-2缺失获准create文件被误拒的阻塞；后续修复主要为自写测试/静态，
不能据此冒称自然生产语义自修已证明。当前`strata-general-core3-repair-20261024-1`
四个错误起点已冻结并通过good/bad与实际宿主起点核验；static-1已独立接受，44tests/
全static通过，重注入原错误19tests全fail且0error。9HTTP/3编辑；源NameError已修，
后续为补测试和修身份oracle，0Primary提示。async-1独立24tests/static全通过，
9HTTP/2编辑；补回await，原故障重注入9tests中4fail/0error。crossfile-1独立23tests/
static全通过，4HTTP/1编辑；仅补formatter白名单span_id，重注入8tests中5fail/0error。
四格均独立接受、0Primary运行中帮助；behavior-1独立24tests/staticgreen，3HTTP/
1编辑，7个补充测试重注入1fail/0error。E正式PASS_SEEDED_REPAIR_4，25HTTP/7编辑。
F新任务6格已冻结于`strata-general-core3-fresh-20261024-7`：filter/http依赖链各2
与均值保留修复2。前六次准备均0live/6NOT_RUN，因Primary夹具/私人参考错误封存，
详见stage/preparation-review及各decision，不计模型失败。第7次三类good全检查/
hidden通过、bad均检出；实际宿主filter/mean起点核对通过，适配器4与统计gate4项
控制分别通过。filter-1已独立接受：38tests+hidden，5HTTP/1编辑；补充重注入11中
10fail/0error。http-1原样失败：11HTTP/1编辑，52tests有1个OpenAPI保护失败+
自写测试类型错误；用满16取证后被budget安全拦住，未交接/未接受。
mean-1原32tests/static与7预封存hidden均绿，13HTTP/4编辑；Primary独立源码审查
确认新缩放算法将[1e308,-1e308,3e-308]均值1e-308退化为0，已拒绝，属wrong-ready/
覆盖缺口而非patch故障。反例仅在settled后运行，未反馈Worker/未改旧验收成绩。
F原6格已全部闭合：3/6独立接受，local2/2/crossfile1/2/preservation0/2，
`HOLD_FRESH_RELIABILITY`。http-2完整同安装依赖链已独立50tests+hidden通过，14HTTP/
2编辑/16取证/1协议恢复，自主修OpenAPI与自写类型；不据单次耗尽就扩大预算。
mean-2原28tests/static+7hidden全绿，但同一取消小量回归被独立复现并拒绝；
两个wrong-ready、0最终错误接受均保留。E/D资格不改，核心仍未release-ready。
stage/amendment4登记仅修可信检查覆盖的后续窄分支，无runtime/prompt/模型/预算变化。
`strata-general-core3-mean-recovery-20261024-1`已闭合0/2/HOLD，不替换旧6成绩。
wrong-1修复原8fail后仍有自写测试inf期望，用尽4编辑/4检查，14HTTP/880.218s；
封存15私有检查虽pass，额外已有合同组合反例证实overflow回退仍丢小量，故不是
只差第5次编辑。legacy-1独立49tests/static+15private全绿，但midpoint算法在
[1e308,-5e307,-5e307,1e-308]把原2.5e-309退化成0，拒绝；10HTTP/3编辑/786.531s。
均无Primary运行中提示，0最终错接受；确认数值语义/组合覆盖缺口，未发现import/patch故障。
stage/design-review-2与amendment5改为一次固定24字面IO组合检查，非追加prompt/预算。
第1次0live准备发现legacy最大值平均溢出分类错误已保留；第2次
`strata-general-core3-mean-composition-20261024-2`离线证明5个已知错误/legacy均红，
参考49全绿且私有12全绿，所有static全绿；两份实际宿主起点49exec6fail0error。
composition-1已独立接受：73fulltests/static+12private全绿，11HTTP/3编辑/1协议恢复/
731.516s；Worker自行选择Fraction精确累加，未获得参考算法/代码提示。原Source坏草稿
重注入24个自写测试中9fail/0error。composition-2同冻结输入执行中；一格成功不能
改写旧失败或称2/2。两格是本次复盘最后的例子型诊断，
之后按结果作设计结论，不继续无界加例子；不是新留出/发布资格。C3字节不变。
继续计划内开发，不启用生产；不是因写完阶段总结而停止。
产品ZIP离线流程1/2真实cancel成功但生成的dirty夹具被Ruff正确拒绝，均0HTTP保留。
`strata-general-core3-product-flow-20261024-3`已PASS：真实CLI定向cancel/status/
doctor/prepare/export、离线宿主API恢复不补预算、AM/未跟踪文件内容与Git状态保持。
产品流程0模型成功数；安装91runtime文件对应冻结92产品文件，包不含开发计划。
未release-ready、不启用生产默认，S5/S6未实施。
weekly实测22%/上限50%，无停止原因，继续计划内自主推进；单iq3_s原实例ready/
131072/parallel1，LMStudio0loaded，无commit/push。下方是接续历史，以上述摘要
及各批canonical registration/decision/disposition为准。

## 当前执行：版本引用阶段（2026-10-24）

C3新固定pair已2/2独立接受；C3原六格兼容也已6/6独立接受，28HTTP/7编辑/
1协议恢复（超120行读取后自主恢复）。tools-1原独立检查149pass/1超时fail保留，
唯一完整环境复验150pass/staticgreen且输入不变；并非模型重跑，见批次validation-
addendum。原生调用/源码/实际diff已审，未发现模型语义错放行。
同92文件C3的`strata-general-core3-retained-20261024-1`固定12格，第一轮六类已
6/6独立接受：20/24/22/52/21/37tests，均0协议恢复。恢复为补齐缺失测试、自写
测试假设或静态修复，生产实现均在首个有效提案后满足现有保护合同，无Primary
运行中指导。selection隔离资格仍为builder/result边界，不新宣称DTO构造复制。
clear-2也已独立接受，21tests/9HTTP/3编辑/0协议恢复：真实读取批准但尚未创建的
测试得到not_created/nullref后继续，完整自修/交接成功，旧C1故障live路径已消除，
旧失败不改写。upload-time-2也独立23tests通过，8HTTP/4编辑/4写后完整检查/
0协议恢复；先缺测试0执行、再夹具收集错误、再错误tuple断言，原预算内自主修复，
不是生产语义修复。tool-snapshots-2与finite-json-2均已独立接受（19/51tests），
当前11/12接受、local4/4/preservation4/4/crossfile3/4；span-flow-2已独立24tests通过，
upload-selection-2执行中，数量及分组已达标但仍需全部12格结算。E/F未准入，不是release-ready。
模型/预算/标准不变；weekly最新19%/上限50%。

当前有效：C1原12格已全部结算，11/12（local3/4,preservation4/4,crossfile4/4），
89真实HTTP，`HOLD_HOST_WORKFLOW`；clear-2为唯一未接受格，宿主误拒而非实现失败。
canonical `strata-general-version-retained-20261024-1/{metrics.json,decision.json,handoff.md}`。
新`0.2.0-observed-version.3`92文件/115完整离线控制通过，实际四读取重放通过，
类型/lint通过；`strata-general-core3-pair-20261024-1`已准入固定已暴露两格，
finite-json-1执行中，第二格未运行。尚无C3 live合格成绩，不复用C1成功。
后续仍是C2格/D6+12/E4/F6及产品流程，S5/S6不启用；weekly16%/上限50%。
下方“执行中”或“尚未live”均为接续历史，以上述最新段和canonical记录为准。

最新产品核对：在任何C2 live之前发现export只含patch/归档路径，且篡改当前检查
仍可导出；离线负控2fail/2pass已保留。按amendment-3补自包含前镜像、账本绑定
checks/JUnit、文件hash清单及导出前冲突预检，持现有项目锁、不运行模型/应用补丁。
0.2.0-observed-version.3已独立冻结为`strata-general-version-c3-20261024-1/product`，
92文件；8项导出控制纳入完整套件执行中，类型/lint通过。原C2两格0executed/
2NOT_RUN_SUPERSEDED，非模型失败；新`strata-general-core3-pair-20261024-1`两格
已准备，起点各25tests/6expectedfail/0error/staticgreen，尚未live准入。
旧C1保留11格已执行10接受，span-flow-2自主修测试/静态后20tests通过；末格
upload-selection-2执行中。C1仍HOLD已知missing-create读取故障，E/F未准入。
本轮离线控制曾与旧诊断格CPU重叠，不能把旧格耗时差当纯候选性能差；新候选
资格live前等待完整离线控制结束。weekly16%/50%，单iq3_s未切换。

最新接续：C1保留批10格已执行、9格独立接受，span-flow-2执行中、selection-2
未运行。finite-json-2为5HTTP/1编辑/0协议恢复，完整独立检查与补充变异控制通过，
源码仅allow_nan=False。clear-2宿主误拒历史保持，因此C1仍不能凭数字达标进入E/F。
单iq3_s原实例ready/131072/parallel1，LMStudio0loaded；weekly实测16%/上限50%。
首个未live的C2在目录冲突负控暴露：已存在目录被当作未创建文件，随后context
读目录PermissionError。负控原样保留；amendment-2登记了not target.exists()窄修，
另冻`strata-general-version-c2-20261024-2/product`，版本0.2.0-observed-version.2.1。
四次真实读取的无模型重放旧版第4次拒绝、新版明确not_created，均0编辑；新版
完整离线套件执行中、尚无live成绩。旧C2的105项控制和冻结字节保留，不冒充覆盖
新增目录反例。此为持续开发进展，不是release-ready或新的通用资格。

最新发现及分支：原候选保留矩阵8executed/7accepted，clear-2因读取精确获准但
尚未创建的`tests/task/test_clear_worker.py`被宿主误判越权，36.125s/2HTTP/0编辑。
原失败及source/action证据保留；无实际越权读写，也非模型实现能力结论。
`strata-general-version-stage-20261024-1/plan-amendment-1.json`登记普通修复分支：
原12格保持冻结继续安全诊断，当前候选整体HOLD_KNOWN_HOST_WORKFLOW_DEFECT。
下一候选`strata-general-version-c2-20261024-1/product`已冻结，版本
`0.2.0-observed-version.2`，仍92文件，只给已批准create缺失返回not_created；
不发源码/版本引用，范围/重复/检查限制保持。完整离线控制执行中，尚未live。
upload-time-2独立23tests通过；一次编造新test版本引用被拒、重读后自修，原事实现存。
旧候选tool-snapshots-2正在运行，其余3格尚未执行；weekly最新15%/上限50%。

D保留12格首轮六类均已独立接受，6/6已执行：finite-json54tests、span-flow20tests、
upload-selection39tests；selection源码两个文件/208行自写测试已全审，默认digest、
服务器ID、实际选择结果和manifest策略隔离通过。其一次超范围读取自主恢复。
第二轮clear-2正在运行，其余5格未运行；12格尚无最终decision，E/F仍未准入。
weekly最新15%/上限50%；候选/标准未变，所有旧成绩/失败保留。

D保留12格当前3/3已执行独立接受：clear21tests、upload-time24tests、
tool-snapshots23tests，补充测试分别6/7/8执行并检出5/4/6次变异失败，0变异收集错误。
UTC格自修timezone不可继承的测试夹具；snapshot格12次取证后一次完整编辑通过。
finite-json-1执行中，其余8格尚未运行；候选/合同/预算/检查保持冻结。最新weekly14%。
未来E实验辅助适配已补：按故障文件前镜像恢复，避免替代修法导致AST注入no-op；
只影响未来E，当前普通任务注入逻辑不变；E未准入、未注册/未live。

最新阶段：`strata-general-version-regression-20261024-1`已6/6独立接受，原三类
各2/2；31实际请求、6编辑、一次超120行读取后自主恢复，0引用错误。
同92文件`0.2.0-observed-version.1`继续D的六类保留任务12格，独立批
`strata-general-version-retained-20261024-1`准备中；明确已暴露，不冒称新迁移。
所有旧HOLD/失败保留。E4与F6仍未准入，weekly最新14%/上限50%。

固定已暴露两格现已2/2独立接受，`PASS_VERSION_REFERENCE_PAIR`。第二格46tests/
全静态过，补充测试21executed/9mutationfail/0error；6请求、2编辑、自主修UP012。
合计16真实请求、5编辑、0协议恢复；旧1/2和11/12不覆盖，不是新迁移资格。
现在自主进入D：已准备`strata-general-version-regression-20261024-1`原六格兼容，
同92文件候选与原预算；真实起点离线控制进行中，未派新六格。E/F尚未准入。

最新：完整冻结离线94项通过、lint/类型通过；固定两格
`strata-general-version-pair-20261024-1`第一格已独立接受，40tests/静态过，
Worker补充测试缺陷注入15executed/9fail/0error；10真实请求、3编辑、0协议恢复。
源码只加allow_nan=False；自主修正缺必需测试及自写测试假设，未发生生产语义修复。
第二格执行中，当前不是2/2资格，未启动D/E/F；weekly派工前实测13%。
以下冻结/准备段落是本阶段进程记录，以本段和逐格disposition为最新状态。

用户已批准按持续收敛计划自主执行，weekly上限50%；启动实测13%。根目录仍
codex/v2.1-dev，DEV仍strata-dev，原HEAD未变；92文件候选
`strata-general-version-c1-20261024-1/product`已冻结，版本`0.2.0-observed-version.1`。
阶段registration/preimages在`strata-general-version-stage-20261024-1`，原91文件
产品和DEV起点逐项一致后才修改。单iq3_s原实例ready/131072/parallel1，LMStudio
0loaded，无遗留Worker/锁。仅显式observed-v1配置启用新引用，不改生产默认。
13项版本边界/真实SDK假传输控制通过，含精确计数和强制压缩；首轮2项测试因
假定SDK工具顺序失败已保留，改为按名称核对后通过，不是Worker live成绩。
完整冻结离线控制正在执行；已知两格只做隔离准备，控制未全部通过不准live。
当前尚无新模型结果/资格；下方HOLD及历史成绩均保留。

## 下一轮计划已更新（2026-10-24；尚未执行）

用户要求补齐失败后的自主推进与复盘分支，新增
[持续收敛执行计划](strata-general-stable-convergence-plan.md)。后续按新计划接续现有
DEV，优先验证宿主管理版本引用；候选HOLD与开发停止分别处理，原正确性门槛保持。
本次仅文档变更，未调用Worker、未修改runtime或历史结果。当前没有新的合格候选。
weekly实测12%，用户上限50%；没有创建新运行goal或启动live。以下最新终态仍有效。

## 最新终态（2026-10-24）

当前窄阶段已关闭：**HOLD_CORE_BOUNDED_REVISION_LIMIT，未release-ready**。
canonical终态：`strata-general-token-preflight-20261023-1/{decision.json,handoff.md}`。
同一冻结runtime：旧6/6；新题11/12（分组4/4、3/4、4/4），数量过门槛，但
finite-json-1绿色检查漏检由Primary拒绝，旧HOLD不覆盖。
自动推进后单独补可信兼容检查，错误草稿被拦、正确草稿/参考通过；固定已暴露
2格回归仅1/2，通过格60tests/静态全部过，失败格0编辑，因三次把64位hash
写成相同58位值，耗尽2次协议恢复。原SSE确认非解析器截短；详情
`strata-general-coverage-20261024-1/{decision.json,handoff.md}`及失败格diagnostic。
这不证明模型不会实现功能，也不意味着可以去掉版本绑定。下一协议目标应是
宿主拥有的观察版本引用，保持完整hash/task/path/current-version校验；本轮未实现。
达到一次窄修订的固定HOLD停止条件，不继续追加credits/提示或第三次尝试。
seeded repair4、S4均未准入；S5/S6未实施；生产默认关闭，无执行中批次/写锁。
weekly最终12%/上限50%，不是usage耗尽。91产品文件与兄弟62+57冻结文件hash
无漂移；同iq3_s单驻留，LMStudio0loaded；不commit/push，历史及原改动保留。
下方执行中描述均属接续历史，以本段及canonical终态为准。

## 当前接续：可核验 token 预检（2026-10-23）

2026-10-24更新：上述候选固定新题12格全部结束，11/12独立接受，分组4/4、
3/4、4/4；90真实HTTP、25有效编辑、93纯计数、3有界压缩、1协议恢复、0no-op，
宿主窗口4562.296秒。旧6/6单列。不因数量达标覆盖finite-json-1语义漏检，
该批decision为HOLD_SEMANTIC_COVERAGE，完整handoff已落盘。
按自动推进权限仅补该既有合同的可信兼容测试：新独立批
`strata-general-coverage-20261024-1`，同91文件runtime/模型/预算，仅增加一个只读
保护测试；2格为已暴露回归，不是新迁移、不改旧11/12。
真实错误草稿2fail/23pass、正确草稿与合规参考各25pass，静态均绿；两个真实宿主
起点各25executed/6expectedfail/0error，0模型。Primary已审查并准入窄回归。
该测试包仅覆盖已知缺口，不证明未知边界检出。修复4/S4仍未准入，S5/S6未实施。
weekly实测11%/上限50%；旧下文执行中描述已被本段和canonical decision取代。

用户指示自动推进，另登记`strata-general-token-preflight-20261023-1`，上轮结果
保持不变。weekly实测8%，上限50%；同iq3_s单实例，未load/reload。
不改网关/安装/凭据，改用只读的已安装Strata纯模板/tokenizer；36份上轮真实
请求与provider input_tokens逐项精确相等（开发区`token-counter-calibration-2`）。
计数过程不运行Service构造/引擎，无HTTP/权重读取；解释器、模板、词表和编码
源码hash固定，隔离子进程带Python审计禁止写入、网络、子进程。这不是OS沙箱。
候选默认关闭，只有显式可信config开启；固定请求hash与单次计数回执，provider
返回实测值不一致则在工具动作前停止。65536上下文/4096框架/12288输出、原
推理/编辑/检查/时间预算与2次有进展约束压缩均不变。额外纯计数每任务≤18次、
每次≤15秒且计入原1800秒；不算模型成功或免费隐藏的模型调用。
完整77项离线通过；lint/类型通过，0真实模型调用。91文件候选
`strata-general-token-c1-20261023-1/product`已冻结，版本`0.2.0-token-preflight.1`。
固定六格`strata-general-token-regression-20261023-1`已完成并6/6独立接受；
31真实请求、6有效编辑、0压缩、0计数差异，工具收集两格均自主显式交接。
旧4/6不覆盖；首次派工前及当前weekly9%。现在按原门槛准备新6题×2，先核对
真实宿主初始检查，再live。新题pytest临时目录固定为项目.agent/host-test-temp，
避免已知系统Temp权限问题；不改测试选择、正确性、lint或预算。
仍不启动S5/S6，候选不默认启用，S4未准入。

新题批`strata-general-token-new-20261023-1`已注册12格；六种起点在
`.checks/token-new-initial-controls-1`实际宿主验证，需求性失败已由Primary逐项
核对，原始检查与参考可行性保留，0模型。当前首轮clear/upload-time/tool-snapshots
三格均已独立接受，Worker新增测试均通过独立缺陷敏感性验证；upload-time保留
一次自写测试假设错误→自主修正。正在按固定顺序推进，批次尚无最终结论。
最新weekly10%，上限50%，同实例驻留，无Primary临场修法或代写。

finite-json-1已结束ready，但Primary拒绝：35tests/静态检查通过，新增Mapping递归
却破坏原default=str兼容。只读probe证实可由旧版编码的不透明UserDict自引用在
新实现触发RecursionError，无非有限数。见该格primary-semantic-probe/disposition。
这是模型语义过度泛化与覆盖缺口，不是token计数或patch应用错误；未错误接受，
不修源、不泄漏probe、不改合同，继续固定剩余配对。当前4executed/3accepted，
批次尚无最终结论；后续live仍同候选同预算，不把这格抹成成功。
首轮六格已全部完成：5accepted/6executed；span-flow-1和upload-selection-1
独立通过。selection保持默认hash与服务器派生identity，16条补充测试经原builder
缺陷注入8fail/0error。两格均有自写测试错误后修正，不冒称生产语义修复。
finite-json-1另以无循环SectionProxy证实default=str退化，原失败不覆盖。
第二轮clear/upload-time/tool-snapshots/finite-json已独立接受，当前10executed/
9accepted；span-flow-2执行中，upload-selection-2尚未运行。finite-json-2在未收到
首轮提示下保留原生JSON容器范围，35tests/静态通过；只读兼容probe5/5通过，
同probe在首轮3/5失配。不能把同题后成功冲掉首轮漏检。模型/候选/门槛不变。
weekly实测11%，上限50%；finite-json-2 CLI沿用10的记录另有真实读数addendum。
汇总工具补齐计划既有语义规则：数量门槛与绿色检查漏检分开，2项离线控制通过，
不改变Worker输入或runtime。批次尚无最终结论。
下方是已关闭的上下文策略阶段，不是当前执行状态。

## 2026-10-23 接续：独立上下文策略窄阶段

用户在上轮HOLD交接后指示继续，已另立
`strata-general-context-policy-20261023-1/registration.json`，不是改写旧阶段。
weekly used实测7%，停止线50%，同iq3_s实例131072/parallel1，未reload。
Strata引擎源码有精确count接口，但已批准桌面网关实测404；不绕网关/读密钥/
修改安装，不做token比例猜测。候选只增加一次有进展约束的确定性重建：每任务
最多2次，第二次必须有首次之后的宿主有效编辑；原字节界限、模型/输出/请求/
编辑/检查/时限、权限与显式submit均不变，配额跨attempt不重置。
63项完整离线控制通过，lint/格式/类型通过；冻结`0.2.0-context.1`（89文件），
`strata-general-context-regression-20261023-1`六格全部完成：仍4/6独立接受、HOLD。
raw/hash各2次接受；tools两次有效编辑/绿色检查后继续调查，第二次压缩已让模型
读到绿色与submission_available，但后续第三次重建被拒，仍未submit。两份草稿
另做完整150tests/静态/目标外AST诊断均过，不追认成功。hash-2有1次真实lint失败
后自行修复。总36真实HTTP、7有效编辑、818.875秒宿主窗口；无Primary提示/代写。
完整结论在`strata-general-context-policy-20261023-1/{decision.json,handoff.md}`。
首次派工前实测weekly8%；raw-1 CLI仍传前值7，保留原记录并在阶段pins文件纠正。
本阶段1个候选和1批原六格回归已关闭；达到固定HOLD停止条件，非usage耗尽。
结束weekly8%、上限50%，无执行中Worker；保持同实例驻留，LMStudio0loaded。
未达到6/6，原S3新题/修复及S4不派工；S5/S6未实施。不再自行加第三/第四次
压缩。下一步须先解决可核验token预检接口/有依据的策略设计，而非继续堆重建。
下方全部是先前已关闭阶段的历史与接续说明，不能当本轮实时状态。

2026-10-23，已到计划规定的修订停止条件；weekly used7%，上限50%，不是usage耗尽。
最终结论 **HOLD，未release-ready**。完整交接：
`benchmarks/work/harness-convergence/strata-general-core-decision-20261023-1/handoff.md`。
本阶段无执行中批次；不再新增live或第四候选，须下一阶段授权后才继续。
兄弟仓库/Strata安装只读，iq3_s同实例单驻留，不commit/push，不实施S5/S6。

唯一开发源码位于：
`benchmarks/work/strata-general-dev/repository/runtime/.local-agents/`，本地分支
`strata-dev`，从发布提交`0f7fe1c08df0d38db8f7b57426582088ab0322cc`克隆。
原工作区仍在`codex/v2.1-dev`，未切换、未暂存其已有改动。

## 已完成

- S0：`strata-general-s0-20261023-2`逐字节核对84个发布包文件、冻结源映射。
  -1保存额外发布说明CRLF的离线准备故障，非Worker失败。
- S1/S2：新任务命名空间、不可补额度账本、精确块变更集/创建、宿主自动完整检查、
  显式submit、补充测试必须实际执行、取消/恢复、当前输入/JUnit/解释器/运行时
  绑定、源导入优先隔离副本、额外检查输入不授予Worker读取权限。
- `.checks/s2-final-build-tests-1`50项离线控制通过；0真实模型调用。
  各历史检查重叠，不与live分母相加。新模块lint通过、类型0错误；共享内核旧lint
  基线11/current10/introduced0，不清理无关旧代码。测试/准备器自身失败均留在`.checks`。

上述批次简称均位于`benchmarks/work/harness-convergence/`；`.checks`位于隔离
开发仓库。原生AgentLoop/工具/本地Messages仍复用已安装harness0.2.1-alpha.3。
共享编辑器/验证器/归档仍被复用，新适配不包含第二套pytest或编辑解释器。

## 冻结候选与当前实验

- 首个正式live候选：`strata-general-c1-20261023-3/product`，
  `0.2.0-candidate.1.2`，87个产品文件；不要修改其字节或已准备格。
- 首批6格旧回归：`strata-general-regression-20261023-3`，已封存1/6接受、HOLD。
- `raw-1`：已结束budget_exhausted；1有效编辑、1写后检查全部通过，但模型未submit，
  继续读到16取证上限。10模型请求/18工具动作，约350.6秒；不能算接受。
  实际diff仅增加UTF8解码及AdapterError映射；尚未独立完整验收该失败格。
- `tools-1`：budget_exhausted，0编辑；`hash-1`：budget_exhausted，2编辑；
  `raw-2`：budget_exhausted，0编辑；`tools-2`：重复无证据停止，0编辑。
  `hash-2`在一次lint修复后ready，独立154tests/静态检查通过，Primary已接受。
  它的首次独立pytest临时目录故障保留，0额外Worker请求的环境复验另存。
  其余5格不追认成功；`metrics/decision/handoff`已生成。
- `raw-1`与`hash-1`额外诊断：完整tests分别153/154通过，静态检查与目标外AST不变
  均通过（实际数量以各pytest.json为准）；仍不追认原运行成功。首次独立诊断的
  系统pytest临时目录权限故障也保留；改用独立`.agent`临时目录后完整检查通过。

两批前置注册不改写：
- `strata-general-regression-20261023-1`：0executed/6NOT_RUN。离线真实raw上下文
  任务56037bytes、反馈60179bytes，保守重建132623bytes超过客户端界限；是宿主
  元数据重复/上限匹配问题，没有真实provider超context证据，不是模型能力失败。
- `...-2`：0executed/6NOT_RUN，最终wire控制前被取代。精简后任务6572bytes、
  反馈22001bytes、重建含输出/框架余量44980bytes（未加工具schema）；13项相关
  控制与2项wire/no-op控制通过。形状错误可修复，越权仍停；原样重复提案停。

首个live候选重建后每个请求丢弃最近对话，未投影累计diff和交接eligibility；
与计划3.5存在差距。两个正确草稿未交接支持工作流缺陷，但不是唯一根因证明。

第一轮修订初稿`strata-general-c2-20261023-1/product`已冻结，版本candidate.2，88文件。
仅修当前工作状态/观测行覆盖/增量反馈/保留最近闭合工具回合，不换模型、预算、
权限、编辑器、检查或显式submit。`c2-frozen-tests-1`52项完整离线控制通过，
真实SDK假HTTP传输控制包含在内，0实际模型调用。期间Primary格式化共享内核触发
一次runtime漂移拒绝（c2-final-tests-2:1failed/51passed），原结果保留；冻结后控制
通过。不在离线检查期间再改源码。该初稿6格`strata-general-regression-c2-20261023-1`
补齐计划S1的Primary一次退回接口前封存为0executed/6NOT_RUN，无模型失败。

第二个正式live候选`strata-general-c2-20261023-2/product`，candidate.2.1，89文件。
新增退回必须绑定当前check/source引用与原合同ID，原budget不补；无有效修复不能
靠旧绿色再次submit，assisted明确标记。本批不使用Primary退回，仍测自主完成。
完整离线`c2-return-frozen-tests-1`58项通过；新模块lint/类型通过。
固定6格`strata-general-regression-c2-20261023-2`：raw-1已接受（块失配后自行收窄，
13请求/1编辑/153tests）；tools-1失败（16取证/0编辑）；hash-1已接受（11请求/
2编辑/154tests）；raw-2已接受（4请求/153tests）；tools-2失败（重复无证据/0编辑）；
hash-2已接受（3请求/154tests）。批次4/6接受、HOLD，52个实际HTTP，5有效编辑，
至少1次失败写后检查→有效修复→完整通过；无Primary修法/退回。新题不派工。

该批又确认压缩后的后续请求仍反复投影“快照+最近一回合”，并在有回合时删去
近期原文证据，不能持续积累新对话。tools-1重复读同样测试/重叠源码窗口，关联
受支持但不声称唯一根因。`interim-analysis.json`有证据与解释。

开发区已完成最后允许修订，`strata-general-c3-20261023-2/product`
candidate.3.1已冻结。保留C2工作状态/预算/工具/验收，改为一次wire锚点重建后持续
追加所有新原生回合；前缀漂移或再次超界失败关闭。当前版本源码证据优先保留，
不被空搜索挤出；无模型记忆授权。61项完整离线控制通过，真实SDK+假SSE证明
强制压缩/续写与超界直接停止（不误当传输错误重启）。真实父批payload离线重放
三类首次重建均在原界限内，后续过长轨迹安全停止，非新增模型成绩。
初稿`c3-...-1`6格0executed/6NOT_RUN封存，在live前补齐超界分类，未消耗模型。
最终live批`strata-general-regression-c3-20261023-2`已完成全部6格：raw/hash各2次接受，
tools两次均完成编辑与完整写后检查，但在下一模型请求前触发
`Post-rebuild context bound exhausted`。两份草稿另做完整150tests/静态检查通过，
不追认原格成功。正式4/6、HOLD；27请求/6有效编辑，宿主窗口666.218秒。
最后已发送的tools-1请求实测输入10878tokens；被拦下一请求实际token未知，
不能把字节上界等同真实模型上下文溢出。详见两格诊断与最终decision。
这是第二且最后允许的post-live修订，现按计划停止；不扩预算、不降门槛、不再开
第四次修订。S3新12/修复4与S4未运行；S5/S6未授权。三个候选的成绩不合并。

## 接续方式

当前首先读取上述最终handoff/decision；旧命令只是诊断/接续接口说明，不是继续
派工授权。下一阶段需决定token预检/压缩策略，再另行注册，原历史和6/6门槛不变。

开发工具`tools/matrix.py`每格只能执行一次；run需当前实际weekly读数。
它会归档process/result、宿主canonical记录、独立全tests/静态检查（仅ready时），
并输出实际diff。`primary_accept`初始是null，需Primary看实际diff后另存不可变
disposition；不得把checks通过当独立接受。失败格也可独立诊断，但不能追认成功。

响应是SSE原文，不可将native-model-response.body直接当一个JSON解析。
实际HTTP计数在任务general/ledger最后记录的state.native_http_requests中；
model_requests是预约数，离线替身也会占，不能混作真实模型调用。

后续新6题在隔离开发仓库`tools/task_contracts.py`，已完成离线准备，尚未注册/live：
clear_correlation、upload时间UTC、ToolRegistry快照防别名、canonical_json有限数、
span_id日志跨文件、upload selection DTO→builder。准备前须验证原检查与合规参考，
`.checks/real-task-preparation-6/decision.json`六题的原切片和合规参考全检查通过；
早期准备器路径/测试数据/格式与导入错误留在-preparation-1至-5，不算Worker失败。
参考和隐藏验收放在Worker根外。按计划2次/题；旧题保持已暴露，S4留出尚未准备。
四个错误起点也完成离线故障观测（`.checks/repair-task-preparation-1`），0模型；
静态/异步/跨文件/行为错误不混作自然模型自恢复成绩，前置live门槛未通过不得派工。

禁止把本文件的执行中状态当最终decision；最新不可变registration/结果优先。
