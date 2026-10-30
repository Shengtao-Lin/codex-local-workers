# Strata 实际任务稳定性：当前执行入口

文档导航更新（2026-10-28）：[架构](strata-architecture.md)明确当前与拟议能力，
[下一阶段](strata-supervised-next-step.md)聚焦正式入口真实任务和Primary重复成本。
下列各段按时间保留快照，“执行中/待批准”只对应当时记录；实际状态查对应decision。

## 最新结论与历史快照

> 最新闭合（2026-10-29）：真实异步输出mapper原任务HOLD0/1，一次另登记的
> Primary-assisted窄修复也HOLD0/1。task.22未改，两次Coder各11请求、分别2/1实改，
> 共22provider/819.375任务活动秒；均Reviewer NOT_RUN。两份产物独立诊断都是
> 47passed/6failed，合法generator awaitable缺陷仍在；辅助产物工程3failed444passed、
> 64deselected，Ruff/Pyright也未通过。原证据池/新协议池分别停止，不借预留或第三次
> 调用。16项零模型表示控制通过，但无损归一化的resolver仍等同失败代码，最后
> 冲突重叠必须拒绝，故不据此新增runtime候选或扩预算。保护/私有输入、product/DEV
> 117文件与runtime-kit来源源码无漂移；单iq3_s。最新指标为辅助批metrics-v2，保留
> 初版token双计量及修正说明。两批handoff/decision齐全，当前无活动批次；原工具/
> Hook窄资格2/2保持，异步新族/通用/Coordinator未准入。weekly登记32%、收尾16%/50%，
> 变化原因unknown，未兑换reset，见closure-observation.json；无commit/push。
> 详见[辅助修复交接](../benchmarks/work/harness-convergence/strata-practical-async-output-repair-20261029-1/handoff.md)。

> 最新闭合（2026-10-29）：`strata-qualified-transfer-20261029-1`为
> PASS_NARROW_SUPERVISED_TRANSFER_2_OF_2。task.22/模型/提示/预算/Reviewer不变，
> 同版本539控制经117文件绑定复用。两题的正负双向私有控制先通过、共同冻结，
> 原私有验收/合同/保护输入未改。工具筛选8Coder+8Reviewer、1改、独立438passed
> （431项目+7私有）；Hook 7+7、3改、独立439（433+6），各61integration未运行。
> Hook首轮源码绿后仍能补测试、遇到两断言/两静态错误并自行修复，一次自动当前
> 源码反馈92行4589JSON字节；没有Primary live修法、代写或封存返工。全批30provider/
> 100上限，719.593任务活动秒，净云省/Primary主动时间unknown。Reviewer有20个
> 显示测试ID与21个JUnit项的疑问，已由canonicalJUnit确认第21项实际执行，无补跑；
> Primary完整读372行自编测试。当前无活动批次；文档推荐窄受监督入口更新task.22，
> 通用、调查、Coordinator及生产资格不变，旧HOLD/Reviewer漏检保留。终验发现
> evaluation-harness工作区变化，actor unknown，未回滚/写入；本批runtime-kit来源和
> 两格冻结输入不变，动作路径与依赖核对无关联，另存sibling-drift-observation。
> 未commit/push；weekly最新30%/50%，具体见handoff。

> 当前执行（2026-10-29）：`strata-qualified-transfer-20261029-1`共同冻结工具定义筛选、
> Hook identity移除/运行快照两题。task.22/模型/显式额度/Reviewer/门槛不变，绑定
> 相同539项控制直接复用。每题原始及隔离正控均通过完整4项工程检查（420项目/
> 61integration排除）；私有正控7/7及6/6，负控4failed3passed及6failed。48条断言
> 正确数据路径实际执行；正控实现和私有验收不在Worker范围。准备脚本一次语法
> 错误保留、修正前未推理。selection执行中，removal尚未运行；无新放行结论。
> 每格50provider、全批100，weekly29%/停止50%。旧批HOLD不改，不commit/push。

> 当前执行（2026-10-28）：跨源码`strata-formal-retry-wrapper-20261028-1`已闭合HOLD0/1。
> Coder11请求/1改/16证据；源码类型错误、自编测试缺导入及错误调用次数仍在，完整
> 3failed437passed，Reviewer NOT_RUN；12私有行为诊断通过不计接受。5请求/3改/3检查
> 尚存，但再次读当前测试行被证据池拦住。task.21既有新任务1/1和旧HookHOLD保持。
> 新独立限定阶段`strata-postwrite-feedback-20261028-1`冻结task.22：失败写后自动展示
> 真实错误对应的当前获准修改文件片段，最多16K字节、每文件120行；显式读/搜额度
> 不变，自动展示量单列。12新控制通过；首版1控制夹具cleanup失败+43通过保留，
> 修正后12新控制通过。真实旧坏写入0模型回放字节一致，显示127行/4631字节，检查
> 仍失败，没有替模型修代码。完整同版本539passed，12新控制是其中子集；两格共同
> 冻结后执行。包装器已独立接受1/1：Coder14请求/4改/14显式证据，三次失败后自主
> 修复，Reviewer7请求合法PASS；独立457passed=445项目+12私有。自动展示两批186行/
> 8899JSON字节另计，未使用封存返工、Primary修法或代写。第二格reset已完成13Coder/
> 5Reviewer、3实改/14证据、合法PASS；Primary冻结私有夹具3用例误比较新随机UUID，
> 原件与3failed429passed保留。机械纠正、同产物独立432passed（428项目+4私有），
> 纠正后原始源码4负控失败，未增加模型调用。原登记HOLD=1接受+1夹具无效；不是
> Worker失败、Reviewer误放或原门槛2/2PASS。两题恢复路径确实触发且实现完成，
> 全批39provider/1018.578任务秒，无Primary实现/语义指导；不报净节省或通用资格。
> 无活动Worker，下一步先补正/负双向夹具控制，候选保持。weekly28%/停止50%。
> 初版43passed包括33旧+
> 10新控制，不是43个独立旧控制；计数更正见批次final-source-review.json，旧记录保留。

> 当前执行（2026-10-28）：task.21的`strata-review-context-projection-20261028-1`
> 完整527离线控制和新模型耗尽任务1/1独立接受435项。Coder13请求/3实改/13证据，
> 自主修静态/测试错误；Reviewer6请求/9证据/1协议恢复后合法PASS，无上下文重建。
> 19provider、任务456.094秒；Primary仍准备合同/5关键验收并完整审查，净省unknown。
> 同旧初始输入29435→8264token的纯计数证明冗余下降，不证明旧Hook必恢复；旧HOLD
> 与所有Reviewer漏检保持。下一格`strata-formal-retry-wrapper-20261028-1`用相同候选，
> 新建包装器+公开导出，12项负控和工程基线/prepare通过，正式CLI执行中，尚无结论。
> 无新runtime修订，weekly27%/停止50%，兄弟/Strata安装只读，不commit/push。

> 当前执行（2026-10-28）：正式CLI真实Hook任务`strata-formal-project-unit-20261028-1`
> 已闭合HOLD0/1。Coder12请求/2实改/16证据，第二次完整检查绿、432工程测试；无
> Primary live提示/代写。Reviewer9请求/12证据/2协议恢复，拟PASS先缺实现文件证据、
> 再引用空白行，两次正确拒绝；第2次上下文重建被“无新编辑”规则停止，剩1请求/
> 约670秒，报告未接受。独立437passed/61integration排除只作实现诊断，不算完整链。
> 21真实调用、任务566.468秒；原代码/模型/候选不变，旧HOLD不覆盖。下一窄候选
> task.21仅改general_projection及生成安装清单，不改预算/报告/重建门槛；已有实际
> 同输入纯token计数29435→8264，完整527项回归通过（含16相关控制），冻结源码绑定
> 一致。新批次`strata-review-context-projection-20261028-1`已登记1个不同的模型客户端
> strict exhaustion任务，复用正式入口和工程检查，正在live，尚无结论。weekly最新
> 26%/停止50%，勿重复派发。原Hook失败不补抽、不改分；详细见各批次registration。

> 最新闭合（2026-10-28）：`strata-full-task-return-20261028-1`为PASS_NARROW_FULL_
> TASK_PRIMARY_RETURN_2_OF_2。task.20默认关闭，初始完整16/4+一次封存14/4，总30/8；
> 所有旧profile/任务保持。完整520passed、4模块实际diff与冻结源码核对通过，
> 受控Primary返工1/1（9Coder+7Reviewer、2实改、8证据、独立429）及新注册器删除
> 行为1/1（8Coder+5Reviewer、2实改、独立429）接受；均有自编测试错误自主修复，
> 无额外Primary修法/代写。脚本首轮3请求/1修改及假审查provider0不计模型成绩。
> 实际29provider/74，任务594.546秒，不含离线/准备/Primary；净云省unknown。
> 首格实际超过旧8请求/6证据返工预留，但只证明此已暴露辅助路径；新格交付后
> 返工NOT_TRIGGERED。旧A0/1、B1/1、HOLD/Reviewer误放不覆盖，完整general/能力
> 门槛未取得。本用户轮另有A/B20真实调用，总49不合并成放行率。weekly5%/50%，
> 无活动批次，无commit/push，兄弟/Strata安装只读，根tracked改动保持。详细
> registration/decision/metrics/handoff/core-review/integrity齐全。窄试用操作说明见
> `docs/strata-supervised-usage.md`，下一步使用正式入口做中等真实单元并测重复成本。

