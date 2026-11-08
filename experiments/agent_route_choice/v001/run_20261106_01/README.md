# 十条双调用：GLM 与本地 Qwen32B 准备批次

2026-11-06：[第3次可视化导出](exports/run_20261106_03/README.md)完成。按v002布局展示支路/选择，加入完整737帧原录像、同步地图双滑条和一键回Crossing；十条逐帧验证及截图审阅通过。原始回答与此前导出均未改动。

更新时间：2026-11-06。Qwen32B十条/20次响应已完成，9条协议有效、1条自相矛盾未通过校验；语义复核未完成，HTML已导出，GPU已释放。GLM因1113账户无额度停止，等待用户处理。

目的与协议见 [v001 README](../README.md)。固定旧 Oracle 十条，来源均为原 seed2 录像；每模型20次逻辑调用，共40次。准备源码基于 Git `0a805dfcf4457f80300822abb4eff7cabba43aae` 加本轮新增未提交文件；实际源码与未提交差异保存在准备目录，不把该 HEAD 当作原录像的历史代码版本。

当前准备目录为 `outputs/agent_route_choice/v001/preparation_20261106_04/`，正式两组输出预定为 `outputs/agent_route_choice/v001/run_20261106_01/{glm,qwen32b}/`。启动前登记：固定原十条；实际PID、GPU与有效回答证据在本批启动记录中补齐。01至03版准备记录保留；04版切换Qwen32B与GLM十进程，prompt仍是03版的第2稿。第2稿按用户要求更新prompt：两次描述输出均为英文；第一调用先定义Crossing，再说明支路是通向不同空间的选择，并允许从视角受限的局部线索合理推断。上述准备阶段没有运行推理。

## 仅准备与检查

