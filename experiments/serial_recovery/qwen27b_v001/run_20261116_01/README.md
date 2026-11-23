# Qwen27B接入串行pipeline：人工错误集33任务

更新时间：2026-11-16 UTC。状态：Qwen部署02在08:09 UTC因显存不足失败，仿真0/33。用户已改为DeepSeek API，本Qwen计划被替代，不再恢复。

## 目的与协议

用户授权在GPU2部署本地Qwen27B，明确选择替换全部DeepSeek模块：节点去重、偏航/语义进度、单目支路盘点、已走分支识别、纠正分支选择和v007局部纠错指令生成。JEV沿用已验证EasyJEV实时图像接口，StreamVLN复用GPU3原模型。先验证真实请求及导航启动，再后台完成33条，不持续人工跟踪。

样本清单来自`outputs/oracle_crossing/distance_v001/run_20261115_05/cohort.json`，33任务/34历史错误事件/9场景，seed2，原生25000物理tick预算包括回退稳定和局部纠错，不恢复时间预算。每条可多次纠错；局部纠错清空StreamVLN记忆，交还恢复接管前快照并核验哈希。原生STOP/跌倒/卡住与场景/RSS生命周期保留。取消的Oracle任务不恢复。

## 模型与环境

GPU2部署仓库已有`Qwen3.8-27B-FP8`目录（实际架构Qwen3_5ForConditionalGeneration），权重位于`/mnt/nas/gezuhao/shared_dataset/Resource_Peng/models/Qwen3.8-27B-FP8`；复用`.runtime/crossing_vllm27`，离线加载，无下载/环境修改。单并发，32768上下文，最多16张图，逐图max_pixels=307200，显存预算0.85。语义调用使用本地模型设置，提示词和验证器继承原串行模块；具体请求设置、源码和样本哈希在正式冻结清单记录。

部署前GPU2无计算进程、约48GiB可用，GPU0/1他人任务及GPU3他人SAM3不操作；GPU3原StreamVLN PID3194667保持加载。上一条已结束的仿真引擎需正常退出，以加载本轮冻结配置和新模块；仅替换本项目该引擎，不重载StreamVLN。之后按原版连续任务/场景切换，只有原生RSS规则或异常才重启仿真。

Qwen服务为本批提供推理，批次完成或失败后释放其GPU2资源；GPU3原模型与最终仿真仍遵循用户既有保留要求。

## 启动与产物

服务配置：`qwen_service.json`；服务输出：`outputs/model_services/qwen27b_gpu2_serial_20261116_01/`。正式批次输出拟为`outputs/serial_recovery/qwen27b_v001/run_20261116_01/`，不覆盖任何历史运行。服务/批次实际PID、接口、启动命令、测试、预检及新导航状态随执行补齐。

## 代码验证与差异

35项CPU检查通过（`tests.test_serial_pipeline`、`tests.test_oracle_distance_native`、`tests.test_oracle_existing_model`）。涵盖六模块均发至本地Qwen、不携带云端密钥、原DeepSeek设置兼容、原生eval主体未修改、回退后的记忆恢复与STOP交还、原版RSS进度重试等。

本地Qwen使用temperature=0、seed=2、enable_thinking=false、最多8192输出token（纠错指令512）。原DeepSeek在去重/偏航阶段为thinking enabled/high、32768；两者生成设置不同，属于模型替换实验，不能声称仅替换了权重且推理预算相同。所有提示词、输入窗口、去重/偏航/选路校验器保持原版。

批次采用原版LMDB跳过已完成任务及原生24GiB RSS重启；同一进程内连续导航不按任务重启。进程退出后最多容忍连续三次无进展；API/协议故障直接停止并保存证据，不擅自跳过任务。最终分别记录整批完成情况、实际触发恢复的任务数及闭环证据，未触发恢复不等于未完成实验。

### 服务部署命令

```bash
.runtime/crossing_vllm27/bin/python -B scripts/serve_qwen27b_standby.py \
  --output outputs/model_services/qwen27b_gpu2_serial_20261116_01 \
  --config experiments/serial_recovery/qwen27b_v001/run_20261116_01/qwen_service.json --gpu 2
```

服务主管PID897511，vLLM API PID897657，端点`http://127.0.0.1:35443/v1`，GPU2。服务启动时间以`service.json`为准，不能与正式导航启动时间混用。无任何新权重下载，已有环境和资源未修改。

部署01：0.85显存预算预热后仅余2.13GiB KV，32K上下文需要2.15GiB，vLLM拒绝启动。保留失败日志和初始配置`qwen_service_initial_failed.json`，不计导航结果。部署02预算调整为0.88，其他参数不变；新服务目录`outputs/model_services/qwen27b_gpu2_serial_20261116_02/`。

## 当前队列状态（本段优先于前面的准备记录）

自动队列PID **917244**，启动时间 **2026-11-16T07:56:33.366455+00:00**；状态`waiting_for_resources`，本轮仿真 **0/33**，真实Qwen请求预检尚未执行。GPU2新增他人Arrow进程906097约14.7GiB；GPU3新增他人进程906100约6.7GiB，当前可用约3GiB。不停止/抢占他人任务。首次服务失败后本项目Qwen进程已清理；GPU3原StreamVLN3194667及上一轮保留仿真836845仍在，未改动。

队列：`outputs/serial_recovery/qwen27b_v001/queue_20261116_01/`。`plan.json`记录1349个来源文件SHA256、实际Git提交及输入哈希，`code/`和workspace差异保留当时源码。启动前再次核验，发现后来修改会安全停止，不静默换版。当前Git提交`7ce5f9fee30686bae304425bc84c36b3fbedc39c`加未提交快照。

```bash
benchmarks/vlnverse/.venv/bin/python -B scripts/queue_serial_qwen.py \
  --queue outputs/serial_recovery/qwen27b_v001/queue_20261116_01 \
  --keys-stdin --detach
```

JEV凭据通过隐藏终端输入，仅在本队列及直接调用子进程内存/环境中；不写文件、命令参数或日志，不需要DeepSeek凭据。

执行顺序：连续资源准入→GPU2部署02（0.88预算）→真实历史RGB接口预检（单列，不计导航成绩）→冻结33任务正式批次→核验归属并正常退出旧的已结束仿真→GPU3新仿真使用原StreamVLN→全批导航与最终审核。预检若合法返回支路证据不足，会记录尚未覆盖的阶段；不伪造实际偏航来触发纠正。正式决策仍只看在线观测。

批次启动后，后台自动验证真实动作、JEV结果和Qwen回答并保存`startup_verified.json`；此标记不代表已验证物理回退完整闭环。队列已独立于终端运行，不需要人工持续轮询。正式任务的结果在`run_20261116_01/status.json`、`validation.json`和`official_result.json`；当前资源等待/启动故障先看队列`status.json`和对应日志。新GPU2服务在结束或失败时清理，GPU3服务沿用保留要求。

35项检查通过，新增覆盖资源准入拒绝他人GPU任务，以及本地六模块请求路由/凭据隔离/旧协议兼容。GPU导航、真实Qwen协议及完整恢复闭环仍待队列运行，不能将CPU检查说成仿真通过。

## 11:25 UTC复核及用户新指令

部署02启动时仅33.14GiB空闲，低于0.88预算所需41.7GiB。队列于08:09:46 UTC退出，未进入API预检或正式仿真，0/33。Qwen主管/API/引擎均已退出；GPU3原模型及旧引擎仍保留。用户随后明确改为DeepSeek API并允许容量足够时共享忙卡；转至[v001运行03](../../v001/run_20261116_03_full33/README.md)，不修复/重启本Qwen队列。
