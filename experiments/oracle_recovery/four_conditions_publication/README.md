# Oracle 四条件既有回放发布

2026-11-07；状态：发布完成。仅整理已有 HTML，不运行模型、仿真或新实验。

用户描述对应最初尽早纠正十条，以及后续同十条的短/中/长语义延迟配对实验。
尽早组为独立历史运行；仅三档延迟共享前缀，不把四组误报为同一次错误的严格配对。
与3/5/8/12米阈值的旧五组实验区分。

源文件：
- outputs/oracle_crossing/seed2_10_multi_20261103/oracle_early10_offline.html
- outputs/oracle_crossing/paired_delay10/run_20261104_01/oracle_paired_delay10_offline.html

计划：保留原始数据，补齐十条任务指令的中文翻译及中英文切换，拆分媒体按需加载，统一入口连接两个回放。
发布版本 oracle_four_conditions_20261107_01；产物 outputs/visualization_publishing/oracle_four_conditions_20261107_01/。
版本、源文件哈希、实际 Git HEAD 和新导出脚本哈希记入产物 manifest；不替代历史实验版本。

## 发布结果

网址：[Oracle四条件回放](http://134.175.18.101/vln/oracle_four_conditions_20261107_01/index.html)。
包含尽早纠正10条及语义短/中/长30项结果；原实验JSON逐字节保留，十条任务指令提供中文/English切换。
本地浏览器检查：尽早18次、延迟33次纠正边界，22个语义阶段、8项未触发，播放/拖动/筛选/CSV导出/移动端通过；两页各10条双语切换均保持帧位置，无JS错误。
全部3259个发布文件远端SHA256通过；入口、两个回放及代表性资源公网HEAD与大小检查通过。本次未重复全量公网下载。
发布记录：`outputs/visualization_publishing/publish_20261107_073855_085084/publication.json`。数据审计、浏览器证据与源版本见输出目录中的 `data_audit.json`、`checks_early/`、`checks_paired/`、`manifest.json`、`public_paths_check.json`。
原早纠正/配对记录分组保持，未重新运行模型或导航。下一步为用户网页审阅。
