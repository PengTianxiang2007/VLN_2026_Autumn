# lite_v003 / frame 56 单帧探针

状态：已完成。单次请求有效，结果没有好转。

目的：验证加入“侧向开口可要求短距离转弯”这一条后，`kujiale_0113_1_4` frame 56 的 1 分是否会被纠正。

除新增下列一句外，prompt、三帧输入、模型、请求 seed、参数和 schema 均与 `lite_v002` 保持一致：

```text
A traversable choice may require a short turn into a nearby side opening;
it does not need to be parallel to the robot's current heading.
```

这不是新方法成立证据。单帧结果只用于决定该措辞是否值得进入下一轮同样本对照；不能更新最优版本。

## 结果

- 模型返回：1 分
- 理由：当前视野中仅显示前方走廊和左侧房间，右侧为固定柜体，无其他可选择的通行路径。
- 对照：`best_v001` 为 1 分，`lite_v002` 为 1 分；`lite_v003` 与 v002 的回答相同。
- 结论：加入“短距离侧向转弯不要求与当前朝向平行”后，该单帧没有改善。不能据此评价整批效果，也不更新 current_best。
- 产物：`outputs/crossing_checkpoint/lite_v003/run_20261108_01/`。
