# JEV 去重回退点：180°与360°重新采集（运行03）

2026-11-16 00:10 UTC检查：采集失败，完成0/159。在前置07完成后自动启动，连续三次均在首点kujiale_0036_0_0__F0005的probe阶段退出，未产生complete.json；底层退出码均为0，但主管正确拒绝计为完成并标记failed。日志无Python异常栈，不能仅凭场景资产警告认定根因；具体原因尚待定位。三次attempt/log完整保留。采集仿真及主管已退出，GPU3原模型PID3194667继续保留。未启动重跑。

2026-11-15T17:54:30.794719+00:00：等待进程PID3570684已启动，tmux `jev_point_capture_20261115_03`，实际状态waiting_for_early_plus05。当前只等待，GPU采集尚未开始；原Oracle队列未修改。

更新时间：2026-11-15T17:53:29.107550+00:00。状态：已准备，等待额外前移0.5米Oracle组07完成；尚未进行GPU采集。

## 目的与范围

用户授权将先前离线JEV＋去重保留节点在仿真中补采，并明确要求估计机器人基础朝向。来源为`experiments/crossing_checkpoint/online_sampling_v001/review_snapshot_20261112/node_deduplication/v001_run02_all/results.json`的final_active_ids；不重新运行JEV或去重，不套用后来的偏航评审筛选。34案例/33轨迹的165节点引用，对应159个不同(episode,frame)、9场景；6个跨案例重复引用保持关联，共用相同采集点。

## 协议与版本

原始XYZ逐帧匹配，节点原图SHA与数据集观测一致。历史无朝向记录；以官方起始四元数、15°动作累积、历史RGB特征运动和直行位移构成朝向先验。只有已发生动作影响当前帧。采集时先取8方向探测图，与原节点RGB做ORB＋单应性RANSAC匹配，要求至少20内点、空间覆盖≥5%、内点占比≥35%、角度MAD≤6°，强候选冲突则拒绝校准；接受时更新朝向和相机光心，再独立采最终8方向。失败时保留先验并记录alignment.accepted=false及原因，不把估计写成测量朝向。

相机光心按记录root XYZ加旋转后的H1静态安装偏移(0.2,0,0.72m)估计；历史身体roll/pitch、关节与真实相机外参未保存。俯视15°、水平FOV90°、640×480、原场景USD与原评估灯光类型/强度；同一点固定光心旋转。相机参数来自既有验证版本，资产SHA已核验。render_seed=20261115。

180套装为相对−45°/0°/+45°三张重叠透视图；360为每45°一张、共8张。分别存目录和metadata，共用新渲染的对应图像字节；不把旧RGB当新采集图、不伪称已经拼成连续全景图。最终有效RGB计划1272张，另保存1272张方向校准探测图。节点原图只参与方向估计。

本轮是Isaac真实场景的静态相机补采，不恢复机器人完整PhysX状态、不执行StreamVLN导航、不提供导航评分。单个Isaac进程逐场景切换，不逐点重启；失败保留逐点完成标记与attempt，最多3次异常重试。GPU3只在07全33条评分/导出完成后交接；模型3194667保持加载。启动需显存空闲≥12000MiB、利用率≤10%两次、主存≥64GiB；不停止其他进程。最终保留模型和最后采集引擎。

执行代码冻结于`outputs/jev_point_capture/v001/run_20261115_03/source/`，manifest/seal含源码哈希、Git 7ce5f9fee30686bae304425bc84c36b3fbedc39c及未提交差异。01仅动作/位移先验，02增加历史RGB估计；两者只做CPU准备与诊断，无采集任务，不自动启动。03复用02有来源哈希的朝向先验，增加实际渲染时的绝对方向校准。

## 启动方式

```bash
python3 -u -B outputs/jev_point_capture/v001/run_20261115_03/source/scripts/run_oracle_retained_followup.py --plan outputs/jev_point_capture/v001/run_20261115_03/queue_plan.json
```

实际等待与采集命令完整保存在queue_command.json和queue_plan.json。等待器仅在07达到complete_services_retained后释放07的已完成仿真，保留同一模型，再启动采集。前置组失败/停止则不越过执行。`cancel_followup`可取消等待或采集。

## 验证与限制

7项CPU检查通过，包括动作帧顺序、位移/碰撞处理、因果性、相机偏移、视角排列，以及已知旋转合成图的绝对方向恢复。冻结入口导入、源码哈希、165节点图像帧映射与相机资产哈希通过。尚无本轮GPU渲染验证，不能声称已经逼近原始观测。

在5条其他已完成且未干预的仿真轨迹上诊断，历史RGB＋动作估计各轨迹中位误差约5.1°～93.7°、p90约10.3°～132.1°；该诊断揭示朝向先验可能严重漂移，不是历史159节点的精度评测。跨渲染绝对方向校准目前仅做合成几何验证，实际纹理重复、视差、相机高度/俯仰和光照差异仍可能导致错误匹配。每点保存匹配证据和是否接受；不得把accepted当作真实朝向已知或语义正确保证。原图与新图仍须实际比对，无法保证像素级/完整物理状态复原。

## 产物

`outputs/jev_point_capture/v001/run_20261115_03/`：manifest.json、heading_estimates/、verification/、queue_status.json、status.json、logs/、points/<episode__frame>/attempt_*/probe/、final/、180/、360/、alignment.json、complete.json、validation.json。当前新图0张。

本次未制作HTML，不触发网页发布。后续需要可视化时另按用户要求处理。

## 下一步

后台等待07完成，然后执行采集；最终验证全部点、PNG尺寸/哈希、180/360对应关系与完整性。实际接近原始观测程度需采图后的逐点证据，不用CPU检查代替。
