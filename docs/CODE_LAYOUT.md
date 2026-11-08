# 代码导航

本次采用实验目录整理说明、配置与结果索引；公共源码保持原路径，保证已有命令与冻结实验可用。

| 职责 | 当前实现 | 主要入口 |
| --- | --- | --- |
| 路径、环境 | core/paths.py、backbone/、benchmarks/ | scripts/check_environment.py、scripts/evaluate.py |
| 原模型复现 | core/vlnverse_reproduction.py、core/vlnverse_runtime.py | scripts/reproduce_streamvln_vlnverse.py、scripts/reproduce_internvla_n1_vlnverse.py |
| 外部Agent复位后选路 | core/agent_route_choice.py、core/agent_route_choice_review.js | scripts/prepare_agent_route_choice.py、scripts/run_agent_route_choice.py、scripts/report_agent_route_choice.py、scripts/export_agent_route_choice.py；默认dry-run，待用户明确开始 |
| Crossing识别/评分 | core/crossing_checkpoint.py | scripts/serve_crossing_vlm.py、scripts/replay_crossing_checkpoint.py、scripts/run_crossing_development.py |
| 地图与归因 | core/checkpoint_review.html、core/crossing_attribution.html | scripts/build_checkpoint_review.py、scripts/analyze_crossing_failures.py |
| Oracle恢复 | core/oracle_crossing.py、core/oracle_policy_state.py | scripts/run_oracle_crossing.py、scripts/oracle_crossing_console.py |
| 跌倒重放 | core/fall_replay.py | scripts/test_fall_retries.py、scripts/summarize_fall_retries.py |
| 动态回放HTML | core/oracle_replay.html | scripts/build_oracle_replay.py |
| Crossing默认可视化模板 | core/crossing_campaign_template.html、core/crossing_campaign_panel.html、core/crossing_campaign.js | scripts/export_crossing_iteration.py、scripts/export_crossing_campaign.py |

实验目录 experiments/ 保存分类README、配置、任务清单和摘要，outputs/保存大体积产物。
历史运行 source/code/code_oracle 快照是追溯证据，不作为日常开发入口，不移动或修改。
已有 .venv/.runtime 不随代码整理迁移；权重、数据统一在外部 Resource_Peng。
公共实现后续确需拆分时，应单独提交并保留旧入口兼容；本次没有修改运行逻辑。
