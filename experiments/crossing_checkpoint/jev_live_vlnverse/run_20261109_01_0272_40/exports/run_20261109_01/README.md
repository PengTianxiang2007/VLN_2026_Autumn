# StreamVLN + 实时 JEV 40 条可视化

更新时间：2026-11-09（UTC）
状态：本地导出与浏览器检查通过，已发布

## 内容

- 40 条 `kujiale_0272` StreamVLN 真实物理导航 episode；
- 2878 个可回放动作帧和 2878 次有效 JEV v004 Noul 回答；
- 215 个 `N=11,D=5` 流式突出度采样节点；
- 俯视路线按 JEV 概率深浅着色，保留数据集参考路线和当前机器人；
- 采样节点默认不在俯视路线显示，勾选后显示 S 编号；
- 横轴显示原始概率、流式突出度和采样节点；
- 帧详情显示 JEV 概率、API 延迟、实际 step 滞后和三帧输入；
- 中文/English 切换，默认中文；40 条英文导航指令均有完整中文译文，
  英文 prompt 与中文翻译同时保留；
- 支持人工分类、备注和复核 JSON 导出。

## 文件

- HTML：`outputs/crossing_checkpoint/jev_noul_v004/vlnverse_live_0272_40/exports/run_20261109_01/streamvln_live_jev_0272_40.html`
- HTML SHA256：`47446d7cc03883d76391c3ca6bda176752bbac58da87fdf8e4c99ac2c4556433`
- 导出清单：同目录 `export_manifest.json`
- 浏览器证据：同目录 `browser_verification.json`
- 桌面截图：同目录 `browser_desktop.png`
- 移动端截图：同目录 `browser_mobile.png`

## 本地验证

Chromium 实际加载通过：

- 40条、2878帧、2878次 JEV、215个节点全部核对；
- 三帧输入索引因果且不超过3帧；
- 中英文切换、完整指令原文/译文、双 prompt、地图节点开关和复核导出通过；
- 移动端无横向溢出；
- 页面错误0、外部请求0。

## 发布

在线入口：

http://134.175.18.101/vln/streamvln_live_jev_0272_40_20261109_01/streamvln_live_jev_0272_40.html

- 在线目录：`outputs/visualization_publishing/streamvln_live_jev_0272_40_20261109_01`
- 在线HTML：1,736,271字节
- 在线HTML SHA256：`6e05540d382e57f6b910b9ba9fc818b3ddb68f403280d03f7451146ee69bdaa5`
- 按需帧图：2878个 WebP；
- 发布记录：`outputs/visualization_publishing/publish_20261109_074207_090427/publication.json`
- 发布记录 phase=`published`，全部2879个文件远端 SHA256 校验通过；
- 公网 HEAD：HTTP 200、`text/html`、长度1,736,271字节。

在线入口的浏览器交互验证沿用发布前同一本地HTML的Chromium检查；发布记录中的
HTTP检查为HEAD，不将HEAD检查表述为在线浏览器检查。
