# 上午无全景 v001 提示词：保留基准

状态：已按用户要求冻结保留（2026-11-06）。基准 ID：`agent-route-choice-v001-morning-20261106`。

这里的“上午版”指原十条 Qwen3-VL-32B-Instruct 实际运行的无全景两次调用版本，prompt revision 为 `02_crossing_definition_permissive_branches_english_output`，不是更早未运行的草稿，也不是 v002 全景版。

- [第一轮：盘点支路，英文实际稿](01_inventory_en.txt) · [中文对照](01_inventory_zh.txt)
- [第二轮：识错与恢复选路，英文实际稿](02_choose_en.txt) · [中文对照](02_choose_zh.txt)
- [协议快照](protocol.json) · [模型配置快照](models.json) · [来源和哈希](manifest.json)
- 实际请求还包含用户消息中的输入元数据、图片及 JSON schema；两轮 schema 分别保存在 `call1_schema.json`、`call2_schema.json`。本目录的中文提示词只供审阅，未发送给模型。

来源为 `outputs/agent_route_choice/v001/preparation_20261106_04/prompts/`。四份提示词与原实验登记文件逐字节一致；20份实际请求的 system 提示词和相应 schema 全部核验一致。实际完整输入、源码和运行版本沿用原准备与运行 manifest，不能用本次归档时的 HEAD 代替历史运行版本。

原结果：10条、20次响应、9条协议有效，sample_07 排除 B1 后又选择 B1。语义选路正确率尚未完成复核；保留基准不表示已证明正确率或优于其他模型。

后续晚间手工数据优化单独登记为 [human_v002](../../../human_v002/README.md)，从新版本复制修改；本目录及原提示词、原响应、旧HTML不覆盖。配置中的历史启动授权只作来源记录。
