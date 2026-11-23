# 回到 A 的选路位置 · DeepSeek 四例物理回退

[打开四例新旧版逐帧对照回放](http://134.175.18.101/vln/deepseek_h1_choice_position4_20261123_01/index.html) · [导出记录](../../exports/choice_position4_20261123_01/README.md)

2026-11-23 UTC。重跑用户指定的 C21、C15、C31、C34，按[冻结样本](../run_20261123_02/README.md)的顺序执行 C15、C21、C31、C34，seed 2。检验加强退出条件能否减少在 B 附近转向后误停或在接近 A 的路上提前退出。四例均从旧版早停案例中指定，本轮成绩适用于这四例。

回程 prompt 使用[选路位置版](../prompt_variants/choice_position/README.md)。仅替换旧版退出句。去程七图描述直接复用[四份原答](outbound_sources.json)。使用同一 DeepSeek 官方模型 `deepseek-flash`、temperature 0、关闭 thinking。H1 从同一历史 B 状态开始，12 次左转后，以四张固定图、最多四张回程图和回程动作记录做决策。保留每轮四个原生动作、25,000 物理步预算和 0.35 米落点判据。

仓库 Git 基线为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c`。[运行清单](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/manifest.json)记录实际脚本与 prompt 哈希，[实时状态](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/status.json)记录当前阶段。结束后自动写入旧版与新版逐例落点误差、回程动作数和退出方式。整条导航 SR 和平均 SPL，当前版与同批原版均为“暂无，已评分 0 条”。

从仓库根目录启动，在隐藏终端输入运行凭据。

启动确认时，C15 首轮返回 `arrived=false` 和四次 `LEFT`，H1 已依次执行，每个动作 50 个物理步。其余轮次与案例交由后台队列继续。[首轮执行记录](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/startup_verified.json)

```bash
tmux -L peng_h1_choice4_20261123 -f /dev/null new-session -s choice4 'bash experiments/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/run.sh'
```

用户在运行期间要求保留仿真。[hold_final.py](hold_final.py) 在 C34 原生结果写入时挂起 worker，并用四份结果完成汇总。2026-11-23 20:38 UTC 按用户后续指示释放。核对启动标识后，对 PID 2031459 发送 `SIGCONT`，由原 worker 正常关闭环境。已验证进程退出，且 GPU 0 上原先占用 9,605 MiB 的该进程条目已消失。[释放记录](../../../../outputs/inverse_rollback/vlm_action_v001/run_20261123_06_choice_position4/simulator_retained.json)

四例已完成。新版达标 0/4，平均终点误差 4.179 米；同批旧版达标 0/4，平均终点误差 3.590 米。 [逐例配对结果](paired_results.json)
