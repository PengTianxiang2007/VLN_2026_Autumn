# 原版选错路56条：原版与自动纠错对照可视化

状态：已完成并发布。用户要求复用已有模板；使用 core/oracle_distance_replay.html，保留地图/RGB双进度条、两组来源切换、事件跳转和中英文显示。

固定样本来自已完成原版102条失败分类的 route_choice 全56条，seed=2，未按纠错结果再次筛选。原版0/56成功，纠错组49/56成功，其中46条实际纠错后成功、3条未纠错成功；其余3条纠错后失败、4条未纠错失败。独立运行配对不是共享前缀的干预因果证明。

只读取既有原生分数、轨迹和图像，不启动模型或导航。原版只有起始两个策略观测RGB，其余位置显示缺失提示，不复用开头图像冒充后续画面。俯视图叠加完整原版轨迹、纠错轨迹、参考路线和真实瞬移。

选择清单见 selection.json。实际Git HEAD：7ce5f9fee30686bae304425bc84c36b3fbedc39c，工作区有未提交修改；修改前源码已保存于输出 source_before/。

计划命令：backbone/streamvln/.venv/bin/python -B scripts/export_oracle_auto_branch_replay.py --campaign outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200 --selection experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/selection.json --translations experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/instructions_zh.json --baseline-analysis outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/analysis/baseline_failure_20261117_01 --review-translations experiments/oracle_recovery/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/review_reasons_en.json --output outputs/oracle_crossing/auto_branch_v001/run_20261117_04_pair200/exports/route_choice56_20261117_01/route_choice56.html

源码快照、数据与浏览器验证、哈希和公开网址已补齐。

## 本地导出与验证

56条、11场景；原版轨迹5998个节点、纠错轨迹4653个节点，66次实际干预、49条有干预。原版0/56成功，纠错组49/56（87.50%）；46条有干预且成功、3条有干预但失败、3条无干预成功、4条无干预失败。原生正常成功停止另为46条，和“有干预且成功46条”是不同统计维度，不应混用。

原版112张初始RGB逐条对应到策略观测0/1；其余5886个轨迹位置使用无图像提示，未借用纠错组画面、未重复首帧。原版未保存朝向，地图不绘制原版朝向箭头。两组完整轨迹始终使用同一场景坐标，所有点在底图范围内。

本地Chromium验证：56条中英文指令与归因理由、两组来源切换、66次纠错前后跳转、双进度条、4类筛选、图层、缩放、播放、CSV导出和手机布局全部通过；页面脚本错误0、外部请求0。逐条原生评分、原版全部位置/动作、同ID/scene/seed、翻译原文绑定、地图ZIP CRC及66份记忆与跳变证据核对通过。

离线HTML：61086321字节，SHA256 `f6123a6a14ab1a155079c35d1e27a817583712ee00c3a47f139b46f16227dfaf`。复用模板 `core/oracle_distance_replay.html`，SHA256 `707c30c0495d9c6644aadf3a384ad620189a28442c64d936ebdf0fd1974231ec`。修改前后源码在输出 `source_before/` 与 `source/`；只是为既有模板增加成对结果、四类筛选和缺失RGB显示，未建立新模板。

发布准备曾因资源清单为字典而非列表、以及独立CSV扩展名不在发布器白名单而中止，均未发生上传。随后额外CSV压缩附件的公开上传被自动审批拒绝，理由是该独立数据附件缺少明确公开授权；该可选附件已从发布清单移除，本地 `paired_results_56.csv` 保留。继续仅发布已授权网页、图像、俯视图ZIP与字体许可ZIP。

## 发布与交付

完成时间：2026-11-17T08:28:37.669213+00:00。

- [打开56条原版/自动纠错对照回放](http://134.175.18.101/vln/oracle_route_choice56_run04_web_20261117_01/route_choice56.html)
- [下载56张俯视地图](http://134.175.18.101/vln/oracle_route_choice56_run04_web_20261117_01/topdown_maps_56.zip)
- 本地56条配对结果：[paired_results_56.csv](paired_results_56.csv)；页面也保留原模板的结果CSV导出功能。

在线入口：2732328字节，SHA256 `5ab7661dac74f3a3f3cd27a7fadf75f3bc10ba609710e1c472e949892971e91f`。共4728个发布文件，全部远端SHA256通过；公网HTML入口和地图ZIP的HEAD均为HTTP200，大小匹配。未执行全量公网下载或宣称公网浏览器验证；交互验证来自上述本地Chromium。

发布记录：`outputs/visualization_publishing/publish_20261117_082704_234319/publication.json`，已复制到导出目录 `publication.json`。在线资源清单：`outputs/visualization_publishing/oracle_route_choice56_run04_web_20261117_01/online_manifest.json`。旧25条网页与所有原实验结果保持不变，没有导航、模型调用或服务生命周期更改。
