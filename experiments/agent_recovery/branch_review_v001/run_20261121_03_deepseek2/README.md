# DeepSeek 两例并行复核

使用 v006 的 C50（S04/F15）、C07（S03/F41）。各自原封复用十例 Qwen 运行对应的 messages，包括完整 Prompt、Schema、七张原图和时序标签。两进程各一次，关注其自然输出能否覆盖右侧开口。沿用历史官方接口 deepseek-flash，temperature=0、top_p=1、max_tokens=4096，关闭 thinking，DeepSeek 请求未指定 seed。run.py 从标准输入读取凭据，运行环境为 .runtime/crossing_vllm27/bin/python。输出保存在 outputs/agent_recovery/branch_review_v001/run_20261121_03_deepseek2，完成后自动写入 results.json。

C50：complete，HTTP 200，支路 [('B1', 'front'), ('B2', 'front_left'), ('B3', 'front_right')]，此前匹配 B1。

C07：complete，HTTP 200，支路 [('B1', 'front'), ('B2', 'front_right')]，此前匹配 B1。
