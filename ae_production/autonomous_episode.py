"""Thin host-agent orchestration over authored_episode, never a second renderer.

Agent jobs contain local source paths and exact bindings. The hosting agent may
fulfil them directly, or an explicitly configured local command may respond.
An unavailable agent/observer is reported; no heuristic fabricates authorship,
human review, source permissions, natural speech, or media observations.
"""
import argparse
from copy import deepcopy
from html import escape
import json
import math
from pathlib import Path
import subprocess
import sys

from video_contracts import ROOT,read,write,sha,verify_bundle,status_matches
from scripts.voice_delivery import sha256
from ae_production.authored_episode import dispatch,checked_author,script_text,production_folder_allowed,validate_copy_review

STAGES=('check','script','chunks','voice','align','prepare','build','audit','render-master',
        'premiere','package-master','review','restore')


def job(folder,role,packet,command=None):
    request={'schema':'production-agent-job/v1','role':role,'packet':packet,
             'authority':'internal_ai_author_or_reviewer_not_human_or_publication',
             'public_render_ready':False}
    key=sha(request);directory=folder/'agent-jobs'/role;directory.mkdir(parents=True,exist_ok=True)
    req=directory/(key+'.request.json');response=directory/(key+'.response.json')
    write(req,request)
    if not response.exists() and command:
        if not isinstance(command,list) or not all(isinstance(x,str) and x for x in command):
            raise ValueError('Agent command must be an explicit argv list; shell execution is forbidden')
        subprocess.run(command+['--request',str(req),'--response',str(response)],check=True)
    if not response.exists():
        return {'status':'NEEDS_HOST_AGENT','role':role,'request':str(req),'request_sha':key,
                'response':str(response),'user_approval_required':False}
    result=read(response)
    if result.get('request_sha')!=key or result.get('human_approved') is not False:
        raise ValueError('Agent response has stale input or claims human approval')
    return result


def request_author(folder,brief):
    spec=read(brief)
    if spec.get('schema')!='autonomous-episode-brief/v1' or spec['product']!='FREE_SHOWCASE':
        raise ValueError('Explicit FREE_SHOWCASE brief required')
    inputs={str(Path(brief).resolve()):sha256(brief)};pool=[]
    for item in spec['asset_pool']:
        b=read(item['bundle']);s=read(item['status']);verify_bundle(b)
        valid=status_matches(b,s)
        pool.append({**deepcopy(item),'asset_id':b['asset_id'],'active':valid,
                     'answer_closed':b['analysis']['answer_verification']['closed'],
                     'source':b['source'],'question_id':b['source_snapshot']['question_id']})
        for key in ('bundle','status'):inputs[item[key]]=sha256(item[key])
    for p in spec['style_inputs']:inputs[p]=sha256(p)
    from creative_os.content_profiles import editorial_handoffs,STAGES as PROFILE_STAGES
    context=editorial_handoffs(spec['product'],{s:None for s in PROFILE_STAGES})
    return job(folder,'creative_author',{'brief':str(Path(brief).resolve()),'brief_sha':sha(spec),
        'content_profile_context':context,
        'input_files':inputs,'asset_pool':pool,'required_output':
        ['author','article_chunks','editorial_manifest','authoring_notes'],
        'requirements':['Read the complete frozen articles, current workflow and source-bound projections.',
        'Actually compare eligible candidates; never solve or relabel an old frozen package.',
        'Produce AV_AUTHOR decisions consumed by the current dispatch; use one scene order and clock.',
        'Point-of-use method name; quick/brief/focus; one useful local replay; complete candidate checks.',
        'Read the knowledge inputs and bind specific design choices; hypotheses are not learning results.',
        'Missing language decisions are a language-author job, never a user approval stop.',
        'Every new copy must be exported and sent in full by the host; keep user review pending.',
        'Keep voices intact; selected rejected takes are ineligible; current rights remain unchanged.']},
        spec.get('agent_command'))


def author(folder,brief):
    result=request_author(folder,brief)
    if result.get('status')=='NEEDS_HOST_AGENT':return result
    return consume_author_response(folder,result,brief)


