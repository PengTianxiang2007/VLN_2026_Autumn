# Codex 直接操作 VLNVerse H1

通过两个 MCP 工具控制已附着的 H1。observe() 返回原生前视 RGB，step(action) 接受 forward、turn_left、turn_right 和 finish_return。动作后返回实拍，finish_return 仅关闭本次局部回退。后台 Isaac 在两次调用之间停在动作边界。

[F38 自主走到电视柜前](run_20261126_03_tv/README.md)已完成。11 次移动决策执行 27 个动作，终点距柜子正面 1.13 米，朝向与屏幕中心相差 3.42°。[逐调用时间线](run_20261126_03_tv/timeline.md)

[首个常驻场景实测](run_20261126_01_f38/README.md)。

[同一台 H1 三个起点的连续移动与回图测试](run_20261126_02_multisite/README.md)已完成。12 次前进、2 次转向和 6 次独立观察均收到前视图，原进程已回到 F38。
