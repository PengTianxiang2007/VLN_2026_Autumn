# GPU 3 双版本评审接续

2026-11-21 04:37 UTC 核对：v6.1 于 04:00:22 UTC 完成。新跑 51 条共 226 轮（180 consistent、44 deviated、2 格式错误），加上复用 C35、C38 的 10 轮，完整 53 条为 236 轮、189 consistent、45 deviated、2 格式错误，45 条轨迹报警。两版全样本队列均完成，主管 PID 619682 已退出。结果为模型输出统计，尚未逐条核验报警准确率。

完整结果及逐例来源：`outputs/deviation_progress/v006_pair_route53_20261121_01/v006.1_all53.json`。原答与实际请求仍保留在对应 `source_run` 下。v6.1 尚未加入已发布的 v3/v5/v6 对比网页，后续可复用现有结果导出，无需重跑模型。本次仅状态核对与登记，没有修改任务或模型服务。

2026-11-21 01:12:46 UTC，v6 补齐 C50–C53，完整 53 条共 253 轮，197 consistent、47 deviated、9 格式错误。47 条轨迹触发有效格式的报警，C04、C18、C23、C35、C40、C41 全程未报警。上述报警数量尚未逐条与离线标注核验。v6.1 自动接续，核对时正在 C03，含既有两条已完成 4/53。[v6 完整汇总及来源](../../../../../outputs/deviation_progress/v006_pair_route53_20261121_01/v006_all53.json)

九次格式错误中，五次将 uncertainties 写成对象，协议要求数组；两次英文引文未逐字对应原指令；一次 consistent 缺合法累计进度；一次 C50／S03 输出达到长度上限。前八份可解析原答的 verdict 全为 consistent。C50 的截断回答没有可解析的完整 JSON，S05 随后返回 deviated。C51、C52、C53 均在 S03 返回 deviated。C38 已知的 F0→F5 提前报警和 C35 漏报仍包含于本组结果。

2026-11-21 00:56:42 UTC，后台接续进程 PID 619682 已启动。C50 的 S01、S02 从旧回答恢复，S03 于 00:56:43 发出真实请求。GPU 3 服务日志确认请求运行中，生成速度约每秒 18 个 token。按用户要求在正常生成后结束人工跟踪。[接续清单](../../../../../outputs/deviation_progress/v006_pair_route53_20261121_01/plan.json) · [日志](../../../../../outputs/deviation_progress/v006_pair_route53_20261121_01.log) · [v6 当前状态](../../../../../outputs/deviation_progress/v006_pair_route53_20261121_01/v006/status.json)

2026-11-21，用户授权继续中断的 v6、v6.1 离线评审。接续使用新的输出目录。v6 复用 C01–C49 的完整结果，恢复 C50 的前两轮已返回回答，从 S03 继续，随后跑 C51–C53。v6.1 复用原有 C35、C38，顺序跑其余 51 条。两组最终各覆盖冻结的同一批 53 条轨迹。[原批次](../README.md)

沿用 GPU 3 上的常驻 Qwen3.8-27B-FP8、原中文 Prompt、seed 2、temperature 0、top_p 1、max_tokens 8192 和关闭 thinking。每条轨迹的有效节点、最多七帧采样和首次报警停止协议沿用历史运行。已完成案例的来源路径写入新清单。C50 的旧回答在请求内容、图像、Prompt 和参数匹配时复制，按原回答恢复进度。

服务日志显示，旧请求直到超时前仍以约每秒 18 个 token 生成。本地模型请求的等待上限由 300 秒延长为 900 秒，以容纳已有的 8192 token 生成上限。临时传输错误最多额外重试三次，间隔 15、30、60 秒。每次失败的请求和响应都保存到相应案例的 `transport_attempts/`。HTTP 200 后的模型回答沿用原格式校验与状态规则。全部重试耗尽时记录失败并退出。接续记录和实际源码在新目录保存。

在仓库根目录启动。

```bash
nohup env PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu \
  experiments/deviation_progress/v006.1/paired53_20261120_01/run_pair.py \
  --resume-from outputs/deviation_progress/v006_pair_route53_20261120_01 \
  --run-dir outputs/deviation_progress/v006_pair_route53_20261121_01 \
  >> outputs/deviation_progress/v006_pair_route53_20261121_01.log 2>&1 < /dev/null &
```

CPU 模拟已验证复用两轮原答、超时重试和失败记录保存，现有请求与状态接口的两项测试通过。确认模型正常生成后，按用户要求结束人工跟踪。v6 完成后同一后台进程自动调用 v6.1。新目录各版本下的 `status.json` 保存运行状态，根目录的 `*_all53.json` 在对应版本完成时汇总新旧结果及来源。
