# v006 全部回退节点的第一次支路识别

2026-11-21，继续使用已保留的 GPU3 Qwen3.8-27B-FP8 服务，完成 v006 首次报警指定的全部回退节点。53 条轨迹中 47 条有目标，6 条无目标（C04、C18、C23、C35、C40、C41）。47 例各有七张原始 PNG。

沿用 [十例运行](../run_20261121_01/README.md) 的中文 Prompt、Schema 和推理参数。节点三向补采图依次为左 +70°、正前 0°、右 −70°，后四张为 C+2、+5、+8、+10 实际前视。每个新案例一次请求，只盘点当前直接支路并匹配此前所走支路。seed=2，temperature=0，top_p=1，top_k=-1，max_tokens=4096，关闭 thinking。模型使用七图及标签，任务指令不参与这次判断。

已有 C42、C46、C49、C50、C07、C05、C09、C10、C20、C21 的十份原始答复与输入一并复用。新增 37 例按编号顺序处理。启动前服务 PID 994127 及本机模型列表均已核对，沿用现有端口 56923。调用结束后按既有指令保留模型。

```bash
.runtime/crossing_vllm27/bin/python -Bu scripts/run_recovery_branch_review.py \
  --continue-from outputs/agent_recovery/branch_review_v001/run_20261121_01 \
  --output outputs/agent_recovery/branch_review_v001/run_20261121_02_all47 --execute
```

输出目录为 `outputs/agent_recovery/branch_review_v001/run_20261121_02_all47/`。其中 manifest 登记 Git HEAD、实际源码快照、未提交差异来源、v006 上游与输入图片哈希、每例的回退节点及用图。results.json 汇总本批与复用结果，cases/ 保留每例的请求、响应和原答。进度见 status.json。

## 结果

10:43 UTC 完成。已处理 47/47 个回退节点，其中新增 37 例、复用 10 例。格式有效 47 例，共列出 101 条支路，匹配到此前所走支路 47 例、模型回答不确定 0 例。

[逐例结果摘要](summary.json) 给出每条轨迹的节点、step、支路数及此前匹配的支路编号与方向。原答保存在输出目录的 cases/。这些数量描述模型输出，本批未做人工准确率评分。

[Qwen / DeepSeek 全量对照网站](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/index.html) · [离线包](http://134.175.18.101/vln/recovery_branch_models_v006_47_web_20261121_02/recovery_qwen_deepseek_v006_47_offline.zip)。
