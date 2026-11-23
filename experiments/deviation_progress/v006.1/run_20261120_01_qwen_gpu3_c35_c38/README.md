# GPU 3 Qwen，v6.1 离线复评 C35、C38

2026-11-20 16:52:59–17:00:22 UTC，GPU 3 Qwen 完成 C35（`kujiale_0234_23_1`）和 C38（`kujiale_0234_34_4`）。两条分别从首节点建立 v6.1 的进度，10 次实际调用全部通过校验，其中 9 次 `consistent`、1 次 `deviated`。C35 在 F14 报警，C38 取消了 v6 的 F5 误报，但漏报 F72–F75 的错误分支。这次运行仅包含两条轨迹。[v6 既有结果](../../v006/run_20261120_01_qwen_gpu3_c35_c38/README.md) · [本次运行状态](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/status.json) · [逐轮判定和实际帧号](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/v006.1_results.json)

使用 GPU 3 的常驻 Qwen3.8-27B-FP8（`route53-qwen27b`）、冻结 Route53 去重后节点与原生前视 RGB。轨迹和请求 seed 2，temperature 0，top_p 1，max_tokens 8192，关闭 thinking。每节点一次调用，首次通过格式校验的偏航判定结束该条评审。运行目录保留实际 Git 提交、源码快照、Prompt 哈希、每轮输入、原答与累计进度。[运行清单](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/manifest.json)

## C35

v6 全程未报警。v6.1 在 S02 仍把“沿走廊直行”记为已完成，原答的观察只描述相机转向柜体。S03（F4→F14）返回 `deviated`，认为机器人从衣柜区走向条纹隔断、偏离应沿行的走廊，回退目标为 S02（F4）。这一报警区间落在离线标注的 F0–F37 选路区间内，B 恰为标注的估计决策帧 F14，确认进入错误浴室的时刻是 F37。[S02 原答](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C35/S02.response.json) · [S03 报警原答](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C35/S03.response.json) · [离线归因](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/evaluation/episodes/kujiale_0234_23_1.json)

原答另声称“穿过该隔断，进入了一个更开阔的房间”。本轮前视从柜体转向竖条墙面、花瓶和更开阔的室内区域，跨越隔断的通行证据不足。事后位姿记录显示 F4→F14 的水平净位移约 0.41 米，净朝向变化约 104°。这两个数值用于复核，模型只看到前视图。[F4 输入](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/observations/kujiale_0234_23_1/000004/policy_front.png) · [F14 输入](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/observations/kujiale_0234_23_1/000014/policy_front.png) · [离线位姿记录](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/provenance/capture_records/kujiale_0234_23_1.jsonl)

## C38

v6 于 F0→F5 报警并停止。v6.1 在该轮回到 `consistent`，正确保留“右转进入走廊”为当前任务。S05（F64→F74）按原文引出了左侧高盆栽和右侧开放厨房，但将画面左侧开口推测为可能的厨房，承认地标细节尚不清晰，随后仍把两项经过关系都写进“已完成”。S06 只审进卧室和到床边，直接将全部路线记为完成。最终七轮都是 `consistent`，到 F112 为止无报警，漏报离线标注的 F72–F75 错误分支。[S02 原答](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C38/S02.response.json) · [S05 原答](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C38/S05.response.json) · [七轮进度与判定](../../../../outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38/run/cases/C38/result.json) · [离线归因](../../../../outputs/offline_route_dataset/v001/run_20261118_01/dataset/evaluation/episodes/kujiale_0234_34_4.json)

## 复现

实际采用的 v6.1 中文 Prompt SHA256 为 `4cc56cc8087ef413c0790cbb7d82efcd9522cae33620f82c0413b480a0394def`。在仓库根目录执行，复现时指定新的输出目录。

```bash
PYTHONPATH=.:scripts .runtime/crossing_vllm27/bin/python -Bu scripts/run_deviation_progress_v004.py \
  --version v006.1 --cases 35 38 \
  --qwen-service outputs/model_services/qwen27b_gpu3_20261120_02/service.json \
  --output outputs/deviation_progress/v006.1/run_20261120_01_qwen_gpu3_c35_c38
```