> 当前开发（2026-10-28）：`strata-full-task-return-20261028-1`已冻结task.20，默认
> 关闭task-rework-v1。初始完整16/4保留，基于实测返工12请求/3修改/11证据/17工具
> 预留14请求/4修改/14证据/24工具，整任务30/8；只允许一次经Primary核实的原合同
> 返工，或原有canonicalReviewer处置路径。78项针对控制+4计数控制通过，完整
> 同版本回归执行中，尚未live、未取得资格。新profile初版15失败/55通过因持久
> 账本未认版本被拒，原记录保留，修正后新目录验证。旧16/4、task-v1、24/6和
> 旧任务不能升级；生产默认/模型/权限不变。准备两个固定格：受控Primary返工
> 兼容、新AgentRegistry.unregister行为；须完整回归通过后登记启动。task.19的
> 可用证据、A0/1和B1/1及旧HOLD均保持；weekly最近4%/停止50%。

> 最新闭合（2026-10-28）：快照A为HOLD_STAGE_EVIDENCE_EXHAUSTED_0_OF_1；匹配
> 原始输入的普通B`strata-supervised-model-ordinary-20261028-1`为PASS_EXPOSED_
> MATCHED_INPUT_ORDINARY_PROFILE_1_OF_1。B7Coder+5Reviewer、1修改、独立433passed/
> 61integrationdeselected，完整源码/自写9测试/diff及当前绑定通过Primary核对。
> B仅8证据，未超过A阶段上限，不能把B成功归因为预算放开；A8请求/1修改、错误
> 自编测试/静态检查及stage10证据停止均保留，Reviewer NOT_RUN，诊断5通过不计接受。
> 两批20真实调用、任务610.906秒，不含准备/独立验收/Primary；准备时钟不匹配，
> 不报成本节省。task.19未改，weekly4%/50%，无活动批次；旧HOLD/门槛保持。今后
> 普通使用保留现有16/4自修空间，特殊task-v1不作为全部任务默认。直接入口和边界见
> `docs/strata-supervised-usage.md`；避免逐题新造驱动，下一预算profile须单独登记。

> 当前执行（2026-10-28）：快照A格`strata-supervised-model-snapshot-20261028-1`
> 已闭合HOLD0/1：8请求/1修改，Worker自编测试的执行时刻错误及静态错误未修完，
> 首阶段10证据耗尽；Reviewer NOT_RUN。停止后原封存5项回归诊断通过不计接受。
> 实际read1..130同时不合120行窗口，不能把所有失败只归预算。零模型账本重放
> 明确stage10 vs total16区别，保持原失败。新B格`strata-supervised-model-ordinary-
> 20261028-1`已匹配所有起点源码/测试字节与原目标，仅删task-v1阶段切分、身份
> 不同；普通16/4，最多26新provider，未提供A草稿/失败/补丁/隐藏验收。B执行中，
> 尚无结论；预先analysis-rules区分是否真正跨越A阶段额度。候选/模型/权限/检查
> 不变；B控制器0模型时的unusedimport lint失误有独立v2/修订记录，原登记不改。

> 当前执行（2026-10-28）：`strata-supervised-model-snapshot-20261028-1`，task.19不变，
> 正常正式入口修复真实DeterministicModelClient脚本/输入记录的别名污染。复用原
> 完整严格检查，仅补4个独立别名回归和1个已有流式生命周期兼容检查；未写参考
> 实现、未改runtime，批次适配/验收仍有Primary准备成本。起点完整420passed，
> 独立4failed/1passed确实复现问题，安装/doctor/prepare通过。task-v1总16/4、
> 首阶段10/3，一次条件续作用实际余额；至多36新provider，一次fresh审查不能
> 在相同代码上抽到PASS。当前live执行中，尚无结论；weekly3%/50%，历史保持。

> 最新闭合（2026-10-28）：`strata-primary-return-path-20261028-1`为
> PASS_NARROW_PRIMARY_RETURN_AND_NEW_TASK。已暴露受辅助同任务返工1/1接受（12Coder+
> 7Reviewer，3实际修改，独立428passed）；新原子register_many行为1/1正常接受
> （7Coder+6Reviewer，1修改，独立431passed），各61integration排除，重叠测试不相加。
> 控制前缀3请求/1修改及脚本审查provider为0，保留占用账本；不计模型成绩或误放。
> 首格源码首个有效写全绿，后加自写测试失败再自主修复，步骤勘误独立留档；次格
> 恢复未触发，不造缺陷续作。实际32provider/59，任务747.469秒，Primary主动时间/
> 云token/净节省unknown。task.19及生产默认不变，旧HOLD/真误放保持；真实Reviewer
> 的Any/JSON约束误述亦保留，未作为接受依据。weekly3%/50%，无活动批次，无commit/
> push，原tracked改动/兄弟源码/候选完整性均核对。详细decision/metrics/handoff齐全。
> 下一步沿已有入口做窄范围受监督使用并记录重复准备负担，当前没有新runtime修订
> 依据；完整调查/通用及其他能力门槛未补齐。下面保留本批执行时快照。

> 当前执行（2026-10-28）：`strata-primary-return-path-20261028-1`已冻结task.19与两格：
> 输出隔离的0provider浅拷贝控制首轮→Primary事实反馈→live同任务返工；新原子
> register_many正常任务→仅在真实缺陷时一次续作。零模型27项相关控制通过，
> 正向组合另以正式observed-lines/observed-line配置复核通过（与27重叠，不相加）。
> 两参考静态/完整独立423/425passed，原始起点负控均拒绝；安装/doctor/prepare通过。
> 脚本3请求/1编辑和假审查不计真实provider或模型误放；总16/4不重置，最多59新
> provider。当前首格live执行中，次格未运行，尚无新结论。weekly2%/50%；候选/
> 模型/权限/默认不变，不commit/push，历史成绩保持。详细下一步见
> `docs/strata-supervised-next-step.md`修订，准备时临时目录/参考排版错误均保留。

> 最新闭合（2026-10-28）：`strata-humaneval-normal-20261028-2`为
> PASS_PUBLIC_BENCHMARK_COMPATIBILITY_3_OF_3。HumanEval1/18/39固定一次完整链
> 各接受，独立429/428/426passed（各61integration排除，含重叠419项目回归，不相加）。
> Worker自写8/7/6测试，Coder请求4/3/3、Reviewer4/4/3；总21provider/78，任务529.234秒。
> 无live提示/代写；he39数论阈值误述经原论文+0模型勘误，原报告保持；大整数保证/
> 训练污染unknown，不能通用放行。全部decision/metrics/handoff齐全，无活动live。
> 连同输出隔离2/2，本次53provider、任务窗口1361.922秒，Primary准备/审查/净节省
> unknown。候选不变、旧HOLD/误放保留；weekly1%/50%。下一步见
> `docs/strata-supervised-next-step.md`：优先复用现有task-v1核对同任务Primary缺陷反馈，
> 不是继续改patch或自动扩权限。无commit/push、生产默认/兄弟源码变化。
>
> 当前执行（2026-10-28）：`strata-humaneval-normal-20261028-2`，HumanEval/1已独立
> 接受（4Coder+4Reviewer请求、1修改，8自写测试，官方+合法括号/空格穷举及全回归
> 429passed/61integrationdeselected）。/18执行中、/39尚未运行，不计未运行失败；
> 固定3格门槛未判。实际weekly1%/50%，task.19未改，无Primary live提示/代写。
>
> 以下为准备快照：`strata-humaneval-normal-20261028-2`，固定官方HumanEval
> 1/18/39，MIT、commit b9453e8...与原始题/参考/测试留档。task.19不变，普通16/4+
> freshReview10，每题一格、总78provider；前置完整检查执行中，尚未live/无成绩。
> 公开训练污染unknown，只测benchmark正常入口兼容。首命名空间0模型文档行长
> lint失败保留，新空间仅换行/类型适配不改算法/原断言。weekly报告0%/停止50%。
>
> 最新闭合：`strata-worker-tests-isolation-20261028-1` PASS_WORKER_IMPLEMENTATION_
> AND_TESTS_2_OF_2。两格各独立428passed/61integrationdeselected，两份Worker自写
> 6测试都检出register和definitions别名错误。32真实provider/52，首格12+7请求
> 自修类型失败，次格8+5请求首改绿；无Primary live提示/代写，旧所有HOLD保留。
> 只支持本任务族重复，不等于通用/未知边界检出或净云节省；无活动live。
>
> 当前注册（2026-10-28）：`strata-worker-tests-isolation-20261028-1`，task.19不变，
> 只测一个新的定义输出隔离行为，固定两次正常入口，Worker同时改source和明确
> 归它所有的补充测试。Primary仅提供7行空列表脚手架，独立保护/参考/变异器不输入。
> 两起点source/tests哈希一致；参考完整检查和独立425通过，原始别名实现被保护拒绝；
> 参考测试检出两种发布边界别名错误，脚手架不能检出。原参考lambda类型失败留档，
> 仅修夹具，0provider。新批最多52调用（每格16/4+freshReview10，无续作），2/2门槛。
> 实测weekly新窗口0%/停止50%，未使用reset；旧87/108闭合不续费，不覆盖任何成绩。
> 尚无新live结论；不改生产默认/模型/权限，不commit/push，兄弟和Strata安装只读。

