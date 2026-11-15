# JEV Noul v002 / 5 条全帧离线对照

状态：完成。421/421 次 JEV Noul 调用有效，0 失败；网页已导出、验证并发布。

目的：在 5 条与 Qwen4B 同帧可比的离线轨迹上，逐步运行统一的
`fallback_point` Noul，得到当前 step 可以作为回退点的概率；网页同时对照
`best_v001` Qwen3.5-4B 的 1–5 分。

样本选择规则：从 `lite_v002/run_20261108_01/evaluation_selection.json` 的固定
20 条中，按 `failure, success` 交替循环，并优先选择尚未使用的 scene，得到 3 条
原导航失败和 2 条成功：

- `kujiale_0208_21_4`（failure）
- `kujiale_0240_0_0`（success）
- `kujiale_0207_41_0`（failure）
- `kujiale_0232_12_1`（success）
- `kujiale_0123_fix_19_3`（failure）

该选择只看预先冻结的 20 条清单、分组和场景，不看 Qwen 或 JEV 预测。

协议：

- 严格 `t-2,t-1,t` RGB；
- 一个自包含 `fallback_point` Noul；不输出1–5分、理由或动作；
- 50 个进程并发，每帧独立请求；
- 不输入任务、动作、位置、地图、成败、人工标注或旧回答；
- Qwen4B 对照直接读取 `lite_v002/run_20261108_01/baseline_predictions.json`，
  不重新调用 Qwen；
- 页面路径颜色：Qwen4B 由 1 分浅色到 5 分深色；JEV 由概率 0 浅色到概率 1 深色。

预期 421 次 JEV 调用。该页面是开发集离线对照，不构成独立准确性评测。

## 结果

JEV 全批平均 `P(yes)=0.394`；40 次选择 Qwen4B 同帧平均分为 `2.064`。
两者量纲不同，不计算相关系数、准确率或“胜出”结论。

| 轨迹 | 帧数 | Qwen均值 | Qwen≥4 | JEV均值 | JEV≥0.5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| kujiale_0208_21_4 | 40 | 3.400 | 24 | 0.592 | 28 |
| kujiale_0240_0_0 | 98 | 1.939 | 23 | 0.369 | 26 |
| kujiale_0207_41_0 | 79 | 2.823 | 36 | 0.515 | 45 |
| kujiale_0232_12_1 | 74 | 2.189 | 22 | 0.398 | 26 |
| kujiale_0123_fix_19_3 | 130 | 1.215 | 7 | 0.275 | 11 |

传输：395 次首请求成功，22 次第二次成功，4 次第三次成功；每次最多4次。

## 网页

[打开在线对照网页](http://134.175.18.101/vln/jev_noul_v002_five50_vs_qwen_20261108_01/jev_noul_vs_qwen.html)

- 本地单文件：`outputs/crossing_checkpoint/jev_noul_v002/run_20261108_02_five50/exports/run_20261108_03/jev_noul_vs_qwen.html`
- 本地 SHA256：`649818112551e364c3429073ab30d85c6d31cf885ac9233f25cba4ed1cd7f295`
- 在线拆分目录：`outputs/visualization_publishing/jev_noul_v002_five50_vs_qwen_20261108_01/`
- 发布记录：`outputs/visualization_publishing/publish_20261108_130807_477642/publication.json`
- 在线浏览器证据：`outputs/visualization_publishing/online_check_jev_noul_v002_20261108_01/browser_verification.json`

页面将Qwen4B路径按1–5分由浅到深染色，将JEV路径按P(yes)由0到1由浅到深
染色；两条路径使用同一地图并同步双进度条。默认中文，可切换完整英文。
