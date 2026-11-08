# 人工34个错误点 / GLM-5.3-Flash / 无全景多进程

2026-11-06：已授权新增GLM批次，并明确使用并行进程。状态：准备中。使用用户在对话中提供的凭据；凭据不记录在本文件或任何配置中。本轮沿用不做HTML的要求。

## 输入与方法

完全复用Qwen的`outputs/agent_route_choice/human_v001/preparation_20261106_01`，34个人工错误点、33条任务、最多68次逻辑请求。人工帧不移动；原v001的最多4张Crossing上下文+4张错误经历、原1.2m错误片段端点规则、英文prompt、完整第一轮JSON传递、仅排除错误支路、schema与校验器均不变。5个首帧点没有虚构历史。具体数据边界见[Qwen批次](../run_20261106_01/README.md)。

仅更换模型后端与原GLM配置：`glm-5.3-flash`、low思考、输出32768、temperature0、JSON object模式。导航来源seed2，云后端不伪造一个API未支持的请求seed。GLM不消费Qwen回答。原协议的空route_description等校验保持原样，协议无效回答也原样保存，不做语义重试。

## 并发与生命周期

最多10个独立worker进程，每个样本内两次请求顺序执行。首个真实样本兼作可用性核验并计入34点；收到完整响应后自动铺开其余33点，始终最多10个在途worker。普通单例失败不停止其他例；明确认证错误或1113账户无额度立即停止本轮，避免对34例重复发送必败请求。读取超时60秒、每请求deadline1200秒、最多8次网络尝试，30–120秒指数退避与抖动；批次上限2小时。

凭据通过关闭终端回显后的stdin进入短期launcher，再经匿名管道传入主管；worker由fork继承内存。凭据不进入argv、环境、配置或模型请求内容。日志仅记录脱敏服务端错误，不保存Authorization头；返回内容防止意外反射凭据。关闭core dump，结束时清理所有本轮worker并检查文本产物未含凭据；不宣称清除聊天中的用户原消息。无GPU服务、不干扰仍运行的Qwen。

## 版本和启动

公共入口`run_human_route_choice_glm.py`新增；原有Qwen冻结源码不改。启动时记录Git、工作区差异、实际源码快照和输入哈希。

```bash
python3 -B scripts/run_human_route_choice_glm.py --launch --prepared outputs/agent_route_choice/human_v001/preparation_20261106_01 --output outputs/agent_route_choice/human_v001/run_20261106_02/glm --registration experiments/agent_route_choice/human_v001/run_20261106_02/registration.json --config experiments/agent_route_choice/human_v001/run_20261106_02/model.json
```

启动器确认关闭回显后从标准输入接收凭据，不使用shell命令传递密钥。不能将用户原文中的凭据复制到命令文件。

## 产物与解释

输出为`outputs/agent_route_choice/human_v001/run_20261106_02/glm`，保存manifest/status、逐点两次请求摘要与原始响应、transport日志、worker列表、summary、请求重建审计和清理证据。无HTML。完成/失败后自动追加本README和状态索引。

完成调用、协议有效与语义选路正确分别记录。正确支路人工复核仍未建立，不把有效JSON或选择率当作正确率。验证正常并行调用后停止人工持续跟踪。


2026-11-06T15:12:48.814078+00:00 GLM-5.3-Flash人工34点无全景批次收尾：`blocked_account`，保存0/68次回答，协议有效0/34。worker全部退出True，凭据未落盘True，本轮无HTML；语义正确率待复核。结果 `outputs/agent_route_choice/human_v001/run_20261106_02/glm`。


2026-11-06T15:14:24.003697+00:00 账户阻塞已核验：首个GLM请求返回HTTP429 / code1113“余额不足或无可用资源包，请充值。”仅1次请求、0次模型回答，未展开10进程队列；主管及首个worker已退出。凭据只经无回显stdin与匿名管道进入内存，运行文本扫描未发现凭据，未生成HTML。等待用户充值或替换有额度的key，不自动反复请求；本地Qwen继续。