> 最新闭合（2026-10-28）：`strata-primary-evidence-repair-20261028-1`为
> PASS_PRIMARY_SEMANTIC_ASSISTED_REPAIR_1_OF_1。Coder10请求/2有效修改/2写后检查，
> 一次Pyright多余cast错误自修、一次未观察行编辑拒绝后重读恢复；freshReviewer5请求
> PASS，独立427passed/61integrationdeselected，同一原合同边界探针通过。15真实调用/
> 26，任务377.375秒，weekly23%/50%，无活动live。Primary事实/回归准备成本明确，
> 不算自主、不证明云节省；父批0/1与Reviewer误放、旧六格5/6 HOLD全部保留。
>
> 当前阶段判断：任务只读材料缺失可通过显式批准已检查源集合修复；awaitable
> 漏判是模型语义+Reviewer/保护覆盖问题，应用器与当前检查没有伪造成功。事实
> 反馈可帮助本地修复，但未知反例发现仍依赖Primary，尚不能通用放行。保持同候选，
> 后续需面向明确任务族的受监督使用与实际Primary负担证据，不继续为这题调patch协议。
> 三个新批都已写registration/decision/metrics/handoff；累计本轮46+11+15+15=87≤108。
> 无commit/push/生产默认改变；兄弟源码和全部原tracked改动保持。
>
> 以下为辅助阶段准备快照：`strata-primary-evidence-repair-20261028-1`，保持task.19，
> 原失败草稿+Primary已核实反例事实+两个公开只读回归；明确assisted，不算自主。
> 原始回归1fail1pass，参考独立427passed/61integrationdeselected及全静态检查绿；
> 普通16/4无续作+freshReview10，总26新调用，72+26≤108。weekly23%/50%。
>
> 最新闭合：`strata-awaitable-entry-transfer-20261028-1` HOLD_PRIMARY_DETECTED_
> AWAITABLE_BOUNDARY_0_OF_1。Coder8请求/3修改后完整检查绿，Reviewer7请求PASS，
> 独立425也绿；Primary额外原合同探针发现合法生成器coroutine被返回原对象，
> ABC成员判断漏检，参考通过；Primary拒绝，Reviewer误放保留，旧8/2不充值。
>
> 以下为该批准备快照：`strata-awaitable-entry-transfer-20261028-1`，同task.19
> 正常入口新任务：修复同步工具返回awaitable的真实缺陷，保持线程/错误/超时/取消/
> hooks语义。原始起点公开2失败，参考独立425passed/61integrationdeselected及
> 全静态检查通过，安装/doctor/prepare0provider通过后冻结1格。最多44新调用，
> 此前46+11+44≤108，weekly22%/50%。live执行中，尚无成绩，不改旧5/6 HOLD。

> 最新闭合（2026-10-28）：`strata-source-context-entry-20261028-1`为
> PASS_EXPOSED_NORMAL_ENTRY_CONTEXT_COMPATIBILITY_1_OF_1。task.19未变；正常CLI
> 入口4次Coder请求/1修改，freshReviewer7请求PASS；独立423passed/61integration
> deselected，当前源码/检查/审查绑定核实。Reviewer实际观察runtime.py调用方，
> 没有重现旧材料清单拒绝。旧六格5/6 HOLD保持；新结果仅已暴露任务组合兼容，
> 不授予通用/恢复/缺陷检出资格。11真实provider/44，任务230.188秒，weekly22/50。
> 无活动live；无commit/push/生产默认改变；下一步新冻结正常任务验证迁移。
>
> 以下是本批准备时快照：`strata-source-context-entry-20261028-1`复用task.19。
> 上批固定六格已闭合HOLD5/6：Coder全6次一次修改全绿；hooks-2 Reviewer请求
> 清单外真实调用方runtime.py被拒，未交付内容。原失败保持，最后安全格完成。
> 新任务显式批准已检查源码/现有测试只读92文件，仍仅一个可写源码。原七动作
> 0provider重放已返回受限caller匹配，安装/doctor/正常CLI准备通过；现注册一次
> 正常入口兼容（非控制前缀），最多44新provider，本轮46+44≤108。weekly22%/50%。
> 当前尚无新live结论；旧490同版本控制及全部HOLD/分母保持，不commit/push/改默认。

> 最新有效结论（2026-10-27）：`strata-recovery-evidence-20261027-1`闭合
> PASS_NARROW_RECOVERY_EVIDENCE_2_OF_2。task.19默认关闭：同六次证据保留
> 写后当前源码；限一个既有可写文件≤120行/16000字节。同版本490完整控制通过。
> 新hooks/usage各一次修改，独立424/434passed，fresh Reviewer均PASS；17真实
> provider/上限36。两次写后刷新确实计费，但live普通拒绝和二次语义修复都未触发，
> 不能称已证明稳定自纠错或相对baseline增益。原task.18.1的2/4 HOLD、SSE及诊断
> 失败保持。无活动live；weekly结束20%/停止50%。完整decision/metrics/handoff
> 及准备失败留档，不commit/push/改生产默认，未取得通用生产资格。

> 最新有效结论（2026-10-27）：`strata-direct-recovery-20261027-1`闭合
> HOLD_DIRECT_RECOVERY_2_OF_4。task.18.1未变；54项相关控制通过，格式后5项
> 复验重叠，同产品472项完整证据复用。新registry注入缺陷2/2独立接受，各426
> passed；已暴露SSE为0/2：首格证据额度耗尽0编辑，第二格阈值误修后仍2失败，
> 主动错误声明生产scope冲突。42次忠实输入反证该声明，模型未获反证提示。
> 四格全部执行、25真实provider/上限72，无活动live。weekly终点19%/停止线50%，
> 因固定批次形成明确结论而停。旧诊断0/2和条件NOT_RUN不改写；未commit/push/
> 改生产默认。详见新批decision/metrics/handoff，准备夹具失败及修订均保留。

> 最新有效结论（2026-10-27）：`strata-diagnostic-projection-20261027-1`
> 已闭合HOLD_DIAGNOSTIC_SEMANTIC_ACCURACY_0_OF_2。task.18.1完整472项
> 离线控制通过，2/2诊断交付、0上下文超限；但两份因果判断被原源码独立
> 执行反证，0/2诊断获资格。关键bytes(integer)源码行均确实展示给模型。
> 条件8/2修复及fresh正式Review均NOT_RUN，不算Coder失败。累计provider13
> （旧批4、本批9）/56，weekly最后18%，停止线50%。无活动live，无commit/push。
> 详见该批decision/metrics/handoff及遥测勘误。以下保留前阶段快照。

> 当前有效快照（2026-10-27）：最新批次
> `strata-failed-draft-diagnostic-20261027-1`已闭合HOLD。task.18同版本467项
> 离线控制通过；两份诊断分别3/1次真实请求后因嵌套原始检查清单造成上下文
> 超限而停止，0份报告，准确性unknown；条件A/B修复NOT_RUN，不算Coder失败。
> 纯token重计数确认可通过机械投影缩小；DEV已准备18.1-offline，35项相关控制
> 通过，8份归档body投影均满足原上限。18.1完整回归/live尚未运行，不能借用
> task.18成绩。保留task.16/17和本批HOLD；无活动live。weekly最新18%，上限50%。
> 详见该批decision/metrics/handoff，原始记录与候选未替换。下文保留历史状态，
> 以最新decision/handoff和本快照为准，不把旧预算/旧候选当当前。

2026-10-25。有效计划为`strata-practical-readiness-plan.md`，用户授权自动迭代，
weekly used上限50%；本轮起点实测8%。原有历史资格和失败保持。

当前冻结候选task.9，路径：
`benchmarks/work/harness-convergence/strata-practical-readiness-20261025-1/candidate/product`。
包含finalize-v1收尾保留与统一调查入口approved_skills透传，默认关闭。
阶段1的63项不同控制和34项只读/报告相邻控制通过；共97项不同控制，无模型调用。

固定调查12格已闭合：A1/6、B4/6，两臂均HOLD；权威为该批decision/metrics/handoff。
两臂12/12合法交付，没有NOT_RUN。A多次核心答案正确但finding证据索引错配；
R2两臂四次都出现未受证据支持的flush/锁保证；另有不可观察的上游保证。
Skill组引用关联较好，但小批次不能证明一般收益或解决语义能力。每格完整判定保留。
旧task.8的A1/3、B1/3及HOLD保持原样。

