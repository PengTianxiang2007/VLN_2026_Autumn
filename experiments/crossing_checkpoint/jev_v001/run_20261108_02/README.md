# JEV v001 / run_20261108_02

状态：失败；Python urllib 发送含图像 JSON 时连接被服务端以
`ssl.SSLEOFError` 断开，未获得业务响应。请求产物保留。

与 `run_20261108_01` 的样本和问题完全相同，仅修复 HTTP 客户端签名：显式发送
`User-Agent: rightapi-jev-node/1.0` 和 JSON `Accept` 请求头。另增加失败时写回
`status.json` / `partial.json` 的收尾逻辑。

失败运行保留在 `run_20261108_01`，不混入本批结果。
同一完整请求经 curl 重放返回 HTTP 200。为避免把传输失败混入结果，改用 curl
作为适配器并另起 `run_20261108_03`；密钥仅经 curl config stdin 进入进程内存。
