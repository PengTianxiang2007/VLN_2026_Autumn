# InternVLA-N1：VLNVerse fine Val Unseen，seed 0

用户于 2026-11-02 授权固定一个 seed 完整评测。范围为本地官方 fine
val_unseen 的 33 个 scene、825 条 episode；使用 seed 0，不训练、不修改权重。
目前下载与带验证门槛的后台流程已经启动，尚未进行真实 GPU 导航。
官方 Agent 导入、仿真配置 CPU 检查通过；不能将 CPU 检查称为复现通过。

## 固定协议

采用 VLNVerse 官方 `vlnverse` 分支的
`scripts/eval/configs/h1_internvla_n1_cfg_vlnverse_fine_val_unseen.py`，
使用 H1 flash、640×480 相机、384×384 模型图像、400 max_step、500 warm-up，
`one_step_stand_still=True`、`filter_stairs=False`，默认同步双系统。
不套用 StreamVLN 的 physical 协议或 250 条子集。

官方当前原 `InternRobotics/InternVLA-N1` 链接重定向至
`InternRobotics/InternVLA-N1-wo-dagger`，本次固定该发布版 revision
`377366bc480b6643b807b6ea8fa642715683cf7b`，`navdp_version=0.1`。
不能将其未经验证地描述为 VLNVerse 论文历史表格的原 checkpoint。
N1 官方代码支持该 NavDP 版本；真实权重加载与导航仍待验证。

模型服务使用官方 InternVLAN1Agent，保持原提示词、BF16、FlashAttention2、
历史采样、S1/S2 和动作队列。每个 scene 独立进程，官方 seed 0 在进程初始化时设置，
保持 scene 内原始 episode 顺序。它不是一次连续单进程运行的随机数消耗序列。
仿真继续使用官方每条任务 seed 0；不设置 StreamVLN 的派生 episode seed 环境变量。

## 隔离与资源

`backbone/internvla_n1/vendor/` 是从本项目已迁入的官方 VLNVerse 文件创建的独立快照；
初始文件哈希在 campaign 的 `vendor_source_manifest.json`。推理模型与 Agent 不作改动。
独立快照中的 model 注册表改成仅按需导入 N1，encoder 注册表也按需导入，
避免 N1 触发无关 LongCLIP 训练基线依赖。
共享的 `benchmarks/vlnverse/upstream` 未修改，避免影响已运行的 StreamVLN。

`backbone/internvla_n1/.venv` 为独立 Python 3.9 环境，通过一个 .pth 文件只读复用
Janus 环境中的 Torch 2.5.1+cu124、FlashAttention 2.7.1.post4 等已装库。
N1 专属依赖安装在自身 site-packages 并优先导入。已装 Transformers 4.51.0、
Diffusers 0.33.1、Pydantic 2.11.7 等，官方 Agent 导入检查通过。
`janus_base_requirements.txt` 保存复用前快照，原 Janus/StreamVLN 环境没有升级。
Isaac Sim、33 个场景、机器人和任务标注全部复用现有资源。

缺失权重由 `scripts/prepare_internvla_n1.py` 下载至 Resource_Peng/models，
验证尺寸与官方 LFS SHA256。新增辅助权重为 Depth-Anything-V2-Small；
不下载训练集，不删除现有权重或数据。

用户最初要求服务器自己的 Mihomo 7892；因节点不可用，随后明确改为 Windows 中转。
用户实际建立反向 SSH 隧道，服务器动态分配 41623，转发至 Windows 127.0.0.1:17897。
该路线已实际验证 Hugging Face HTTP 200，大文件从既有 `.partial` 继续增长。
下载器要求显式 `--proxy`，不自动回退。权重现已全部校验完成，后续评测离线执行。
该隧道依赖用户电脑联网、保持唤醒以及 SSH 窗口开启；不在电脑磁盘保存权重。
不要把 Windows 17897 与服务器上同号端口混淆，不得指定或抢占服务器固定端口。

