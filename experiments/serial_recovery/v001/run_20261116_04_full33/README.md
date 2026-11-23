# DeepSeek串行恢复：33任务格式兼容修复运行04

2026-11-16 13:15 UTC检查：运行04已于13:01 UTC（北京时间21:01）异常退出，完成1/33、成功0/1。首条kujiale_0257_4_3执行83动作后STOP，NE6.2749米，80次JEV、6次去重、9次偏航评审；实际回退/交还均0（接管前复核为uncertain），完整恢复闭环未验证。第二条kujiale_0257_8_1执行5动作、6次JEV后，首个偏航答HTTP200且完整结束，但uncertainties为{zh:[两项],en:[两项]}，不符合双语对象数组格式，上次仅兼容单个双语字符串对象的修复未覆盖此结构，抛出Invalid uncertainties。主管1121493与仿真1121566已退出；GPU2本项目占用已释放，GPU3原模型3194667按要求保留。只检查并登记，未重启或改代码；证据progress_check_20261116_1315.json。

2026-11-16：继续用户已授权的33任务/34事件仿真批次。03在首条第50个动作后因uncertainties容器类型错误退出，0完成；保留03，不合并或冒充正式结果。当前状态：新运行已启动，GPU2仿真初始化中，0/33；真实导航启动验证待完成。

## 目的、协议与版本

与[运行03](../run_20261116_03_full33/README.md)相同：seed2、9场景、每条从原生起点重跑，原25000物理tick预算含恢复，单目纠错40动作预算，多次恢复并交还接管前记忆。JEV使用EasyJEV实时接口，六个语义环节均使用DeepSeek官方API/deepseek-flash；提示词、思考设置、图像窗口、采样/去重和偏航/选路规则不变。参考轨迹与人工标签不参与在线决策。GPU2共享仿真、GPU3保留原StreamVLN3194667/40617，显存准入仍12GiB，不以GPU利用率高拒绝运行。

本次仅兼容偏航响应的一个无损容器差异：若uncertainties是键严格为zh/en、文字均完整非空的单个对象，包装成单项数组，再通过原严格验证器。原response.json/answer.json保留；另存normalization.json和normalized_answer.json。不给缺失翻译补字、不改结论、不把无效答视为有效、不重新采样模型判断。其余错误仍失败并保留证据。

11份03实际偏航答离线重验全部通过，其中1份转换容器、其余10份未改；原失败答和缺失翻译/非法结论用例纳入回归测试。实际Git、未提交差异、源码/配置/提示词/数据hash见本轮manifest和code/。

## 启动命令

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py \
  --cohort outputs/oracle_crossing/distance_v001/run_20261115_05/cohort.json \
  --jev-endpoint https://api.easyjev.online/v1/systemone \
  --output outputs/serial_recovery/v001/run_20261116_04_full33

benchmarks/vlnverse/.venv/bin/python -u -B outputs/serial_recovery/v001/run_20261116_04_full33/code/scripts/run_serial_pipeline.py \
  --campaign outputs/serial_recovery/v001/run_20261116_04_full33 \
  --gpu 2 --model-pid 3194667 --port 40617 --allow-active-shared-gpu --keys-stdin --detach
```

密钥仍仅在进程内存/环境中。状态/轨迹/逐请求原答及结构转换记录写入`outputs/serial_recovery/v001/run_20261116_04_full33/`。原版连续任务、场景和RSS生命周期不改；最终分别统计完成数、导航评分、实际恢复次数和完整交还循环。正常启动检查通过后停止人工持续跟踪。

## 实际启动

2026-11-16T12:36:19.388521+00:00：主管1121493、仿真1121566，GPU2共享运行（准入空闲29911MiB，利用率100/6%），GPU3原模型3194667/40617不变。38项CPU检查通过，11份历史响应均通过（1份无损转换），1345个源码/测试/提示词文件冻结。当前场景初始化，正式评分0/33，尚未把进程启动称为真实导航或完整恢复通过。
