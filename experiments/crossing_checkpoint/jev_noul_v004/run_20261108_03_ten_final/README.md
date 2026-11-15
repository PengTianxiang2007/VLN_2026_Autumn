# JEV v004 十条轨迹最终合并

状态：完成。862/862个v004结果有效，3个首轮失败帧补跑全部成功。

复用 `run_20261108_02_ten_cases` 中859个成功结果，只补跑3个空响应失败帧：

- `kujiale_0113_66_1` F101
- `kujiale_0232_12_1` F68
- `kujiale_0240_0_0` F43

补跑使用3个并发worker，最多5次重试。最终目标为862/862有效。

## 结果

- 10条轨迹、872个回放帧；
- v004有效862/862；
- 上一版v002平均概率0.380，v004平均概率0.495；
- v004升高753帧、降低91帧、相同18帧；
- 首轮200并发完成859/862，3个空响应失败帧用3并发补跑后全部成功。

## 网页

[打开10条轨迹v002/v004对照](http://134.175.18.101/vln/jev_noul_v004_ten_cases_20261108_01/jev_noul_v002_vs_v004.html)

- 本地HTML：`.../exports/run_20261108_02/jev_noul_v002_vs_v004.html`
- 本地SHA256：`f0fd2d46dc0015e98b2c0660ffb44557786a3ff1aabe243deec8ee32ab3678c3`
- 发布记录：`outputs/visualization_publishing/publish_20261108_153330_611211/publication.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v004_ten_20261108_01/browser_verification.json`

页面支持10条轨迹切换，v002为蓝色调、v004为红色调，颜色越深概率越高。地图仅保留
同一Qwen轨迹和当前机器人位置，没有人工点、高分方块或其他路点。
