# 单函数输出协议：独立窄候选

2026-10-19，用户已授权逐测试自主分析/优化，weekly used20%停止；起点实测14%。
前批normal-task-repeat-20261019-1固定4格2/4：request_keys2/2，single_content0/2。
失败保持，不用新候选重写。原候选及新来源映射保存在前/本批candidate-preimages。

实际证据：single_content六次响应是两个唯一合法函数，原守卫要求整个模块而拒绝。
离线原样嵌回：一份13行为测试通过但有Pyright多余isinstance错误；另一份全部原检查通过，
零语义修改/零模型调用/零live信用。Primary最初误读JSON转义，已追加更正，原review不覆盖。

本候选只改变输出范围：明确要求一个完整目标函数；宿主按当前源码与稳定符号嵌回。
拒绝多定义、导入、签名/decorator改变、抑制及坏转义，不猜测完整模块或自动反转义。
输入仍同一完整模块/合同/真实失败/依赖；不裁上下文、不额外给修法。
继续用原编辑器、版本绑定、格式化、全部可信profile、fresh Reviewer、Primary独立终验。
入口显式--function-output，与旧模式互斥；默认生产配置和旧入口含义不变。
不加类层/全局替换/角色/权限，runner仅接受显式batch/order/command参数复用。

先12项离线控制（8安全负控、AST不变、两项真实CLI完整脚本链、互斥格式），通过后冻结。
固定4格顺序：request_keys-1、single_content-1、single_content-2、request_keys-2。
所有起点/合同/保护/私有测试与前批一致；均已暴露，非holdout或并行A/B，不估计因果提升。
预算不变：12请求、3有效编辑+3写后检查、1起点、12格式准备、2协议恢复、2no-op、900秒、4096输出；
Reviewer16请求/4错误/600秒/4096输出；Qwen/Muse24576，单驻留，不启动Explorer/Coordinator。
四格4/4且逐题2/2、无代写/语义辅助/安全漂移才有精确暴露重复资格。
普通失败HOLD但跑完固定诊断；基础设施/安全/保护漂移/时间或weekly20%停止；不补跑冲失败。
外层单格2220秒、批次10800秒不变。旧Reviewer负控仍有效，不因clean任务通过取消。
R4 HOLD/R5未准入，不能从本批直接启用Coordinator或生产。
