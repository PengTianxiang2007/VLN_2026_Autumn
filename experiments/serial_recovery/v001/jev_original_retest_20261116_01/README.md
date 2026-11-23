# 原成功脚本复测 api.site

更新时间：2026-11-16 UTC。状态：复测完成，仍HTTP400；没有启动导航。

用户明确要求重新测试上一个api.site渠道，并使用以前成功的调用脚本。本次直接运行未修改的 `scripts/probe_anyaigc_jev_systemone.py`；该脚本虽以anyaigc命名，支持通过 `--endpoint` 指定api.site，历史成功记录就在 `probe_api_site_prev/`。

配置：`https://api.site/v1/systemone`、`jev-1.14.0`、原样本 `kujiale_0036_0_0` 的F35/F36/F37，用户本轮提供的api.site密钥通过无回显输入传入。不声称密钥与2026-11-09历史成功密钥相同，历史密钥未保存。保留原脚本的请求头、构建逻辑、超时和重试规则；仅输出tag改为新编号。

## 结果与一致性

- 历史2026-11-09结果：HTTP200，yes概率0.7。
- 本次结果：脚本退出码1，`JEV HTTP 400: TypeSafe rejected the request`，原始终端错误已保存。
- `core/jev_node.py` 与历史成功实验冻结源码逐字节相同，SHA256 `d6829524cc9d7628d1ac41e4e6ddeaa454a92a63079fdb390d9b6827d471d8e2`。
- 新旧 `request_full.json` 逐字节完全相同，SHA256 `769b099633850b968a6cccedb7838ecf6fa93a44dc229406153949aa06990521`。
- 新旧 `images.json` 逐字节完全相同。
- 新旧请求语义规范化哈希均 `0d64d20a80d1c0a7ff6599151e473b6864b172e4f93b90846db1689efee5edda`。

旧调用路径也可复现当前失败，不是只有本轮新诊断代码才失败。当前这组端点/密钥的图像调用尚未恢复；上述结果不能单独区分网关、上游或账户配置原因。

## 命令与产物

```bash
env -u JEV_API_KEY benchmarks/vlnverse/.venv/bin/python -u -B \
  scripts/probe_anyaigc_jev_systemone.py \
  --endpoint https://api.site/v1/systemone --model jev-1.14.0 \
  --tag probe_api_site_prev_retest_20261116_01
```

输出根：`outputs/crossing_checkpoint/jev_noul_v004/wrong_choices34_anyaigc_20261109_01/probe_api_site_prev_retest_20261116_01/`。这是新子目录，历史成功 `probe_api_site_prev/` 未修改。

保留 `retest_manifest.json`、`source/`执行源码快照、请求及图像审计、`terminal_output.txt`、`comparison.json`。基线Git以manifest记录为准；不覆盖或改造旧调用脚本。后续仍需渠道恢复或提供上游具体错误才能继续真实闭环验证。
