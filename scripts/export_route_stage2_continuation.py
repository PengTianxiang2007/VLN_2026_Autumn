"""Export the continued two-stage run using the existing full offline timeline."""
import argparse,base64,copy,io,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.agent_route_choice import read,write,file_hash,digest,now

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);a=ap.parse_args();run=a.run.resolve();out=run/'exports/run_20261106_01';out.mkdir(parents=True,exist_ok=False)
 old_path=ROOT/'outputs/agent_route_choice/human_v001/run_20261106_01/exports/run_20261106_01/human_qwen27b_review.html';text=old_path.read_text();old=json.loads(text.split('<script id="data" type="application/json">',1)[1].split('</script>',1)[0]);del text
 images={};maps={};cases=[];audits=[]
 for item in read(run/'dataset.json')['cases']:
  c=copy.deepcopy(next(x for x in old['cases'] if x['sample_id']==item['sample_id']));c.update(item);folder=run/'cases'/c['sample_id']
  for im in c['images']:
   p=run/im['path'];assert file_hash(p)==im['sha256'];images[im['sha256']]='data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode();c['frames'][im['frame']]['image_key']=im['sha256']
  for f in c['frames']:
   k=f['image_key']
   if k not in images:images[k]=old['images'][k]
  maps[c['review']['scene']]=old['maps'][c['review']['scene']];calls={}
  for stage in (1,2):
   p=folder/f'call{stage}_response.json';raw=read(p) if p.exists() else None
   try:answer=json.loads(raw['content']) if raw else None
   except ValueError:answer=None
   defaults=dict(view_summary='',branches=[],uncertainties=[]) if stage==1 else dict(status='not_called',wrong_branch_id=None,excluded_branch_ids=[],selected_branch_id=None,instruction_evidence=[],wrong_branch_evidence_ids=[],selection_evidence_ids=[],uncertainties=[],route_description=None,error_reason=None,confidence=None)
   extracted=answer if not(stage==1 and answer and 'branches' not in answer) else answer.get('properties',{})
   calls[str(stage)]=dict(answer=answer,display={**defaults,**(extracted or {})},raw_content=raw['content'] if raw else None,validated=(folder/f'call{stage}_answer.json').exists(),response_sha256=file_hash(p) if raw else None)
  c['calls']=calls;c['status']=read(folder/'status.json');c['inventory_transfer_verified']=False
  if (folder/'call2_request.json').exists():
   req=read(folder/'call2_request.json');meta=json.loads(req['messages_image_hash_preview'][1]['content'][0]['text']);assert meta['branch_inventory']==calls['1']['answer'];assert req['inventory_sha256']==digest(calls['1']['answer']);c['inventory_transfer_verified']=True
  if (folder/'observed_route_answer.json').exists():
   c['observed_route']=read(folder/'observed_route_answer.json');c['locked_exclusion']=read(folder/'locked_exclusion.json') if (folder/'locked_exclusion.json').exists() else {'branch_id':None};c['observed_route_raw']=read(folder/'observed_route_response.json')['content'];c['recognition_input_ids']=[i['id'] for i in json.loads(read(folder/'observed_route_request.json')['messages_image_hash_preview'][1]['content'][0]['text'])['image_order']]
  cases.append(c);audits.append(dict(sample_id=c['sample_id'],input_frames=[i['frame'] for i in c['images']],inventory_transfer_verified=c['inventory_transfer_verified'],first_wrapper_preserved=c['status']['inventory_wrapper_preserved']))
 summary=read(run/'summary.json');summary['replay_frames']=sum(len(c['frames']) for c in cases);data=dict(cases=cases,images=images,maps=maps,summary=summary,run_hash=file_hash(run/'manifest.json'),exported_at=now())
 script=(ROOT/'core/human_route_review.js').read_text()
 script=script.replace("im.phase==='checkpoint_context'?'第一次输入':c.calls[2].answer?'第二次新增':'未发送 · 复核用'", "im.roles.includes('checkpoint_context')?(im.roles.includes('wrong_attempt')?'两轮上下文＋错误经历':'两轮上下文'):'第二轮新增 · 错误经历'")
 script=script.replace('${DATA.summary.response_count}次原响应 · 无新推理','第一轮复用${DATA.cases.length}份 · 第二轮${DATA.summary.stage2_responses}份响应')
 script=script.replace("$('incoming-note').textContent='来路", "$('incoming-note').textContent=(c.status.inventory_wrapper_preserved?'本例第一轮原答包装格式异常，卡片提取内部字段展示；原答完整传入第二轮。 ':'')+'来路")
 script=script.replace('本次导出没有模型调用。','第一轮原答完整复用，第二轮重新调用；本HTML导出不增加推理。')
 if read(run/'manifest.json').get('forced_choice'):
  script=script.replace('原协议校验通过；不代表选择正确。','强制选择协议校验通过；不代表选择正确。').replace('原协议校验未通过：','本版协议校验未通过：')
  script=script.replace('语义正确率：待复核','强制选择 · 正确率待复核')
 if read(run/'manifest.json').get('split_observed_route'):
  script=script.replace('第一轮复用${DATA.cases.length}份 · 第二轮${DATA.summary.stage2_responses}份响应','第一轮复用${DATA.cases.length}份 · 视觉识别${DATA.summary.observed_route_responses}次＋替代选择${DATA.summary.stage2_responses}次')
  script=script.replace(' bindEvidence();', ''' if(c.observed_route){const o=c.observed_route;$('observed-route-detail').innerHTML=`<h3>独立视觉调用：实际走过哪条路线</h3><p>不提供任务指令、动作词或错误标签。输入：${esc(c.recognition_input_ids.join("、"))}。</p><p><b>实际分支：${esc(o.observed_branch_id)} · ${esc(DIR[o.observed_direction])}；置信度：${esc(CONF[o.confidence])}</b></p><p>${esc(o.visual_description)}</p>${evidence(o.evidence_ids)}<p>程序锁定排除：${esc(c.locked_exclusion.branch_id||'未识别，未进入替代选路')}。下一次选路不可修改。</p><p>${esc(o.uncertainties.join(' '))}</p>`;}else{$('observed-route-detail').innerHTML='<h3>独立视觉调用</h3><p>未获得有效路线识别结果。'+esc(c.status.error||c.status.phase)+'</p>';} bindEvidence();''')
  script=script.replace('first:c.calls[1].answer,second:c.calls[2].answer','first:c.calls[1].answer,observed_route:c.observed_route,observed_route_raw:c.observed_route_raw,locked_exclusion:c.locked_exclusion,second:c.calls[2].answer')
 if read(run/'manifest.json').get('full_human_dataset'):
  script=script.replace('第一轮复用${DATA.cases.length}份 · 视觉识别${DATA.summary.observed_route_responses}次＋替代选择${DATA.summary.stage2_responses}次','已完成10例复用 · 新增24例 · 视觉识别${DATA.summary.observed_route_responses}份＋替代选择${DATA.summary.stage2_responses}份')
  script=script.replace('第一轮原答完整复用，第二轮重新调用；本HTML导出不增加推理。','10例完整复用历史结果，另外24例按同一协议新运行。本HTML导出不增加推理。')
 style=(ROOT/'core/agent_panorama_choice_page.html').read_text().split('<style>',1)[1].split('</style>',1)[0];page=(ROOT/'core/human_route_review_page.html').read_text()
 page=page.replace('手工标注 34 条','七帧上下文 · 接续第二轮 10 条').replace('本次34条手工标注离线结果','本次10条手工标注离线结果').replace('GLM原批因账户无额度没有有效回答。','')
 page=page.replace('第一轮最多4张历史/当前观测；第二轮最多增加4张错误尝试观测。未发起第二轮的样本，其错误帧只供复核。','第一轮七帧：C−4、C−2、C、C+2、C+4、C+6、C+10；第二轮保留七帧并加入错误片段均匀四帧，去重后最多11张。C始终为原标注点。超过错误片段终点的上下文仅是补充观察，不属于该段错误经历。')
 if read(run/'manifest.json').get('forced_choice'):
  page=page.replace('接续第二轮 10 条','第二轮强制选择 10 条').replace('该版只要求排除错误支路，来路标识按第一次原答展示，不套用全景版的双排除协议。','本版强制从原清单选择一个最可能分支；错路未知不阻断选择，已识别的错路仍须排除。低置信度与不确定性保留，强制选择率不等于正确率。')
 page=page.replace('第二轮强制选择 10 条',f'第二轮强制选择 {len(cases)} 条').replace('本次10条手工标注离线结果',f'本次{len(cases)}条手工标注离线结果')
 if read(run/'manifest.json').get('split_observed_route'):
  page=page.replace('<section class="detail-grid">','<section class="card" id="observed-route-detail"></section><section class="detail-grid">')
  page=page.replace(f'第二轮强制选择 {len(cases)} 条',f'视觉识别与选路隔离 · {len(cases)}例').replace('本版强制从原清单选择一个最可能分支；错路未知不阻断选择，已识别的错路仍须排除。','本版先独立识别实际路线，再由程序锁定排除，最后独立结合任务选择替代路线。')
  page=page.replace('第一轮原答完整复用，第二轮重新调用；本HTML导出不增加推理。','第一轮原答复用；独立视觉识别不给指令和动作，程序锁定排除后再独立选路。本HTML导出不增加推理。')
 if read(run/'manifest.json').get('full_human_dataset'):
  page=page.replace('第一轮原答复用；独立视觉识别不给指令和动作，程序锁定排除后再独立选路。本HTML导出不增加推理。','10例复用已完成结果，另外24例按同一协议新运行；识别与任务选路独立，排除由程序锁定。')
  page=page.replace('第一轮七帧：C−4、C−2、C、C+2、C+4、C+6、C+10；','第一轮目标七帧：C−4、C−2、C、C+2、C+4、C+6、C+10；轨迹开头缺失的历史帧直接略去，不补造；')
 page=page.replace('__SHARED_STYLE__',style).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('__SCRIPT__',script)
 from fontTools import subset
 from fontTools.ttLib import TTFont
 cfg=read(ROOT/'core/crossing_visualization_template.json');font=TTFont(cfg['font'],fontNumber=0);sub=subset.Subsetter();sub.populate(text=page);sub.subset(font);buf=io.BytesIO();font.save(buf);page=page.replace('__FONT__','data:font/ttf;base64,'+base64.b64encode(buf.getvalue()).decode())
 html=out/'crossing_two_stage_review.html';html.write_text(page);shutil.copy2(cfg['font_license'],out/'FONT_LICENSE.txt');(out/'review.js').write_text(script)
 hashes={}
 for rel in ['scripts/export_route_stage2_continuation.py','core/human_route_review.js','core/human_route_review_page.html','core/agent_panorama_choice_page.html']:
  dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);hashes[rel]=file_hash(dest)
 write(out/'export_audit.json',dict(html_sha256=file_hash(html),run_manifest_sha256=data['run_hash'],source_hashes=hashes,cases=audits,summary=summary,model_calls_added=0,created_at=now()));print(json.dumps(dict(html=str(html),mib=html.stat().st_size/1024**2,summary=summary)))
if __name__=='__main__':main()
