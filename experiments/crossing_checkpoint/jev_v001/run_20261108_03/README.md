# JEV v001 / run_20261108_03

状态：失败；curl 实际已返回 F58 的有效 JEV 响应，但状态标记字符串在
curl config 中夹带了换行，导致程序没有解析到 HTTP 状态并误报传输失败。
不把该响应补记为正式结果，修复后另起 `run_20261108_04`。

样本、问题、图像和分数映射与 `run_20261108_02` 相同，仅将 HTTP 传输从 urllib
改为 curl。完整非密钥请求保存为 `request_full.json`；Authorization 通过 curl config
stdin 注入，不进入命令行参数或磁盘。

`run_20261108_01` 和 `run_20261108_02` 的传输失败记录保留且不参与结果。
