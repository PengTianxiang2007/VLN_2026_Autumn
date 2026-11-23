# EasyJEV 新端点图像验证

更新时间：2026-11-16 UTC。状态：图像接口验证通过，2/2真实请求成功。

用户提供 `https://api.easyjev.online`、对应令牌及[服务文档](https://www.easyjev.online/zh/#/docs)。公开文档为前端页面，已读取实际HTML/应用源码，确认原生POST `/v1/systemone`，文档说明旧JEV模型名继续兼容。没有发送凭据到文档站或其他渠道。

## 实测结果

- GET `/v1/models` HTTP200，共33条，JEV目录名为`typesafe/jev-1.13`、`typesafe/jev-1.14`、`typesafe/jev-latest`。
- 请求模型仍使用原`jev-1.14.0`，实际响应模型为`typesafe/jev-1.14-20261014`，provider为TypeSafe。
- 历史相同F35/F36/F37三帧：HTTP200，yes概率0.64，input_tokens5172，14.12秒。
- 串行联调首帧预检图片：HTTP200，yes概率0.61，input_tokens2535，4.54秒。
- 两次响应均通过项目现有`validate_noul_response`；curl实际发送日志确认图像开关为true，图像请求体不修改。

这是API可用性验证，不是导航或纠错成功。历史同三帧曾返回0.7，此次0.64；新渠道有不同的模型名称封装和token计数，应保留实际来源，不能声称与历史端点数值等价或混用缓存。

## 执行与产物

```bash
benchmarks/vlnverse/.venv/bin/python -u -B scripts/probe_jev_header.py \
  --endpoint https://api.easyjev.online/v1/systemone --catalog --with-header-only \
  --request outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01/probe_api_site_prev/request_full.json \
  --extra-request outputs/serial_recovery/v001/run_20261116_01/preflight_jev/request.json \
  --output outputs/serial_recovery/jev_easyjev_20261116_01
```

源码、完整无凭据请求、实际非敏感请求头、原始响应和概率校验保存于`outputs/serial_recovery/jev_easyjev_20261116_01/`；文档源记录在`jev_easyjev_20261116_docs01/`。凭据getpass输入，仅在进程内存中使用，没有落盘。

后续：按用户原授权继续单条串行联调，使用新运行号02冻结新端点，不扩大任务量、不修改旧结果。协议和原任务记忆恢复规则不变。