实现批次位于同批`implementation-2/`，固定六格已登记并完成起点负控/参考正控。
I1批量解析、I2跨模块scripted_text_client、I3官方HumanEval/86，三种各两次。
I1首格完整接受：Worker6请求/2有效编辑/2写后检查，首次生产实现正确、后续修自写
测试断言；fresh Reviewer8请求/1引用纠正，独立432passed/61deselected，约596秒。
Primary无运行中指导或代写。固定六格现已6/6完整接受；I2独立448passed，
I2b独立453passed，I1b独立430passed，两次HumanEval/86均独立10passed。
均有自写测试/静态检查修复，生产实现首轮正确；不能冒充生产语义缺陷修复成绩。
六格合计83次实际Worker及Reviewer请求、3070.971秒；metrics/decision/handoff已闭合。
I1b的Primary不可变记录误写medium；独立correction明确原合同始终high，实际已经
逐文件完整审查并运行完整回归，未降低检查或风险。首次`implementation/`准备因Primary夹具缺少
RuntimeContext UUID而失败，模型调用0，已保留原记录，不计Worker失败。
公开benchmark固定官方commit、MIT许可和数据hash，原测试/参考解位于Worker范围外；
仅小任务管道验证，不能声称SWE-bench或无污染陌生仓库能力。

另有compact-v1报告窄修订的离线准备：
`strata-compact-answer-trial.md`。新增8项控制通过（与选择回归重叠不累加），
task.10已经冻结；121项相关离线控制通过（含真实条件续作；不与旧控制相加），
当前完整产品离线回归335passed/567.91秒，均无真实模型调用，不与选择控制累加。
新批次`strata-compact-answer-20261025-1`固定6迁移+2暴露诊断已登记。
T1/T2首次自主接受，T3一次原合同内证据争议反馈后接受：先撤回两处无证据保证，
重读同来源，无新要求/算法/权限/预算。T3b也在一次同类证据争议反馈后接受，
当前新题6/6最终接受=4首次自主+2监督恢复；T2b/T1b首次接受。
暴露R2首次仍过度保证空批次无flush，退回后耗尽共享额度且最后仍读取，被收尾门槛
拒绝，没有交付修正稿；最终reject。R2b首次也在收尾轮选择读取，没有交付报告，
不具备条件续作资格。固定八格现已全部闭合；新题6/6，暴露诊断0/2，分开记录。
总计31真实请求、1200.876秒包含两条暴露失败，不把条件未启动续作再算模型失败。
新题范围与暴露DB/concurrency诊断分开，不能借6/6撤销旧HOLD或放行DB语义权威。
DEV最新源码包含该默认关闭候选，不能把DEV等同task.9。
它省去重复finding及数字索引，答案/问题仍在summary，引用和语义门槛保持。
Reviewer和权限边界不变。task.9已记录完整HOLD，可按原授权启动一次窄修订；
下一批分别统计首次自主成功、一次原合同争议反馈后恢复、assisted及最终失败。

独立snapshot-repair两格已完成准备/负控/参考正控：修复构造时仅浅复制
ModelResult列表导致外部对象修改影响将来输出的隔离问题；保留生成/流式/重复末项行为。
这是另一个明确兼容性合同，不覆盖I1自写测试修复或六格实现成绩。
S1完整接受：独立429passed/61deselected，12Worker请求、3编辑/3写后检查，完整链
1012.703秒；先修实际源码缺陷，再补缺失测试并修自写调用次数断言，无Primary指导。
S2自行修正测试别名/async-generator误await/类型错误后完整接受：独立431passed，
8Worker请求、3编辑/3写后检查，完整链714.250秒。两格2/2接受，总计含Reviewer
31实际请求、1726.953秒；均无Primary运行中指导/代写，保护输入未改。

task.10另有全新安装/doctor/prepare/status/拒绝覆盖控制通过，模型调用0。
`strata-practical-capability-smoke-20261026-1`准备了两个已暴露兼容性smoke，
复用原公开资料+固定操作、只读孩子+编码，前置控制通过，不计新迁移成绩。
公开资料+固定操作当前版本独立接受（4请求/123.407秒）；已核对实际抓取和独立数值。
只读孩子+编码完整链也独立接受：父共享7请求含孩子3，fresh Reviewer4请求，
1编辑/1写后检查，独立3passed；兼容批次2/2接受，合计15真实请求。
试用说明和合同形状见`strata-practical-project-trial.md`、`strata-practical-contract.md`。
打包器只在所有固定范围门槛及兼容smoke闭合后执行，不含开发计划或历史日志，
不自动将试用资格改为生产默认。

本轮未commit/push、未更改生产默认，兄弟仓库与Strata安装只读，iq3_s单驻留。
已从当前线程自己的落盘计数取得云token观测，未读其他线程内容；精确Primary主动
时间仍unknown。`cost/benchmark-repeat-review-window.json`：一次终验/等待/状态窗口
3730未缓存输入、2830592缓存输入、2367输出（含1556推理，不能重复加），不含
此前合同/测试准备，也没有Primary-only对照，不据此推算净节省。
整轮基线后的首次计数含大量一次性开发/试验准备，不能当日常任务成本。
本地实际请求、token和时间从canonical记录提取。最后先观察12%，末次接口0%且
reset时间改变，原因unknown；未调用兑换reset，停止线上限仍50%。

本轮限定受监督试用门槛完成，已经产出并实际解包安装验证task.10 ZIP。
最新综合结论见`strata-practical-readiness-results.md`和原批新建的
`release-decision.json`/`release-handoff.md`，不覆盖原task.9 investigation HOLD。
所有live已结束，安装控制仅prepared、从未调用模型；没有活动执行需要中断。

## 后续真实项目改动试用（2026-10-26）

用户要求新建真实任务后，task.10另跑`strata-real-project-changes-20261026-3`。
注册3项：SSE实际协议修复失败（0编辑），跨文件AllOfGuardrail完整接受（435passed），
评估导出新指标因完整检查清单137>125而在模型前阻塞。实际执行2，接受1，失败1，
基础设施NOT_RUN1，总体HOLD，不覆盖上文的旧范围资格或任何失败。
辅助SSE锚点校正诊断仍有2个真实实现/回归失败，单列、不重算正式成绩。
详见`strata-real-project-trial-results.md`。未改冻结运行时、兄弟仓库或生产默认，
未commit/push。末次weekly used1%/上限50%。

## task.11：检查清单与编辑恢复窄修订（2026-10-26）

独立批次`strata-edit-recovery-20261026-1`已闭合，候选task.11默认关闭。
计划见`strata-edit-recovery-trial.md`。开发只在隔离DEV；原task.10源码与本轮
修复前preimage逐文件一致。完整产品离线355passed（含54项选择控制，不相加）。
修复前新控制12项为4失败/8通过，过程中一个测试异常类型预期错误保留在offline。

宿主检查清单独立限2048文件/32MiB，模型读取仍限125文件/8MiB，均有遍历/时间限额。
新增显式opt-in observed-lines-v1：当前文件版本引用+已观察闭区间行号+新内容；
不复述旧代码，不模糊匹配。复用原编辑器/预演/格式化/事务/完整检查。
目标错误2次恢复与协议错误2次分池，总请求16/工具24/证据16/有效编辑4/
写后检查4/任务1800秒不变；分池属于新候选，不冒充旧预算原样重跑。
终态保留停止原因、耗尽资源及最后拒绝。旧profile保持原编辑形状。

固定两格、原上游/合同/公开与封存测试不变：SSE为已暴露诊断，metrics为之前
Primary已准备但Worker首次执行；不是新holdout。两格均顺利编辑与全量检查，
无Worker协议/目标错误及no-op，但都没有失败写后检查，不能称为新语义修复证据。

- SSE：7Worker请求、2修改/2写后检查，fresh Reviewer6请求给PASS，原独立
  验收446passed/61deselected。Primary额外复核确认同一20字节事件在19字节
  上限下整块拒绝、跨CRLF分块却接受：吸收LF未计入event_bytes。Reviewer其实
  发现少算，却误把“允许保守计数”理解为允许放宽上限。Primary拒绝；这是
  实现边界与审查处置错误，不是报告格式错误，也不是最终错误接受。
  定点审计在Worker/Reviewer结束后进行，0模型调用，不改原测试或反馈答案。
- metrics：原137文件准备阻塞已消除；7Worker请求、1修改/1写后检查，fresh
  Reviewer6请求（一次超120行读取被拒后恢复，非重抽审查），独立464passed/
  72deselected，Primary完整审查及调用方核对后接受。未测真实MLflow/数据库集成。

本批1/2最终接受，HOLD，原1/2执行接受+1NOT_RUN及所有失败保持原样。
改善证据在宿主容量与编辑可执行性；未证明通用稳定、独立语义修复或净云成本节省。
下一重点应是原合同边界的可执行证据和Reviewer对确认偏差的处置，不能继续把所有
问题都归因于patch或用更多提示掩盖。当前批次不追加重跑，不把旧题恢复为holdout。
两格合计26实际模型请求、1280.890秒执行进程时间，不含全部准备/审查额外成本；
Primary无运行中语义提示或生产实现接管，主动时间/净节省unknown。
已核验兄弟仓库内容、根HEAD/既有tracked diff、旧成绩和两个冻结产品未变。
所有live已结束，无生产启用、commit或push。末次weekly used3%，停止线50%。

## SSE原额度内退回修复（2026-10-26）

