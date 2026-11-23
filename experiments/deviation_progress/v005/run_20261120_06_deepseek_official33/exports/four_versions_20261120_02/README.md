# 四版本对比：去重开关显示修复

用户报告开启去重后仍显示被删除的候选点。根因：四版本导出更改了页面 `tag`，没有同步 `dedup.source_tag`，前端因此将冻结去重记录判定为不匹配，回退显示全部候选。

本次仅同步显示数据标识，并更新原网址及离线包。四组偏航原答、历史有效报警、节点清单不变，不调用模型。DeepSeek v005 实际冻结节点清单与 v003 完全相同，共 53 条、376 个保留节点加 53 个终止节点；对照全部 219 轮已保存结果，A/B 端点均在冻结清单内，未包含删除的候选点。被删除候选对应的 RGB 可以作为区间内普通采样观测，这不使其成为节点。

显示验证已通过：C02 开启去重显示 14 个保留节点，关闭显示全部 15 个原始候选；F50 删除候选只在关闭时出现，重新开启后恢复正确，保留节点标签为重编号后的 S01–S14。终止节点 F129 单独保留。证据见 `check_dedup.cjs`、`dedup_check.json`。复用上一版其他交互检查，不重跑模型或导航。状态：已发布，原入口切换成功。

实现改动：`scripts/export_deviation_four_versions.py` 在更改页面 tag 后同步 `dedup.source_tag`；未绕过去重数据匹配检查。新版本位于 `outputs/visualization_publishing/deviation_four_versions_web_20261120_02/`，旧版完整保留。

HTML SHA256：`6302e7d0b2336b99aed951641c6dbd1fea210f5686eaba2953613d49ef03daf1`。
新版离线包 `vln_v003_v005_four_versions_offline_02.zip`，82,297,932 字节，SHA256：`3b90b49363c7e2fd560aa19ba69f996d09ba4190c55f2eb8278bcdf5277deddc`。模型返回 JSON 和图片资源均未改变。

- [修复后的原网址](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/index.html)
- [修正版下载包](http://134.175.18.101/vln/deepseek_v004_six_web_20261120_02/vln_v003_v005_four_versions_offline_02.zip)

标准发布器通过远端资源哈希和 HTTP 200 检查；原入口页面与四组 JSON 的公网内容哈希一致，ZIP HEAD 大小与本地一致。详细发布时间与核验见 `publication.json`；标准发布记录为 `outputs/visualization_publishing/publish_20261120_135538_683428/publication.json`。原入口备份为 `index_before_four_versions_dedupfix_20261120.html`，旧下载保留。未重新下载整个 ZIP。
