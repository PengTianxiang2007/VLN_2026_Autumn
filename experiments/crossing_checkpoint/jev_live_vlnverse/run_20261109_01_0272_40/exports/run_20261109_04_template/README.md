# StreamVLN + 实时 JEV：既定三栏模板修订版

更新时间：2026-11-09（UTC）
状态：本地 Chromium 与在线发布验证通过

## 修订内容

- 页面骨架改回既有 JEV/Qwen 对照模板：
  `245px 轨迹列表 + 中央双地图/曲线 + 390px RGB与逐帧详情`；
- 左侧使用纵向轨迹按钮，不再使用自定义双列卡片；
- 中央两张真实户型俯视图：
  - 左：原始 JEV 概率路线；
  - 右：`N=11,D=5` 流式突出度路线和采样节点；
- 右侧恢复模板式 RGB、双进度条、三项数值、三帧缩略图、原始结果和复核区；
- HTML实际按钮点击已验证：点击第10条轨迹后，标题、active按钮、两张地图、
  RGB、曲线和逐帧详情同步切换；
- 40条英文任务指令继续保留完整中文译文和英文原文。

## 文件与验证

- 本地HTML：`streamvln_live_jev_0272_40.html`
- HTML SHA256：`1a851d6a8e505faf9d5c3139af9a397e83c6efeeb44b621729bf2a83b88aabba`
- 浏览器证据：`browser_verification.json`
- 40条、2878帧、2878次JEV、215节点；
- 真实按钮切换、双户型图、地图节点开关、双滑条、双语、prompt、复核导出、
  移动端均通过；页面错误0、外部请求0。

## 发布

http://134.175.18.101/vln/streamvln_live_jev_0272_40_template_20261109_03/streamvln_live_jev_0272_40.html

- 在线HTML：1,756,651字节
- 在线SHA256：`2f2b63ad39face250114be5796ca6896dadb2fafd3f0d8d51e14b78ead05d893`
- 发布记录：`outputs/visualization_publishing/publish_20261109_105150_732749/publication.json`
- 2880个远端文件SHA256通过，入口HTTP 200、`text/html`。