新批次`strata-sse-defect-return-20261026-1`，task.11代码/模型不变。
旧正式任务未预开task-v1续作，未事后改配置；在新隔离检查点副本复用既有
`strata-worker.py resume --feedback`与原fresh-review快照/版本绑定门槛，
记为直接入口受监督恢复诊断，不冒充正式统一入口续作资格。
原项目及闭合decision/metrics/首轮拒绝和Reviewer误PASS逐文件未改。

26项既有退回/续作离线控制通过；另固定82格字节边界矩阵，旧错误草稿4格失败、
既有参考实现82/82通过。准备时审计辅助函数闭包lint调整以独立amendment保留，
0模型调用，未改场景、合同、资源或权限。完整产品355项同版本证据复用，不相加。

Worker收到原合同内20字节/19上限的真实失败事实及当前源码引用；没有算法、补丁、
参考实现或隐藏矩阵输入。新增4请求、3读取、1有效修改/1完整写后检查、1提交，
累计11请求/3修改/3写后检查，原16/4/4额度与1800秒时间保持，没有新起点检查。
累计活跃857.506秒、尚余942.494秒。此为受监督恢复，不是首次自主成功。

实际修复预先按2字节计入边界CR，然后无重复计数吸收后续LF；保留即时派发。
新增58行自写测试覆盖19/20/21、不同切分和逐字节输入。51聚焦测试和全部
配置检查通过，独立475passed/61integration deselected，固定82格矩阵0失败。
fresh Reviewer用5请求给pass_to_primary，Primary逐hunk核对后接受，输出accepted.patch。
保守超计仍属原合同允许的取舍，不新增精确计数/病理性能/真实provider集成保证。

本轮PASS_SUPERVISED_DEFECT_RETURN，实际新增9次模型调用含Reviewer；本地输入
227613、输出22235，非唯一token。Primary诊断、给反例与引用、做独立矩阵及终验
都是实际成本；没有代写源码，但不能由此推算净云用量节省。
它证明给出确认的缺陷事实后，local Worker可在原额度内完成真实语义修复；
并未证明Reviewer发现未知边界的可靠性，或抹去旧task.11的1/2、HOLD与误PASS。

下一阶段应在新任务起点显式启用已有task-v1正式入口续作，先核对它与
observed-lines-v1的组合控制，再测普通实现与有条件退回；不在旧任务上追改开关，
也不靠重复旧题获得迁移成绩。生产默认、兄弟仓库、Strata安装均未改，无commit/push。
本轮live全部结算，weekly used3%/上限50%；因固定诊断形成明确阶段结论交接。

## 固定候选的多类完整链与正式证据续作（2026-10-26）

最新结论：`READY_FOR_LIMITED_SUPERVISED_TRIAL`，不是通用生产启用。
证据在 `strata-formal-readiness-20261026-3/readiness-conclusion.json`，路径前缀仍为
`benchmarks/work/harness-convergence/`。task.11源码、模型和验收标准全程不变，
每个新任务起点显式启用原有`task-v1`续作与`observed-lines-v1`组合。

先新增两项无模型组合控制：不改代码续作必须复用旧Reviewer；真实编辑续作必须
重新检查并独立审查，原额度与起点检查不能重置。两项通过；355项同版本旧控制
只复用，不相加。准备命名空间1/2中的参考实现检查顺序、严格类型注解错误原样
保留，均为0模型调用；正式五格在全部可解性负控/参考验收通过后一次性登记。

| 固定单元 | 独立完整链接受 | Worker请求 | 有效编辑/写后检查 | 独立验收 |
| --- | --- | --- | --- | --- |
| any-1：多文件异步规则组合 | accept | 10 | 3/3 | 441 passed |
| reset-1：客户端重置/已启动流 | accept | 7 | 2/2 | 431 passed |
| digits-1：公开HumanEval/104 | accept | 6 | 3/3 | 11 passed |
| reset-2：同起点、新上下文重复 | accept | 6 | 2/2 | 432 passed |
| any-2：同起点、新上下文重复 | accept | 7 | 2/2 | 433 passed |

四个真实源码单元每格另有61项integration deselected，未验证真实外部集成。
表中测试大量重叠，不能相加成独立覆盖；只有三类任务，公开小题可能训练暴露，
不是大benchmark或陌生仓库修复成绩。完整链含原项目全部配置检查、fresh Reviewer、
Primary逐文件实际diff审查和独立封存验收。五格都在首次有界调用中完成，
不等于第一次修改就正确：12次有效编辑配12次完整写后检查，7次写后失败全部保留。
其中一次是先写测试、实现仍为NotImplementedError的中间状态；其余主要是自写测试
中的错误对象身份/Hook场景、漏await、错误数字预期、流结束调用记录预期。
模型自主修正的是这些可核实错误，没有改保护测试，也没有Primary运行中修法、
算法提示、参考答案注入或生产实现接管。两次缺换行的编辑拒绝、一次协议恢复
也保留；它们造成成本，但没有阻断本批完成。诊断见`postrun-failure-audit.json`。

正式入口另登记`strata-formal-followup-20261026-1`：复制已结算any-1及其花费账本，
原项目逐文件不变；实际`strata-task.py resume --feedback`新增3请求/4证据动作，
累计13请求、3修改、3写后检查、1起点检查。一次超过120行读取被拒后自行收窄。
源码与当前检查输入未变，因此复用原Reviewer，不重抽PASS。结论
`PASS_FORMAL_EVIDENCE_FOLLOWUP`；这是已暴露任务的证据续作，不增加新题成功分母，
也不冒充“正式入口改代码续作live”资格。后者在本组合下只有离线控制；此前
SSE直接入口真实语义修复是独立证据，旧HOLD/Reviewer误PASS均未改写。

本轮共65次实际模型调用（五格62、续作3），本地输入1,290,197/输出75,485，
输入不是唯一token数。本地执行进程合计2920.608秒，约48.7分钟，不含全部
实验准备与Primary主动审查时间。模型已驻留，加载时间未单独测量。
Primary仍承担合同、权限、公开/封存测试、私有可解性参考与最终全量审查；
这些都是真实成本。主动时间和净云用量节省unknown，无Primary-only配对，
不能从weekly百分比推算节省。

处置：保留当前候选，可以在相同信任边界和完整验收下开展受监督小任务试用；
不为追求零中间错误继续调这些已暴露题。未知边界的Reviewer可靠性、通用任务、
Coordinator拆包、额外联网/任意脚本/递归能力不由本批取得新资格，生产默认未启用。
这轮没有改生产runtime；新增的是隔离测试、离线组合控制、驱动和证据。
新增文件Ruff通过，根`git diff --check`通过；DEV继承的worker-runtime.py空白
告警仍保留，未借机清理既有改动。冻结产品与DEV runtime源码哈希一致，根HEAD/
既有tracked diff和旧decision完整保留，无commit/push、兄弟仓库或Strata安装写入。
所有live均已结束。结算时weekly used4%，最终交接复核5%/上限50%，追加观测
见`final-budget-observation.json`，未回写已闭合decision；因预登记批次完成并形成
限定范围的可用性结论结束，不是预算耗尽，也不宣称整套系统已通用稳定。

## 新迁移与真实缺陷续作：不能扩大通用资格（2026-10-26晚）

批次`strata-transfer-return-20261026-1`，统一前缀仍是
`benchmarks/work/harness-convergence/`。最终综合记录`phase-conclusion.json`：
`HOLD_EXPANDED_GENERAL_QUALIFICATION`。冻结task.11、iq3_s和生产默认不变；
不是修改同一runtime来回切换导致另一题回归。此前五格5/5及所有旧HOLD保持。

本次核对weekly used6%，结算观察9%、最终交接复核10%/上限50%，追加观测见
`final-budget-observation.json`，未回写闭合成绩；模型由用户重启后的实例驻留，
仍为Qwen3.8-Flash-Next iq3_s、engine0.1.47、context131072、parallel1。
LM Studio接口关闭，旧实验预检因此拒绝；新增实验侧只读证明检查端口拒绝与
LM引擎进程，未启动LM Studio。Windows WDDM存在权限不完整的GPU进程项，
不宣称OS级GPU独占。五项预检负控和两项正式入口组合控制通过，0provider调用。
临时目录父级缺失、脚本控制Reviewer漏变更测试引用的准备失败全部保留，分别
修正临时目录和新隔离控制夹具；它们不是模型质量失败，没有修改生产runtime。

| 单元/诊断 | 原始或最终处置 | 已确认事实 |
| --- | --- | --- |
| 新任务remove-1 | accept | 431 passed/61 deselected；注销/重注册、旧快照和在途handler身份均验证；6Worker请求、2编辑/2检查，无Primary修法 |
| 新任务canonical-1 | rework | 480 passed/72 deselected且Reviewer PASS，但Primary证实新预遍历调用键repr，破坏原可编码有限字符串子类输入 |
| natural-return-canonical | HOLD | 真实两阶段正式resume修复已给键反例，累计12请求/4修改/4检查；另一个有限列表子类被多迭代一次，原[1]变[2]，Primary再次拒绝 |
| formal-return-2（SSE） | HOLD | 首阶段是零模型控制，不算新题；实际续作源码通过固定82格诊断，但自写测试失败且用满原4修改/4检查，真实Reviewer未启动 |