def complete_chunks(folder,command=None):
    chunk=dispatch('chunks',folder)
    if chunk.get('status')!='NEEDS_LINGUISTIC_AUTHOR':return chunk
    a,_=checked_author(folder)
    decision=job(folder,'language_author',{'chunking_packet':chunk,
        'author_sha256':sha256(folder/'AV_AUTHOR.json'),'sources':a['sources']},command)
    if decision.get('status')=='NEEDS_HOST_AGENT':return decision
    write(folder/'ARTICLE_CHUNKS.json',decision['article_chunks'])
    return dispatch('chunks',folder)


def consume_author_response(folder,result,brief=None):
    a=result['author'];manifest=result['editorial_manifest']
    for p,d in result.get('input_files',{}).items():
        if sha256(p)!=d:raise ValueError('Changed authoring input: '+p)
    output=folder/'AV_AUTHOR.json'
    validate_copy_review(a)
    if result.get('human_approved',False) is not False or a['public_render_ready'] is not False:
        raise ValueError('Internal autonomy does not approve copy or public release')
    dest=folder/'EDITORIAL_MANIFEST.json'
    if dest.exists() and read(dest)!=manifest and output.exists():
        raise ValueError('Preserve existing editorial decisions; revise into a new folder')
    if result.get('article_chunks') and (folder/'ARTICLE_CHUNKS.json').exists() and read(folder/'ARTICLE_CHUNKS.json')!=result['article_chunks']:
        raise ValueError('Preserve existing linguistic decisions; revise into a new folder')
    write(dest,manifest)
    a=deepcopy(a);a['editorial']={'schema':'authored-editorial/v1','manifest':str(dest.resolve()),'sha256':sha256(dest)}
    if output.exists() and read(output)!=a:raise ValueError('Preserve the current author; revise into a new folder')
    write(output,a);checked_author(folder)
    if result.get('article_chunks'):
        write(folder/'ARTICLE_CHUNKS.json',result['article_chunks'])
    chunk=complete_chunks(folder,read(brief).get('agent_command') if brief else None)
    if chunk.get('status')=='NEEDS_HOST_AGENT':return chunk
    write(folder/'AUTHORING_RECEIPT.json',{'response_sha':sha(result),'brief':str(brief),
        'author_sha256':sha256(output),'notes':result['authoring_notes'],
        'human_approved':False,'public_render_ready':False})
    return {'status':'AUTHORED','revision':a['revision'],'questions':len(a['sources']),
            'voices':len(a['voices']),'author_sha256':sha256(output)}


def status(folder):
    result={'folder':str(folder),'public_render_ready':False,'user_acceptance':'PENDING'}
    for key,name in [('author','AV_AUTHOR.json'),('plan','AV_PLAN.json'),('native','native-identity.json'),
                     ('proxy','DELIVERY_QA.json'),('master','MASTER_DELIVERY_QA.json'),
                     ('review','INTERNAL_MEDIA_REVIEW.json'),('run','AUTONOMOUS_RUN.json')]:
        p=folder/name
        result[key]={'path':str(p),'sha256':sha256(p)} if p.exists() else 'NOT_COMPLETED'
    return result


def actual_scene_map(folder,plan,qa):
    """Map the real continuous native edit without claiming human observation."""
    from ae_production.authored_native import validate_edit
    picture=read(folder/('MASTER_PICTURE_RECEIPT.json' if qa['formal_4k_rendered'] else 'PICTURE_RECEIPT.json'))
    timeline=read(folder/'PR_TIMELINE.json')
    if (qa.get('video_payload_and_timestamps_unchanged') is not True
            or qa['frames']!=plan['frames'] or sha256(picture['output'])!=picture['sha256']):
        raise ValueError('Actual scene mapping requires the unchanged complete native picture')
    validate_edit(plan,timeline,picture['output'],(3840,2160) if qa['formal_4k_rendered'] else (1920,1080))
    fps=plan['format']['fps']
    result={'schema':'authored-actual-media-map/v1','media':qa['media'],'media_sha256':qa['sha256'],
            'plan_sha256':qa['plan_sha256'],'native_picture_sha256':picture['sha256'],
            'premiere_timeline_sha256':sha256(folder/'PR_TIMELINE.json'),
            'basis':'same native picture packets/timestamps; one full uncut native PR picture clip at zero; actual complete take placements',
            'authority':'automatic_engineering_mapping_not_external_human_review',
            'scenes':[{'scene':s['id'],'source_refs':s['source_refs'],
                       'actual_frame_range':[round(s['start']*fps),round(s['end']*fps)],
                       'actual_seconds':[s['start'],s['end']]} for s in plan['scenes']],
            'human_confirmed':False,'public_render_ready':False}
    write(folder/'ACTUAL_MEDIA_SCENE_MAP.json',result)
    return {'path':str(folder/'ACTUAL_MEDIA_SCENE_MAP.json'),'sha256':sha256(folder/'ACTUAL_MEDIA_SCENE_MAP.json')}


