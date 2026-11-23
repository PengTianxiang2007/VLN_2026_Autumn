# TypeSafe 官方格式与 SDK 核验

更新时间：2026-11-16 UTC。状态：文档、结构和图片校验完成；官方SDK实测完成，api.site图像调用仍失败，未启动导航。

## 目的与依据

用户要求直接阅读TypeSafe官方文档，排查实验性图片协议变更。读取[图像协议](https://docs.typesafe.ai/images)、[OpenAPI定义](https://docs.typesafe.ai/api/system-one)、[错误规则](https://docs.typesafe.ai/api/errors)、[Python SDK](https://docs.typesafe.ai/sdk/python)、[同步客户端](https://docs.typesafe.ai/sdk/python/api/clients/sync)及官方GitHub/PyPI。使用官方SDK `typesafe-sdk==0.7.5`，没有修改导航/JEV方法或冻结的旧脚本。

官方原生方法为POST `/v1/systemone`，使用state、questions及assets；图片需要`TypeSafe-Danger-Zone-Images: true`。JSON/base64仍受支持，multipart为推荐方式。multipart首段须是名为request的JSON，后续图片part与assets中的part逐一对应。SDK的Image对象会自动生成multipart；extra_body可显式提供JSON/base64的assets。这些是官方协议，不等于每个中转渠道都完整兼容。

官方当前要求静态PNG/JPEG、每边280–1568像素、单图不超过16MiB、整个请求不超过32MiB；引用须出现在state/问题正文中。第三方旧文档写256像素的下限，与当前官方280不同，但本项目实际640×480图像满足两者。官方文档内部分小尺寸代码示例仅用于说明类型，不能取代图像限制表。

## 本地验证结果

取历史成功的三帧请求进行校验，完整请求SHA256为`769b099633850b968a6cccedb7838ecf6fa93a44dc229406153949aa06990521`。

- 按当前官方OpenAPI的SystemOneRequest定义运行jsonschema验证：0个错误。
- 三张图片均可严格base64解码，为RGB静态PNG、640×480，约198/214/210KB；没有data URI前缀、动画或损坏。
- 每个图片引用在模型输入正文中恰好出现一次。完整原JSON为833417字节，无UTF-8 BOM，符合已检查的大小要求。
- 这些检查证明符合公开的结构和图片规则，不证明中转转发内容或未公开的上游规则。

公开`api.typesafe.ai/openapi.json`在当前网络返回451，未绕过；改从官方文档公开的`api/system-one.md`提取同页OpenAPI。实际下载的文档、schema、SDK官方PyPI元数据与验证结果保存在outputs中。

## 官方SDK实际对照

均使用用户提供的api.site端点及对应密钥，**不是使用中转密钥直连TypeSafe官方服务**。关闭请求压缩和自动重试，显式关闭环境代理、禁止跳转，图像开关为true。

| 官方SDK请求 | HTTP结果 | 内容核对 |
| --- | --- | --- |
| 文本对照 | 200，响应通过SDK解析 | 有效noul结果 |
| Image对象自动multipart，三帧 | 400 `invalid JSON request` | 首part为request，图片part名称唯一；三张图片字节、模型、state、questions与旧请求一致 |
| extra_body提供JSON/base64，三帧 | 400 `TypeSafe rejected the request` | JSON解析后整体与旧请求相等，图片字节一致 |

请求钩子保存的非敏感头确认两种图片请求都携带图像开关，且没有Content-Encoding。SDK只是改变封装形式，未改变输入图片、提示词或问题。

结论：暂未发现客户端格式不符合当前官方协议。官方SDK亦重现图像失败，api.site至少没有接受该SDK生成的合法multipart请求；JSON/base64失败尚无法从泛化错误定位根因。需渠道提供上游完整detail，或使用TypeSafe官方凭据进行有权限的直连对照，才能继续区分中转兼容、上游或账户问题。没有因此擅自修改正式请求协议或替换方法。

## 环境与执行

按仓库约定通过uv创建独立`.runtime/jev_sdk_probe_20261116`，Python复用现有3.10.15，未改动仿真或模型环境。清华镜像安装无进展后只停止本轮自己的安装PID；随后阿里云镜像成功安装固定0.7.5版本。依赖快照在输出目录。此处无GPU任务。

实现：`scripts/probe_jev_official_sdk.py`，基线Git及实际执行源码hash见对应manifest；每次运行的脚本已冻结在输出目录。

```bash
.runtime/jev_sdk_probe_20261116/bin/python -u -B scripts/probe_jev_official_sdk.py \
  --base-url https://api.site \
  --request outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01/probe_api_site_prev/request_full.json \
  --output outputs/serial_recovery/typesafe_official_sdk_20261116_01
```

JSON/base64补充组加`--base64-only`，输出目录为`typesafe_official_sdk_20261116_02`。运行密钥只经getpass进入内存，不保存完整HTTP头；只记录Content-Type/Length、图像开关等白名单字段。SDK请求原始body不含Authorization。

## 产物与后续

- `outputs/serial_recovery/typesafe_official_audit_20261116_01/`：官方文档快照、OpenAPI、PyPI元数据、format_validation.json及合并summary。
- `outputs/serial_recovery/typesafe_official_sdk_20261116_01/`：文本与multipart的实际请求、响应、源码、图片一致性证明。
- `outputs/serial_recovery/typesafe_official_sdk_20261116_02/`：SDK JSON/base64的请求、响应与整体JSON一致性证明。

完整串行pipeline仍未取得真实仿真闭环通过证据；GPU3原模型按用户要求保留。下一步取决于JEV图像通道恢复或获得能定位问题的上游detail，不自动扩大实验。