新增任务原始分母2，接受1，不能把两项续作计成新任务成功或替换canonical原
rework。表中测试重复大量旧测试，不相加为新覆盖。canonical两份不同源码的
fresh Reviewer都给PASS，Primary两次拒绝，属于两次已观察的审查漏错建议，
不是对同一代码抽样直到PASS，也不是最终错误接受。

canonical具体证据：`cells/canonical-1/primary-preservation-audit.json`确认
原实现对`{K('kept'):1}`返回`b'{"kept":1}'`；K是repr抛错的str子类，新实现却
在`key_path`求repr时抛RuntimeError。真实正式入口在独立副本复用原6请求/
2修改/2检查及全部花费，Primary只给原合同缺陷事实与源码引用，没有给补丁或
算法。Worker新增2修改/2检查并fresh review，原反例探针通过，但
`natural-return-canonical/primary-iteration-audit.json`确认：对于每次迭代产出
有限调用计数的list子类，旧编码器迭代一次输出[1]，新预遍历加编码器迭代两次
输出[2]。未修改“保持原有限输入字节”的冻结合同，也未继续补额度。
`execution-vs-qualification.json`明确正式改代码续作确实执行；闭合decision中
`formal_changed_evidence_live=false`表示未取得最终资格，不是NOT_RUN。

这些是较强Python兼容性合同下的容器子类反例，不是普通JSON primitive载荷的
失败证据，更不能推出模型普遍无能力。本轮没有把合同缩窄来获取PASS。
Reviewer把编码器参数未变直接等同于有限行为未变，漏看了额外遍历/回调的
可观察作用；这是实现与语义审查问题，不是报告格式或工具没有执行。

SSE控制路径单独记录：已暴露错误草稿经脚本写入，控制报告不是实际Reviewer
成绩；原82格负控检出错误、参考实现通过后才启动一次真实formal resume。
Worker修改了字节预留处理，但补充测试把`bytes(byte)`误作单字节切片，且另一
测试错误要求超过10字节上限的事件被接受。其后一次修复提案被4修改/4检查
上限拦住，未应用。`poststop-source-matrix.json`在已停止草稿上运行同一82格，
源码0失败；这只是诊断，不能越过失败测试和缺失Reviewer接受。排队提案仍未
修复单字节构造问题，更多额度是否足够尚未验证，不能称为“只差放宽预算”。
脚本首阶段花费与旧真实7请求首阶段不同，不能作旧耗时/能力的等条件比较。

本轮47次实际provider调用，输入1,181,843/输出77,513（输入非唯一token），
执行进程合计1332.735秒约22.2分钟，不含全部准备和Primary主动时间。
Primary合同/测试/参考可解性准备、两次源码反例审计与语义反馈都是真实成本；
没有生产代写不等于没有协调工作。净云成本节省仍unknown，不能用weekly变化
推算。各项registration/decision/handoff/metrics及错误草稿均保留。

后续应分两条小线判断：恢复额度与有效写后检查的对齐（新注册对照，不能回写
本次4次上限成绩）；真实调用域下的可执行兼容性不变量与审查证据。不能用
增加提示、无差别加预算、缩小旧合同或反复旧题代替这些判断。
此前有限受监督试用证据仍在，但本轮没有扩大通用/无人值守/联网/脚本/递归或
Coordinator资格。未commit/push，根HEAD、既有tracked diff、冻结产品和旧成绩
均未改变；兄弟仓库与Strata安装未改。所有live已停止并结算，模型最终空闲。

## 已暴露失败的证据修复诊断：实现与审查交付分开结算（2026-10-27）

批次`strata-evidence-repair-20261027-1`，前缀仍为
`benchmarks/work/harness-convergence/`。两项独立修复诊断已完成，结论
`HOLD_EXPOSED_EVIDENCE_REPAIR`：完整链接受0/2，未扩大通用资格。weekly used
起点10%、结算11%，停止线50%；结束原因是固定批次完成并形成明确诊断，非预算耗尽。

先做无模型核查：原SSE被拒排队提案按原版本引用/已读范围在隔离副本应用，
仍为2 failed/25 passed，证明该具体提案不是“再给一次写入就完成”。canonical
已知兼容性错误转为7项只读合同控制，错误草稿失败、最小参考通过；另封存两项
容器回调边界。参考实现、私有验收均未进入Worker输入。

隔离DEV补一项宿主诊断：有效写入前按当前阶段实际额度同时检查编辑/写后检查
资源，记录耗尽资源及写前拒绝事实，源码保持不变；不增加额度、不改变验收。
四项新负控覆盖共享/阶段额度及两种耗尽资源；完整366项离线控制通过，所选26项
是其子集，不能相加。封装安装及哈希验证通过，候选`task.12-diagnostic`只取得
离线诊断资格。本批live仍使用冻结task.11，不能把结果归因于该诊断代码修改。

| 独立诊断 | 实现及检查 | Reviewer与最终处置 |
| --- | --- | --- |
| sse-repair | 16请求、4有效修改/4完整写后检查；最终focused 24 passed/2 failed | 未启动Reviewer；rework |
| canonical-repair | 7请求、1修改/1写后检查；配置回归493 passed、focused41 passed；独立完整+私有500 passed/72 deselected | fresh Reviewer7请求，无有效报告；rework |

这些是从已暴露停止草稿开始的新任务，给普通独立任务完整预算，不是给原任务
账本补额度；本批未预留续作阶段。新上下文、可见回归和完整独立预算同时变化，
不能作为单因素预算对照，也不是新题迁移成绩，不能覆盖任何旧失败或HOLD。
canonical各测试集合重叠，不能相加；72项integration未运行。

SSE三次先改源码，一次后改自编测试，但`_all_chunkings`仍保留`bytes(byte)`，
构造零填充缓冲而非单字节输入。模型修过新增退化，原失败仍在；所有允许编辑
确实都有写后检查，不能把本次失败归为验证槽不足。停止后同一82格源码矩阵
仍0失败，仅为诊断，不能越过失败测试接受。实际源码还把单事件上限检查移到
整块网络缓冲解析之前，存在将多事件合并长度当单事件长度的风险；未为此新增
测试或修改分数，82格单事件矩阵也不证明该行为正确。

canonical去掉递归预遍历，已知及封存回调检查通过；Primary查看实际源码与
两文件累计diff，未在登记控制中确认新的实现缺陷。但fresh Reviewer先越过
120行读取窗口，再使用调查角色的`answered`状态，最后提交`pass_to_primary`
仍有四处引用行号/原文不匹配，耗尽两次协议恢复，无正式有效报告。前三次
拒绝均保留在`cells/canonical-repair/review-delivery-audit.json`，没有重抽同一
代码和证据直到PASS。未接受报告还声称嵌套float子类会转为字符串；Primary
离线stdlib探针确认NaN/inf子类实际抛ValueError，这条推断不可采信。现有
observed-line绑定只适用investigate，不能冒称Reviewer已经具备或静默开启。

本批30次实际provider请求，输入838,668/输出80,720（输入非唯一token），
执行进程合计1306.673秒约21.8分钟，另有约15分钟离线完整控制及准备/审查。
未提供运行中算法提示或代写；合同、可解性参考、回归准备和全量审查仍是Primary
真实成本。主动时间和净云节省unknown。保护输入、旧产品/旧decision、根HEAD
及既有tracked diff核对保持；模型最终空闲，生产默认未改，无commit/push。

后续修复重点应分开：Reviewer角色状态/已读引用的机械交付，以及SSE从失败
证据判断测试输入自身是否正确的能力。前者不能靠放过错误引用解决，后者不能
靠无限补预算或把Primary修法注入后计自主成功。该批没有取得通用稳定放行。

## Reviewer交付与新真实单元：限定范围通过（2026-10-27）

`strata-review-delivery-20261027-2/decision.json`结论
`PASS_REVIEW_DELIVERY_AND_NEW_UNITS`，统一证据前缀仍为
`benchmarks/work/harness-convergence/`。候选task.13默认关闭，只为普通实现的
fresh Reviewer新增角色专属状态schema、已读当前行的宿主原文绑定、超长读取
分页与聚合形状反馈。模型仍选择状态、判断缺陷并解释语义；宿主不替它选PASS。
原Coder、完整检查、权限/版本/预算和Primary独立接受义务保持。

同版本完整386项离线控制通过；所选20项是其子集。命名空间1在0provider调用时
先后发现Primary私有夹具错误使用Message.metadata，以及恢复准备时的import布局
与已验证参考不一致，全部保留并拒绝live。命名空间2只修准备结果，复用同一
冻结产品和控制；实际保护测试与通过的参考版本、安装hash逐项一致后再注册。

| 固定单元 | 结果 | 证据与成本 |
| --- | --- | --- |
| merge-bad | 有效rework | 真实普通测试绿，正确识别重叠值被update覆盖；3请求 |
| tail-clean | 有效pass | 正确解释count0分支；4请求，1次info findings报告错误自行改为unknowns |
| merge-clean | 有效pass | 正确解释求和、零/负值保留及不变输入；3请求 |
| tail-bad | 有效rework | 正确识别items[-0:]返回全列表；3请求 |
| contains新真实单元 | Primary accept | 11Worker请求、3修改/3检查；独立428 passed/61 deselected |
| peek新真实单元 | Primary accept | 7Worker请求、1修改/1检查；独立426 passed/61 deselected |

