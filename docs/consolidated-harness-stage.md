# 实验Harness收敛阶段

2026-10-18用户批准继续；开始weekly used12%，停止线20%。当前仅实验代码，模型/角色/单驻留不变，
不改生产默认或原runtime、不commit/push、兄弟仓库只读，历史与失败不覆盖，R4仍HOLD、R5未准入。

## 边界

用一个直接继承原WorkerRuntime的实验控制器，替代旧7层左右的实验类组合。
一个显式CLI提供preflight、coder、unit和禁止网络的replay；没有Popen路径替换、动态import拦截或__class__替换。
继续使用原SafeEditor、validator、锁、canonical档案与host-proposal-v1 verifier、原Reviewer。
保留行为单元AST/import guard；不引入shell/自主权限/新角色/记忆/Planner。

解析仅容忍一个非活动null字段；重复键、未知字段、两个非空动作、空字符串和全部null仍拒绝。
写前固定Ruff stdin preparation，检查AST不变和所有批准输入不变。格式化结果与当前代码相同则no-op，
不占编辑/验证槽；准备命令本身计次数/时间，不能当免费调用。
失败状态与历史验证不改，遗漏profile命令只作绑定同版本的补充诊断，不能凭补充PASS交接。
当前完整正常检查通过后才fresh Reviewer，最终仍Primary独立验收。

## 预算与资格

仍12提案请求、3有效编辑/3写后检查、1起点检查、2协议恢复、2no-op停止、4096输出、900秒。
格式准备改为每提案最多1次、共最多12次（此前1次格式化不是原样预算），均计时/受总上限。
Reviewer仍16请求/4错误/600秒。这个预算变化只属于新候选，不追改旧结果。
scripted请求与真实model请求分开计数；preflight/replay不获取模型lease、不加载模型、不启动真实Reviewer。
unit replay只在独立档案认证Reviewer输入，避免预检占用日后live档案。

## 执行门槛

先真实CLI离线控制：安全范围、strict envelope/inactive null、T1nullable检查、格式no-op、写后检查、
canonical认证及陈旧验证拒绝、完整unit Reviewer输入认证。原生产默认和用户改动须验证保留。
通过后冻结候选；若恢复live，仅新注册4格（原已暴露T1/T2各2），不宣称未暴露迁移或严格A/B因果。
该批必须4/4独立完整链接受才有新迁移验证价值，不直接R4。普通失败HOLD但完成固定批次；
安全/基础设施/保护漂移或weekly20%停止，未运行单列，不补跑冲掉失败。
新live前冻结准确输入/顺序/检查/预算；无需为普通技术选择重复询问，重大产品边界仍交用户。
无改善不再围绕同两题追加协议/提示/预算变体。旧Reviewer null漏检保持，本阶段不修审查模型。

开发、夹具和重放是一次性工程成本；任务执行代写/语义提示单列，云token/主动时间不可测写unknown。
