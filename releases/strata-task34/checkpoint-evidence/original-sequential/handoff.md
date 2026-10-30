# 连续使用验证：HOLD，输入绑定错误在live后才被拦住

U1 Coder9请求/3编辑，完整配置检查通过（工程571通过）；fresh Reviewer6请求、
两次协议恢复额度耗尽，三个意图PASS报告均未通过绑定，所以无正式PASS、无Primary接受。
U2按已登记依赖门槛NOT_RUN，不计调查失败。原输出、失败和分母不改写。

最早确认偏离点是Primary合同compatible把implementation_ref绑定到类ToolRegistry。
现有citation-binding.statement_lines只支持函数/方法/赋值，明确排除ClassDef；即使
读完整类或引用class声明/方法内部也无法满足该ref。prepare却接受了这个已有类引用。
这是Primary输入错误叠加宿主前置校验缺口，不是该次Coder没有实现功能或Reviewer
语义错误放行。模型重复提交不能修好这个合同。没有通过重抽Reviewer追求PASS。

下一窄修复只在隔离候选为prepare增加现有class引用负控，提前要求Primary选择具体
方法；不增加class PASS、不变权限/模型/预算/语义验收。旧task.33和本批HOLD均保留，
新候选与正确绑定后的输入另行登记，不重写本档案或给旧账本充值。
