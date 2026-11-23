# v006 Qwen 离线复评 C35、C38

2026-11-20 16:19:11–16:25:01 UTC，GPU 3 Qwen 完成 C35（`kujiale_0234_23_1`）和 C38（`kujiale_0234_34_4`）。两例共 7 轮，6 次 `consistent`、1 次 `deviated`，全部通过校验。v005 在两例均未报警。v006 在 C35 仍然漏报，在 C38 提前误报。[运行状态](../../../../outputs/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/status.json) · [全部区间与帧号](../../../../outputs/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/v006_results.json)

复用 GPU 3 上的 Qwen3.8-27B-FP8 服务 `route53-qwen27b`，使用中文 v006、temperature 0、top_p 1、seed 2、max_tokens 8192，关闭 thinking。沿用 seed 2 冻结轨迹的指令、节点及前视 RGB。从各自的首节点重新建立进度，每节点一次调用，首次有效报警即结束该条。完整观测与参考路线用于事后归因。运行入口保存实际 Git 提交、源码快照、Prompt 哈希和请求参数。[运行清单](../../../../outputs/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/manifest.json)

## C35

五轮均返回 `consistent`，到终止帧 F44 仍无报警。S03（F4→F14）将竖条装饰板认作指令中的绿色装饰板。S04（F14→F30）在理由中写明圆形装饰位于床侧墙面，又据此认定已到达走廊尽头并按要求左转。S05 凭淋浴房、窗和卫浴设施的位置确认终点。v005 同样漏报，但在 S03 还保留了是否身处目标走廊这一疑点。离线归因在 F37 确认机器人进入卧室套内浴室，指令指定的是经外部走廊抵达的另一间浴室。[v006 五轮原答与进度](../../../../outputs/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C35/result.json) · [v005 对照](../../../../outputs/deviation_progress/v005/run_20261120_03_remaining47/run/cases/C35/result.json) · [离线归因](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/evaluation/episodes/kujiale_0234_23_1.json)

## C38

初始化 S01 返回 `consistent`。S02（F0→F5）引用“右转进入走廊”，描述六帧主要是视角转动、尚未进入走廊，理由又提到后续的盆栽和厨房未出现。原答将这些未完成事项判为 `deviated`，未指出实际走入了哪条冲突通路。该回答格式有效，系统记录回退目标 S01（F0）后结束本例。离线标注的错误分支在 F72–F75，v006 提前误报，余下五个节点未评审。v005 和 v5.1 都审至 F112，全程无报警。[v006 报警原答](../../../../outputs/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C38/S02.response.json) · [v005 与 v5.1 既有对照](../../v005.1/run_20261120_01_qwen_gpu3_c38/README.md) · [离线归因](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/evaluation/episodes/kujiale_0234_34_4.json)

## 复现

工作树基于 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，实际调用的中文 Prompt SHA256 为 `d3fb3fe87b61fa1ff51ba45480721f4d5e20eed2b1c8f1fff0e259f99bbae3ea`。运行目录保存实际源码和两个案例的逐轮请求、原答与累计进度。在仓库根目录执行，复现时替换成新的输出目录。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004.py \
  --version v006 --cases 35 38 \
  --qwen-service outputs/model_services/qwen27b_gpu3_20261120_02/service.json \
  --output outputs/deviation_progress/v006/run_20261120_01_qwen_gpu3_c35_c38
```