## 队列与验证

工作目录：`outputs/reproduction/internvla_n1_fine825_seed0_20261102`。

```bash
python3 scripts/reproduce_internvla_n1_vlnverse.py prepare
# 权重缺失时才下载，代理须由用户指定并有权使用：
# python3 scripts/prepare_internvla_n1.py --proxy http://127.0.0.1:<用户代理端口>
# 仅在依赖导入检查通过并保存 imports_verified.json 后启动：
python3 scripts/reproduce_internvla_n1_vlnverse.py run
python3 scripts/reproduce_internvla_n1_vlnverse.py status
```

队列需要权重校验和依赖导入校验，先验证两条完整任务，再开放 33 个完整 scene。
smoke 不计入正式 825 条成绩。每次启动检查连续两次 GPU 低负载、显存余量、主存，
与 StreamVLN 共用 GPU 锁，最多八组，不能抢占其他人的进程。
出现推理异常、未完成评分、服务退出等情况停止新增任务，保留所有日志；
原 Agent 捕获异常后生成的 fallback STOP 不计为正常成绩。
不因导航失败而重跑或剔除任务。

结果从官方 LMDB 按任务身份核验，保留原始指标、轨迹、动作、模型输出和官方 debug 视频。
完整结果需 825 条、无重复无遗漏、每条评分有效。完成后按 episode 汇总均值，
不对各 scene 做不等权平均。与物理行走协议的 StreamVLN 结果单独报告。

后台 supervisor 已启动。活跃 PID 和阶段见 `status.json`。
进入模型加载时额外记录 Hugging Face loading_info，任何缺失、形状不匹配或未审计的
意外参数均阻止评测。唯一允许的额外参数是 RGB/Depth DINOv2 的两个 mask_token：
官方 dinov2.py 第170行已注释其注册，NavDP 使用 get_intermediate_layers，无 masks 输入，
所以这两项按官方 from_pretrained 的行为忽略。CPU meta 审计已确认 1460 个实际参数全部
存在且尺寸匹配；这不能替代完整文件 SHA256 或真实 GPU 加载验证。
两条 smoke 还必须均产生真实模型动作，并完成任务切换和有效评分。

下载器已改成 16 MiB 分段、每连接最长120秒、低速30秒重连、四个文件并行；
只有 HTTP206、正确 Content-Range 起点/总长度的字节才追加到已有 partial。
最终仍按 LFS SHA256 验证；连续八次无进展才终止，不因有进展的短连接而丢失下载内容。

配置审计发现上游 TaskCfg schema 未声明 `one_step_stand_still`，因此官方配置的该项
被 Pydantic 忽略；本次保留官方实际行为。其在任务代码中的条件同时要求非 flash，
本次 flash 模式不会进入该分支。此差异已明确记录，不能声称所有配置文字均有效传递。

2026-11-03 修复模型服务初始化：官方 `Agent.register` 装饰器只写注册表，不返回类，
所以模块中的 `InternVLAN1Agent` 名称为 None。服务改用官方 `Agent.init(cfg)`，
依赖检查同时验证 `Agent.agents[cfg.model_name]` 可调用。未修改官方 Agent 的推理实现。
此前失败尝试的日志保留，新的导航验证使用新的运行目录。

修复后的 GPU 验证已于 2026-11-03 02:31 UTC 通过：完整加载全部四个权重分片，
missing_keys、mismatched_keys、error_msgs 均为空；两条任务累计 131 次实际动作调用，
包含任务 reset、像素目标/S1、离散动作和 STOP，LMDB 身份及指标检查均通过。
验证任务 `kujiale_0272_26_1` / `kujiale_0272_23_4` 均 success=1，
SPL 分别为 0.76577 / 0.81858。验证不计入正式 825 条成绩。
证据位于该 campaign 的 `runs/smoke/1793672442686712094`，正式队列继续使用 seed 0。
