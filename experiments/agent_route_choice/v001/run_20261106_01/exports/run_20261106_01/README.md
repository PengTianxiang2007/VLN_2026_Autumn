# 十条选路结果中文可视化导出

状态：完成，2026-11-06。用户要求导出可视化，回答使用中文翻译，并提供Windows下载命令。

本次只读取已完成的Qwen32B十条/20次响应和GLM恢复批次的失败记录，不发起模型请求，不改变推理prompt、样本、seed或原始回答。Qwen使用preparation_20261106_04，GLM恢复使用preparation_20261106_05；合并前核验输入、标签及两次prompt一致，各组仍绑定自己的准备manifest。

沿用地图/RGB双进度条和原C/复位P模板。中文翻译由当前助手按原始回答制作，每份译文绑定源响应SHA256；编号、方向枚举、选择/排除关系保持不变，英文原文可展开。第七条原始无效回答也展示，并明确其矛盾。GLM无可用回答，显示账户无额度，不作为已完成模型比较。语义正确率仍待复核。

输出新目录：outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/。历史HTML保留。计划文件agent_route_choice_qwen32b_zh.html，内嵌80张RGB、场景地图与中文字体，可单文件离线打开。

验证：CPU协议回归、全部样本两次回答/中文译文/模型切换/双进度条/原始失败回答浏览器检查及截图。实际结果与源码快照在完成后补齐。

用户下载目标：C:\Users\93232\Desktop\SCIENCE\CVPR2027_VLN_FDU\Version2\Files。SSH端口5476，用户root，主机101.132.180.249；私钥文件保留在用户电脑，不读取或打包其内容。


## 交付与验证

已导出单文件HTML（28,416,786字节，约28.4MB）。默认展示20份中文回答和10条中文任务；可切换英文原文，保留第七条B1同时被排除和选择的原始矛盾。GLM无额度、0回答仅作为状态组展示。

27项CPU检查通过；浏览器检查10条、两组共20个样本视图、280次图像、20份译文、1份无效原始回答通过，意见下载与窄屏布局正常；页面错误0，外部网络请求0。已人工查看第七条截图，双进度条与矛盾提示显示正常。此次无模型请求、无GPU任务，未进行语义正确率复核。

- [离线中文可视化](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.html)
- [导出摘要](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/delivery_summary.json)
- [浏览器验证](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.browser_validation.json)
- [第七条截图](../../../../../../outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.invalid_case07.png)
- [源响应绑定的中文译文](translations_zh.json)

源码快照、实际Git提交、工作区状态、代码差异与测试日志保存在输出目录；推理原始回答、准备目录及旧HTML保持不变。

在用户Windows电脑的PowerShell中执行：

```powershell
$vlnExportDir = "C:\Users\93232\Desktop\SCIENCE\CVPR2027_VLN_FDU\Version2\Files"
New-Item -ItemType Directory -Force -Path $vlnExportDir | Out-Null
scp -P 5476 -i "C:\Users\93232\Desktop\shared_key_5476" "root@101.132.180.249:/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/agent_route_choice/v001/run_20261106_01/exports/run_20261106_01/agent_route_choice_qwen32b_zh.html" "$vlnExportDir\agent_route_choice_qwen32b_zh.html"
```

下载后双击HTML离线查看，无需下载服务器依赖、图片文件夹或密钥内容。
