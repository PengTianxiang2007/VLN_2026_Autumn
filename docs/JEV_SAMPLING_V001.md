# JEV 在线采样 v001：固定版本说明

该方法从连续 JEV 回退点概率生成候选供后续模型审阅，满足有界延迟、输出只追加、历史不可回改。接手命令与当前用户要求见 [JEV_SAMPLING_HANDOFF.md](JEV_SAMPLING_HANDOFF.md)。

## 参数与时间

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| window | 7 | 平滑尺度 N；奇数，3–101 |
| delay | 5 | 总等待步数 D；0–30 |
| high / low | 0.60 / 0.45 | 高分区域的进入/退出阈值 |
| debounce | 2 | 进入/退出需要连续满足的次数 |
| peakDrop | 0.03 | 局部峰两侧的最小落差 |
| initialFloor | 0.45 | 初始原始概率的候选门槛 |
| minGap | 3 | 任意相邻候选的最小位置间距 |
| plateauGap | 5 | 高分区域内部的采样间距 |

令局部峰确认等待 `H=min(2,D)`，平滑等待 `F=D-H`。默认 F=3、H=2，合计5个新反馈步，不是毫秒；不包含上游JEV推理用时。

## 滤波

对原始概率 p，在收到第 t 帧时只发布一次 `i=t−F` 的滤波值。令 `σ=max(0.5,N/6)`、`R=ceil(3σ)`：

$$s_i=\frac{\sum_{j=\max(0,i-R)}^{i+F}e^{-(j-i)^2/(2\sigma^2)}p_j}{\sum_{j=\max(0,i-R)}^{i+F}e^{-(j-i)^2/(2\sigma^2)}}.$$

保留原概率量纲，不做整轨迹P95归一化或基线扣除。`p_i=null` 时 s_i 为 null；其他缺失邻居不参与分子分母。起点只使用实际存在的历史。末尾没有补值或结束时强制刷新。

这是一种有界等待的平滑：以位置i为参照使用最多F步后续观测，以实际发布时刻t为参照只使用已经到达的信息。

## 顺序选点

在实际到达时刻t决定位置 `k=t−D`，位置按顺序各决定一次。

1. **高分区域状态**：未进入时连续 debounce 个 `s_k≥high` 则进入；已进入时连续 debounce 个 `s_k<low` 则退出。缺失值清空区域状态和连续计数。
2. **局部峰分支**：H>0、k>0、`s_k≥low`；s_k 严格高于左侧最多H个值，不低于右侧H个值。两侧各取窗口最小值，峰与两侧最小值的差均须≥peakDrop。窗口有缺失值则不采用峰分支。代码使用 `1e-12` 浮点容差。
3. **入口分支**：本位置使状态进入高分区域，当前值≥low。
4. **区域内分支**：区域激活、当前值≥low、距上个已接受候选至少 plateauGap。
5. **起点分支**：k=0且原始 `p_0≥initialFloor`。该分支使用原始起点概率，不要求平滑起点也达到low；它仍在F0+D时才确认。

同一位置的优先级为 **起点 → 局部峰 → 入口 → 区域内**。所有分支最后接受 minGap 约束；距已接受点太近的新点直接丢弃，后来的高峰不能替换旧点。区域状态仍正常更新。D=0时仅使用起点和区域分支，不等待右侧局部峰。

这里的局部落差不是整段峰突出度；入口与区域内候选也不一定是局部最大值。宽高分区域会产生多个候选，供下一阶段语义判断。

## API 与输出

```js
const Sampler = require('../core/jev_online_sampler_v001.js');
const sampler = new Sampler({window: 7, delay: 5});
// 实际使用时，每到达一个新反馈执行一次。
const result = sampler.push(probabilityYes, consecutiveFrameIndex);
if (result.filtered) appendCurve(result.filtered);
if (result.node) enqueueCandidate(result.node);
```

`push` 只接受[0,1]有限数值或null，frame从0开始连续递增；未提供frame时自动递增。乱序/跳帧、NaN、越界和字符串报错。一个episode结束后新建实例，不复用前一个的状态。

`result.filtered` 为 null 或 `{index,value,raw,emittedAt}`；`result.node` 为 null 或：

| 字段 | 含义 |
| --- | --- |
| id | 稳定编号S01、S02……，接受后不重排 |
| index | 候选在轨迹中的位置k |
| emittedAt | 实际可用时刻k+D |
| delay | emittedAt−index |
| value / rawScore | 该位置的固定平滑值 / 原始概率 |
| kind | initial、peak、entry、plateau |
| drop | 峰分支的局部落差；其余分支为null |

返回的记录使用Object.freeze，不含图像/地图/任务内容。调用方需要自行保存对应图像和导航状态。不要把已经滤波的值再次传给该采样器，它的push输入是原始概率，内部已经完成滤波。

## 约束为何成立

s_i在i+F时计算后固定。决定k所需的最晚平滑值是s_(k+H)，它在k+H+F=k+D时固定。区域状态和最后接受位置只按时间向前更新，既没有全局排序也不重新抑制旧点。因此任意未来续接都无法改变已经发出的记录。

核心只保存有限窗口及计数器，内存与每步计算均为O(N+D)。网页保存整个历史用于离线查看，是展示层行为。候选间距约束会优先保留较早的点，可能压掉稍后的更高峰；这是冻结历史的明确取舍。

## 证据与限制

33条已记录轨迹在默认参数下产生284个候选：起点27、局部峰58、入口35、区域内164。34事件网页含一条重复轨迹，候选引用共298。固定样例包含这些33条原分数及8组合成情形；不含图像或人工标签作为采样输入。

检查覆盖固定输出一致性、15组N/D参数、不同未来续接、不可变记录、延迟、间距、缺失值、末尾不补值和100000步有限状态运行。它们证明实现与在线约束，不能据此推导检测准确率或导航收益。阈值尚未独立校准，后续大模型审阅尚未接入。

设计背景参考 [SciPy peak detection](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html)、[local prominence windows](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html) 以及 [TI hysteresis comparator](https://www.ti.com/tool/CIRCUIT060073)。参数与分支组合是本项目的工程实现，没有声称是已验证的VLN最优算法。
