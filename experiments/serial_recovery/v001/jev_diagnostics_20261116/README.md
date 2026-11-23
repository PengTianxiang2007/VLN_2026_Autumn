# JEV 图像接口诊断

更新时间：2026-11-16 UTC。状态：诊断完成，图像调用仍阻塞。未启动新的仿真或导航实验。

## 目的与范围

用户要求优先解决 JEV，按 Right Code 文档核对模型，并分别通过直连和用户代理 `http://127.0.0.1:7892` 测试。同一密钥、同一 `https://api.site/v1/systemone` 端点；每种请求均独立保存结果。未修改全局代理、渠道设置或模型配置。

官方入口：[模型总览](https://docs.rightapi.io/docs/rc_jev/)、[图片协议](https://docs.rightapi.io/docs/rc_jev/images)、[接口与错误码](https://docs.rightapi.io/docs/rc_jev/api)、[SDK](https://docs.rightapi.io/docs/rc_jev/sdk)。交叉核对 [TypeSafe 模型表](https://docs.typesafe.ai/models)。两份模型文档均声明 1.13/1.14 支持图片，区别是 box 框选仅 1.14 支持。本项目发送 noul，不发送 box。

## 实测结果

| 对照 | 直连 | 7892 代理 |
| --- | --- | --- |
| 文档原样纯文本请求，1.14 | HTTP 200，返回有效答案 | HTTP 200，返回有效答案 |
| 项目原始单帧图像请求，1.14 | HTTP 400，TypeSafe rejected the request | 相同 HTTP 400 |
| 最简单帧 PNG JSON 请求，1.14 | HTTP 400，TypeSafe rejected the request | 相同 HTTP 400 |
| 按文档构造 multipart，1.14 | HTTP 400，invalid JSON request | 相同 HTTP 400 |

额外直连检查：

- 1.14 和 1.13 的文本均 200，响应 model 分别与请求版本一致；同一最简图像请求均 400。
- `jev-latest`、`jev-preview` 文本/图片均被渠道以“模型已停用，请选择其他模型”拒绝；诊断不改变正式配置。
- 纯文本加上图像开关仍 200；PNG 改普通 JPEG、请求头改小写均未解决。
- 单张 320×320 RGB 纯红 PNG 传输对照也返回 400，排除了原场景图像内容和大请求体是唯一原因的解释。此图仅为接口诊断，不是导航样本。
- 实际原图是 640×480、RGB、静态 PNG，204509 字节，base64 解码与 Pillow 校验通过；请求已带 `TypeSafe-Danger-Zone-Images: true`，引用存在且无请求压缩。

结论：当前配置使用文档明确支持图像的 `jev-1.14.0`，不能归因为选中了纯文本模型。密钥与两个版本的文本推理可用，切换本机代理路径没有解决图像失败。图像请求仍不可用；仅凭网关返回的泛化错误，无法断定是网关转发、上游图像功能、账户配置还是未披露协议限制，不能冒充已定位服务端根因。

## 证据与复现

源码：`scripts/probe_serial_endpoints.py`。基线 Git：`7ce5f9fee30686bae304425bc84c36b3fbedc39c`，脚本是本轮未提交新增文件。整理时源码与 SHA256 保存于本目录对应 outputs 诊断包；早期探针源码未逐次冻结，不把整理版冒充早期执行快照。

结果目录均在 `outputs/serial_recovery/`：

- `api_diagnostics_20261116_04/results.json`：直连/代理 8 次请求。
- `api_diagnostics_20261116_05/results.json`：开关、编码与请求头兼容性 4 次请求。
- `api_diagnostics_20261116_06/results.json`：四个模型名的文本/图像 8 次请求，以及无凭据完整请求。
- `api_diagnostics_20261116_07/results.json`：简单图片 1 次请求及无凭据完整请求。
- `v001/run_20261116_01/preflight_jev/`：此前模型目录和已知成功三帧的重放诊断。

01/02 探针在密钥输入前终止；03 因本地 httpx 0.25.2 不接受 `proxy` 参数而未发出请求，随后改用该版本支持的 `proxies`。DeepSeek 图像预检亦在密钥输入前取消，遵从用户先处理 JEV 的最新要求。

```bash
benchmarks/vlnverse/.venv/bin/python -u -B scripts/probe_serial_endpoints.py \
  --request outputs/serial_recovery/v001/run_20261116_01/preflight_jev/request.json \
  --output outputs/serial_recovery/api_diagnostics_NEW \
  --routes direct proxy7892
```

密钥通过无回显输入进入进程，不写参数或产物。重试须使用新输出目录。版本对照用 `--model-check --routes direct`；简单图片用 `--synthetic-image --routes direct`。

可交服务方查询的请求 ID：

- 1.14 图片失败：`59e43b04-b9da-4113-89ea-3fb7835152af`。
- 1.13 图片失败：`6c051016-38cf-4fe5-a26f-6d9a83c8767e`。
- 简单图片失败：`7a8b9261-1b20-4be7-ab9d-c3a0fe9e4b58`。
- 对照 1.14 文本成功：`183c7c6f-a2a5-448a-843b-94c27d54aee1`。

## 后续条件

### 用户追问请求头后的实际发送核验

使用 `scripts/probe_jev_header.py` 对同一份项目单帧请求进行两次 curl 直连，唯一请求差异是是否携带 `TypeSafe-Danger-Zone-Images: true`。两次请求体 SHA256 都为 `560ab612671ec5b55975927f81690499088926376a8da9031c745b0bcfde276f`。

`outputs/serial_recovery/jev_header_wire_20261116_02/results.json` 保存 curl 实际发送日志的非敏感请求头白名单：带头组明确出现 `> TypeSafe-Danger-Zone-Images: true`，不带头组没有该行。两次均 HTTP 400 `TypeSafe rejected the request`。完整 curl trace 和 Authorization 不落盘，诊断源码已随02冻结。01在密钥输入前修正状态码输出格式并终止，没有发出请求。

该检查证明客户端发往 api.site 的请求确实带了图像开关；不能证明 api.site 转发给 TypeSafe 时仍保留此头。网关转发是否遗漏仍是待验证假设，不是已确认根因。原 `core/jev_node.py` 调用亦已包含该请求头。

需要服务方根据请求 ID 返回上游具体拒绝原因或修复图像通道，再用最小图像和真实三帧确认。没有擅自换 JEV 方法、用历史概率替代实时输出、向其他服务发送此密钥或恢复导航。GPU3 原 StreamVLN 模型保留；完整串行闭环仍未通过实际验证。
