# 2026-10-22：显式安装版本的有限试用交接

结论：**限定范围受监督试用PASS；通用生产HOLD。** 停止线是用户最新指定的
weekly used60%，本轮32%开始，最近实测35%。本阶段注册内容已完成，无live执行中。
不修改默认配置、不commit/push、不修改兄弟仓库、不换模型、始终单模型驻留。

统一证据根：`benchmarks/work/harness-convergence/`。
汇总裁决为 `packaged-release-20261022-1/decision.json`；候选源码逐文件hash在同目录
`candidate.json`。不要把下文成绩相加成“通用成功率”，也不要覆盖旧HOLD。

## 已实际验证的东西

| 批次 | 固定结果 | 解释边界 |
| --- | --- | --- |
| `packaged-profile-live-20261022-1` | 安装版本6/6完整链接受；Coder6请求/6编辑，Reviewer8请求/2协议纠正 | 三道已暴露局部改动各2次，不是新题迁移 |
| `project-live-20261022-2` | 实际完整项目快照2/2接受；每格151独立测试及全静态检查通过 | 同一已暴露身份归一化需求，不是外部服务部署 |
| `reviewer-profile-screen-20261022-3` | 正控1/1；真退化拒绝2/2；3请求、0协议错误 | 脚本产生真实canonical草稿，Coder模型零调用；明确合同边界，不证明未知缺陷检出 |
| `explorer-locator-profile-20261022-1` | 两道不同问题证据定位2/2；每题6动作、0协议错误 | 已知路径和字面锚点，Primary准备不为零；只取证，不作因果判断 |
| `packaged-chain-profile-20261022-1` | Coordinator正确拆分；两单元接受；最终6项公私集成及全静态profile通过 | 已合格stable_unique→render_tags快照链的当前安装版本兼容，不是新语义迁移 |

每个批次有registration、逐格原始结果、Primary裁决、decision；部分交接为handoff.json。
完整项目只复制兄弟仓库已提交HEAD，没混入或修改其工作区现有改动。
两次真实项目Coder都一次有效编辑；不能拿简单成功证明困难多轮恢复。

离线证据分开计算：初始产品profile44项、Explorer及profile104项、当前桥接57项；均有
重叠，不相加。全runtime回归663通过、18夹具setup错误；显式预加载已有fixture插件后
78通过，其中包含原18错误项及60重叠项。`offline-evidence.json`验证18项逐一覆盖；
原XML保留，没改断言、没宣称第一次全绿。

## 从失败中确认的改动

1. **Coder输出协议。** 旧strict schema含oneOf，但真实响应仍两次产生replacement数组；
   同输入flat必填string两次按类型输出。新默认关闭`flat-v1`使用
   `{"kind":"replacement|blocked","content":"..."}`，宿主严格解码到原内部协议。
   不靠服务端schema替代本地类型/重复key校验；编辑位置/hash/签名/AST/范围/检查不变。
   旧ASCII语义修复仍失败，不能用协议改善把它改记成功。
2. **加载确认。** Muse实际已驻留但CLI360秒未返回；原生API可确认正确唯一模型、
   context和并发。`api_verified`只允许CLI TimeoutExpired后继续原全部驻留校验；
   未就绪仍拒绝，不加模型调用或扩预算。旧设施失败另存，一次运输恢复不重抽语义PASS。
3. **实验准备。** 全项目manifest漏包初始化，导致正确实现虽过151独立测试却不能交接；
   第一批0/2保留，修完整批准源码集合后先真实离线重放再建新批。
   Reviewer正负控初次被offline inspection占用一次派发，下一次准备又错误依赖unit
   模式生成request；均零实质模型审查，记录保留。最终用Coder-only真实档案及产品原
   handoff verifier生成request，未删锁或绕过防重放。
4. **Explorer义务和能力边界。** 旧文字启发式将“no code/test changes”当成要求测试证据，
   TRACE命中的测试路径又触发必填。新增Primary显式布尔义务，默认推断不变，cache绑定
   义务。缺少实际读取的引用给出补读提示；source-only证据齐备后可用已有一次报告恢复，
   缺TRACE/regex/必需路径不绕过。但叙述调查随后仍在JSON尾字符、缺报告字段上失败；
   结构诊断成功那次结论正确，却把实际220行的revision赋值引成219行。
   **runtime success没有记作因果调查合格。** 复用已有定位模式后，宿主准确摘录
   callee215及argument220、字段26；另一题摘录真实request_hash及canonical_json定义。

## 使用资格，不是“任意项目复制即用”

显式选择的关键配置（不是完整配置，不能省略原可信packet、capture和检查profile）：

```json
{
  "bounded_execution_profile": "bounded-v1",
  "bounded_compatibility_profile": "flat-v1",
  "model_load_ack_policy": "api_verified"
}
```

按AGENTS.md走`local-bounded-unit.py`，宿主自动完整写后检查，再fresh Reviewer，
最后Primary验收。默认关闭；安装不自动选择新profile。不是旧local-code动作循环的改名。
Coder保持Qwen、Reviewer及Coordinator保持Muse、Explorer保持OSS；context分别
24576、24576、32768，单驻留。Coder保持12请求、3有效编辑/3写后检查、900秒及4096输出；
起点检查独立。Reviewer保持16请求/4共享错误/600秒及4096输出；不重抽相同代码求PASS。
原有总时限、无改动/重复循环和安全停止规则继续生效。

- Explorer只路由已知路径/符号的定位；可信配置可设`explorer_mode: "locate"`及
  必需citation paths/source anchors。叙述诊断仍不合格，不能将模型主张当实际证据。
- Coder只路由已资格化局部单函数任务。现有模块大小、签名/import、严格四检查profile及
  canonical观察绑定限制没放开；任意跨文件、类方法或复杂算法不因本成绩自动准入。
- Reviewer发现问题仍由Primary逐finding裁决；未确认意见自动变成Coder修法的历史0/4
  候选不采用。不因为测试绿就省略独立最终验收。
- Coordinator仅在Primary已批准合同/风险/源码及任务族下生成分解；本轮实际生成了
  两个单元及依赖，不只测试调度。但合同、测试、位置和分类由Primary给出。
  单元内`coordinator_enabled`仍关闭；外层显式快照桥不等于全局自动派工。

## 停点与剩余边界

本阶段有限门已闭合，不再用不断补题作为隐含要求。旧R4、困难ASCII语义恢复、
叙述Explorer和Reviewer未知边界检出仍保留原结论，不能宣称通用E/C/R稳定。
后续使用应在上述范围内；出现同类语义失败按既定进展/质量门停止或交Primary，
不是无限加提示和retry。扩大任务族或同工作区连续执行需独立资格证据。

Primary本轮承担不少一次性协议/安装/夹具修复，也持续承担合同/测试/定位/分类准备、
分解审批、实际diff和最终审查。无代写不等于无协调成本。本地执行时间见各metrics，
加载成本部分单列、其余unknown；云tokens和Primary主动时间unknown。
没有Primary-only对照，**不声称已减少多少云usage**；weekly used只是停止线观测。
