"""Publish-ready index of historical early and paired semantic-delay Oracle replays."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/visualization_publishing/oracle_four_conditions_20261107_01'
OUT.mkdir(parents=True,exist_ok=False)
translations=[
'右转，让电视和电视柜位于右侧。从门口向前走，进入下一个房间。继续直行，经过右侧的一把棕色椅子和左侧的一盆植物，在窗户前停下。',
'从走廊左转进入用餐区。直走，经过右侧的餐桌。继续进入厨房，在带水槽的台面前停下。',
'从有衣柜的房间左转进入走廊。沿走廊直走，经过右侧的卫生间和左侧通向卧室的敞开门口。穿过走廊尽头敞开的拱门进入客厅。向前走，经过左侧的沙发和电视，朝左侧敞开的门口走去。从这个门口进入阳光房，然后左转。在客厅的沙发前停下，此时大窗户位于右侧。',
'右转进入走廊，左侧是一幅绿色画框的画，右侧墙上挂着四幅画。沿走廊直走，经过左侧的一盆高大植物和右侧的开放式厨房。穿过正前方的门口进入卧室。朝左侧的床走去，在床右侧的床头柜旁停下。',
'右转，经过左侧的白色衣柜，然后进入前方的走廊。沿走廊直走，经过两侧敞开的门口。进入走廊尽头的大房间。左转，让带椅子的餐桌位于右侧，在前方墙上的深色门前停下。',
'从当前位置右转，经过左侧的装饰架和电视。继续直走，进入右侧的门口，让嵌入式衣柜位于左侧。向前走进铺着浅色地毯的开放走廊，经过右侧的墙面装饰画。沿走廊继续直走，经过左侧的厨房和用餐区。右转进入下一个房间，穿过门口时经过左侧的一盆大型植物。直走进入客厅，经过右侧的电视柜，在带蓝色和黄色靠垫的沙发前停下。',
'向前走，让装有电视的墙位于左侧，带沙发的客厅位于右侧。继续直走，经过左侧的装饰隔断，朝前方的餐厅走去。到达开口处时，左转进入走廊。直走，经过右侧的画，进入卧室。继续向卧室内走，让电视位于左侧，在床前停下，床头柜位于床的右侧。',
'沿走廊直走，经过右侧的卧室门口。继续向前，经过左侧的书房区域。经过左侧的架子时，右转进入餐厅。朝餐桌走去，让餐桌位于左侧。然后右转进入厨房。直走进入厨房，在窗户正下方的水槽前停下。',
'左转进入卧室，经过左侧的电视和右侧的床。在梳妆台前停下，镜子位于左侧。',
'直走穿过门口进入客厅，经过左侧的沙发和茶几，以及右侧的电视。右转穿过下一个门口。继续直走进入卧室，让电视位于左侧，在床和窗户前停下。'
]
sources={
'early':ROOT/'outputs/oracle_crossing/seed2_10_multi_20261103/oracle_early10_offline.html',
'paired':ROOT/'outputs/oracle_crossing/paired_delay10/run_20261104_01/oracle_paired_delay10_offline.html'}
manifest={'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sources':{},'assets':[]}
lookup=None
for kind,source in sources.items():
 s=source.read_text();d=json.loads(re.search(r'<script id="[^"]+-data" type="application/json">(.*?)</script>',s,re.S).group(1))
 if lookup is None:lookup=dict(zip([c['instruction'] for c in d['cases']],translations));assert len(lookup)==10
 assert all(c['instruction'] in lookup for c in d['cases'])
 toolbar='<div style="padding:10px 24px;background:#e7eff8"><a href="../index.html">← 四组实验入口</a>　<label>任务指令语言 / Instruction language <select id="language"><option value="zh">中文</option><option value="en">English</option></select></label></div>'
 s=re.sub(r'(<body[^>]*>)',lambda m:m.group(1)+toolbar,s,count=1)
 needle="$('instruction').textContent=cc.instruction"
 assert s.count(needle)==1,(kind,s.count(needle))
 s=s.replace(needle,"$('instruction').textContent=instructionText(cc)")
 prefix='let displayLanguage="zh";const INSTRUCTIONS_ZH='+json.dumps(lookup,ensure_ascii=False)+';function instructionText(cc){return displayLanguage==="en"?cc.instruction:INSTRUCTIONS_ZH[cc.instruction]}\n'
 # Only modify the executable script; JSON experiment payload is unchanged.
 s=s.replace('<script>','<script>'+prefix,1)
 s=s.replace('</script></body>',"$('language').onchange=e=>{displayLanguage=e.target.value;$('instruction').textContent=instructionText(c())};\n</script></body>")
 assert "$('language').onchange" in s
 temp=OUT/(kind+'_bilingual.html');temp.write_text(s)
 subprocess.run([sys.executable,'-B',str(ROOT/'scripts/prepare_online_visualization.py'),'--html',str(temp),'--destination',str(OUT/kind)],check=True)
 online=json.loads((OUT/kind/'online_manifest.json').read_text())
 manifest['assets'] += [kind+'/'+online['html']]+[kind+'/'+a for a in online['assets']]
 manifest['sources'][kind]={'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'online_html':kind+'/'+online['html'],'cases':len(d['cases'])}
(OUT/'translations.json').write_text(json.dumps(lookup,ensure_ascii=False,indent=2))
(OUT/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Oracle 纠正时机 · 十条任务四组回放</title><style>body{font:17px/1.8 system-ui,sans-serif;background:#f1f5f9;color:#18354e;max-width:1000px;margin:40px auto;padding:0 20px}section{background:white;padding:24px;border-radius:14px;margin:20px 0}a{color:#155bb4}table{border-collapse:collapse;width:100%}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}.note{background:#fff4db;padding:16px;border-radius:9px}</style><h1>Oracle 纠正时机：同十条任务、四组回放</h1><p>VLNVerse R2R 风格任务 · StreamVLN · 保留 policy memory（策略记忆）· 已完成实验的可视化</p><p class="note">确认已经走错后，Oracle 修改机器人位置与朝向，使其回到关联正确路线，再让原策略继续导航。允许多次纠正。尽早组来自较早的独立运行；只有短、中、长三档延迟共享错误前缀，四组不是严格同前缀配对。</p><section><h2>① 确认走错后尽早纠正</h2><p>10 条任务 · 成功 10/10 · 18 次纠正。</p><a href="early/early_bilingual.html">打开尽早纠正组：轨迹、纠正前后画面、后续决策 →</a></section><section><h2>② 短延迟　③ 中延迟　④ 长延迟</h2><p>同十条任务，按错误发展的语义阶段触发；每条三个分支并排回放。</p><table><tr><th>条件</th><th>全部十条成功</th><th>实际纠正分支</th><th>未触发</th></tr><tr><td>短延迟</td><td>6/10</td><td>8</td><td>2</td></tr><tr><td>中延迟</td><td>5/10</td><td>7</td><td>3</td></tr><tr><td>长延迟</td><td>5/10</td><td>7</td><td>3</td></tr></table><p><a href="paired/paired_bilingual.html">打开三档延迟：共同前缀及纠正后分支同步回放 →</a></p></section><section><h2>阅读口径</h2><p>三档均触发的七条完整配对任务，各档成功均为5/7，但成功任务不同。未触发项保留自然结局，不当作纠正后的结果。近目标落点、多次干预及不同运行的错误差异限制因果解释，不能据此认定延迟越长一定越差。</p><p>此处是“尽早＋短／中／长语义延迟”，不是另一套3／5／8／12米距离阈值实验。任务指令支持中文与English切换；其余审阅说明原本为中文。保持原始数据，图片按需加载。</p></section></html>''')
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'output':str(OUT),'assets':len(manifest['assets'])}))
