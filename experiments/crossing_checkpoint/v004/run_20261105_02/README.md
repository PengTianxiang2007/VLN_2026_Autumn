# 智谱十条重试 run_20261105_02

用户要求继续重试并跑完。保留原批次，复用其26次成功回答与对应因果历史，剩余562次；10条、10个进程，prompt和样本/存档/评分不变。

修复依据：先前8192输出（含思考）出现length，重试又连接重置。改为流式传输；实际远端输出预算32768，若length则递增至最多131072；网络/429/5xx最多8次指数退避重试。永久鉴权/参数错误快速报告，不盲目重复。单条失败不再立即中止其他条；整体8小时上限。

内部请求保留8192用于校验此前26条缓存哈希，实际API预算及完整请求hash单独写入transport/<pid>.jsonl及reply元信息。这是传输/输出预算变更，不能称作与旧版完全相同的推理设置。JSON仍严格校验，缺失finish_reason的中断流不能当成功。

启动：benchmarks/vlnverse/.venv/bin/python -B scripts/run_crossing_remote.py /mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/v004/run_20261105_02（密钥经stdin，进程结束释放；不落盘）。源代码哈希、Git与工作区差异已保存，流拼接及中断流拒绝的CPU检查通过。模型沿用glm-5.3-flash，思考开启，导航seed2，API不承诺seed复现。

状态：准备启动。完成后评分、诊断并按默认模板导出exports/final/visualization/crossing_review_offline.html。实时状态见status.json，旧结果不覆盖。