四格审查控制为两个小函数的正/负版本，不是四个真实实现，不证明未知复杂边界
审查能力；本四格未观察到误放/误拒。两真实任务从冻结runtime兄弟仓库快照开始，
完整配置检查、fresh Reviewer、封存验收和Primary全部实际源码/两文件diff审查
均通过，无运行中算法/补丁指导，无接管。contains自行补齐缺失测试并修静态问题；
peek覆盖深拷贝、重复调用、耗尽和已启动流交错。测试集合大量重叠，不相加。
peek的Reviewer称“索引始终在范围内”不准确：计数器会增长，实际是min选择表达式
钳制位置。Primary明确记录该措辞问题，以实际表达式和执行证据确认行为，不把
报告每句话当权威，也不宣称纯净的全因果审查资格。

本批40次provider请求，本地输入559,311/输出37,620，进程691.406秒约11.5分钟；
另有完整离线543.46秒及准备/审查。Primary主动时间和净云节省unknown。
候选14尚未因此获得新资格；旧SSE/canonical失败与此前5/5均保持原样。

contains中0执行测试时旧失败被归档delta误标resolved，记录在
`observations/zero-test-delta.json`。随后逐一核对11份实际Worker请求，均未包含
该字段；`zero-test-delta-exposure.json`明确它是归档元数据问题，不能作为本轮
Worker决策或失败原因，亦未触发错误接受。未因此改共享旧runtime或扩展本批。

## 更多真实局部值未修好SSE，暴露测试单元表达限制

`strata-sse-local-evidence-20261027-1`使用同一task.13，原草稿/合同/保护验收
与旧16请求失败的起点一致，仅在focused及完整pytest中加入--showlocals。
这是一次已暴露诊断，不是新题或纯因果A/B；原成绩不变。结果
`HOLD_EXPOSED_LOCAL_EVIDENCE_REPAIR`：16请求、3有效修改/3检查，请求先耗尽，
Reviewer未启动，原2/26失败变25/27失败，停止后固定82格全部失败。

退化可在模型原始`native-action-1-9.json`确认：新增keep_tail只把尾部UTF-8
续字节追加到buffer，普通ASCII整段被丢弃。它不是宿主应用器或formatter改坏
了正确提案。后续提案还保留重复解析尾部，最后145..160的未读范围编辑被正确
拒绝。模型始终未修原bytes(byte)测试构造错误。初始真实请求包含pytest展示的
281处零字节标记，初始8090 tokens，证明这些诊断事实实际到达模型。

上下文预检最高58720输入tokens，超过当前安全总窗口时未发送超限请求；宿主
在修改revision2、3各重建一次上下文，未补额度。日志变大与代码退化互相影响，
不能把这一次结果解释成“局部值造成退化”或模型普遍无能力。16次provider请求，
输入457,873/输出46,576，进程749.422秒约12.5分钟；无最终误接受。

下一分支明确记录Primary定位成本：把剩余工作定为自编测试修复，并冻结生产
源码，不能冒充原SSE自主完成。参考在原生产源码不变时通过475项/61排除及82格；
但`strata-test-repair-routing-20261027-1`正式入口要求至少1个生产源码写入文件，
在0模型调用时拒绝测试专用单元。这是实际任务表达限制，不是Worker质量失败。
`strata-test-unit-contract-20261027-1`默认关闭test-repair-v1修订正在执行同版本
离线控制，live尚未运行、尚无结论；其后状态以该批decision/handoff为准。

## 测试专用任务已接通，正确审查后的返工缺少额度

`strata-test-unit-contract-20261027-1/decision.json`结论
`HOLD_TEST_REPAIR_SEMANTICS`。task.14新增默认关闭test-repair-v1，仍复用implement
入口与同一工具集，仅1..2个批准tests/test_*.py可写；生产/配置/conftest及可选
能力组合不开放，普通实现1..4源码门槛保持。同版本397项完整离线控制通过，
所选49项是子集。初版控制缺紧凑结果unit_kind标记及异常类型预期错误均保留，
没有计为模型失败。安装/哈希和原源码不变的参考475项+82格均核对后才注册live。

一格test-only是Primary明确定位后的assisted-planning诊断，不是原SSE自主成绩。
Coder16请求、4修改/4检查，修正了chunk构造与不可能通过的10字节正例；中间
两次pytest.fail诊断探针被语法质量检测误判为“无断言”，未实际执行。最后去掉
探针后全部配置检查通过：focused26、完整445；独立450 passed/61 deselected，
固定82格0失败，生产及保护输入不变。测试集合重叠，不能相加。

fresh Reviewer9请求、0协议错误，正确返回rework：LONE_CR_WIRE实际为
`b"data: aaa\r\ndata: bb\r\n\r\n"`，所有CR后都有LF，任意分块仍是同一CRLF
字节流，因此未覆盖名称/文档声称的“lone-CR reservation release”。其byte-peak
评论也不实。Primary核对真实字节和生产elif reserved分支后确认major finding；
更紧的负边界仅为optional建议，不新增合同。逐项处置绑定canonical Reviewer
报告SHA与identity，保存在`cells/sse-test-unit/primary-disposition.json`。
没有接受错误测试，没有再抽同一审查，也没有把绿色检查当全部语义完成。

该格25次实际provider请求，输入741,730/输出61,941，执行1010.234秒约16.8分钟；
Primary主动时间和净云节省unknown。Primary定位和收窄任务是额外真实介入，
不能因未代写就记为零成本。旧SSE失败、task.13两真实单元通过分别保持。

关键设计缺口现有实证：Coder在独立Reviewer指出有意义的剩余缺陷之前，已经
花完16请求/4修改。现有task-v1虽然能预留原总额，但其10请求/3修改首阶段
不覆盖本格实际首阶段。不能给已闭合任务补额度；新的完整任务预算需要在起点
就包含审查返工。具体24/6共享总额、16/4首阶段加封存8/2、最多两次有实际新
证据的独立审查方案位于`strata-review-rework-budget-proposal-20261027-1/proposal.json`
及当前计划末节；这是资源与停止策略选择，已集中提交用户确认，尚未实施/live。

另一个普通修复已独立完成于DEV：pytest.fail及其显式import别名属于真实失败
断言，执行仍会失败并挡住提交；空白/skip/无关fail不获通过。
`strata-diagnostic-fail-control-20261027-1/selected-controls.json`20项通过，含11项
既有测试专用控制，不能与397相加。其完整回归正在运行；未把该未冻结DEV修复
冒充task.14的live同版本证据。当前所有Worker/Reviewer均已结束，模型空闲。

### 离线修复收口与当前待决事项

上述完整回归现已完成：task.15-pytest-fail同版本406项通过，所选20项是子集。
独立冻结包已安装并逐文件核对哈希；正式结果见
`strata-diagnostic-fail-control-20261027-1/decision.json`及`handoff.md`。
这是离线修复资格，新增模型调用为0，不改写task.14的rework或赋予新live资格。

最后一次实际预算观测weekly used为14%，当前停止线50%。本轮暂停点是已集中
提交的完整任务审查返工预算选择，而非usage耗尽。24请求/6修改方案尚未实施，
也未给旧任务充值。16/4耗尽中包含已修机械浪费，故尚不能断言修复后16/4仍不足，
或24/6就是最低必要额度。所有失败与Primary收窄任务的辅助成本继续保留。
生产默认、兄弟仓库、Strata安装保持不变；没有commit/push。

## 已批准并实现完整任务预算，正在完成正式前置控制

用户明确批准首阶段16请求/4修改、封存一次8/2审查返工，总额24/6。
`strata-review-rework-budget-20261027-1`的新默认关闭profile为review-rework-v1；
复用原TaskLedger/StageLedger、编辑器、完整检查、canonical档案与fresh Reviewer。
prepare绑定预算类型，旧账本不可升级；返工需Primary逐项处置canonical findings，
绑定报告hash/identity、现稿与当前检查；只有确认的原合同缺陷可返工一次。
未用首阶段余额不会扩大返工上限，无实际改动不会重新抽审。

初版43项预算/续作控制通过，完整429项通过。负控记录保留了首阶段时间基数
偏差的修复前失败；前两次pytest因Windows默认临时目录权限失败，未进入候选逻辑。
随后代码核对发现纯token预检仍硬编码16请求，定向控制实测第17请求被拒。
修复后16项counter控制通过，覆盖原token绑定与新阶段准入；旧模式仍保留18次
计数上限，新profile为24请求+原2次重建共26次计数，整个任务不重置。
因此冻结task.16-review-rework后重新执行最终同版本完整回归；429不是最终版
完整回归成绩，最终以full-controls-final.json为准。本记录写入时仍执行中。

