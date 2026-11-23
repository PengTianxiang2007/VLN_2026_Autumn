# AnyAIGC 新端点与令牌验证

更新时间：2026-11-16 UTC。状态：验证完成，JEV不可用，完整串行仿真仍阻塞。

用户本轮提供 `https://anyaigc.ai/v1` 和新令牌，授权测试。凭据仅由 getpass 无回显输入进入内存，没有写入源码、命令参数、请求体或记录。仅向用户指定域名发送此令牌。

## 实际请求与结果

- 原生路径：`POST https://anyaigc.ai/v1/systemone`，模型 `jev-1.14.0`，固定已有单帧和已知三帧请求，不变更JEV提示词或图片。
- 两次 curl 实际发送记录均确认 `TypeSafe-Danger-Zone-Images: true`。
- 单帧与三帧均 HTTP 404，错误码 `model_not_found`，消息 `No available channel for this model on the current token`。
- 随后 `GET https://anyaigc.ai/v1/models` HTTP 200，目录返回321个模型，匹配JEV/TypeSafe的条目为0。

这说明新令牌可以鉴权访问模型目录，但当前请求没有可用JEV渠道；不是本轮图像开关缺失。不能由此推断整个平台永久不支持JEV，也不能把2026-11-09另一轮的429问题当成本轮原因。

## 复现与产物

```bash
benchmarks/vlnverse/.venv/bin/python -u -B scripts/probe_jev_header.py \
  --endpoint https://anyaigc.ai/v1/systemone --with-header-only \
  --request outputs/serial_recovery/v001/run_20261116_01/preflight_jev/request.json \
  --extra-request outputs/serial_recovery/v001/run_20261116_01/preflight_jev/known_three_frames/jev-1.14.0.request.json \
  --output outputs/serial_recovery/jev_anyaigc_20261116_01
```

脚本基线Git为 `7ce5f9fee30686bae304425bc84c36b3fbedc39c` 加当前未提交新增探针；实际执行探针已冻结在输出目录。再次运行需更换输出编号。

- `outputs/serial_recovery/jev_anyaigc_20261116_01/`：执行源码、两份完整无凭据请求、HTTP响应、实际非敏感请求头、请求体哈希。
- `outputs/serial_recovery/jev_anyaigc_catalog_20261116_01/catalog.json`：只读模型目录诊断摘要。
- 单帧失败请求ID：`20261116093554682143265XVP21Dm0`。
- 三帧失败请求ID：`2026111609355869492660CH2ZJouM`。

## 下一步

需要AnyAIGC确认新令牌的JEV渠道可用性，或提供能调用JEV的令牌。没有把此失败端点替换进正式实验配置，没有重启仿真或释放用户要求保留的模型。
