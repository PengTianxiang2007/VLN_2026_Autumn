from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
p=(ROOT/'work/jev_guard_v003_remaining/prepare.py').read_text(encoding='utf-8')
p=p.replace("OLD=ROOT/'outputs/jev_deviation_progress_v003_terminal_20261112_run03'","OLD=ROOT/'outputs/jev_deviation_progress_v003_terminal_12cases_20261112_run04'")
p=p.replace("SITE=ROOT/'outputs/jev_deviation_progress_v003_terminal_12cases_20261112_run04'","SITE=ROOT/'outputs/jev_deviation_progress_v003_terminal_34cases_20261112_run05'")
p=p.replace('ALL=[4,5,6,7,11,13,14,15,16,17,20,28]\nNEW=[5,6,13,15,16,20];REUSED=[4,7,11,14,17,28]','ALL=list(range(1,35))\nREUSED=[4,5,6,7,11,13,14,15,16,17,20,28];NEW=[n for n in ALL if n not in REUSED]')
p=p.replace('update(cases=12,','update(cases=len(ALL),')
a=p.index('runner=runner.replace(');b=p.index("compile(runner,'run_review.py','exec')",a);p=p[:a]+p[b:]
p=p.replace('User explicitly requested these twelve cases. Only the six unprocessed cases are submitted; the previous six v003 cases are reused byte-for-byte, including failures and early-stop records.','All 34 user-authorized cases. Submit only the remaining 22 cases. Reuse the previous 12 cases byte-for-byte, including failures and early-stop records. Cases 32 and 33 refer to the same episode and are not independent trajectories.')
p=p.replace('Only cases 5,6,13,15,16,20. Reuse all six prior v003 results without retries or additional calls, including their failed answers. Other settings unchanged.','Only the 22 cases listed in new_case_numbers. Reuse all 12 prior results without retries or additional calls, including failed answers. Six workers; other settings and prompts unchanged.')
a=p.index("ui=(SITE/'guard_ui.js')");b=p.index("(SITE/'guard_ui.js').write_text(ui,encoding='utf-8')",a)
p=p[:a]+'''ui=(SITE/'guard_ui.js').read_text(encoding='utf-8')
ui=ui.replace('十二条轨迹离线评审','34 个案例离线评审').replace('Twelve-case offline review','34-case offline review')
ui=ui.replace('原列表第 4、5、6、7、11、13、14、15、16、17、20、28 条。本次补跑 5、6、13、15、16、20；其余六条直接复用上一轮结果。','完整 34 个案例，来自 33 条独立轨迹、9 个场景。本次补跑剩余 22 条，已有 12 条结果原样复用。第 32、33 个案例对应同一条轨迹。')
ui=ui.replace('Original cases 4, 5, 6, 7, 11, 13, 14, 15, 16, 17, 20 and 28. Cases 5, 6, 13, 15, 16 and 20 are newly reviewed; the other six reuse prior results.','All 34 cases from 33 distinct trajectories and 9 scenes. Only the remaining 22 cases are new; 12 prior cases are reused unchanged. Cases 32 and 33 share one trajectory.')
'''+p[b:]
a=p.index("doc=REPO/'experiments/")
p=p[:a]+'''doc=REPO/'experiments/deviation_progress/v003/run_20261112_05/README.md';doc.parent.mkdir(parents=True,exist_ok=True)
doc.write_text('# v003：扩展至全部34个案例\\n\\n2026-11-12，准备运行。只补跑剩余22条，已完成的12条（4、5、6、7、11、13、14、15、16、17、20、28）直接复用run04，包括40次请求中的7次失败，不重试。34个案例对应33条独立轨迹、9场景；32和33为同一轨迹的两个事件。\\n\\n沿用v003：有效节点连续编号、追加终止节点、首节点单图初始化、端点＋均匀最多5张中间图。DeepSeek flash、thinking enabled/high、JSON、max_tokens32768、六进程、每条串行，seed未指定。首次偏航后停止评审，没有真实回退或新导航。提示词与配置不变。\\n\\n本地网页完整中文任务指令、无去重开关，新增与复用来源分别标明。原始结果按case_number关联，旧case_index作为来源保留。\\n\\n启动：python -u <产物>/run/run_review.py --site <产物> --key-stdin。产物及源码快照：`'+str(SITE)+'`；基线、源码及复用文件哈希见manifest。\\n',encoding='utf-8')
for p,link in [(REPO/'docs/STATUS.md','../experiments/deviation_progress/v003/run_20261112_05/README.md'),(REPO/'experiments/README.md','deviation_progress/v003/run_20261112_05/README.md')]:
    s=p.read_text(encoding='utf-8');i=s.index('\\n')+1;s=s[:i]+f'\\n2026-11-12：[全部34个案例]({link})准备运行：仅补跑22条，12条复用；六进程、本地网页。\\n'+s[i:];p.write_text(s,encoding='utf-8')
print(json.dumps({'site':str(SITE),'new':NEW,'reused':REUSED,'scenes':len(maps),'nodes':manifest['cached_nodes'],'new_nodes':sum(len(c['nodes']) for c in cases if c['case_number'] in NEW),'cases':[{'case':c['case_number'],'nodes':len(c['nodes'])} for c in cases]},ensure_ascii=False))
'''
compile(p,'prepare.py','exec');(HERE/'prepare.py').write_text(p,encoding='utf-8')
f=(ROOT/'work/jev_guard_v003_remaining/finalize.py').read_text(encoding='utf-8')
f=f.replace('jev_deviation_progress_v003_terminal_12cases_20261112_run04','jev_deviation_progress_v003_terminal_34cases_20261112_run05').replace('jev_deviation_progress_v003_terminal_12cases_20261112.html','jev_deviation_progress_v003_terminal_34cases_20261112.html')
f=f.replace("==[4,5,6,7,11,13,14,15,16,17,20,28]","==list(range(1,35))")
f=f.replace("len(results['cases'])==12 and sum(len(c['nodes']) for c in inputs)==58","len(results['cases'])==34 and sum(len(c['nodes']) for c in inputs)==manifest['cached_nodes']")
f=f.replace("['reused_calls']==23","['reused_calls']==40")
f=f.replace("'effective_nodes':58,'terminal_nodes':12,'reused_six_cases_unchanged':True,'only_six_new_case_processes':True","'effective_nodes':manifest['cached_nodes'],'terminal_nodes':34,'reused_twelve_cases_unchanged':True,'six_new_worker_processes':True")
f=f.replace("'full_chinese_instructions':12","'full_chinese_instructions':34")
a=f.index("report='");b=f.index("(SITE/'README.txt').write_text",a)
f=f[:a]+'''report='本地可视化 v003｜全部34个案例｜2026-11-12\\n\\n打开 '+SINGLE.name+' 或本目录index.html。网页本地离线，不调用API。\\n\\n34个案例对应33条独立轨迹、9场景。仅补跑22条，已有12条原样复用（40次历史请求，包括7次失败）。编号32、33属于同一条轨迹，不作为两个独立样本统计。\\n\\n沿用v003，仅有效节点连续编号，增加终止节点，首节点单图初始化；端点两图＋均匀最多五张中间图。首次偏航停止后续评审，未执行真实回退。\\n\\n结果：'+json.dumps(s,ensure_ascii=False,indent=2)+'\\n\\n偏航区间：'+json.dumps(red,ensure_ascii=False,indent=2)+'\\n\\nnew_calls为本次新调用，reused_calls为历史复用，calls为合计。字段或请求错误均保留，未推进可信进度。模型结论不等同于真值或准确率。\\n'
'''+f[b:]
f=f.replace('v003/run_20261112_04','v003/run_20261112_05').replace('run_20261112_04/README.md','run_20261112_05/README.md')
a=f.index('for p in [REPO/');b=f.index('for p in Path(__file__).parent.glob',a)
f=f[:a]+'''for p in [REPO/'docs/STATUS.md',REPO/'experiments/README.md']:
    text=p.read_text(encoding='utf-8');text=text.replace('准备运行：仅补跑22条，12条复用；',f'已完成：补跑22条，新请求{s["new_calls"]}次、有效{s["new_valid"]}次，12条的40次记录原样复用；');p.write_text(text,encoding='utf-8')
category=REPO/'experiments/deviation_progress/README.md';text=category.read_text(encoding='utf-8')
if 'v003/run_20261112_05' not in text:text+='\\n- [v003 / run_20261112_05](v003/run_20261112_05/README.md)：全部34个案例；仅补跑22条，12条直接复用。\\n'
category.write_text(text,encoding='utf-8')
version_doc=REPO/'experiments/deviation_progress/v003/README.md';text=version_doc.read_text(encoding='utf-8')
if 'run_20261112_05' not in text:text+='\\n- [全部34个案例](run_20261112_05/README.md)：补跑22条，复用12条。\\n'
version_doc.write_text(text,encoding='utf-8')
'''+f[b:]
compile(f,'finalize.py','exec');(HERE/'finalize.py').write_text(f,encoding='utf-8')
print('Prepared run05 scripts.')
