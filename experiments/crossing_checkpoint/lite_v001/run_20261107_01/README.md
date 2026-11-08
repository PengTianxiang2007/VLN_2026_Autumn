# 三帧 Crossing 五级评分：10失败＋20成功

## 2026-11-07 HTML 发布

按用户新增交付规则，将本次已完成 HTML 原样上传至
[三帧 Crossing 在线回放](http://134.175.18.101/vln/crossing_lite_v001_run_20261107_01_publish_20261107_01/crossing_lite_review.html)。
本地原件：`outputs/crossing_checkpoint/lite_v001/run_20261107_01/exports/final/crossing_lite_review.html`。
大小 64,960,159 字节；SHA256 `f8821d26b5582d7dd97e8fad06b6f4cbe67aa044fccc98ced862013adeb727d4`。
上传/远端哈希校验完成时间为 2026-11-07 06:54:46 UTC；公网 HTTP 200、HTML 类型与 gzip 已核验。
完整公网下载与在线交互未完成验证：直连下载超时，后续代理浏览器检查因耗时过长已停止，
不记作完整在线验收通过。发布记录：`outputs/visualization_publishing/setup_20261107_01/`，
直连失败记录独立保留。未重跑模型、导航或导出，结果与历史文件保持不变。

## 原实验记录

2026-11-07；状态：准备完成，即将启动。用户明确授权GPU0，先释放27B，再通过vLLM部署4B，多进程；正常运行后不持续人工跟踪。

目的：只据当前与过去两帧RGB判断眼下是否面临多个直接可选方向。掉头算分支；远处入口和依赖先前选路的后续分岔不算眼下选项。评分1–5，不输出导航动作、不评路线正确性。

模型：已有Qwen3.5-4B BF16，.runtime/crossing_vllm27环境，GPU0共享，vLLM单服务＋4独立进程，max_num_seqs=4、max_model_len=8192、显存预算0.50、每请求最多3图，temperature=0，thinking=false，输出256 tokens，JSON schema约束。复用原640×480 WebP，不重新编码。

数据：人工数据集61条中冻结10失败、20成功。seed=20261107，按成败组内场景轮转随机抽样，selection.json为最终清单。覆盖10场景，计划2559次调用。原导航seed2；请求seed由episode/frame/20261107的SHA256派生。不是独立场景盲测。

输入：严格t-2,t-1,t；开头缺帧略去，不复制。终止/复用RGB不调用。worker任务文件剥离指令、动作、地图、位置、标签、成败和模型历史回答。每步独立输出score/reason，无平滑和存档确认。prompt_en.txt为用户确认的完整英文提示词。

评价：保留原始分数分布、人工点同帧分数；未标帧不作为负类，无精确率/召回率/F1，也不复用旧1m评分。可视化P为展示阈值>=4的连续片段起点，非确认存档。原人工标注定义与新增掉头分支可能不同，需语义复核。

版本：实际Git提交、工作区差异与source快照见outputs/crossing_checkpoint/lite_v001/run_20261107_01/manifest.json等；注册源码哈希启动前核验，旧运行不覆盖。

启动：`python3 -B scripts/run_crossing_lite.py --output outputs/crossing_checkpoint/lite_v001/run_20261107_01`。

GPU0原Qwen27B主管395599、API396074、引擎400489身份已核验；向主管SIGTERM后全部退出。其他用户PID3727957保留，GPU0恢复44520MiB空闲。证据release_qwen27b.json。旧常驻授权被本次释放指令更新，不自动重启27B。

自动收尾：推理完成、失败、取消后清理仅本主管拥有的worker及vLLM会话并核验GPU；然后经scripts/export_crossing_iteration.py导出双进度条模板评分变体，重建实际请求哈希、保留原始回答、C/P、三帧历史与复核导出，并执行CPU浏览器检查。每请求180秒、网络最多两次尝试，连续三次传输失败终止worker，整批最多8小时；失败结果保留，不自动改prompt或扩大样本。

产物：outputs/crossing_checkpoint/lite_v001/run_20261107_01/下status.json、service/、workers/、cases/、summary.json、request_audit.json、cleanup.json；最终HTML为exports/final/crossing_lite_review.html。当前尚无模型评分。

下一步：首批真实请求和4进程并发验证通过后停止人工持续跟踪，等待后台收尾；用户询问时再查。

2026-11-07：三帧评分后台主管1292524、vLLM API1292779已启动加载，端口60859；冻结30条/2559次调用。6项CPU协议测试通过，独立无预测预览30条/2589帧/156关键位置浏览器检查通过（双滑条、复核导出、移动端、零外部请求/JS错误），不计作模型结果。

2026-11-07T03:34:36.957330+00:00 启动核验通过：GPU0 Qwen3.5-4B vLLM、4独立episode进程；前12份真实响应及三帧输入/请求哈希/1–5评分通过，4请求时间区间并发已确认。此刻有效回答12/2559。停止人工持续跟踪；后台自动完成、导出双进度条HTML及请求/浏览器审计，释放本轮服务。

2026-11-07T03:41:01.901924+00:00：按用户要求更新三帧评分HTML俯视轨迹配色，1–5分浅绿到深绿；t→t+1线段使用起点t的有效原始评分，无评分灰色虚线，原地转向同色点，并加入图例。仅修改core/crossing_lite_review.js；原启动manifest/source快照保留，导出修订与授权哈希见outputs/crossing_checkpoint/lite_v001/run_20261107_01/export_revisions/score_route_colors_20261107_01/。推理源码、prompt、任务与原答未改，不查询/跟踪运行进度。独立CPU预览30条/2589帧/156位置及五档明度、实际Canvas线段颜色、起点评分对应、回放前缀和灰色缺失检查通过；合成配色测试不计模型结果。本轮自动导出会应用此修订。

2026-11-07T03:54:38.445077+00:00：三帧Crossing五级评分 outputs/crossing_checkpoint/lite_v001/run_20261107_01 自动收尾：{"phase": "complete", "supervisor_pid": 1292524, "started_at": "2026-11-07T03:27:26.666080+00:00", "gpu": 0, "concurrency": 4, "expected_calls": 2559, "updated_at": "2026-11-07T03:54:38.399180+00:00", "base_url": "http://127.0.0.1:60859/v1", "server_pid": 1292779, "worker_pids": [1300869, 1300871, 1300874, 1300875], "inference_error": null, "gpu_released": true, "finished_at": "2026-11-07T03:54:38.399149+00:00", "error": null, "summary": {"episodes": 30, "groups": {"failure": 10, "success": 20}, "expected_calls": 2559, "attempted_calls": 2559, "responses": 2559, "valid_calls": 2559, "invalid_or_missing": 0, "audited_requests": 2559, "score_histogram": {"1": 1911, "4": 2, "5": 646}, "replay_frames": 2589, "annotation_points": 70, "mean_latency_seconds": 1.2661769690414968, "evaluation": "Raw score distribution and exact annotated-point scores only. No unlabeled-frame negatives or PR/F1.", "created_at": "2026-11-07T03:54:30.690423+00:00"}, "html": "/mnt/nas/gezuhao/PengTianxiang/VLN-Papers/VLN_2026_Autumn/outputs/crossing_checkpoint/lite_v001/run_20261107_01/exports/final/crossing_lite_review.html"}。未标帧不视为负类，语义准确性待复核。

2026-11-07 后续快速重验已通过：使用仓库保存的密码自动 SSH 认证，远端 SHA256 一致，公网直连 HEAD 返回 HTTP 200、类型及大小正确；未重新上传或下载完整 HTML。记录：`outputs/visualization_publishing/publish_20261107_071616_640892/publication.json`。

2026-11-07 在线加载修复：原单文件包含约62 MiB内嵌媒体，初始化脚本位于文件末尾，慢网下载未结束时只显示框架。已生成媒体按需加载版本，HTML 3,799,721字节、2600个图片/字体资源，全部远端SHA256验证通过。
新网址：[在线回放](http://134.175.18.101/vln/crossing_lite_v001_online_20261107_01/crossing_lite_review.html)。
本地浏览器验证30条/2589帧/156位置、2559有效回答、双滑条、复核导出及移动端通过，零JS错误。
记录与原始来源哈希：`outputs/visualization_publishing/online_20261107_01/`；发布清单：`outputs/visualization_publishing/publish_20261107_072020_383244/publication.json`。原离线文件保留，未重跑模型或导航。

新在线地址实际浏览器直连验证通过：HTTP 200、30条轨迹、首末轨迹图片、双进度条、零JS错误，耗时19.9秒；7892代理45秒超时后已按规则绕过。证据：`outputs/visualization_publishing/online_20261107_01/public_browser.json`。
