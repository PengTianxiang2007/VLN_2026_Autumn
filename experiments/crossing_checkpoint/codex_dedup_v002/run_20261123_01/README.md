# VLNVerse C01–C10 · GPT-6.2 Astra 三帧去重

状态：调用失败，等待可用 GPT-6.2 Astra Codex 配置；用户明确授权同十条、十个进程并行。

目的：对既有 89 个原始候选进行第一轮去重；预计 63 次比较。复用 v001/run_20261123_02 完全相同的 seed=2 轨迹、候选编号与图像。只删除每组 ±1 观测，实际输入为 A-2、A0、A+2、B-2、B0、B+2；开始前缺图仍标记缺失。模型 gpt-6.2-astra / medium，每轮超时 600 秒。Codex 无固定采样 seed。

每条新建独立会话，内部显式 resume，不复用旧五帧会话。仍按间隔不超过 8 步比较，same 删旧留新，different/uncertain 保留双方。输出 JSON 格式与校验沿用原版；仅可引用实际提供的三帧标签。不运行导航或 JEV 采样，不占 GPU。

定向验证：三帧附件/提示词一致、±1 引用被拒绝、合法答案按原规则执行，1 项测试通过。源码、Git 提交与差异由运行入口归档；实际每轮 prompt 和图片在独立历史目录。

```bash
.runtime/crossing_vllm27/bin/python -u scripts/run_codex_node_dedup.py --input experiments/crossing_checkpoint/codex_dedup_v002/run_20261123_01/input.json --output outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_01 --workers 10 --model gpt-6.2-astra --reasoning-effort medium
```

输出：`outputs/codex_tasks/checkpoint_dedup/v002/run_20261123_01/`；启动记录位于同版本 `launches/run_20261123_01/`。

完成后在既有对照模板增加 GPT-6.2 Astra 三帧选项，保留 GPT-6 Astra 五帧、Qwen、DeepSeek，另存新发布版本。模型与观测同时变化，不能将差异单独归因于模型或删图。

当前版 SR / 平均 SPL：暂无，已评分 0 条；配对原版 SR / 平均 SPL：暂无，已评分 0 条。

## 实际运行与阻塞

2026-11-23T22:21:41.338750+00:00 启动，主管 PID 2480946；十个独立工作进程与十个独立 thread ID 均已进入任务。2026-11-23T22:22:24.115629+00:00 全部退出。首轮十次请求均被服务端 HTTP 400 / model_not_found 拒绝：

> The 'gpt-6.2-astra' model is not supported when using Codex with a ChatGPT account.

完成 0/10 例，成功比较 0/63，技术失败 10 例，未生成有效去重结果。实际请求每端仅 -2/0/+2，C01 起点缺一张，其余首轮各六张；逐轮请求与服务端原始错误已保留。启动前缓存曾列出该模型；本次刷新后的模型列表不再包含该模型，故缓存不能证明该登录实际可用。未改用 API 或其它模型，未重复提交同一失败请求。

网页导出代码已增加独立 astra62 选项、三帧证据、三/五帧输入标注及旧版结果保留，Python/JavaScript 语法检查通过；因无新版结果，尚未导出或发布，浏览器验收待真实结果。原已发布页面保持原状。

下一步：获得可用 Codex 配置后以新运行编号重跑同十条，完成翻译、浏览器检查和标准发布。2026-11-23 已向用户询问可用配置，未授权自动降级模型。

## 后续模型可用性诊断

用户要求检查可用模型后，通过指定二进制的 `app-server model/list` 直接查询（不依赖共享缓存）。实际 CLI 为 0.164.0，返回八个普通可选模型，均无 6.2：gpt-6.1-terra、gpt-6.1-sol、gpt-6-astra、gpt-6-sol、gpt-6-luna、gpt-5.6-sol、gpt-5.6-terra、gpt-5.6-luna。另两个隐藏模型不作为实验候选。详见 [诊断](model_availability.json)。

同一 CODEX_HOME 的缓存也曾被 client_version=0.167.0 写入，并包含 6.2；因此先前由缓存判断指定客户端可用并不可靠。无图最小 6.2 请求仍返回相同 HTTP 400，排除三帧 prompt 与图片导致该错误。当前证据提示客户端与新模型可用性不一致，不能据此断定账户本身无权限；新版 CLI 实测尚未进行。官方更新记录显示 0.171.0 增加 6.2 模型目录：https://learn.chatgpt.com/docs/changelog 。未升级、替换客户端或启动新一轮十条实验。

对照最小请求：同一二进制、登录和 JSON 协议，gpt-6-astra 用时 36.054 秒成功返回 `{"ok":true}`；gpt-6.2-astra 仍拒绝。这说明该登录与网络整体可用，但不能证明其它仅在列表中出现的模型均已实测。
