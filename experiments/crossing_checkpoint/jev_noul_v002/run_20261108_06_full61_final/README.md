# 完整61条最终合并运行

状态：完成。61条、5378/5378个 JEV Noul 结果有效，失败0。

复用 `run_20261108_04_full61_1000` 中已完成的5007条成功结果，只对371条失败帧
补跑。补跑最多5次重试、100个worker；1000并发首次全量运行的异常收尾和部分
超时均保留在来源运行中。

输出将形成61条/5378个有效结果，用于最终网页对照。

结果：复用首轮5007条成功结果，100并发补跑371条全部成功。JEV全批平均
`P(fallback_point=yes)=0.391`；同帧Qwen4B平均分1.955。

## 网页

[打开完整61条在线对照](http://134.175.18.101/vln/jev_noul_v002_full61_vs_qwen_20261108_02/jev_noul_vs_qwen.html)

- 本地单文件：`outputs/crossing_checkpoint/jev_noul_v002/run_20261108_06_full61_final/exports/run_20261108_03/jev_noul_vs_qwen.html`
- 本地SHA256：`5741a780c34022e8c394c20a65f4b8a3c0d8381ae2d77aa3b1651fdc0000aa1d`
- 在线HTML：2,667,725字节；按需资源5,450个
- 发布记录：`outputs/visualization_publishing/publish_20261108_141011_401490/publication.json`
- 本地浏览器证据：`.../exports/run_20261108_03/browser_verification.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v002_full61_20261108_02/browser_verification.json`

地图严格使用Qwen原始轨迹；Qwen路径按1–5分着色，JEV路径按概率0–1着色。
地图不绘制人工点、JEV高分方块或其他路点，仅保留路线和当前机器人位置。
