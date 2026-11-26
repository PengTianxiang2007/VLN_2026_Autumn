# C01、C03 新版回退点筛选对照

用户要求优先导出两例，复用 run_20261124_03_retry2 已完成结果，冻结在 outputs/codex_tasks/checkpoint_dedup/v003/selected2_20261124_01。两例 11 个原始候选，新版保留 3 个，旧三帧 Astra 保留 6 个，Qwen 保留 8 个。新版排除 4 个不符合定义的候选和 4 个重复候选，0 不确定、0 格式错误。11 次候选评审及 2 次初始化。

页面使用原模板，新增 v003 默认选项，保留旧 Astra、Qwen 对照。DeepSeek 两例均无覆盖，页面明确标为未评审。英文原答与实际 prompt 保留，逐条提供中文译文。模板交互检查通过，覆盖 2 例、每例 6 种筛选组合、语言切换、原始 JSON、图像、双进度条和移动布局，见 browser_check.json。

离线 HTML 为 outputs/codex_tasks/checkpoint_dedup/v003/selected2_20261124_01/exports/c01_c03/index.html，在线目录为 outputs/visualization_publishing/codex_memory_c01_c03_web_20261124_01，离线包为 outputs/codex_tasks/checkpoint_dedup/v003/selected2_20261124_01/exports/c01_c03_offline.zip。离线 HTML SHA256 为 20c2e28de94d51b9e2271bc85fa74e86a82e3cf492179f2c0f524071836de929，ZIP SHA256 为 663b71dfd2385c0d3960468ca36908b06b629fc6f2569eaa9788c5068106b799。已发布，全部远端 SHA256 与公网 HTTP 200 检查通过。发布记录为 outputs/visualization_publishing/publish_20261124_101009_314271/publication.json。

页面为 http://134.175.18.101/vln/codex_memory_c01_c03_web_20261124_01/index.html ，离线包为 http://134.175.18.101/vln/codex_memory_c01_c03_web_20261124_01/c01_c03_offline.zip 。

其余七例已按用户要求在 run_20261124_05_restart7 独立目录重启，3 路并发。旧的部分结果和会话保留。新版按已确认协议跳过重复当前候选，证据不足时保守保留并标记。当前版及配对原版 SR、平均 SPL 均暂无，已评分 0 条。
