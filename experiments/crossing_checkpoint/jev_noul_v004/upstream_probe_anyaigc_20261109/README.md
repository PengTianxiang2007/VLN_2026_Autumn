# AnyAIGC 上游阻塞记录：JEV v004 人工 34 点

状态：已完成请求准备与精确复用审计；新网关上游持续 HTTP 429，正式调用尚未提交。

## 目的

只对 `seed2_human_v001` 中人工标记为 `wrong_choice` 的 34 个错误选择点运行当前
最佳 JEV `jev_noul_v004`，随后与同一批点的 Qwen3.5-4B 1–5 分对照，并发布事件级
三栏可视化。

不跑全部 61 条 episode，不把普通 Crossing 混入本批结果，不评价路线是否选对。

## 固定协议

- 样本：34 个 `wrong_choice`，分布在 33 条 episode；`kujiale_0257_82_4`
  有 F12、F37 两个错误点。
- 模型与版本：`jev-1.14.0`，`jev_noul_v004`。
- 输入：严格因果的 `t-2,t-1,t` RGB；起点不足两帧时只给已有帧。
- 问题：单个 `fallback_point` Noul，只返回 yes 概率。
- 图像输入不包含任务、动作、位置、地图、标注类型、成败、参考路线或旧回答。
- 已有结果只有在重新构造的完整请求 SHA256 与旧记录完全一致时才复用。
- 用户指定并发上限 500。缺失点为 29 个，因此所有缺失任务一次提交，最多启用
  29 个 worker，不启动无任务的 471 个进程。
- 每任务最多 5 次 HTTP 尝试；失败原样保留，不用零值或默认分数填补。

## 已确认结果

34 个点中 5 个可从既有 v004 完整观测结果精确复用：

| episode | frame | JEV yes probability |
| --- | ---: | ---: |
| `kujiale_0113_1_4` | 22 | 0.75 |
| `kujiale_0123_fix_19_3` | 6 | 0.77 |
| `kujiale_0207_41_0` | 13 | 0.61 |
| `kujiale_0208_21_4` | 2 | 0.89 |
| `kujiale_0232_72_1` | 6 | 0.82 |

需新调用：29 个点、28 条 episode。

## 新网关阻塞

用户提供 `https://anyaigc.ai/v1`。核验结果：

1. `/v1/models` 使用新 key 鉴权成功，`jev-1.14.0` 与 `jev-1.13.0` 均存在。
2. 平台价格配置明确声明 JEV 原生路径为 `/v1/systemone`，不是仅靠
   `/v1/chat/completions` 适配。
3. 2026-11-09 对 `jev-1.14.0` 的原生 Noul 请求连续探测两轮，每轮最多 5 次退避，
   全部为 HTTP 429：
   `Current group upstream load is saturated, please try again later`。
4. `jev-1.13.0` 诊断请求同样 429，说明是共享 `jev-1` 上游组的可用性问题，不是
   1.14 单模型或本地请求格式问题。
5. `/v1/chat/completions` 兼容路由同样 429。
6. 平台官方备用域名 `www.openlux.ai` 对相同原生请求同样 429；
   `www.anyaigc.ai` 返回 HTTP 405，不用于正式请求。

在这些条件下提交 29 个并发任务只会制造 145 次必然失败的请求，不会产生可分析结果，
因此正式 runner 暂停在单请求成功验证之前。

## 代码与输入审计

- Runner：
  [`scripts/run_jev_noul_v004_wrong_choices34_concurrent.py`](../../../../../scripts/run_jev_noul_v004_wrong_choices34_concurrent.py)
- 数据源：
  `outputs/crossing_dataset/seed2_human_v001/run_20261106_01/crossing_seed2_human_v001`
- Qwen 对照：
  `outputs/crossing_checkpoint/lite_full_v001/run_20261108_01/annotated_point_scores.json`
- 准备检查：34 events / 34 unique event-frame keys；5 exact reuse / 29 missing。
- 凭据只从无回显 stdin 进入父进程内存，再由 worker 环境继承；不写入请求、manifest、
  status、日志或源码。

## 待完成

1. 在任一原生单点探针收到合法 `answers.fallback_point.type == "noul"` 响应后，
   一次提交 29 个缺失任务。
2. 核验 34/34 行、29 个新调用、5 个复用、请求 SHA、原始响应和状态。
3. 制作中文默认、English 可切换的事件级三栏对照页：34 点列表、真实户型与位置、
   RGB/三帧输入、JEV 概率、Qwen 1–5 分及原始 JSON。
4. 按统一发布流程上传并记录网址、SHA256 和验证范围。