在仓库根目录执行；已存在目录不能覆盖，重准备须使用新编号：

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_agent_route_choice.py --output outputs/agent_route_choice/v001/preparation_YYYYMMDD_NEW
python3 -B scripts/run_agent_route_choice.py --prepared outputs/agent_route_choice/v001/preparation_20261106_04 --model glm
python3 -B scripts/run_agent_route_choice.py --prepared outputs/agent_route_choice/v001/preparation_20261106_04 --model qwen32b
python3 -B -m unittest discover -s tests -p 'test_agent_route_choice.py' -v
```

两个不带 `--execute` 的入口只检查哈希并打印计划，不联网、不读密钥、不查询或加载 GPU。

## 正式启动命令（用户已授权）

GLM 会交互式无回显读取密钥；不将凭据放入文档或 shell 命令：

```bash
python3 -B scripts/run_agent_route_choice.py --prepared outputs/agent_route_choice/v001/preparation_20261106_04 --model glm --output outputs/agent_route_choice/v001/run_20261106_01/glm --execute
```

Qwen的 `GPU_A GPU_B` 必须替换为启动时刚核验的两张空闲GPU编号；该入口自行启动并清理本组模型服务：

```bash
python3 -B scripts/run_agent_route_choice.py --prepared outputs/agent_route_choice/v001/preparation_20261106_04 --model qwen32b --output outputs/agent_route_choice/v001/run_20261106_01/qwen32b --gpus GPU_A GPU_B --execute
```

两组各自生成 `manifest.json`、`status.json`、逐样本两次请求摘要与原始回答、校验后答案、网络尝试记录、待填写 `review_template.json` 和离线 `route_choice_review.html`。本地组另有服务命令、日志、准入及清理记录。中断不覆盖；后续重跑另建编号。

## 复核与评分

运行完成后复制评分模板为新的复核文件，逐样本映射两个模型各自的支路编号，填写复核者/图像证据/理由，再运行：

```bash
python3 -B scripts/report_agent_route_choice.py score --prepared outputs/agent_route_choice/v001/preparation_20261106_04 --run outputs/agent_route_choice/v001/run_20261106_01/glm --review outputs/agent_route_choice/v001/run_20261106_01/glm/review_completed.json --destination outputs/agent_route_choice/v001/run_20261106_01/glm/summary.json
```

Qwen 同理。两组完成后用 `export_agent_route_choice.py --runs` 显式列出两组运行目录，导出到新的 HTML 路径；模型切换保持同一样本与同一帧。

## 结果、限制与下一步

准备阶段没有实验结果；实际启动与回答证据见下方追加记录。十条均具备离线输入，每条8张真实RGB，共80张；第一调用4图，第二调用8图。第5条标注片段结束于44帧（终止帧），实际输入截到43帧；未复用终止RGB。第6条历史决策帧离原C约0.95米，按原标注保留，不为改善画面而换点。

准备阶段的假响应只用于临时目录中的 CPU 单元测试，不写入正式结果。输入预览的地图/标签仅供审阅；实际模型请求不含这些信息。有限历史视角、预先知道“上次走错”、旧案例选择及辅助标注的限制见版本 README。

产物：[可离线打开的输入预览](../../../../outputs/agent_route_choice/v001/preparation_20261106_04/input_review.html)、[逐条输入盘点](../../../../outputs/agent_route_choice/v001/preparation_20261106_04/input_audit.json)、[冻结源码与文件哈希](../../../../outputs/agent_route_choice/v001/preparation_20261106_04/manifest.json)、[准备状态](../../../../outputs/agent_route_choice/v001/preparation_20261106_04/status.json)。CPU裁帧使用现有VLNVerse环境；中文字体导出使用现有StreamVLN环境，无新增依赖安装。

原03版第2稿prompt已完成22项CPU测试、两组dry-run及真实浏览器10条/140次图像检查，页面错误和外部请求均为0。此次新增十进程隔离与双卡准入检查，24项CPU测试通过；03版输入及prompt保持不变。04版冻结后重新核验哈希和两组dry-run，结果存入 preparation_20261106_04/launch_checks.json。

用户已明确开始并要求首批正常后停止人工持续监控。GLM设十进程/每样本两调用；Qwen32B使用双卡BF16 TP=2，单请求。进程完成自动导出HTML、保留待复核表；Qwen结束自动释放自己的服务。语义正确率须后续依据真实输出复核，不用结构校验冒充正确选路。


2026-11-06T03:53:41.853390+00:00 自动收尾：Agent选路 run_20261106_01/glm；状态 `failed_partial`，完成两次调用 0/10 条，HTML导出 True，GPU释放 不适用。结果 `outputs/agent_route_choice/v001/run_20261106_01/glm`；语义正确率仍待复核。


2026-11-06 启动异常：GLM首次十进程30次网络尝试均为HTTP429，未获得回答；原 `glm/` 记录及HTML完整保留。恢复使用新 `glm_retry02/`，冻结准备05版，十条/十进程/模型参数/prompt不变，仅网络最多8次尝试与30–120秒抖动退避，并保存服务端错误代码。Qwen32B继续使用04版在GPU 0、3加载；未因GLM异常重启Qwen。


2026-11-06T03:59:36.574355+00:00 自动收尾：Agent选路 run_20261106_01/glm；状态 `interrupted`，完成两次调用 0/10 条，HTML导出 True，GPU释放 不适用。结果 `outputs/agent_route_choice/v001/run_20261106_01/glm_retry02`；语义正确率仍待复核。


2026-11-06 GLM启动阻塞已确认：服务端错误1113“余额不足或无可用资源包，请充值”。首次glm/及恢复glm_retry02/均无有效回答；已正常停止本轮恢复进程，不再重复请求，等待用户充值或替换key。Qwen32B原批继续，GPU 0、3，监督PID3194485；运行状态以 outputs/agent_route_choice/v001/run_20261106_01/qwen32b/status.json 为准。


当前运行对应关系：

| 组 | 冻结准备 | 输出目录 | 状态 |
| --- | --- | --- | --- |
| Qwen32B | preparation_20261106_04 | run_20261106_01/qwen32b | 模型初始化中；监督PID3194485，服务PID3194661，GPU 0、3 |
| GLM首次 | preparation_20261106_04 | run_20261106_01/glm | 10进程，30次HTTP429，0回答；已结束并导出 |
| GLM恢复 | preparation_20261106_05 | run_20261106_01/glm_retry02 | 10进程，20次尝试，0回答；明确1113无额度，已停止并导出 |

04版24项CPU测试通过；05版新增429退避、Retry-After与脱敏错误记录验证，共25项通过。两个准备版本输入及prompt SHA256一致。32B启动时使用的是04版冻结源码，运行期间修改的GLM恢复入口不会改写其已加载的Python代码；源码及git差异各自保留。


2026-11-06 启动验证完成：Qwen3-VL-32B-Instruct在GPU 0、3正常推理；验证时sample_01两次调用均完成，sample_02已开始，第二次请求的清单与第一次实际回答哈希完全一致。现在停止人工持续跟踪，余下任务由后台完成，自动导出HTML并释放本轮GPU服务；语义正确率仍待复核。GLM十进程因账户无额度（1113）已停止，0有效回答，等待充值或新key。

- [启动验证证据](startup_verified.json)
- [Qwen动态状态](../../../../outputs/agent_route_choice/v001/run_20261106_01/qwen32b/status.json)
- [首条第一次回答](../../../../outputs/agent_route_choice/v001/run_20261106_01/qwen32b/cases/sample_01/call1_answer.json)
- [首条第二次回答](../../../../outputs/agent_route_choice/v001/run_20261106_01/qwen32b/cases/sample_01/call2_answer.json)
- [GLM账户阻塞记录](glm_account_blocker.json)


2026-11-06T04:16:08.990844+00:00 自动收尾：Agent选路 run_20261106_01/qwen32b；状态 `failed_partial`，完成两次调用 9/10 条，HTML导出 True，GPU释放 True。结果 `outputs/agent_route_choice/v001/run_20261106_01/qwen32b`；语义正确率仍待复核。


2026-11-06 当前进度：Qwen32B原十条全部返回两次响应（20/20次，04:16 UTC结束），其中9条通过协议校验；sample_07在第二次回答中将B1判为错误并排除，却又选择B1，保留原始回答并标记无效。尚未语义复核，9条有效回答不代表9条选路正确。离线HTML已导出，本轮服务与子进程全部退出，GPU 0、3已释放。GLM仍因账户无额度（1113）停止，0有效回答，等待充值或新key。

[本次进度核验](progress_check_20261106_0434.json) · [Qwen离线回放](../../../../outputs/agent_route_choice/v001/run_20261106_01/qwen32b/route_choice_review.html) · [第七条原始回答](../../../../outputs/agent_route_choice/v001/run_20261106_01/qwen32b/cases/sample_07/call2_response.json)。下一步为真实输出语义复核；GLM账户恢复后另建运行编号，不覆盖失败记录。


2026-11-06 中文可视化交付：20份Qwen回答和10条任务的忠实中文译文，原始英文可切换，第七条矛盾完整保留；GLM标为无额度/无回答。27项CPU与浏览器280次图像检查通过。[离线HTML](../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.html) · [本次导出记录](exports/run_20261106_01/README.md)。无新推理，语义正确率待复核。


2026-11-06 按用户反馈重做选路可视化：首屏固定判断时Crossing原帧，明确逐条支路与最终选择；完整回放折叠，第七条矛盾保留。十条、31支路、10选择及固定帧一致性检查通过。 [新版HTML](../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.html) · [导出记录](exports/run_20261106_02/README.md)。


2026-11-06：按用户要求，将上午无全景Qwen32B十条按同步主视图/俯视地图模板重新导出至 `outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_04/crossing_v001_timeline_zh.html`，约55.4 MiB。20份原答、31支路、中英切换及第7条矛盾完整保留；十条全部737帧浏览器检查通过，无新模型调用。导出记录：`experiments/agent_route_choice/v001/run_20261106_01/exports/run_20261106_04/README.md`。
