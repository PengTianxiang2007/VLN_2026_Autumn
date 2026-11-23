# Cttai 端点与新令牌验证

更新时间：2026-11-16 UTC。状态：诊断完成，当前令牌没有可用JEV渠道，未启动导航。

用户提供 `https://llmapi.cttai.art` 和新令牌，授权测试。令牌通过无回显输入进入内存，仅向该域名发送；不写参数、源码、产物或全局配置。

## 实测

| 请求 | 返回 | 含义 |
| --- | --- | --- |
| GET `/v1/models` | 200，`data: []`、`success: true` | 当前令牌模型列表为空 |
| POST `/v1/systemone` | 404，`Invalid URL (POST /v1/systemone)` | 当前地址未提供该原生路径 |
| POST `/systemone` | 200，New API HTML首页 | 网页回退，不是推理成功 |
| POST `/v1/chat/completions`，模型jev-1.14.0 | 503，`model_not_found` | 明确提示default (distributor)分组没有可用模型渠道 |

原生请求使用以前成功的完整F35/F36/F37图像请求，逐字节不变；curl实际发送记录确认 `TypeSafe-Danger-Zone-Images: true`。聊天兼容与无v1路径仅使用最小文本探针定位路由，不替换正式JEV协议，也不算图像或导航结果。

兼容路由错误原文：`No available channel for model jev-1.14.0 under group default (distributor)`。请求ID：`202611160551095468094358268d9d661g0wqQb`。

需要平台为当前令牌配置可用的JEV渠道/分组，并提供支持的原生SystemOne路径；不能由现状推断整个平台永久不支持JEV。

## 启动方式与证据

```bash
benchmarks/vlnverse/.venv/bin/python -u -B scripts/probe_jev_header.py \
  --endpoint https://llmapi.cttai.art/v1/systemone --catalog --with-header-only \
  --request outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01/probe_api_site_prev/request_full.json \
  --output outputs/serial_recovery/jev_cttai_20261116_01
```

`outputs/serial_recovery/jev_cttai_20261116_01/` 保存实际探针源码、manifest及源码哈希、完整无凭据请求、目录摘要、原生错误和实际请求头。请求SHA256 `769b099633850b968a6cccedb7838ecf6fa93a44dc229406153949aa06990521`，与历史成功请求一致。

`outputs/serial_recovery/jev_cttai_routes_20261116_01/results.json` 保存后续三个路径的原始响应。补充只读探针经命令行Python运行、密钥getpass输入，无自动重试。已有历史实验与正式pipeline配置不改，GPU3原模型继续保留。
