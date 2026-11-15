# lite_v008 / F58、F96、F105三帧探针

状态：已完成。按原有三帧评分规则，仅限制评测step为58、96、105。

样本均为 `kujiale_0207_14_4`：

- frame 58，输入F0056—F0058；
- frame 96，输入F0094—F0096；
- frame 105，输入F0103—F0105。

使用 `prompt_draft01`，每帧只调用Qwen4B一次。除system prompt和评测step白名单外，沿用原规则：当前帧及过去两帧RGB、不含任务指令/动作/地图/标签，temperature=0、thinking=false、max_tokens=256、JSON schema输出，请求seed继续按episode/frame/20261107派生。运行器文件名为probe，但请求由同一`core.crossing_lite.request`生成。

三个step的实际输入与请求seed：

- F58：F0056—F0058，seed 337999615；
- F96：F0094—F0096，seed 1459752198；
- F105：F0103—F0105，seed 612097489。

结果仍均为1分。不运行导航、整批对照或可视化发布，不更新最优版本。
