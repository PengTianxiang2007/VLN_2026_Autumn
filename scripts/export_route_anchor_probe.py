"""Standalone two-case stage-one review using the existing synchronized timeline layout."""
import argparse,base64,copy,io,json,math,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write,file_hash,now

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);a=ap.parse_args();run=a.run.resolve();out=run/'exports/run_20261106_01';out.mkdir(parents=True,exist_ok=False)
 old_html=ROOT/'outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html'
 text=old_html.read_text();old=json.loads(text.split('<script id="data" type="application/json">',1)[1].split('</script>',1)[0]);del text
 cases=[];images={};maps={}
 for item in read(run/'dataset.json')['cases']:
  c=copy.deepcopy(next(x for x in old['cases'] if x['sample_id']==item['sample_id']));c['previous_call1']=c['calls']['1']['answer'];comparison=read(run/'manifest.json').get('comparison_run');c['previous_call1']=json.loads(read(ROOT/comparison/'cases'/item['sample_id']/'call1_response.json')['content']) if comparison else c['previous_call1'];c['previous_checkpoint_frame']=c['checkpoint_frame'];c['checkpoint_frame']=item['checkpoint_frame'];c['wrong_end_frame']=item['checkpoint_frame'];c['images']=item['images'];c['approach_actions']=item['approach_actions'];c['attempt_actions']=[]
  for im in c['images']:
   b=(run/im['path']).read_bytes();assert file_hash(run/im['path'])==im['sha256'];images[im['sha256']]='data:image/png;base64,'+base64.b64encode(b).decode();c['frames'][im['frame']]['image_key']=im['sha256']
  for frame in c['frames']:
   key=frame['image_key']
   if key not in images:images[key]=old['images'][key]
  c['review']['checkpoint_position']=c['frames'][c['checkpoint_frame']]['position'];c['crossing_distance_m']=math.dist(c['review']['crossing']['position'][:2],c['review']['checkpoint_position'][:2]);scene=c['review']['scene'];maps[scene]=old['maps'][scene]
  f=run/'cases'/c['sample_id']/'call1_response.json';raw=read(f);answer=json.loads(raw['content']);display=answer if 'branches' in answer else answer.get('properties',{});c['calls']['1']=dict(answer=answer,display=display,raw_content=raw['content'],validated=(f.parent/'call1_answer.json').exists(),response_sha256=file_hash(f));c['calls']['2']=dict(answer=None,display=dict(selected_branch_id=None,excluded_branch_ids=[]),validated=False,raw_content=None);c['status']=read(f.parent/'status.json');cases.append(c)
 data=dict(cases=cases,images=images,maps=maps,summary=read(run/'summary.json'),run_hash=file_hash(run/'manifest.json'),exported_at=now());del old
 script=(ROOT/'core/human_route_review.js').read_text();start=script.index('function decisionText(c)');end=script.index('function selectCase(n)',start)
 render=r'''function decisionText(c){return `${c.previous_call1.branches.length} → ${c.calls[1].display.branches.length} 条支路`}
function renderDetails(){
 const c=current(),inv=answer(1),previous=c.previous_call1;
 $('case-title').textContent=`${c.sample_id} · ${c.review.scene} · 窗口后移对照`;
 $('task').textContent=(english?c.instruction:c.instruction_zh)+'（任务仅供复核，本轮模型未接收指令）';
 $('case-meta').textContent=`原标注 C=F${String(c.previous_checkpoint_frame).padStart(4,'0')}；新判断 P=F${String(c.checkpoint_frame).padStart(4,'0')}；水平相距 ${c.crossing_distance_m.toFixed(2)} m。只测试阶段一。`;
 $('decision').className='card decision';$('decision').innerHTML=`<div class="decision-title">阶段一分支数量：${esc(decisionText(c))}</div><p>原覆盖：${esc(previous.coverage)}；新覆盖：${esc(inv.coverage)}。数量增加及模型自报完整不代表清单正确。</p>`;
 $('branch-title').textContent=`新窗口：模型识别 ${inv.branches.length} 条分支`;$('inventory-summary').textContent=inv.view_summary;
 $('branches').innerHTML=inv.branches.map(b=>`<article class="branch" data-branch="${esc(b.id)}"><h3>${esc(b.id)} · ${esc(DIR[b.direction]||b.direction)}</h3><p>来路标记：${esc(b.incoming)}</p><p><b>入口：</b>${esc(b.landmark)}</p><p><b>模型认为通向：</b>${esc(b.destination_hypothesis)}</p>${evidence(b.evidence_ids)}</article>`).join('');
 $('incoming-note').textContent='描述保留模型英文原答。'+inv.uncertainties.join(' ');
 $('protocol').textContent=`阶段一结构校验：${c.calls[1].validated?'通过':'未通过（原答多包了一层type/properties等字段；卡片仅提取内部内容供查看，原答未修改）'}；阶段二未调用。英文prompt、schema、temperature、max_tokens及请求种子保持不变；当前帧与已执行动作窗口一起后移。`;
 $('raw').textContent=JSON.stringify({old_first:previous,new_first:c.calls[1].answer,original_annotation_frame:c.previous_checkpoint_frame,new_current_frame:c.checkpoint_frame},null,2);
 $('reference-text').textContent='相对原C多看了后续10帧；只在延迟后的P具有因果性。没有执行新路线。原样本是开发案例，不据此计算泛化正确率。';bindEvidence();
}
'''
 script=script[:start]+render+script[end:];start=script.index("$('stats').innerHTML=");end=script.index("$('case-select').onchange",start)
 script=script[:start]+"$('stats').innerHTML=[`${DATA.cases.length}个案例`,`${DATA.summary.responses}次阶段一响应`,'阶段二0次','窗口后移10帧','原prompt不变'].map(t=>'<span class=\"stat\">'+esc(t)+'</span>').join('');\n$('case-select').innerHTML=DATA.cases.map((c,i)=>`<option value=\"${i}\">${c.sample_id} · ${c.review.scene} · ${decisionText(c)}</option>`).join('');\n"+script[end:]
 script=script.replace('这就是两次独立调用共同指定的当前观测帧。','本次阶段一实际指定的当前观测帧。').replace("'判断前历史'","'新判断帧之前的历史'")
 template=(ROOT/'core/human_route_review_page.html').read_text();template=re.sub(r'<section class="detail-grid">.*?</section>','',template,flags=re.S)
 replacements={'本地 Qwen27B · 手工标注 34 条':'本地 Qwen27B · 阶段一窗口后移试验','模型识别的支路、最终选择与原始轨迹':'窗口后移 · 阶段一支路盘点对照','错误片段末帧':'回到新判断帧','第一轮最多4张历史/当前观测；第二轮最多增加4张错误尝试观测。未发起第二轮的样本，其错误帧只供复核。':'本轮阶段一只接收这4张图。P=C+10；C之后的图像只在延迟后的P可用。','原始回答、两次清单传递与协议状态':'旧窗口与新窗口的阶段一原始回答','我认为选择正确':'我认为清单合理','我认为选择错误':'我认为清单存在问题','本次34条手工标注离线结果':'本次阶段一开发试验','此图与模型请求中的当前观测图像逐字节一致。':'此图与新窗口阶段一请求中的当前观测图像逐字节一致。'}
 for x,y in replacements.items():template=template.replace(x,y)
 style=(ROOT/'core/agent_panorama_choice_page.html').read_text().split('<style>',1)[1].split('</style>',1)[0]
 page=template.replace('__SHARED_STYLE__',style).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('__SCRIPT__',script)
 offsets=read(run/'manifest.json')['registration']['sample_offsets_from_annotation']
 page=page.replace('本轮阶段一只接收这4张图。P=C+10', '本轮阶段一只接收这4张图，采样偏移：'+ '、'.join(format(x,'+d') for x in offsets)+' 帧。P=C+10')
 page=page.replace('本轮阶段一只接收这4张图','本轮阶段一接收这7张图').replace('P=C+10；C之后的图像只在延迟后的P可用。','P=C；C前2张、C当帧、C后4张，后续图像仅帮助复核原C处的分支。')
 page=page.replace('窗口后移10帧','当前固定为原标注C').replace('窗口后移','以C为中心采样').replace('新判断帧之前的历史','原C之前的历史').replace('当前帧与已执行动作窗口一起后移。','当前帧固定为原标注C；前后观测和动作分别标记。').replace('相对原C多看了后续10帧；只在延迟后的P具有因果性。','目标始终为原标注C。使用C前后观测进行离线回顾，不代表C时刻的在线因果输入。')
 page=page.replace("im.phase==='checkpoint_context'?'第一次输入':c.calls[2].answer?'第二次新增':'未发送 · 复核用'", "im.phase==='before_checkpoint'?'C之前':im.phase==='current_checkpoint'?'当前标注C':'C之后 · 上下文'")
 if read(run/'manifest.json').get('comparison_run'):
  page=page.replace('原prompt不变','小幅放宽prompt').replace('英文prompt、schema、temperature、max_tokens及请求种子保持不变','英文prompt小幅更新；七张输入、user消息、schema、temperature、max_tokens及请求种子不变').replace('旧窗口与新窗口','保留版与放宽版').replace('新窗口：模型识别','放宽提示词：模型识别')
 from fontTools import subset
 from fontTools.ttLib import TTFont
 cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font);buf=io.BytesIO();font.save(buf);page=page.replace('__FONT__','data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode())
 html=out/'crossing_centered_stage1_review.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt');(out/'review.js').write_text(script)
 hashes={}
 for rel in ['scripts/export_route_anchor_probe.py','core/human_route_review.js','core/human_route_review_page.html','core/agent_panorama_choice_page.html']:
  p=out/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p);hashes[rel]=file_hash(p)
 write(out/'export_audit.json',{'html_sha256':file_hash(html),'source_run_manifest_sha256':file_hash(run/'manifest.json'),'source_hashes':hashes,'model_calls_added':0,'samples':len(cases),'created_at':now()});print(str(html))
if __name__=='__main__':main()