def production_ledger_root(folder,stored=None):
    """Keep observations with the actual registered production worktree."""
    folder=Path(folder).resolve()
    raw=subprocess.check_output(['git','-C',str(ROOT),'worktree','list','--porcelain','-z'])
    roots=[Path(row[len(b'worktree '):].decode('utf-8')).resolve()
           for row in raw.split(b'\0') if row.startswith(b'worktree ')]
    matches=[r for r in roots if folder.is_relative_to((r/'local-data').resolve())]
    if not matches:raise ValueError('Review ledger requires the production registered worktree')
    root=max(matches,key=lambda p:len(p.parts))
    expected=(root/'local-data/audience-learning').resolve()
    if (not expected.is_relative_to((root/'local-data').resolve())
            or (stored is not None and (not isinstance(stored,str) or stored!=str(expected)))):
        raise ValueError('Cached review ledger is outside its production worktree')
    return expected


def review(folder):
    """Request actual observations of the same final full film, not a PASS log."""
    from ae_production.authored_native import plan
    a,p=plan(folder)
    qpath=folder/'MASTER_DELIVERY_QA.json'
    if not qpath.exists():qpath=folder/'DELIVERY_QA.json'
    qa=read(qpath);media=qa['media']
    if sha256(media)!=qa['sha256']:raise ValueError('Review requires current actual encoded media')
    bindings={'plan_sha256':sha256(folder/'AV_PLAN.json'),'same_revision':a['revision'],
              'voice_delivery_sha256':p['voice_delivery_sha256'],
              'complete_copy_sha256':p['complete_copy_sha256'],'frames':p['frames']}
    if any(qa.get(k)!=v for k,v in bindings.items()):raise ValueError('Review media is not the current plan, voice and copy revision')
    mapping=actual_scene_map(folder,p,qa)
    from creative_os.content_profiles import editorial_handoffs
    context=editorial_handoffs(a['product'],{
        'selection':{'sources':a['sources'],'teaching_focus':a['teaching_focus']},
        'copy':script_text(a),'director':p.get('editorial_consumption',{}),
        'motion':read(folder/'native-audit.json') if (folder/'native-audit.json').exists() else None,
        'voice':{'delivery_sha256':p['voice_delivery_sha256'],'complete_takes':len(p['segments'])},
        'premiere':read(folder/'PR_TIMELINE.json') if (folder/'PR_TIMELINE.json').exists() else None,
        'human_review':None})
    write(folder/'CONTENT_PROFILE_CONTEXT.json',context)
    observation=job(folder,'independent_media_reviewer',{
        'media':media,'media_sha256':qa['sha256'],'duration':p['duration'],
        'plan':str(folder/'AV_PLAN.json'),'plan_sha256':sha256(folder/'AV_PLAN.json'),
        'script':str(folder/'EPISODE_SCRIPT.md'),'content_profile_context':context,'scenes':[
            {'id':s['id'],'range':[s['start'],s['end']],'task':s['audience_intent']} for s in p['scenes']],
        'requirements':['Review the whole continuous episode in order.',
          'See real moving transitions and listen to real audio before claiming those scopes.',
          'Bind each issue to media SHA, scene, seconds, observed fact, severity, responsible module and recheck.',
          'Static frames, waveforms and hashes do not certify motion or natural delivery.',
          'Keep unobserved video/audio scope explicit; do not fabricate observations.']})
    if observation.get('status')=='NEEDS_HOST_AGENT':return observation
    if observation['media_sha256']!=qa['sha256']:raise ValueError('Reviewer observed another cut')
    if not {'issues','continuous_coverage','video_observed','audio_observed'}<=observation.keys():
        raise ValueError('Independent observation is missing required facts')
    # Reviewer commentary cannot grant acceptance. Compare the same protected
    # host values that were persisted on the first consumption, so a descriptive
    # user_acceptance field cannot make an unchanged observation non-resumable.
    authority={'human_approved':False,'user_acceptance':'PENDING','public_render_ready':False}
    accepted_observation={**observation,**authority}
    existing_path=folder/'INTERNAL_MEDIA_REVIEW.json'
    if existing_path.exists():
        previous=read(existing_path)
        derived={'actual_media_mapping','continuous_video_review_completed',
                 'complete_listening_review_completed','ledger_root','ledger_records',*authority}
        if (previous.keys()-derived==observation.keys()-derived
                and all(previous.get(k)==v for k,v in accepted_observation.items())):
            from content_os.engagement_learning import AudienceLearning
            ledger_root=production_ledger_root(folder,previous.get('ledger_root'))
            if not (ledger_root/'audience.sqlite3').is_file():raise ValueError('Cached review ledger is missing')
            ledger=AudienceLearning(ledger_root)
            for ident in previous['ledger_records']:
                row=ledger.get(ident,'internal_ai_review')
                if row['media_sha256']!=qa['sha256'] or row['plan_sha256']!=bindings['plan_sha256']:
                    raise ValueError('Cached internal review ledger belongs to another cut')
            review_page(folder,qa,previous)
            return previous
        raise ValueError('Preserve the existing independent observation; revise into a new cut')
    ranges=observation['continuous_coverage']
    cursor=0
    for lo,hi in ranges:
        if abs(lo-cursor)>1/24 or not lo<hi<=p['duration']+1/24:raise ValueError('Review coverage is not continuous')
        cursor=hi
    complete=abs(cursor-p['duration'])<=1/24
    from content_os.engagement_learning import AudienceLearning
    ledger_root=production_ledger_root(folder)
    learning=AudienceLearning(ledger_root)
    ids=[]
    for issue in observation['issues']:
        ids.append(learning.internal_ai_review(media,p,issue,qa=qa,plan_path=folder/'AV_PLAN.json'))
    result={**observation,'actual_media_mapping':mapping,'continuous_video_review_completed':complete and observation['video_observed'],
            'complete_listening_review_completed':complete and observation['audio_observed'],
            'ledger_root':str(ledger_root),'ledger_records':ids,**authority}
    write(folder/'INTERNAL_MEDIA_REVIEW.json',result)
    review_page(folder,qa,result)
    return result


