# 53 条前视轨迹的 JEV 候选回退点网页发布

[打开在线回放](http://134.175.18.101/vln/jev_route53_sampling_v001_web_20261118_01/index.html)。2026-11-18 用户指定发布本批网页，沿用先前的 JEV 采样回放模板。源为 `outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01/exports/front_candidates_01/index.html`，SHA256 为 `026dfe5db51731bbe5e597320ad997bf1a9b8b07550438fe194968e272fd0667`。53 条轨迹、4,837 个前视评分、494 个去重前候选。

保留分支 v001 的采样器、原始与滤波波形、地图、双进度条和中英文内容。地图上的“显示回退点”与采样勾选框同步。前视图保持原始分辨率，网页传输使用 WebP；模型评分仍来自原始前视图。此发布只使用已完成的实验结果。

```bash
run=outputs/crossing_checkpoint/online_sampling_v001/run_20261118_01
release=jev_route53_sampling_v001_web_20261118_01
backbone/streamvln/.venv/bin/python -B scripts/prepare_online_route_jev.py --html "$run/exports/front_candidates_01/index.html" --destination "outputs/visualization_publishing/$release"
```

在线包由标准拆分器提取字体，随后补齐页面引用的前视图、地图与字体许可证。上传使用 `scripts/publish_visualization.py` 和 `online_manifest.json` 中的完整静态资源清单。

## 发布验收

发布时间为 2026-11-18 07:00:43 UTC。在线目录 `outputs/visualization_publishing/jev_route53_sampling_v001_web_20261118_01/`，入口 1,986,010 字节，SHA256 为 `92cfab126dd4c4cabba29841725e30ac582ff5088722642f5a4f37cb64e495f4`。入口、4,837 张前视图、19 张地图、字体及字体许可证共 4,859 个文件，远端全部 SHA256 校验通过。公网入口 HTTP 200，前视图和地图各抽验一项，HTTP 状态、类型和长度符合清单。详见[发布摘要](publication_summary.json)与[全量发布记录](../../../../../../outputs/visualization_publishing/publish_20261118_065938_476932/publication.json)。

上线包在本地浏览器通过 53 条轨迹的双语指令检查，全部 4,837 个概率及 494 个节点与源记录一致。地图节点开关与采样开关同步，播放位置变化后节点保持一致，前视图加载通过。[浏览器验收](browser_validation.json)。