两格离线准备完成：已暴露merge缺陷的脚本首阶段/脚本审查兼容控制，以及新
ToolRegistry.unregister完整任务。真实任务起点匹配冻结兄弟快照，保护公开检查
证明缺功能，私有参考完整检查与独立423项/61排除通过。参考/隐藏输入不送模型。
Primary夹具先后被目标Ruff导入顺序及严格Pyright的未标注lambda拦下，原文件和
失败receipt保留；在新参考目录修正类型与目标排版，合同/候选未改变。这是
真实Primary准备成本，不是Worker失败。另有独立副本的0provider兼容预演通过，
没有更改正式两格起点。尚未启动新增live，正式成绩尚无结论。

### task.16两格已闭合，开始一次原始SSE诊断

最终同版本完整回归433项通过，运行前后与冻结包哈希一致。固定两格结论为
`strata-review-rework-budget-20261027-1/decision.json`的
PASS_SCOPED_REVIEW_REWORK_BUDGET。选择43项/counter16项均为子集，不累加。

兼容格脚本首阶段和脚本Reviewer为0provider，不计自主成绩；真实返工3请求/
1新增修改，fresh live Reviewer3请求通过，Primary读实际5行源码并独立2项通过。
unregister新真实单元Coder13请求/2修改/2检查：首次生产实现正确，focused8及
完整427已绿，但补测contextmanager的Iterator标注被Pyright拒；Worker自行改成
Generator后提交。fresh Reviewer5请求通过，Primary读完整源码、205行补充测试
和实际累计diff，独立429项/61排除通过，保护输入未变。没有运行中修法或代写。
Reviewer坦陈辅助类只在diff看到；Primary已读全部当前辅助类并核对实际执行，
不把这次结果说成Reviewer完整覆盖已解决。新单元未触发Review返工。

两格合计实际24provider请求，输入437238/输出22781，本地进程427.594秒。
Primary主动时间、云token与净节省unknown，无Primary-only配对；参考/夹具和
适配器/控制是一次性研发与实验准备，不能当日常执行成本。此结果只证明封存返工
通路可用及一个新任务完整成功，不证明24/6必要、最小或提高了整体成功率。

同候选另登记`strata-sse-review-reserve-20261027-1`，仅一次已暴露测试修复诊断。
起点逐文件匹配原routing项目，owned test还匹配task.14 canonical preimage；
goal/硬合同/保护测试/范围/模型不变。原475项+82格参考证据在源码及所有非owned
输入哈希一致后复用，额外0provider控制验证test-repair-v1与新预算可组合。
起点仍2failed24passed。无旧正确补丁/隐藏验收/旧Reviewer答案输入Worker。
这是pytest.fail修复与新预算的组合候选，非纯预算A/B；旧HOLD不回写，仍属
Primary定位和测试专用路由后的assisted-planning证据，不恢复新题身份。
本记录写入时first执行中、尚无结论；最新weekly used15%，停止线50%。

### 原始SSE诊断首次接受，固定两次重复已注册

`strata-sse-review-reserve-20261027-1/decision.json`为
PASS_EXPOSED_TEST_REPAIR_WITH_UNCHANGED_PRODUCTION。Coder12请求/3有效修改/
3完整检查/1协议纠正，Reviewer4请求/0协议；独立452项/61排除通过，固定82格
0失败，实际变动只有owned test。Primary读全部230行测试、113行decoder和
实际累计diff；原有测试意图保持，新增真实lone-CR释放用例和对比边界。
在独立停止后副本仅禁用event_bytes-=reserved，新用例随即失败，证明并非
又用CRLF输入冒充lone-CR。该额外诊断验证原合同意图，不增加Worker要求，
也未反馈给Worker。旧HOLD和历史误放均保留。

第一修改将原2个失败变为3个，第二修改检查通过，第三修改再补有效覆盖，
所有中间失败原样归档。这是有界自主恢复；不是失败数单调下降。实际原始
action中没有pytest.fail提案，本轮也没有使用Review reserve，因此不能把
成功归因于guard修复或预算扩大。实际16provider请求、输入373610/输出35773，
进程642.359秒；Primary主动时间/云tokens/净节省unknown。它仍是已暴露且经
Primary先行定位为测试修复的工作，不能冒充原生产SSE自主修复或新holdout。

为区分单次成功与重复性，另注册`strata-sse-reserve-repeats-20261027-1`。
两格已同时封存原始失败起点、候选task.16、合同、顺序和2/2门槛，不带成功
补丁或旧Reviewer答案。一格普通失败即HOLD，仍完成另一安全格；不加次数，
不改候选或标准。此处repeat-1已启动，repeat-2尚未运行，尚无批次结论。

### 固定重复已HOLD，单次窄进度候选进入离线控制

`strata-sse-reserve-repeats-20261027-1/decision.json`为HOLD_REPEATABILITY_1_OF_2。
repeat-1仅7请求、0编辑、2协议纠正，因3次无新增行停止；Reviewer未启动。
轨迹明确先读完decoder1..113和owned test1..168，最后3次不同范围分别为
decoder105..130（实际113）、decoder86..100、test158..168，最后一段未交付。
非法decoder1..130窗口和根目录搜索另有拒绝，不能把它们说成权限逃逸或唯一根因。
`observations/repeat-1-progress-stop.json`保留新证据计数和实际动作，支持检验
“新事实”与“有用的注意力重聚焦”是否被混同，不证明再读就会实现正确补丁。

repeat-2首阶段16请求/3编辑/3检查/1协议/1编辑恢复后通过；Reviewer通过，
独立450项/61排除、82格及no-release副本负控均通过。所有生产和保护输入不变。
Primary核对保留的所有测试意图：CRLF全分块正例21允许原合同明确许可的保守
计数，负例19保留，另有真正lone-CR的20/19及split-CRLF的24/23精确边界；
不凭额外“必须20接受所有分块”发明新硬要求。Readonly Reviewer坦陈work_state
自身0编辑与review_material累计diff的表面差异，Primary检查实际preimages/diff；
这是另存的表示问题，没有混入本批修复。两格总28provider请求，686037输入/
60761输出，进程1021.265秒。第一格失败不被第二格成功冲掉。

单次窄候选task.17仅在显式review-rework-refocus-v1下允许第3次不同局部重读，
第4次无新行和3次参数完全相同的重复仍停止；原所有总额度/权限/Reviewer/提示
不变。35项选择控制通过，0provider原样重放旧10动作确认最后局部行交付且原
2非法动作仍拒绝。候选已冻结，两格live起点已准备，最终同版本完整回归执行中；
尚未注册live、尚无模型成绩。若这唯一窄修订后门槛仍失败，按计划停下来总结边界。

最终同版本441项完整控制通过，候选前后哈希一致。`task.17-bounded-refocus`
固定两格已在registration.json登记，只有continuation profile值变化，原始失败
草稿、合同、预算、模型、Reviewer、验收都不变；refocus-1已启动，refocus-2
未运行。每格会单列“实际交付第三次非新行局部重读”的处理是否被触及；未触及
的成功只能算兼容性，不能归因于新启发式。最新weekly used15%，停止线50%。

### 唯一窄修订已闭合HOLD：停止阈值微调，等待角色边界决策

`strata-bounded-refocus-20261027-1/decision.json`为
HOLD_REFOCUS_1_OF_2_TREATMENT_UNEXERCISED。refocus-1独立接受，11请求/2修改/
2检查/2协议纠正，独立450项/61排除、82格及no-release负控通过。refocus-2
16请求/4有效修改/4完整写后检查后仍2测试失败，未进入Reviewer。不是最后
全绿却无法交付：其初始2失败，写后依次2、3、2、2失败，中间F821被修，但
原始输入构造问题持续存在。最后原始model action替换里直接包含
`[bytes(byte) for byte in wire]`，当前文件也是这个表达式；它构造NUL填充数据，
不是原wire的单字节分块。调整wire/limit不能修这个输入失真。应用器忠实应用
模型提案，完整检查正确拒绝；不能把该格称Reviewer误放或单纯harness交付故障。

两个live都未触及第三次非新行重读，因此不能将一次成功归因于新规则，也不能
据第二格失败反证该启发式。候选不推广，旧task.16的1/2与更早失败全部保留。
两格合计31次实际provider请求，808226输入/81070输出，进程1385.032秒；云
tokens、Primary主动时间和净节省仍unknown。441项完整控制与35项子集不累加。

本次指定唯一窄修订未达门槛，按登记停止旧题阈值/提示微调。关键待决方向是：
能否将现有只读Reviewer增加“失败草稿诊断”用途，在不允许PASS的模式下核实
根因，再用原8/2修复并做fresh正式审查。总24/6、最多两次Review、权限和最终
验收都不增加。现有direct readonly入口能绑定failed checks，正式workflow只
接ready/currentfullchecks；需要改变的是诊断到恢复的路径，不能冒充已经支持。
`next-design-proposal.json`给出了先负控、两档案各一次诊断、条件受控修复对照，
最多56新provider调用、weekly50优先。没有新增常驻咨询角色或更多咨询轮次；
若识因仍不能落实补丁就停止该路线。当前尚无此设计授权，没有新增live。

关闭观测为`close-observation.json`：HEAD及所有原有tracked diff哈希与起点
一致，生产默认未改，兄弟仓库/Strata安装只读，无commit/push。停止是关键
角色/恢复设计选择，非usage耗尽（实测16%对50%上限）。
