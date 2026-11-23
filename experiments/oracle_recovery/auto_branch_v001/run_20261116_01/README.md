# 400条 / 22场景：在线分离位置Oracle与原版对照准备01

2026-11-16，状态：**准备完成，等待用户验收；未启动导航。** 用户明确要求“完成后先不开始导航，等我验收”，本次没有创建后台导航队列。

## 目的与协议

用户确认继续采用实际轨迹在线定位：只使用本次已经观察到的位置历史与官方参考路线估计分离位置；达到0.75米偏离且分离位置可以估计、原动作队列为空时，沿该锚点之后的正确参考路线前移1.25米，取落点处前进方向。保留策略记忆，允许后续再次纠正，原生任务预算/评分/重启机制不变。未知分离位置不以当前位置投影或静态候选点代替。

同一份400条新任务、导航seed=2，原版baseline与auto_branch各400次。选样seed=20261116；ID文件SHA256 `579c835e83dcf7b9701e32f672ebaaa7de1e67d488de90946d470ced33d860b5`。任务身份来源与新任务审计见`../scene_plan_20261116_01/README.md`。22场景的162个静态候选不作为运行时锚点，不预先为400条任务固定落点。

## 版本与环境

起始Git `7ce5f9fee30686bae304425bc84c36b3fbedc39c`，含既有未提交修改；冻结保存实际源码、工作区状态/差异与哈希。复用现有StreamVLN/仿真环境；CPU准备不启动模型、仿真、队列，不恢复暂停serial任务或触碰保留服务。

## 准备与验证

核对在线分支定位实现，补齐同一参考路线在不同位置走错的验证；22场景几何只用于检查/记录落点的静态通行证据，其投影不是仿真碰撞真值。先检验几何与官方路线的一致程度，不能未经核验就据此更改运行协议。

检查产物放`outputs/oracle_crossing/auto_branch_v001/preparation_20261116_02/`；正式冻结计划放`outputs/oracle_crossing/auto_branch_v001/run_20261116_01/`。准备入口`scripts/prepare_oracle_auto_branch.py`，运行入口沿用冻结`scripts/run_oracle_distance.py`，此次只打印计划，不加`--execute`。

## 验收结果

- 固定400条、22场景：18场景各18条，4场景各19条；baseline与auto_branch顺序和seed=2一致，官方指令/参考路线不改，历史新任务筛选口径不变。
- 59项CPU检查通过，实际仿真Python3.10环境复验其中21项也通过。包括不同位置分离、纠正后再次走错、原地抖动、平行错路、回环、重新接入参考路线、不确定时跳过、动作队列、记忆证明及原生生命周期边界。测试中的模拟环境不能替代真实导航。
- 1325份源码及44份几何数据哈希验证通过；原生`run_full.py`与仓库原版字节一致。baseline无Oracle环境钩子；两组均不继承旧33条的结果。只打印计划：两次原生入口调用、各400条，共800次计划导航，实际启动0次。
- 22场景投影几何核对约6万个参考路线位置：无栅格越界，109个位置未落在投影地面，55个位置与投影障碍重叠，涉及19条任务；566个位置未通过近似安全区域。投影不是物理碰撞真值，因此仅记录，不移动目标或否决纠正。所有400条保留，不据此换样本。
- 几何审计的最终可复现脚本在StreamVLN Python3.9下取59671个均匀样点；初步Python3.10探查取59666个。参考弧长计算的浮点差异在`ceil(length/0.05)`边界造成5个样点差，障碍/非地面/安全区计数及19条任务结论一致；两份记录均保留。不是实际落点统计。
- 原暂停主管1160721、仿真1160808、采样1218163仍为T状态，保留模型3194667仍在线；没有向其发送控制或推理请求。

## 验收材料

[轻量摘要](summary.json) · [固定400条清单](../scene_plan_20261116_01/draft_episode_ids.json) · [合成分支示意图](../../../../outputs/oracle_crossing/auto_branch_v001/preparation_20261116_02/mechanism_demo_02/branch_examples.png) · [冻结核验结果](../../../../outputs/oracle_crossing/auto_branch_v001/preparation_20261116_02/preparation_verification.json)。

示意图由实际算法处理合成位置序列产生：参考路线`(0,0)→A(3,0)→B(3,4)→(8,4)`。在A走错，锚点为`(3,0)`、落点`(3,1.25)`、朝向正Y；在B走错，锚点为`(3,4)`、落点`(4.25,4)`、朝向正X。A纠正后又在B走错时仍得到B的落点。完整逐步输出在同目录`examples.json`；这不是模型的实际导航结果。`mechanism_demo/`为保留初稿，最终使用动作边界一致的`mechanism_demo_02/`。

检查目录另含`cpu_tests.log`、`simulation_python_cpu_tests.log`、`reference_geometry_audit_reproducible.json`、`plan_only.json`、`source/`及`source_sha256.json`。正式冻结目录含`manifest.json`、`cohort.json`、`seal.json`、`code/`、`geometry/`和待验收状态。

## 可复现命令

以下准备输出已存在，重复准备会拒绝覆盖；复查时直接使用第二条只打印命令。

```bash
backbone/streamvln/.venv/bin/python -B scripts/prepare_oracle_auto_branch.py \
  --episode-ids-file experiments/oracle_recovery/auto_branch_v001/scene_plan_20261116_01/draft_episode_ids.json \
  --expected-episodes 400 \
  --geometry-root outputs/oracle_crossing/scene_annotations_v001/run_20261116_01 \
  --output outputs/oracle_crossing/auto_branch_v001/run_20261116_01

backbone/streamvln/.venv/bin/python -B \
  outputs/oracle_crossing/auto_branch_v001/run_20261116_01/code/scripts/run_oracle_distance.py \
  --campaign outputs/oracle_crossing/auto_branch_v001/run_20261116_01
```

计划内GPU编号只是默认参数，不表示资源已分配，也不允许复用/中断当前暂停任务。以后启动前须重新检查资源及保留服务归属。

## 限制与下一步

准备工作完成，不等于实际分叉定位已经准确。当前算法估计的是已走轨迹与参考折线的几何分离位置；急弯、缓慢漂移、相邻/回环路段等仍可能误定位或无法定位。位置稳定误差0.35米、朝向15°及原物理预算检查保持原实现，但新400条尚无真实落地验证。

**等待用户验收和后续明确启动指令。** 不启动导航、不自动恢复其他队列。获准后才进行必要的真实启动验证和同400条两组评测；未知结果不得填报定位准确率、恢复成功率或收益。本次只生成PNG与JSON验收材料，没有新HTML，不涉及网页发布。