def review_page(folder,qa,observations=None):
    p=read(folder/'AV_PLAN.json');media=Path(qa['media']).as_uri()
    sections=''.join('<li><a href="#" onclick="v.currentTime='+str(s['start'])+';v.play();return false">'
        +escape(s['id']+' · '+s['title'])+'</a> '+str(round(s['start'],3))+'s</li>' for s in p['scenes'])
    files=[(Path(qa['media']),'完整影片'),(folder/'media/MAIN_FILM.aep','AE 可编辑工程'),
           (folder/'media/MAIN_FILM.prproj','Premiere 可编辑工程'),
           (folder/'EPISODE_SCRIPT.md','完整逐字稿'),(folder/'EPISODE_SUBTITLES.srt','字幕'),
           (folder/'ARTICLE_CHUNKS_REVIEW.html','两篇文章的意群划分'),
           (folder/'MODULE_CONSUMPTION_AUDIT.md','模块实际消费与限制')]
    links=' '.join('<a class="file" href="'+path.resolve().as_uri()+'">'+escape(label)+'</a>' for path,label in files if path.exists())
    html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>英语有画说 · 整片审阅</title><style>body{max-width:1120px;margin:36px auto;padding:0 22px;background:#f4f1e8;color:#18232a;font:17px/1.7 Arial}h1{font-size:28px}video{width:100%;background:#18232a;border-radius:8px}a{color:#205c7c}.file{display:inline-block;margin:8px 16px 8px 0}li{margin:5px}details{margin:26px 0}pre{white-space:pre-wrap;font-size:13px}</style>'
    html+='<h1>英语有画说 · 学霸这题怎么做？</h1><p>'+escape(p['revision'])+' · '+str(round(p['duration'],3))+' 秒 · 原生 4K / 24 帧 · 冻结诊断材料</p>'
    html+='<video id="v" controls preload="metadata" src="'+media+'"></video><p>'+links+'</p>'
    if p.get('copy_review')=='USER_REVIEWED_EXACT_COPY':
        html+='<p>此逐字稿已由用户独立审阅；观感、听感和整片仍待你验收。内部 AI 观察不等于人类认证，也不授权公开发布。</p>'
    else:
        html+='<p>整片由你验收，文案、观感和听感仍待确认。内部 AI 观察不等于人类认证，也不授权公开发布。</p>'
    if observations:
        if not observations.get('audio_observed'):
            html+='<p>声音已完整编排；本次工具不支持音频感知，自审未声称完成试听。</p>'
        if not observations.get('video_observed'):
            html+='<p>自审检查了实际编码画面与连续帧；完整原速运动观感未获感知确认。</p>'
    html+='<h2>按章节回看</h2><ol>'+sections+'</ol>'
    html+='<details><summary>制作、审阅与未完成事项</summary><pre>'+escape(json.dumps(observations or {'状态':'等待内部观察'},ensure_ascii=False,indent=2))+'</pre></details></html>'
    (folder/'REVIEW.html').write_text(html,encoding='utf-8')


def run(folder,brief=None,through='restore',batch_size=96):
    folder.mkdir(parents=True,exist_ok=True)
    receipt_path=folder/'AUTONOMOUS_RUN.json'
    index=read(receipt_path) if receipt_path.exists() else {'schema':'autonomous-production-run/v1',
        'stages':{},'public_render_ready':False,'user_acceptance':'PENDING','revisions':0}
    brief=brief or (folder/'BRIEF.json' if (folder/'BRIEF.json').exists() else None)
    if not (folder/'AV_AUTHOR.json').exists() or (brief and not (folder/'AUTHORING_RECEIPT.json').exists()):
        if not brief:raise ValueError('A new production starts with an actual brief and asset pool')
        result=author(folder,brief);index['authoring']=result;write(receipt_path,index)
        if result.get('status')=='NEEDS_HOST_AGENT':return result
    author_sha=sha256(folder/'AV_AUTHOR.json')
    if any(x.get('author_sha256')!=author_sha for k,x in index['stages'].items() if k in ('build','premiere','restore')):
        raise ValueError('Completed native stage belongs to another author; use a new revision')
    if 'restore' in index['stages'] and (folder/'MASTER_DELIVERY_QA.json').exists():
        from ae_production.authored_native import current_native
        a,p,_=current_native(folder);q=read(folder/'MASTER_DELIVERY_QA.json')
        if (q.get('plan_sha256')!=sha256(folder/'AV_PLAN.json') or q.get('same_revision')!=a['revision']
                or q.get('frames')!=p['frames'] or sha256(q['media'])!=q['sha256']):
            raise ValueError('Completed delivery changed; inspect before reopening any host')
        validate_cached_stage(folder,'restore')
        return {'status':'DELIVERED_HOSTS_ALREADY_RESTORED','media':q['media'],
                'user_acceptance':'PENDING','public_render_ready':False}
    for op in STAGES:
        # Recompute read-only validations; native writes rely on their exact
        # existing receipts. Never use a completed log to replay uncertain work.
        if op in index['stages'] and op in ('build','premiere','render-master','package-master','restore'):
            validate_cached_stage(folder,op)
            result=index['stages'][op]['result']
        else:
            index['active_stage']=op;write(receipt_path,index)
            try:
                if op=='review':result=review(folder)
                elif op=='chunks':result=complete_chunks(folder,read(brief).get('agent_command') if brief else None)
                elif op=='build' and (folder/'native-identity.json').exists():
                    from ae_production.authored_native import current_native
                    _,_,native=current_native(folder);result={'reused_verified_native_identity':sha(native)}
                elif op=='premiere' and (folder/'PR_SEQUENCE.json').exists():
                    if (folder/'PR_EXPORT_RECEIPT.json').exists():
                        validate_cached_stage(folder,op);r=read(folder/'PR_EXPORT_RECEIPT.json');result={'native_export':r['output'],'verified_existing_export':True}
                    else:result=dispatch('premiere-resume',folder)
                elif op=='package-master' and (folder/'MASTER_DELIVERY_QA.json').exists():
                    validate_cached_stage(folder,op);q=read(folder/'MASTER_DELIVERY_QA.json')
                    result={k:q[k] for k in ('media','actual_seconds','frames','full_decode','media_role')}
                else:result=dispatch(op,folder,batch_size=batch_size)
            except BaseException as error:
                index['failure']={'stage':op,'type':type(error).__name__,'message':str(error)}
                write(receipt_path,index);raise
            index['stages'][op]={'result':result,'author_sha256':sha256(folder/'AV_AUTHOR.json')}
            index.pop('failure',None);write(receipt_path,index)
        print(json.dumps({'stage':op,'result':result},ensure_ascii=False),flush=True)
        if result.get('status')=='NEEDS_HOST_AGENT' or op==through:return result
    return status(folder)


def restored_saved_projects(folder):
    """Verify final saved bytes only after a complete same-author restore stage."""
    folder=Path(folder)
    index=read(folder/'AUTONOMOUS_RUN.json');stage=index.get('stages',{}).get('restore',{})
    result=stage.get('result',{})
    if (stage.get('author_sha256')!=sha256(folder/'AV_AUTHOR.json')
            or not isinstance(result,dict) or set(result)!={'after_effects','premiere'}
            or result['after_effects'].get('restored') is not True
            or result['premiere'].get('opened') is not True or result['premiere'].get('verified') is not True):
        raise ValueError('Complete same-author restored native stages required')
    restored=read(folder/'RESTORED_HOSTS.json');saved=restored['saved_current_projects']
    if (restored.get('results')!=result or set(saved)!={'after_effects','premiere'}):
        raise ValueError('Complete saved AE and Premiere restoration evidence required')
    for name,filename in (('after_effects','MAIN_FILM.aep'),('premiere','MAIN_FILM.prproj')):
        expected=(folder/'media'/filename).resolve();entry=saved[name]
        if (entry.get('path')!=str(expected) or not expected.is_file()
                or sha256(expected)!=entry.get('sha256')):
            raise ValueError('Final restored project path or saved bytes changed')
    return saved


def saved_project_matches(folder,name,digest):
    filename='MAIN_FILM.aep' if name=='after_effects' else 'MAIN_FILM.prproj'
    path=(folder/'media'/filename).resolve();actual=sha256(path)
    if actual==digest:return True
    try:saved=restored_saved_projects(folder)
    except (ValueError,FileNotFoundError,KeyError,TypeError):return False
    return saved[name]['sha256']==actual


def validate_cached_stage(folder,operation):
    """A stage log is not a substitute for its bound saved outputs."""
    from ae_production.authored_native import current_native,media_directory
    if operation=='restore':
        restored_saved_projects(folder)
        return
    _,p,n=current_native(folder)
    if not (media_directory(folder)/'MAIN_FILM.aep').is_file():raise FileNotFoundError('Cached native build has no saved AEP')
    if operation in ('premiere','package-master'):
        r=read(folder/'PR_EXPORT_RECEIPT.json')
        if (r.get('plan_sha256')!=sha256(folder/'AV_PLAN.json') or sha256(r['output'])!=r.get('sha256')
                or not saved_project_matches(folder,'premiere',r.get('project_sha256'))):
            raise ValueError('Cached native edit/export changed')
        for name in ('PR_SEQUENCE.json','PR_TIMELINE.json','PR_SETTINGS.json'):read(folder/name)
    if operation=='render-master':
        picture=read(folder/'MASTER_PICTURE_RECEIPT.json')
        if (picture.get('plan_sha256')!=sha256(folder/'AV_PLAN.json')
                or picture.get('comp_id')!=n['master_comp_id'] or picture.get('frames')!=p['frames']
                or picture.get('formal_4k_rendered') is not True or sha256(picture['output'])!=picture['sha256']):
            raise ValueError('Completed native master changed')
        cursor=0
        for part in picture['parts']:
            if (part.get('done') is not True or part['start']!=cursor
                    or not 0<=part['start']<part['end']<=p['frames'] or part['comp_id']!=n['master_comp_id']
                    or part['plan_sha256']!=picture['plan_sha256']
                    or part['native_identity_sha256']!=sha256(folder/'native-identity.json')
                    or sha256(part['path'])!=part['sha256']):
                raise ValueError('Completed master part binding or coverage changed')
            if 'reuse' in part or part.get('new_native_render') is False:
                from ae_production.native_parts_reuse import validate_reused_part
                validate_reused_part(folder,part,part['path'])
            elif not Path(part['path']).resolve().is_relative_to((folder/'native-master-parts').resolve()):
                raise ValueError('Parent master part requires a verified reuse proof')
            cursor=part['end']
        if cursor!=p['frames']:raise ValueError('Completed master has incomplete part coverage')
    if operation=='package-master':
        q=read(folder/'MASTER_DELIVERY_QA.json')
        required={'plan_sha256':sha256(folder/'AV_PLAN.json'),'same_revision':p['revision'],
                  'frames':p['frames'],'voice_delivery_sha256':p['voice_delivery_sha256'],
                  'complete_copy_sha256':p['complete_copy_sha256'],'full_decode':'PASS',
                  'formal_4k_rendered':True,'media_role':'NATIVE_4K_MASTER',
                  'video_payload_and_timestamps_unchanged':True,'audio_payload_unchanged':True,
                  'public_render_ready':False}
        if (any(q.get(k)!=v for k,v in required.items()) or sha256(q['media'])!=q['sha256']
                or not saved_project_matches(folder,'after_effects',q['native_project_sha256'])
                or not saved_project_matches(folder,'premiere',q['premiere_project_sha256'])):
            raise ValueError('Completed full media or editable project changed')
        if ([x['id'] for x in q['complete_takes']]!=[s['id'] for s in p['segments']]
                or any(not math.isfinite(x['correlation_at_actual_start']) or x['correlation_at_actual_start']<.99 or x['complete_samples']<=0 for x in q['complete_takes'])):
            raise ValueError('Completed audio coverage changed')


def revise(folder,new_folder,decision):
    review_data=read(folder/'INTERNAL_MEDIA_REVIEW.json');request=read(decision)
    if request['media_sha256']!=review_data['media_sha256']:raise ValueError('Revision is not bound to reviewed media')
    previous=read(folder/'AUTONOMOUS_RUN.json')
    limit=request.get('max_directed_revisions',3)
    if type(limit) is not int or limit<1:raise ValueError('A positive directed revision budget is required')
    if previous.get('revisions',0)>=limit:raise ValueError('Directed revision budget exhausted; preserve user aesthetic acceptance')
    selected={i['issue_id']:i for i in review_data['issues']}
    if not request['issue_ids'] or any(i not in selected for i in request['issue_ids']):raise ValueError('No observed issue authorizes this revision')
    if new_folder.exists():
        if not (new_folder/'REVISION_REQUEST.json').exists() or read(new_folder/'REVISION_REQUEST.json')!=request:
            raise FileExistsError('Preserve another revision or changed issue selection')
    else:
        new_folder.mkdir(parents=True)
        write(new_folder/'REVISION_REQUEST.json',request)
        write(new_folder/'AUTONOMOUS_RUN.json',{'schema':'autonomous-production-run/v1','stages':{},
            'revisions':previous.get('revisions',0)+1,'parent':str(folder),
            'public_render_ready':False,'user_acceptance':'PENDING'})
    response=job(new_folder,'directed_revision',{'parent_author':str(folder/'AV_AUTHOR.json'),
        'issues':[selected[i] for i in request['issue_ids']],'request':request,
        'preserve':'Unchanged complete takes and independently verified native parts only; never reuse by filename alone.'})
    if response.get('status')=='NEEDS_HOST_AGENT':return response
    return consume_author_response(new_folder,response)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('request','author','run','status','review','revise'))
    parser.add_argument('folder',type=Path);parser.add_argument('--brief',type=Path)
    parser.add_argument('--through',choices=STAGES,default='restore');parser.add_argument('--batch-size',type=int,default=96)
    parser.add_argument('--new-folder',type=Path);parser.add_argument('--decision',type=Path)
    args=parser.parse_args();folder=args.folder.resolve()
    if not production_folder_allowed(folder):raise ValueError('Keep private production in indexed repository local-data')
    folder.mkdir(parents=True,exist_ok=True)
    if args.operation in ('request','author'):
        if not args.brief:parser.error('--brief is required')
        result=request_author(folder,args.brief) if args.operation=='request' else author(folder,args.brief)
    elif args.operation=='run':result=run(folder,args.brief,args.through,args.batch_size)
    elif args.operation=='revise':
        if not args.new_folder or not args.decision:parser.error('revise requires --new-folder and --decision')
        target=args.new_folder.resolve()
        if not target.is_relative_to((ROOT/'local-data').resolve()):raise ValueError('Keep the new private revision in local-data')
        result=revise(folder,target,args.decision)
    else:result=globals()[args.operation](folder)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
