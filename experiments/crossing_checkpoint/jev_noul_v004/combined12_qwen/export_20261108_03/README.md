# v004/Qwen4B 滤波增强导出

状态：本地和在线浏览器验证通过，已发布。

- 在线入口：http://134.175.18.101/vln/jev_noul_v004_vs_qwen4b_12cases_filters_20261108_02/jev_noul_v004_vs_qwen4b.html
- 本地SHA256：`8a563d9073b1bfb42d258d677e8549ffd6f3ae48c6ad026fd6edbc301b423621`
- 发布记录：`outputs/visualization_publishing/publish_20261108_163253_629709/publication.json`
- 在线HTML：547,249字节；按需资源1,071个

新增：Qwen原始线、JEV原始线均可独立勾选；Gaussian、EMA、Moving Average和
Relative Prominence可叠加显示；统一窗口N=3..31。

验证：12条轨迹、1062回放帧、两版各1050个结果；三种滤波和相对突出度数值正确，
原始线切换有效，滤波改变折线但不改变地图，移动端和中英切换通过；页面错误0、
请求失败0。
