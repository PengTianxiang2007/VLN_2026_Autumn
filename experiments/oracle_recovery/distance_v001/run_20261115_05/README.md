# 自动距离 Oracle：原版复现，固定GPU3运行05

2026-11-15 用户最新变更：取消其余距离组、保留已加载模型与环境，改为只做最后的回退组。short保留19条官方评分，旧launcher/仿真已暂停、模型仍在GPU3响应；没有释放服务，不得恢复旧距离队列。新回退组尚未开始，见[运行06](../run_20261115_06_checkpoint/README.md)。下方运行状态为历史检查记录。

2026-11-15 15:24 UTC：0.75米组33条任务的双语回放已发布，含历史原始轨迹、正确参考路线、本次Oracle轨迹及93次瞬移前后画面。[制作与验证记录](exports/early_20261115_01/README.md)；[在线回放](http://134.175.18.101/vln/oracle_distance_075m_33_run05_web_20261115_02/oracle_075m_33.html)。全部静态文件远端哈希与入口HTTP 200通过；未重跑导航。

日期：2026-11-15。状态（14:59 UTC检查）：GPU3继续运行，累计正式评分40/165，含旧20条及本轮新增20条。early全33条完成；short完成7/33，其余三组未开始。19项CPU检查、原版连续导航与early整组导出验证通过。

## 14:59 UTC进度与结果

| 条件 | 正式评分完成 | 官方成功 | 成功率 | 触发任务 | 纠正次数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| early，0.75米 | 33/33 | 17 | 51.52% | 26 | 93 |
| short，1.5米 | 7/33 | 5 | 71.43% | 4 | 25 |
| medium，3米 | 0/33 | — | — | — | — |
| long，4米 | 0/33 | — | — | — | — |
| checkpoint，实际存档回退 | 0/33 | — | — | — | — |

early的26条触发任务中13条官方成功，7条未触发任务中4条成功；平均SPL 0.36189、NE 3.10905米。终止原因为正常success 15、stuck 8、not_reach_goal 9、fall 1。`kujiale_0232_68_1`跌倒（NE 0.92586米）和`kujiale_0240_7_0`卡住（NE 2.12606米）均因终点距离小于3米计入官方17条成功，须与正常成功停止15条区分。

本轮early剩余13条在同一原版仿真进程连续完成，`early.log`记录单个chunk完成13/13；原版`validation.json`为passed，核验2102条模型动作记录。short当前7条已有官方逐任务评分，尚未完成整组导出。主管3098932、short模型3146022和仿真3147041存活并使用GPU3，14:59:08最新模型动作来自`kujiale_0234_55_1`（step 87，STOP），已纳入上述7条评分。没有发现任务异常退出；场景加载包含既有资源警告。

逐条来源、结果哈希和各组汇总：[本次进度快照](progress_20261115T145926Z.json)。不同组当前完成子集不同，不能据此比较阈值优劣；未触发成功不归因于纠正，尚无新增配对无干预对照。继续按既定原版机制后台执行，不持续人工跟踪。下方13:41内容为启动时历史记录。

## 授权、范围与版本

用户在获知GPU3上huangyinuo的SAM3服务约占3.9GiB、空余约43.5GiB后明确要求“用GPU3”。本轮模型、仿真均指定GPU3，采用原版`--allow-shared-gpu`；不再自动选择其他卡，不操作SAM3或其他用户进程。

实验仍采用[04](../run_20261115_04/README.md)的原版run_full.py与原生评测循环，只接入距离Oracle钩子。原版默认内存预算、任务/场景切换、评分和断点续跑机制不变，不引入固定批次或场景缓存。
04已通过空闲准入在GPU2加载模型和启动仿真；切换时没有新增官方评分，已核验PID归属并通过主管SIGTERM触发原版清理，日志保留于04。02/03共20条完整结果保留；05继续145条，early13、其余四组各33。

基线7ce5f9f加未提交源码，prepare冻结实际版本和差异。相较04仅队列透传原版共享GPU参数，并允许已明确选择的共享卡按原版显存准入。共享参数必须搭配显式GPU编号，禁止与自动选卡同时使用。

## 命令与检查

```bash
python3 -B scripts/prepare_oracle_distance.py --output outputs/oracle_crossing/distance_v001/run_20261115_05
python3 -u -B outputs/oracle_crossing/distance_v001/run_20261115_05/code/scripts/run_oracle_distance.py --campaign outputs/oracle_crossing/distance_v001/run_20261115_05 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_02 --reuse-from outputs/oracle_crossing/distance_v001/run_20261115_03 --gpu 3 --sim-gpu 3 --allow-shared-gpu --execute
```

CPU验证覆盖原版入口不变、原生循环钩子、样本继承、记忆隔离及显式GPU3共享参数。环境和原版模型源码未变化，引用04已通过的环境检查；本轮GPU实际启动另行核验。

实际启动：tmux`oracle_distance_20261115_05`，主管PID3098932，原版launcher PID3099103；上方冻结入口命令已执行，原版preflight显示gpu=3、sim_gpu=3。模型PID3099126，CUDA_VISIBLE_DEVICES=3，nvidia-smi确认GPU3显存约15888MiB；13:40:36 UTC生成ready.json，原版初始reset成功。仿真PID3099726于13:40:37 UTC启动，13:41检查处于Isaac扩展初始化，渲染参数activeGpu=3，尚无Oracle观测/评分。GPU3既有SAM3 PID2982374保持运行，约3990MiB；未操作它。04模型/仿真已退出，GPU2本项目占用已释放。

验证记录位于`validation/cpu_summary.json`（19通过，原版launcher哈希相同）和`validation/streamvln_environment_from_04.json`。当前进程存活、日志推进，无异常退出；完整导航与自动纠正仍待本轮实际证据，不将AGENT_READY等同于episode完成。

## 产物与下一步

输出根：`outputs/oracle_crossing/distance_v001/run_20261115_05/`。保留源码、manifest/seal、20条继承证据、五组计划、原版日志和逐条Oracle记录。
下一步：实际GPU3导航、自动纠正、任务间记忆重置与early导出已验证，后台继续剩余125次评测；按用户要求不持续人工跟踪。

## 用户查询：已保留20条结果

来源为02的17条、03的3条，全部是early / 0.75米组；不包含05新任务。已重新核对20条结果哈希。
官方SR为11/20（55%），其中触发纠正14条、官方成功8条，未触发6条、官方成功3条；累计38次纠正。
终止原因分布为success10、fall1、stuck3、not_reach_goal6。`kujiale_0232_68_1`终点距离0.9259米，虽然以跌倒终止，原版距离指标仍给success=1；须与正常成功停止分开说明，不修改原始评分。
这是early组20/33条的中间结果，未触发成功不归因于纠正，没有新的配对无干预对照，不能据此推断净收益。
逐条成绩：[inherited20_results.csv](inherited20_results.csv)；含结果路径/哈希的汇总：[inherited20_summary.json](inherited20_summary.json)。
