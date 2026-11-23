# 串行单目恢复：首条真实仿真联调

更新时间：2026-11-16 UTC。状态：首次仿真在进入导航前失败，完成0/1。原模型保留，未宣称闭环通过。

后续：导入问题及去重无效答复保留双方处理已修复，完整链路标志要求实际局部动作和原任务续接；相关29项CPU检查通过。用户要求先处理JEV，最新[模型/代理诊断](../jev_diagnostics_20261116/README.md)显示两个图像版本文本可用、图像仍400，未启动运行02。

实际启动：GPU3仿真PID3915875，原模型3194667未重载。Isaac初始化后，VLNVerse自己的scripts包遮蔽了项目scripts包，导致`ModuleNotFoundError: scripts.run_deviation_progress_review`；外层Isaac退出码为0，主管正确依据缺少完整结果拒绝计为完成。源码01及日志保留。公共实现已改为显式项目脚本目录导入，并增加包冲突CPU测试；后续使用新运行号。

接口预检：DeepSeek鉴权及图像模型目录正常。JEV模型目录HTTP200，列出jev-1.14.0与jev-1.13.0；1.14单帧、两版本此前成功过的三帧请求均HTTP400，原文`TypeSafe rejected the request`。预检属于历史图像API诊断，不是本轮仿真结果。证据位于preflight_jev/。正在继续核对网关图像传输，不擅自把文本请求或缓存概率替代实时JEV。

目的：验证 JEV → 建点 → 去重 → 偏航判断 → 实际回退 → 单目选路 → v007局部纠错 → 原任务记忆恢复与续走能否贯通。用户授权仅先验证，不自动扩为33条。

样本：开发样本 `kujiale_0208_21_4`，seed 2；历史记录存在较早的偏航和有效回退，用于技术联调，不能据此计算泛化准确率。模型 StreamVLN_R2R_v1_3，VLNVerse H1 physical；25000原生物理tick，640×480单目前视RGB。GPU3原模型3194667/40617经实时归属核查后复用。其他进程不操作。

协议见[版本说明](../README.md)。JEV端点为用户提供的`https://api.site/v1/systemone`；DeepSeek使用`https://api.deepseek.com`及已使用过的`deepseek-flash`。密钥经无回显终端读入，运行期内存/子进程环境传递，不写源码、配置、命令行或记录。实际接口可用性以本轮请求为准。

代码版本：Git基线7ce5f9fee30686bae304425bc84c36b3fbedc39c及未提交差异、1340份实际执行源码/提示词已冻结到新输出目录code/，哈希见manifest.json；不覆盖历史运行。DeepSeek只读鉴权HTTP200，模型列表确认deepseek-flash为DeepSeek-V4.1-Flash并支持text/image；本轮还需验证实际图像请求。

准备命令：
```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/prepare_serial_pipeline.py --episodes kujiale_0208_21_4 --output outputs/serial_recovery/v001/run_20261116_01
```

执行命令（运行时重新检查GPU3资源）：
```bash
benchmarks/vlnverse/.venv/bin/python -u -B outputs/serial_recovery/v001/run_20261116_01/code/scripts/run_serial_pipeline.py --campaign outputs/serial_recovery/v001/run_20261116_01 --model-pid 3194667 --port 40617 --gpu 3 --keys-stdin
```

产物：`outputs/serial_recovery/v001/run_20261116_01/`内manifest/config/status、evaluator.log、episodes下逐帧图像/节点/请求/原答/实际动作/回退姿态和memory证明、官方评分与validation。成功跑完导航但未实际触发恢复时，标记`complete_without_full_recovery`，不得宣称完整链路验证通过。局部STOP只证明发生控制交接，不证明分支语义正确。

完成后按用户既有授权保留模型和最后仿真；失败只关闭本轮仿真，尽力恢复已保存原任务记忆并保留模型。下一步：CPU接口验证通过后启动首条真实仿真。
