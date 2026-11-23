# Qwen27B 全部 53 条轨迹的去重回放

[在线回放](http://134.175.18.101/vln/qwen27b_route53_dedup_v001_web_20261118_01/index.html)于 2026-11-18 09:19:06 UTC 发布。4,859 个远端文件 SHA256 验证通过，公网入口返回 HTTP 200。[发布记录](../../../../../../outputs/visualization_publishing/publish_20261118_091820_898651/publication.json) · [下载离线 ZIP](../../../../../../outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/qwen27b_all53_dedup_offline_01.zip)

沿用前 31 条预览的双语回放模板，收录 C01–C53、19 个场景和 4,837 个有 JEV 评分的动作前视帧。默认显示 Qwen 去重后保留的 376 个节点。关闭节点去重开关可查看全部 494 个候选，选择一次比较可查看对应的 A、B 前视图、分支描述和判定理由。

338 次模型比较中，118 次判为相同，210 次判为不同，9 次有效回答判为不确定。另有 1 次证据引用校验失败。C51 的 S01 与 S02 比较中，模型原答判为不同，其中一个匹配分支缺少 B 帧引用。实际去重流程保留两个节点。页面单列该次校验失败，并提供模型原答与实际处理结果。全组共移除 118 个节点。

[输入快照](snapshot.json)登记每条轨迹的结果文件及 SHA256、实际保留节点、组内统计及 C51 的原始响应哈希。[英文展示文本](review_en.txt)与 933 个不同的中文原文逐条对应。页面收录节点去重阶段的结果。

[浏览器验收](browser_online_package.json)覆盖 53 条轨迹。逐条核对双进度条和去重前后节点 ID，两种语言下检查任务指令、去重提示词、每次判定的理由、分支数量及证据图片引用；C51 单独核对原始回答和失败标记。验收未记录脚本或资源错误。

离线目录为 `outputs/deviation_progress/v003/run_20261118_01_qwen27b/exports/all53_dedup_01/`，解压同级的 `qwen27b_all53_dedup_offline_01.zip` 后打开 `index.html`。在线构建目录为 `outputs/visualization_publishing/qwen27b_route53_dedup_v001_web_20261118_01/`。

离线 ZIP 共 77,589,823 字节，4,859 个文件均通过 ZIP 校验。将 HTML 的内嵌字体替换为在线字体路径后，离线与在线 HTML 逐字一致。

| 文件 | SHA256 |
| --- | --- |
| 离线 ZIP | `73a4e82cad3a93149aea36534c0557c4cf978ac0aadd10fc80c00f0ba6da47cb` |
| 离线 HTML | `d33d6d7303ad5208df442f9b7712857e629a60eaa299bfadbb240b60a2a1f497` |
| 在线 HTML | `a80a651295f7b548d8ef33fd6246217fa0b413650f73907d35ee67a046d58618` |

复现导出使用 `scripts/export_route53_deepseek_dedup.py --snapshot <本目录>/snapshot.json --offline <新离线目录> --online <新在线目录>`，模型与样本由快照指定。
