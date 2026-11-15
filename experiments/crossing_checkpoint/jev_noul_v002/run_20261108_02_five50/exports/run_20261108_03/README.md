# 导出 run_20261108_03

状态：本地 Chromium 检查和公网浏览器检查通过。

源文件：
`outputs/crossing_checkpoint/jev_noul_v002/run_20261108_02_five50/exports/run_20261108_03/jev_noul_vs_qwen.html`

SHA256：
`649818112551e364c3429073ab30d85c6d31cf885ac9233f25cba4ed1cd7f295`

本地验证：5条轨迹、426回放帧、421个Qwen分数、421个JEV概率；双地图、双滑条、
颜色深浅、双语、自包含prompt、复核导出、移动端均通过，外部请求0、页面错误0。

在线版本：HTML 235,046字节，432个按需资源；公网入口HTTP 200，远端SHA256全部
验证通过。在线Chromium复验5条/421个结果、切换轨迹和语言、RGB 640像素加载通过，
页面错误0、请求失败0。

发布记录：`outputs/visualization_publishing/publish_20261108_130807_477642/publication.json`。

首次导出 `run_20261108_01` 因环境缺少fontTools失败；`run_20261108_02` 因切换轨迹
时滑条最大值未更新而浏览器检查失败。两者均保留，不计作最终页面。
