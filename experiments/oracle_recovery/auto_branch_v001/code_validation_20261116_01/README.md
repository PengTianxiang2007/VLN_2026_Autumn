# 轨迹分支锚点：CPU验证01

开始：2026-11-16 15:15 UTC。状态：CPU验证完成；未启动模型或仿真。实际完成时间见同目录summary.json。

目的：验证从真实轨迹的分离变化点定位参考路线锚点、固定落点、不沿错误分支漂移；确保原版对照和历史Oracle协议不受影响。

版本：Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c`加记录的未提交改动。上一版auto_route_v001的CPU快照保留，新增协议auto_branch_oracle_v001。

样本/seed/协议：合成直行、斜分支、漏转弯、平行路、回环、抖动、起始分支与不确定输入；原历史记录仅作离线输入检查，不使用人工事件参与算法，不进行仿真。导航seed=2，阈值0.75米、估计分支锚点后前移1.25米。

产物：`outputs/oracle_crossing/auto_branch_v001/code_validation_20261116_01/`。暂停的serial运行05不恢复。

## 结果

- 最终52项CPU检查：分支定位14、旧当前点投影10、人工距离协议12、原生循环7、保留模型9，均通过。最终日志在`final_checks_02/`，首轮51项日志保留。
- 覆盖直角/斜分支、漏转弯、稳定侧偏、起点分支、错误平行通道继续前进、动作队列等待、原地抖动、回环的重复参考位置、证据不足、阈值抖动、路线重采样、末端截断、瞬移后的新轨迹段以及绕行接入另一参考段后再次分支。
- 官方825条路线、每条21个给定弧长锚点，共17325个落点检查通过；这仅验证插值/朝向/截断，不证明825条的分支定位准确或物理可走。
- 33条既有轨迹的最终顺序回放`offline_replay_02/`：3039条观测，1558条距离达到阈值，其中1524条有固定分支候选，34条因拟合RMSE过大未给出落点；31条任务产生31个候选。输入只含参考路线与已到达帧位置，不读取events.jsonl，不实际纠正、无反事实续走，也没有定位准确率结论。首轮回放保留为offline_replay_01。
- 最终准备探针`prepared_probe_02/`冻结1324文件，两组各2条已有任务、同seed；原生run_full字节不变，实际入口仅打印计划。首版prepared_probe保留，最终执行源码以02为准。
- StreamVLN环境检查通过，仅读取导入/数据/权重元信息，没有加载模型。重接补充只改纯CPU算法，不改变环境依赖。

## 验证命令

```bash
backbone/streamvln/.venv/bin/python -B -m unittest discover -s tests -p test_oracle_auto_branch.py -v
# 其余四份test_oracle_*.py按最终test_runs.json中的命令分别执行。
backbone/streamvln/.venv/bin/python -B scripts/replay_oracle_auto_branch.py \
  --dataset outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001 \
  --episode-ids-file outputs/oracle_crossing/auto_branch_v001/code_validation_20261116_01/historical_ids.json \
  --output /path/to/NEW_offline_audit
```

## 限制与下一步

当前是因果轨迹几何估计，不是拓扑分叉真值识别。拟合置信不足时记录并跳过；转弯切角、缓慢漂移、多次偏离、近邻路线和楼层重叠仍有歧义。保留分支位置、对应弧长、观测区间、拟合基线/斜率/RMSE和重定位标记供复核。

没有本版导航成绩、实际回退或物理稳定性验证；后续同400条的两组实验仍需清单正式冻结、资源准入和首条真实导航核验。未生成HTML或上传网页。
