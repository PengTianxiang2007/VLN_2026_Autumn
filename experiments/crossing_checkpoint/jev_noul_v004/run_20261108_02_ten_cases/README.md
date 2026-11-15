# JEV v004：新增10条完整轨迹

状态：准备运行。

沿用 v004 自包含英文 prompt。从冻结61条中排除已经跑过v004的
`kujiale_0123_fix_15_3`、`kujiale_0257_13_4`，再按原清单顺序取前5条失败和
前5条成功：

- `kujiale_0208_21_4`
- `kujiale_0207_41_0`
- `kujiale_0232_72_1`
- `kujiale_0123_fix_19_3`
- `kujiale_0113_1_4`
- `kujiale_0240_0_0`
- `kujiale_0232_12_1`
- `kujiale_0123_fix_1_3`
- `kujiale_0113_66_1`
- `kujiale_0259_26_1`

共862个有效观测，全部一次性提交；最大200个并发worker（用户上限为500）。
所有任务使用严格 `t-2,t-1,t` RGB 和单个 `fallback_point` Noul。每个请求最多重试
5次。对照数据为同一批帧的JEV v002与Qwen4B `best_v001`，不重新调用这两个模型。
