# 自动落点 v001：CPU代码验证01

开始时间：2026-11-16 14:54 UTC；完成时间：2026-11-16 15:04 UTC。状态：CPU验证完成，未启动模型或仿真。

目的：去除人工分叉点依赖，实现实时距离触发、当前投影后沿路线前移1.25米、自动朝向，并为同任务原版对照提供独立冻结入口。

基线Git：`7ce5f9fee30686bae304425bc84c36b3fbedc39c`，存在会话前未提交修改；本轮只追加新协议和兼容接入，不覆盖历史输出。实际源码、哈希及差异快照保存在`outputs/oracle_crossing/auto_route_v001/code_validation_20261116_01/`，两条准备探针的1322文件快照位于其`prepared_probe/code/`。

验证范围：纯几何、队列时序、记忆不变、原生钩子与原版对照隔离、冻结/计划。正式400条清单尚未准备，GPU导航0条。已暂停的serial运行05不恢复，不操作保留模型/仿真。

## 已完成验证

- 新增10项自动落点/双组隔离检查、原距离12项、原生循环7项、保留模型9项，共38项通过。按测试文件独立进程运行，使用既有StreamVLN Python3.9，不启动模型服务。
- 官方全部825条路线均可构建无标注清单；任务起点及所有参考顶点共39958次纯几何探针，落点均在参考折线上、弧长前移/末端截断/朝向为有限合法数值。探针包含终点，因此截断或近目标探针数量不代表实际干预频率或收益。
- 用官方前两条已有任务执行准备工具并冻结；两组各2条、相同ID与seed；冻结runner与原`run_full.py`字节一致。实际运行入口仅打印计划，`phase=plan_only`、`simulation_started=false`。这两条不是正式新样本，也未执行导航。
- StreamVLN环境检查通过：本仓库模型/适配器/Habitat源码，R2R/RxR数据读取、场景navmesh、四片权重元信息检查通过；无完整权重加载。原有依赖提示保留，未升级环境。
- 额外修复主管只读轮询原生评分JSON写入中状态时的误停：暂时沿用本组最近完整计数，最终仍严格验证完整导出和评分。

```bash
backbone/streamvln/.venv/bin/python -B -m unittest discover -s tests -p test_oracle_auto_route.py -v
# 同方式分别运行test_oracle_distance.py、test_oracle_distance_native.py、test_oracle_existing_model.py。
python3 -B scripts/check_environment.py --backbone streamvln \
  --output outputs/oracle_crossing/auto_route_v001/code_validation_20261116_01/streamvln_environment.json
```

产物：`test_runs.json`及逐文件测试日志、`official_geometry.json`、`prepare_probe.log`、`plan_probe.json`、`streamvln_environment.json`、`implementation_source_sha256.json`；本目录`summary.json`为轻量摘要。

## 限制与下一步

仅证明CPU几何、时序与入口接入。未验证825条场景资产全部可运行或实际落点物理稳定性，未启动GPU任务，无本版导航指标。正式400条清单待历史ID筛选并冻结；之后获准启动时先核对资源及首条实际纠正/评分，再执行同400条两组。原33条结果不作为新协议成绩；原暂停串行任务保持暂停，旧取消队列不恢复。新结果可视化适配尚未制作。
