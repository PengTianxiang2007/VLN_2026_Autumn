# v003 七例局部纠正命令生成

2026-11-07；状态：准备后台启动。用户授权按已确认prompt跑一遍；只生成命令，不恢复已取消的导航部署队列。

目的：限制纠正路径在关键分支附近，允许必要的靠近、转向、少量前进；不按句子数裁剪，不重新选路。

配置：样本17/18/19/20/28/29/34；昨晚human_v002/run_20261107_01已选方向与route_description原样复用，C分别66/15/117/6/34/39/0。每例提供唯一C帧RGB（哈希核验），不提供原任务全文或未来帧。prompt为用户确认的v003原文，checkpoint_context说明所附图是起始姿态画面；没有人为补写路线。

Qwen3.8-27B-FP8，既有.runtime/crossing_vllm27，temperature0，seed20261107，thinking=false，max_tokens512，单并发7次请求，不自动重试。GPU0三次低负载/显存/主存准入后加载，保留他人4234MiB服务。后台结束/失败/取消自动清理自己的服务并记录GPU；不保持空载服务。

实际Git/源码快照与哈希在manifest.json、source/；未提交修改在workspace.patch及workspace_status.txt。启动前7例图像哈希、prompt原文一致、请求构造和AST检查通过；无模型结果。

启动：`python3 -B scripts/run_local_correction_commands.py --prepared experiments/agent_recovery/r2r_v003/run_20261107_01 --output outputs/agent_recovery/r2r_v003/run_20261107_01 --gpu 0 --allow-shared-gpu`。

输出：outputs/agent_recovery/r2r_v003/run_20261107_01；status.json记录状态，instructions.json为原始生成命令，cases/保存完整请求/原答/输入审计，server.log为服务日志。自动追加completion.json与最终记录。不生成HTML。

限制：命令短并不证明局部路线正确，语义待复核；无StreamVLN实际执行、无仿真或导航成功率。按用户要求只核验后台启动，不持续跟踪。

后台已启动，主管PID 1908790；一次启动检查后停止人工持续跟踪，当前实际阶段见status.json。


2026-11-07 v003七例局部纠正命令后台收尾：状态`complete`，完成7/7，GPU释放True；原答语义待复核，无导航或仿真。产物 `outputs/agent_recovery/r2r_v003/run_20261107_01`。
