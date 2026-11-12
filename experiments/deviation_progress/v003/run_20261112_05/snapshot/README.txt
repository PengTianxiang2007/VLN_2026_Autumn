本地可视化 v003｜全部34个案例｜2026-11-12

打开 jev_deviation_progress_v003_terminal_34cases_20261112.html 或本目录index.html。网页本地离线，不调用API。

34个案例对应33条独立轨迹、9场景。仅补跑22条，已有12条原样复用（40次历史请求，包括7次失败）。编号32、33属于同一条轨迹，不作为两个独立样本统计。

沿用v003，仅有效节点连续编号，增加终止节点，首节点单图初始化；端点两图＋均匀最多五张中间图。首次偏航停止后续评审，未执行真实回退。

结果：{
  "cases": 34,
  "scenes": 9,
  "calls": 114,
  "valid": 106,
  "errors": 8,
  "initializations": 34,
  "consistent_segments": 40,
  "deviations": 33,
  "uncertain": 5,
  "terminal_nodes_reviewed": 7,
  "cached_nodes": 199,
  "cached_retained_nodes": 199,
  "unreviewed_after_stop": 85,
  "total_tokens": 946049,
  "peak_inflight_requests": 6,
  "worker_processes": 18,
  "new_calls": 74,
  "reused_calls": 40,
  "new_valid": 73,
  "new_errors": 1,
  "new_tokens": 620865,
  "new_worker_processes": 6,
  "new_cases": 22,
  "reused_cases": 12
}

偏航区间：[
  {
    "case": 1,
    "nodes": "S01 → S02",
    "frames": [
      5,
      38
    ]
  },
  {
    "case": 2,
    "nodes": "S04 → S05",
    "frames": [
      25,
      35
    ]
  },
  {
    "case": 3,
    "nodes": "S01 → S03",
    "frames": [
      0,
      36
    ]
  },
  {
    "case": 4,
    "nodes": "S02 → S04",
    "frames": [
      57,
      99
    ]
  },
  {
    "case": 5,
    "nodes": "S01 → S02",
    "frames": [
      5,
      10
    ]
  },
  {
    "case": 6,
    "nodes": "S03 → S04",
    "frames": [
      59,
      70
    ]
  },
  {
    "case": 7,
    "nodes": "S01 → S02",
    "frames": [
      5,
      80
    ]
  },
  {
    "case": 8,
    "nodes": "S02 → S03",
    "frames": [
      13,
      26
    ]
  },
  {
    "case": 9,
    "nodes": "S01 → S02",
    "frames": [
      5,
      10
    ]
  },
  {
    "case": 10,
    "nodes": "S02 → S03",
    "frames": [
      17,
      36
    ]
  },
  {
    "case": 11,
    "nodes": "S03 → S04",
    "frames": [
      35,
      44
    ]
  },
  {
    "case": 13,
    "nodes": "S01 → S02",
    "frames": [
      8,
      23
    ]
  },
  {
    "case": 14,
    "nodes": "S01 → S02",
    "frames": [
      0,
      9
    ]
  },
  {
    "case": 15,
    "nodes": "S01 → S02",
    "frames": [
      8,
      33
    ]
  },
  {
    "case": 16,
    "nodes": "S02 → S03",
    "frames": [
      16,
      21
    ]
  },
  {
    "case": 17,
    "nodes": "S05 → S06",
    "frames": [
      74,
      100
    ]
  },
  {
    "case": 18,
    "nodes": "S02 → S03",
    "frames": [
      19,
      46
    ]
  },
  {
    "case": 19,
    "nodes": "S09 → S10",
    "frames": [
      127,
      132
    ]
  },
  {
    "case": 20,
    "nodes": "S03 → S04",
    "frames": [
      15,
      20
    ]
  },
  {
    "case": 21,
    "nodes": "S01 → S02",
    "frames": [
      0,
      14
    ]
  },
  {
    "case": 22,
    "nodes": "S01 → S02",
    "frames": [
      0,
      17
    ]
  },
  {
    "case": 23,
    "nodes": "S01 → S02",
    "frames": [
      32,
      49
    ]
  },
  {
    "case": 24,
    "nodes": "S03 → S04",
    "frames": [
      58,
      102
    ]
  },
  {
    "case": 25,
    "nodes": "S03 → S04",
    "frames": [
      39,
      66
    ]
  },
  {
    "case": 26,
    "nodes": "S01 → S02",
    "frames": [
      0,
      5
    ]
  },
  {
    "case": 27,
    "nodes": "S02 → S04",
    "frames": [
      48,
      71
    ]
  },
  {
    "case": 28,
    "nodes": "S04 → S05",
    "frames": [
      43,
      63
    ]
  },
  {
    "case": 29,
    "nodes": "S01 → S02",
    "frames": [
      0,
      41
    ]
  },
  {
    "case": 30,
    "nodes": "S02 → S03",
    "frames": [
      40,
      45
    ]
  },
  {
    "case": 31,
    "nodes": "S02 → S03",
    "frames": [
      13,
      23
    ]
  },
  {
    "case": 32,
    "nodes": "S03 → S04",
    "frames": [
      44,
      98
    ]
  },
  {
    "case": 33,
    "nodes": "S04 → S06",
    "frames": [
      44,
      102
    ]
  },
  {
    "case": 34,
    "nodes": "S01 → S02",
    "frames": [
      5,
      15
    ]
  }
]

new_calls为本次新调用，reused_calls为历史复用，calls为合计。字段或请求错误均保留，未推进可信进度。模型结论不等同于真值或准确率。
