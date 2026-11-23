# 自动距离 Oracle：33任务/34事件，正式运行01

日期：2026-11-15。状态：启动前资源准入失败；模型/仿真均未启动，历史记录保留。

## 目的与设置

用户要求完成代码后直接在GPU启动，核验正常后后台自动运行，不持续人工轮询。
VLNVerse fine val_unseen中的原人工集33条任务、34个错误事件，StreamVLN，seed=2，H1 physical。
early/short/medium/long阈值0.75/1.5/3/4米，保留干预时记忆并可多次纠正；checkpoint为0.75米、实际存档状态一次回退后自主续走。
共165个完整作业；四个距离组独立运行，不声称共享错误前缀。34事件中两个属于kujiale_0257_82_4。
落点及其他协议见上级README。原生STOP、跌倒、卡住、25000tick预算保持。

## 版本与资源

实际Git基线7ce5f9f，加本轮未提交修改。prepare工具保存源码快照、工作区差异、1319个源码哈希和数据/配置封印。
启动前初次检查：GPU2/3各48520MiB空闲、0%利用率且无计算进程；GPU0/1为其他用户chenziyuan任务，不操作。
MemAvailable约340GiB。计划GPU2运行模型、GPU3运行仿真，队列启动前逐卡再采样两次。

## 命令与产物

```bash
python3 -B scripts/prepare_oracle_distance.py --output outputs/oracle_crossing/distance_v001/run_20261115_01
python3 -u -B scripts/run_oracle_distance.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_01 --gpu 2 --sim-gpu 3 --execute
```

输出根目录：`outputs/oracle_crossing/distance_v001/run_20261115_01/`。
`manifest.json`、`cohort.json`、`seal.json`固定方法与样本；`status.json`记录队列状态；`oracle_records/<arm>/<episode>/`保存逐帧、触发距离、复位和memory证明、结果。
`runs/vlnverse/streamvln/results/`保存官方结果、LMDB与模型/仿真日志；每条成功后记录complete标记和结果哈希，失败不静默重跑。

## 验证与下一步

新增10项CPU检查、StreamVLN环境检查通过；全套回归的Python版本/依赖差异已经在对应环境补验。
待核验模型就绪、自动纠正的实际位姿与memory证明、至少一条完整任务原生评分。通过后停止人工持续跟踪，后台队列继续。
主管PID2779911、tmux会话oracle_distance_20261115_01在首次准入时发现GPU2/3已被新任务占用，退出。
GPU2为其他用户panyingxie的CARLA进程2777416；GPU3为chenziyuan的评测进程2779317，未操作任何占用进程。
`status.json`为failed、simulation_started=false、completed=[]。没有导航、模型或仿真子进程。
新增资源等待和空闲卡自动选择后使用[运行02](../run_20261115_02/README.md)，不覆盖本轮源码或状态。
