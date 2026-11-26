# Codex 电视前导航的逐调用时间线

UTC 为仿真端收到调用和回图完成的时间。帧号从本次 F38 起连续递增。模型响应序号来自当前会话的计量响应 ID，同一序号内的操作由同一次模型输出发起。

| 调用 | 模型响应 | 开始 UTC | 完成 UTC | 调用 | 帧 | 物理 tick | 水平移动 cm | 朝向变化 ° | 返回前视图 | 图像进入模型上下文 |
|---:|---:|---|---|---|---|---:|---:|---:|---|---|
| 1 | 2 | 12:08:55.659 | 12:08:55.848 | 主动观测 | 38→38 | 0 | 0.0 | +0.0 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00001.png) | 是 |
| 2 | 3 | 12:09:01.198 | 12:09:01.800 | 前进 | 38→39 | 50 | 2.2 | +0.3 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00002.png) | 是 |
| 3 | 4 | 12:09:07.576 | 12:09:08.081 | 前进 | 39→40 | 50 | 7.3 | -1.8 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00003.png) | 是 |
| 4 | 5 | 12:09:17.502 | 12:09:18.194 | 前进 | 40→41 | 50 | 14.6 | +0.2 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00004.png) | 是 |
| 5 | 5 | 12:09:18.589 | 12:09:19.110 | 前进 | 41→42 | 50 | 18.3 | -0.6 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00005.png) | 是 |
| 6 | 5 | 12:09:19.423 | 12:09:19.954 | 前进 | 42→43 | 50 | 21.1 | +1.0 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00006.png) | 是 |
| 7 | 6 | 12:09:25.167 | 12:09:25.661 | 前进 | 43→44 | 50 | 23.1 | -0.8 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00007.png) | 是 |
| 8 | 6 | 12:09:25.940 | 12:09:26.441 | 前进 | 44→45 | 50 | 24.5 | +0.3 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00008.png) | 是 |
| 9 | 6 | 12:09:26.632 | 12:09:27.176 | 前进 | 45→46 | 50 | 25.5 | -0.3 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00009.png) | 是 |
| 10 | 7 | 12:09:32.600 | 12:09:33.122 | 右转 | 46→47 | 50 | 22.7 | -12.4 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00010.png) | 是 |
| 11 | 8 | 12:09:38.445 | 12:09:38.996 | 右转 | 47→48 | 50 | 14.4 | -13.4 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00011.png) | 是 |
| 12 | 8 | 12:09:39.318 | 12:09:39.782 | 右转 | 48→49 | 50 | 10.5 | -15.5 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00012.png) | 是 |
| 13 | 8 | 12:09:40.035 | 12:09:40.672 | 右转 | 49→50 | 50 | 7.9 | -15.6 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00013.png) | 是 |
| 14 | 9 | 12:09:52.913 | 12:09:53.663 | 左转 | 50→51 | 50 | 6.0 | +10.7 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00014.png) | 否 |
| 15 | 9 | 12:09:53.941 | 12:09:54.435 | 左转 | 51→52 | 50 | 5.3 | +12.9 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00015.png) | 否 |
| 16 | 9 | 12:09:54.671 | 12:09:55.147 | 左转 | 52→53 | 50 | 4.1 | +14.1 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00016.png) | 否 |
| 17 | 9 | 12:09:55.382 | 12:09:56.022 | 左转 | 53→54 | 50 | 3.6 | +14.1 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00017.png) | 是 |
| 18 | 10 | 12:10:00.874 | 12:10:01.372 | 前进 | 54→55 | 50 | 4.2 | +2.8 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00018.png) | 是 |
| 19 | 10 | 12:10:01.654 | 12:10:02.135 | 前进 | 55→56 | 50 | 8.9 | -0.4 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00019.png) | 是 |
| 20 | 10 | 12:10:02.623 | 12:10:03.171 | 前进 | 56→57 | 50 | 15.4 | -0.4 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00020.png) | 是 |
| 21 | 11 | 12:10:08.534 | 12:10:09.107 | 前进 | 57→58 | 50 | 20.0 | -0.7 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00021.png) | 是 |
| 22 | 11 | 12:10:09.366 | 12:10:10.162 | 前进 | 58→59 | 50 | 21.9 | +0.0 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00022.png) | 是 |
| 23 | 12 | 12:10:14.771 | 12:10:15.266 | 右转 | 59→60 | 50 | 20.1 | -13.1 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00023.png) | 否 |
| 24 | 12 | 12:10:15.477 | 12:10:15.954 | 右转 | 60→61 | 50 | 15.7 | -15.8 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00024.png) | 否 |
| 25 | 12 | 12:10:16.129 | 12:10:16.595 | 右转 | 61→62 | 50 | 8.6 | -15.8 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00025.png) | 否 |
| 26 | 12 | 12:10:16.851 | 12:10:17.416 | 右转 | 62→63 | 50 | 6.9 | -14.4 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00026.png) | 是 |
| 27 | 12 | 12:10:17.619 | 12:10:18.065 | 右转 | 63→64 | 50 | 5.8 | -15.8 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00027.png) | 是 |
| 28 | 13 | 12:10:22.942 | 12:10:23.400 | 右转 | 64→65 | 50 | 6.6 | -14.9 | [图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/agent/frames/00028.png) | 是 |

## 每次模型响应发出的动作

| 模型响应 | 机器人工具调用 | 执行内容 |
|---:|---|---|
| 1 | — | 查找可用工具 |
| 2 | 1 | 主动观测 |
| 3 | 2 | 前进 |
| 4 | 3 | 前进 |
| 5 | 4, 5, 6 | 前进、前进、前进 |
| 6 | 7, 8, 9 | 前进、前进、前进 |
| 7 | 10 | 右转 |
| 8 | 11, 12, 13 | 右转、右转、右转 |
| 9 | 14, 15, 16, 17 | 左转、左转、左转、左转 |
| 10 | 18, 19, 20 | 前进、前进、前进 |
| 11 | 21, 22 | 前进、前进 |
| 12 | 23, 24, 25, 26, 27 | 右转、右转、右转、右转、右转 |
| 13 | 28 | 右转 |
| 14 | — | 文字报告到达 |

[每次调用的完整位姿、时钟与图像哈希](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/call-timeline.json) · [模型对外发出的工具代码与响应对应](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_03_tv/model-tool-groups.json) · [结果](README.md)
