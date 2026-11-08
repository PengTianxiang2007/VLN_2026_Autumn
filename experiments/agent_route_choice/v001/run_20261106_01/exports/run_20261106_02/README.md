# 十条选路结果直观展示：Crossing原帧、支路、最终选择

状态：完成，2026-11-06。用户指出第一版可视化难以理解，明确要求直接给出模型认为有哪些支路、最终选哪一条，以及判断时在Crossing看到的那一帧画面。

此次以用户最新要求调整布局：首屏固定Crossing原始RGB（明确帧号），逐条列出第一次返回的B编号、方向、地标与空间去向，突出第二次的最终选择和排除支路。回放、地图、完整回答、英文原文与复核记录收进展开区；原地图/RGB双进度条功能保留。第七条仍显示原始B1选择，同时标明它被排除，不能掩盖矛盾。

不重跑模型，不改prompt、seed、数据或答案。复用exports/run_20261106_01/translations_zh.json的20份中文译文及其原响应哈希绑定；Qwen32B主结果、GLM无额度状态均来自原记录。固定Crossing图必须严格使用dataset.json的checkpoint_frame对应图像，切换回放或证据时不会变化；前后调用仍使用相同当前视角。

新输出目录：outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/，计划文件crossing_branches_choice_zh.html。第一版HTML保留。检查全部十条的固定帧、支路与选择一致性、原始矛盾、中文及展开回放；截图审阅之后交付，并提供用户Windows目标Files目录的scp命令。


## 交付

首屏固定展示判断时Crossing原始帧和帧号，第一次的所有支路逐项列出编号、方向、地标及空间去向；上方直接突出第二次最终选择，下方标明排除支路。所有原始选择均保留，包括第七条同时排除和选择B1。

已检查全部10条、两模型视图、31个实际支路、10个最终选择、20份中文译文，300次图像检查通过；固定图与原请求中的current_view_id及图像SHA256逐条一致，回放、证据浏览及语言切换均不会改变固定图。27项CPU检查通过；浏览器错误与外部请求均为0，图片放大和窄屏布局通过。已人工查看第1条和第7条截图。

- [新版单文件HTML](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.html)
- [首屏截图](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.preview.png)
- [第七条矛盾截图](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.invalid_case07.png)
- [逐条支路与选择记录](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/branch_choices_zh.json)
- [验证摘要](summary.json)

本次只改展示，不重新推理、不修改真实响应，不进行语义正确率评分；第一版输出完整保留。实际Git提交、源码快照、哈希、工作区状态和测试日志均随输出保存。

Windows PowerShell下载命令：

```powershell
$vlnExportDir = "C:\Users\93232\Desktop\SCIENCE\CVPR2027_VLN_FDU\Version2\Files"
New-Item -ItemType Directory -Force -Path $vlnExportDir | Out-Null
scp -P 5476 -i "C:\Users\93232\Desktop\shared_key_5476" "root@101.132.180.249:/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_02/crossing_branches_choice_zh.html" "$vlnExportDir\crossing_branches_choice_zh.html"
```
