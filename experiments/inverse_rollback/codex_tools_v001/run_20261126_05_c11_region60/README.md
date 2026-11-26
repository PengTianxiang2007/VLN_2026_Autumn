# C11 回退到 S05 区域 · 60 动作上限

2026-11-26。kujiale_0128_fix_20_0，seed 2。使用同一次 Astra medium 偏航评审的父会话 `01a21418-31a2-7261-aeff-69b81c8aa1f2`，从第 12 轮完成处分叉，独立于运行 04。原 Isaac 进程中按同一多视角采集 F57 终止帧重新初始化，目标 S05（F45）。用户要求回到附近、当前位置符合回退点定义、能看清当时的其他支路。[实际英文 prompt](prompt.txt)。模型自主判断；F45 的水平几何误差供事后对照，单独记录视角依据。每个前进和转向算一个动作，观察及 finish_return 零计步。第 61 次移动请求在物理执行前强制退出，保留实际终点及单台原仿真。

Git 基线 `60c8751e59bdfddbc57a3efbe2955e3352ea02bb`，已有上轮动作计数修复与运行、导出登记为未提交改动。模型 gpt-6-astra / medium，代理 127.0.0.1:7892。仓库根目录运行 `python3 experiments/inverse_rollback/codex_tools_v001/run_20261126_05_c11_region60/run.py`；在原 H1 控制台先按同一摆位过程接入本轮 60 步端点。

## 结果

独立分支 `01a21834-13fc-7443-b988-c0ddb46a5d8f` 从 F57 开始。在 31 个移动动作（27 次右转、4 次前进）、1 次独立观察后调用 `finish_return`，尚余 29 步。工具返回 `return_declared`，31 步全部取得原生回执。F45 的起始水平距离为 2.016 米，第 24 步最近为 0.984 米，终点为 1.060 米。Codex 正常退出（返回码 0），动作接口已脱离，原 Isaac 进程 3122551 保留在现场 F88。

模型以木椅、沙发边和柜子定位，并称转身时分别辨认出餐区与客厅。回执图像显示，第 8 步可见餐桌椅，第 22 步可见客厅的电视和茶几。终点前视图主要为白墙，局部可见木椅与柜缘，两条支路并未同时入镜。此处记录模型主动结束及所依据的观察，未单独评定语义回退成功。当前版与配对原版的整条导航 SR、平均 SPL 均暂无，已评分 0 条。

[运行结果](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_05_c11_region60/result.json) · [实际英文 prompt](prompt.txt) · [末次前视图](../../../../outputs/inverse_rollback/codex_tools_v001/run_20261126_05_c11_region60/live/frames/00033.png)

## 回放导出

从根目录运行 `backbone/streamvln/.venv/bin/python -B experiments/inverse_rollback/codex_tools_v001/run_20261126_05_c11_region60/replay.py`。沿用原 C11 地图、历史评审与动作回放模板，收录 58 个历史位置、33 次实际工具调用和 5 条控制分支发言。区域判定页用距离曲线标记最近位置及实际停点，单独提供餐区和客厅实拍跳转。

[离线 HTML](../../../../outputs/inverse_rollback/exports/c11_region60_20261126_01/release01/index.html) · [导出清单](../../../../outputs/inverse_rollback/exports/c11_region60_20261126_01/release01/export.json)

[公网回放](http://134.175.18.101/vln/c11_codex_region60_f57_f45_web_20261126_01/index.html) · [离线 ZIP](http://134.175.18.101/vln/c11_codex_region60_f57_f45_web_20261126_01/replay.zip) · [发布回执](../../../../outputs/visualization_publishing/publish_20261126_142323_430934/publication.json)。发布时间 2026-11-26T14:23:29.491665+00:00，远端 95 个文件的 SHA256 均通过，公网入口 HTTP 200。本地浏览器核对中英文切换、F45、餐区、客厅与结束画面、双进度条和图层。离线入口 SHA256 为 `17c52a0d7b507f55d630032bfe0f34e4518a82509ec09bdcbdb9ca62f52b8da3`，在线入口 SHA256 为 `794965539fc6c3c1760654a28fa2f964ae3e2ac33b1c2241daa01e9d3da19388`。
