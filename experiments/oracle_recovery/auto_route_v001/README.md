# 无人工分叉标注的自动参考路线纠正 v001

2026-11-16后续用户更正：落点应来自实际轨迹与参考路线的分支位置。当前点投影方案已由[auto_branch_v001](../auto_branch_v001/README.md)取代；本页及冻结代码保留为历史准备记录，无本版导航运行。

2026-11-16：用户要求改变落点来源，由脚本自动决定偏航纠正的位置与朝向。代码、38项CPU检查、825条路线几何与冻结/计划及环境检查已通过；未启动本轮导航，原暂停任务保持暂停。

## 协议

原版StreamVLN / VLNVerse fine val_unseen / H1 physical，seed=2。机器人到完整正确参考折线的最短XY距离达到0.75米，且模型动作队列为空时，取**执行纠正时当前位置**在参考折线上的最近投影，再沿参考路线弧长前移1.25米；朝向落点所在的前进线段，恰好在折角时使用下一段方向。高度沿用已有瞬移实现的任务初始站立高度。

每次新观测重新计算距离和候选落点；队列等待期间回到0.75米内则不纠正。每次实际纠正可产生不同落点，保留纠正时策略记忆，允许重复纠正。使用原50tick稳定、0.35米/15度恢复校验；稳定消耗计入原25000tick预算，不恢复预算，不延长STOP/跌倒/卡住规则。

超过路线末端时截断到终点并记录实际前移距离；不额外排除目标3米成功半径内的落点。最近投影有等距回环时沿用最早参考段；不增加进度约束或语义判断。近邻平行路线、回环、多层场景及落点碰撞是已知限制，GPU物理可行性尚未验证。

这是使用正确参考路线的特权Oracle；不依赖人工分叉点、历史错误帧或模型判断。它与旧`early_plus05`的“人工分叉点投影后前移1.25米”是不同协议，成绩必须分开统计。

## 对照与执行

准备工具读取官方任务与显式episode-ID清单，冻结同一批任务的`baseline`和`auto_route`两组。baseline不启用Oracle钩子；两组均保留原生连续评测循环、任务重置、seed、评分、RSS重启机制。预计最终400条×2组；本次尚未冻结正式400条清单。

```bash
# ids.json为JSON字符串列表；也接受每行一个episode ID。这里只冻结，不启动。
backbone/streamvln/.venv/bin/python -B scripts/prepare_oracle_auto_route.py \
  --episode-ids-file /path/to/ids.json --expected-episodes 400 \
  --output outputs/oracle_crossing/auto_route_v001/run_NEW

# 使用该次冻结入口；默认只打印同400条×2组计划，不加载模型。
backbone/streamvln/.venv/bin/python -B \
  outputs/oracle_crossing/auto_route_v001/run_NEW/code/scripts/run_oracle_distance.py \
  --campaign outputs/oracle_crossing/auto_route_v001/run_NEW
```

`--execute`才实际运行；GPU、资源准入及现有保留服务的使用在启动时按最新指令处理。当前不添加该参数。新协议不继承旧人工标注Oracle成绩；准备工具也不自行声称清单从未运行，需单独核对历史任务ID。

公共实现：`core/oracle_auto_route.py`（几何/实时事件/无标注清单），`core/oracle_distance_runtime.py`（复用物理瞬移和记忆核验），`scripts/prepare_oracle_auto_route.py`（冻结），`scripts/run_oracle_distance.py`（原生两组计划与评分）。旧Oracle回放导出器依赖历史人工轨迹，不能直接用于本版；取得新结果后需提供对应导出适配，本轮不生成HTML。

代码验证：[code_validation_20261116_01](code_validation_20261116_01/README.md)。实际导航完成数为0；无本版SR/SPL/NE或收益结论。
