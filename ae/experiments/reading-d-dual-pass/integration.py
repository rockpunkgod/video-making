"""Extend accepted native original words using existing reviewed evidence only."""
import argparse
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import shutil
import time
from PIL import ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from frozen_case import file_sha,project
from video_contracts import read,write,sha
from ae_production.execution import mutation_call
from ae_production.memory_guard import monitor_existing_render,available_memory

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'method-relay-dual-pass'))
import run as relay
import locating_render
import acquisition_ab


def local(path):
    result=Path(path).resolve()
    if not result.is_relative_to(relay.ROOT/'local-data/reading-d-dual-pass'):
        raise ValueError('Real case data stays in the ignored case directory')
    return result


def segments():
    return [dict(id=i,start=a,end=b,source_start=c,source_end=d)
        for i,a,b,c,d in [('ORIGINAL_QUESTION',0,8,0,0),('FAST_LOCATE',8,15,0,7),
            ('FAST_APPLICATION',15,32,20,37),('REPLAY_ENTRY',32,35,7,8),
            ('GUIDED_LOCATE',35,47,8,20),('GUIDED_APPLICATION',47,94,40,87)]]


def validate_timeline(rows):
    if rows!=segments():raise ValueError('Preserve literal locating windows and complete application')
    cursor=0
    for s in rows:
        if s['start']!=cursor or not s['start']<s['end']:raise ValueError('Contiguous timeline required')
        if any(abs(v*24-round(v*24))>1e-8 for v in [s['start'],s['end'],s['source_start'],s['source_end']]):raise ValueError('Frame boundary required')
        if s['id'] not in ('ORIGINAL_QUESTION','REPLAY_ENTRY') and s['end']-s['start']!=s['source_end']-s['source_start']:raise ValueError('No speed change')
        cursor=s['end']
    return cursor


def screen_projections(source):
    copies=[source['segments'][0]['screen_text'],source['segments'][1]['screen_text'],
            source['segments'][2]['screen_text'].split('\n')[0],source['segments'][2]['screen_text'].split('\n')[1],
            source['segments'][3]['screen_text'],source['segments'][4]['screen_text']]
    return [{'text':text,'text_sha':sha(text),'segment_ref':source['segments'][si]['segment_id'],
             'source_field':'screen_text'} for text,si in zip(copies,[0,1,2,2,3,4])]


def template_path(folder,r):
    # A saved build replays its exact executed bytes, even after code advances.
    snapshot=folder/'executed-template.jsx'
    path=snapshot if snapshot.exists() else Path(r['template'])
    if file_sha(path)!=r['template_sha']:raise ValueError('Executed template binding changed')
    return path


def verify_frame_files(checks):
    # Exact byte checks still run on every resume; parallel reads avoid repeatedly
    # serializing tens of GB of compressed native frames after a guarded restart.
    def matches(item):
        path,digest=item
        return file_sha(path)==digest
    with ThreadPoolExecutor(max_workers=8) as pool:
        if not all(pool.map(matches,checks)):raise ValueError('Changed native frame bytes')


def validate_display_cues(cues,source,units):
    if cues.get('source_binding')!=source['semantic_binding_sha']:raise ValueError('Cue source binding changed')
    allowed={u['id']:u['span'] for u in units};refs={s['segment_id']:s for s in source['segments']}
    for cue in cues.get('cues',[]):
        a,b=cue['span'];lo,hi=allowed[cue['unit_id']]
        if not lo<=a<b<=hi or cue['text']!=source['passage'][a:b] or cue['text_sha']!=sha(cue['text']):
            raise ValueError('Highlight must be a literal frozen span')
        if not cue['review_refs'] or not set(cue['review_refs'])<=set(refs):raise ValueError('Existing review references required')
        if not any(e.get('field')=='passage' and e['start']<=a<b<=e['end']
                   for ref in cue['review_refs'] for e in refs[ref].get('evidence',[])):
            raise ValueError('Highlight lacks containing reviewed evidence')
        for start,end in cue['windows']:
            if not 20<=start<end<=source.get('render_duration',87):raise ValueError('Application highlight window required')
    if not cues.get('cues'):raise ValueError('Explicit local display cues required')
    return cues['cues']


def validate_original_question(original, source):
    bound=original['source']; parts=original['question_parts']; stem=source['question']['stem']
    if (bound['semantic_binding_sha']!=source['semantic_binding_sha']
        or bound['question']!=source['question']
        or ''.join(p['text'] for p in parts)!=stem
        or any(stem[p['start']:p['end']]!=p['text'] for p in parts)):
        raise ValueError('Original question and options must match the frozen question')


def validate_director_decisions(source):
    expected=[('A','retain'),('B','eliminate'),('C','eliminate'),('D','eliminate')]
    if source['answer']!='A' or sorted((d['candidate'],d['effect']) for d in source['decisions'])!=expected:
        raise ValueError('Revised option decisions require a new reviewed director plan')


def current(folder):
    r=read(folder/'integration.json');source=project(read(r['bundle']),read(r['status']))
    validate_director_decisions(source)
    locating_render.current(read(r['locating_config']));human=read(r['human_review'])
    if (source!=r['source'] or human['status']!='HUMAN_VISUAL_ACCEPTED'
        or human['movie_sha']!=r['accepted_movie_sha'] or file_sha(r['accepted_movie'])!=r['accepted_movie_sha']
        or r['spec_sha']!=sha({k:v for k,v in r.items() if k!='spec_sha'})
        or validate_timeline(r['segments'])!=r['duration']
        or any(file_sha(r[k])!=r[k+'_sha'] for k in ('locating_project','original_request'))
        or r['screen_projections']!=screen_projections(source)
        or r['method_role']!='interpreter' or r['grammatical_peeling']!='NOT_AUTHORIZED'
        or r['comparison_authority']!='direct_text_review' or r['final_voice_accepted'] is not False
        or r['public_render_ready'] is not False or r['strict_two_method_relay']!='HOLD'):
        raise ValueError('Current upstream, same source, approved picture and preserved native project required')
    template_path(folder,r)
    validate_original_question(read(r['original_request']), source)
    if 'display_cues' in r:
        validate_display_cues(r['display_cues'],source,r['units'])
    words=r['words'];spans=[(w['start'],w['end'],w['text']) for w in words]
    if len(set(w['id'] for w in words))!=len(words):raise ValueError('Unique original identity required')
    for a,b,t in spans:
        if source['passage'][a:b]!=t:raise ValueError('Original word changed')
    for unit in r['units']:
        a,b=unit['span'];selected=[w for w in words if w['id'] in unit['word_ids']]
        if not selected or any(not a<=w['start']<w['end']<=b for w in selected):raise ValueError('Evidence word ownership mismatch')
    return r


def prepare(folder,cue_manifest=None):
    folder=local(folder);folder.mkdir(exist_ok=False,parents=True);root=relay.ROOT
    location=root/'local-data/method-relay-dual-pass/locating-trace-v01';cfg=location/'plan/render-r6.json'
    config=read(cfg);patch=locating_render.current(config)
    original=root/'local-data/method-relay-dual-pass/fulltext-acquisition-r28-4k/request.json';o=read(original)
    source=project(read(config['bundle']),read(config['source_status']))
    units=[{'id':i,'span':[a,b],'word_ids':[w['id'] for w in o['words'] if a<=w['start']<w['end']<=b]}
           for i,a,b in [('condition',686,793),('hard',794,919),('low',920,1043),('coverage',1044,1108),('types',1109,1288),('process',441,684)]]
    font=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',24);states={}
    layouts={'pair':{'condition':(400,650,2800,52),'hard':(400,990,2800,48),'low':(400,1360,2800,48)},
             'process':{'condition':(260,590,1900,44),'hard':(260,845,1900,40),'low':(260,1080,1900,40),'process':(260,1370,1900,38)},
             'scope':{'condition':(260,590,1900,44),'hard':(260,845,1900,38),'low':(260,1060,1900,38),'coverage':(260,1330,1900,42),'types':(260,1510,1900,34)}}
    layouts['memory']={'condition':(500,500,2800,48)}
    layouts['hard']={'condition':(500,500,2800,44),'hard':(500,1110,2800,68)}
    layouts['low']={'condition':(500,400,2800,38),'hard':(500,750,2800,46),'low':(500,1210,2800,68)}
    layouts['pair']={'condition':(500,400,2800,38),'hard':(500,800,2800,58),'low':(500,1260,2800,58)}
    layouts['process']={'condition':(500,400,2800,38),'process':(500,980,2200,58)}
    layouts['scope']={'condition':(500,400,2800,38),'coverage':(500,1000,2200,58),'types':(500,1290,2200,48)}
    for name,layout in layouts.items():
        states[name]={}
        for unit in units:
            if unit['id'] not in layout:continue
            x,y,width,size=layout[unit['id']];left=x;line=y
            for w in o['words']:
                if w['id'] not in unit['word_ids']:continue
                length=float(font.getlength(w['text']))*size/24
                if left+length>x+width and left>x:left=x;line+=size*1.4
                states[name][w['id']]={'screen':[left,line],'scale':100*size/24};left+=length+size*.3
    r={'kind':'real_q33_same_original_objects_dual_pass','version':'0.1.0','duration':94,'source_duration':87,
       'bundle':config['bundle'],'status':config['source_status'],'source':source,'source_binding':source['semantic_binding_sha'],
       'locating_config':str(cfg),'locating_project':config['project'],'patch_sha':patch['patch_sha'],
       'original_request':str(original),'words':o['words'],'units':units,'states':states,'layouts':layouts,
       'human_review':str(location/'comparison/q33-r6/human-review.json'),
       'accepted_movie':str(location/'comparison/q33-r6/GUIDED_B.mp4'),
       'accepted_movie_sha':read(location/'comparison/q33-r6/human-review.json')['movie_sha'],
       'segments':segments(),'template':str(HERE/'integration.jsx'),'project':str(folder/'Q33_COMPLETE_4K.aep'),
       'method_role':'interpreter','strict_two_method_relay':'HOLD','grammatical_peeling':'NOT_AUTHORIZED',
       'comparison_authority':'direct_text_review','hearing_review':'DEFERRED_BY_USER',
       'human_full_film_review':'PENDING','final_voice_accepted':False,'public_render_ready':False}
    r['screen_projections']=screen_projections(source)
    if cue_manifest is not None:
        r['display_cues']=read(local(cue_manifest))
        validate_display_cues(r['display_cues'],source,units)
    elif 'R.display_cues' in Path(r['template']).read_text(encoding='utf-8'):
        raise ValueError('Provide an ignored local --cue-manifest bound to the frozen spans')
    for k in ('locating_project','template','original_request'):r[k+'_sha']=file_sha(r[k])
    r['spec_sha']=sha(r);write(folder/'integration.json',r);return current(folder)


def validate_layer_lifetimes(layers, duration):
    if not layers or any(v.get('in_point') != 0 or v.get('out_point') != duration for v in layers):
        raise ValueError('Added picture layers must cover the application timeline')


def build(folder,recovery_id=None):
    r=current(folder);c=relay.client()
    state=json.loads(c.call('ae_exec',{'code':'JSON.stringify({path:app.project.file?app.project.file.fsName:null,dirty:app.project.dirty,rendering:app.project.renderQueue.rendering}) // '+str(time.time_ns())})['content'])
    if state['dirty'] or state['rendering']:raise ValueError('Preserve current edits')
    write(folder/'session-before.json',state)
    template=template_path(folder,r).read_bytes()
    (folder/'executed-template.jsx').write_bytes(template)
    code='var INTEGRATION_REQUEST='+json.dumps((folder/'integration.json').as_posix())+';\n'+template.decode('utf-8')
    args={'code':code,'undo_group_name':'Continue original frozen words','checkpoint_label':'before-q33-integration','timeout_sec':120}
    tool='ae_exec'
    if recovery_id:tool='ae_execRecover';args.update(recoveryId=recovery_id,retryMode='continue')
    result=mutation_call(c,tool,args,folder,150)
    write(folder/'build-result.json',result);n=json.loads(result['content'])
    validate_layer_lifetimes(n['new_layer_window_checks'], r['source_duration'])
    if (n['canvas']!=[3840,2160,24,r['duration']] or n['before_words']!=n['after_words'] or n['old_samples']!=n['protected_samples']
        or any(v['fast_opacity']!=0 or v['guided_opacity']!=0 for v in n['new_layer_window_checks'])
        or n['renderers']!={'source':'ADBE Advanced 3d','outer':'ADBE Calder'}):raise ValueError('Native identity or approved window changed')
    write(folder/'native-identity.json',n)
    check=c.call('ae_validateExpressions',{'comp_id':str(n['source_comp_id']),'sample_times':[3.5,13.25,19.5,21,25,29,34,45,57,69,79,95],'max_results':2000},timeout=90)
    write(folder/'expressions.json',check)
    if not check.get('valid') or check.get('errors') or check.get('truncated'):raise ValueError('Expression audit failed')
    return n


def render_mapping(start,n,batch_size=4):
    if isinstance(batch_size,bool) or not isinstance(batch_size,int) or not 1<=batch_size<=32:
        raise ValueError('Bounded native batch required')
    segment=next(s for s in segments() if s['start']*24<=start<s['end']*24)
    count=min(batch_size,round(segment['end']*24)-start)
    if segment['id']=='ORIGINAL_QUESTION':
        if start!=0:raise ValueError('Resume only the complete original-question hold')
        return {'comp':n['source_comp_id'],'source_start':0,'native_count':1,'logical_count':192,'segment':segment['id']}
    if segment['id']=='REPLAY_ENTRY':
        return {'comp':n['comp_id'],'source_start':start/24,'native_count':count,'logical_count':count,'segment':segment['id']}
    return {'comp':n['source_comp_id'],'source_start':segment['source_start']+start/24-segment['start'],
            'native_count':count,'logical_count':count,'segment':segment['id']}


def inherited_guided(r,m):
    if m['segment']!='GUIDED_LOCATE':raise ValueError('Only accepted Guided locating may be inherited')
    source=Path(r['locating_config']).parents[1]/'delivery/q33-r6'
    receipt=read(source/'render-receipt.json');manifest=read(source/'native-frame-shas.json')
    if (receipt['patch_sha']!=r['patch_sha'] or receipt['frames']!=[192,480]
        or receipt['native_canvas']!=[3840,2160,24]
        or receipt['frame_manifest_sha']!=sha(manifest)
        or receipt['movie']['sha256']!=r['accepted_movie_sha']
        or file_sha(receipt['movie']['path'])!=r['accepted_movie_sha']
        or sorted(manifest)!=['FRAME_'+str(i).zfill(5)+'.tif' for i in range(192,480)]):
        raise ValueError('Accepted native lineage changed')
    first=round(m['source_start']*24);paths=[];checks=[]
    for index in range(first,first+m['native_count']):
        path=source/'native-frames'/('FRAME_'+str(index).zfill(5)+'.tif')
        checks.append((path,manifest[path.name]))
        paths.append(path)
    verify_frame_files(checks)
    proof={'receipt':str(source/'render-receipt.json'),'receipt_sha':file_sha(source/'render-receipt.json'),
           'manifest_sha':receipt['frame_manifest_sha'],'source_frames':[first,first+len(paths)],
           'accepted_movie_sha':r['accepted_movie_sha']}
    return paths,proof


def render(folder,pid,hwnd,batch_size=4,inherit_accepted=False):
    r=current(folder);n=read(folder/'native-identity.json');c=relay.client();frames=folder/'native-frames';frames.mkdir(exist_ok=True)
    total=round(r['duration']*24);chunks=[];existing=sorted(frames.glob('*.tif'))
    if [p.name for p in existing]!=['FRAME_'+str(i).zfill(5)+'.tif' for i in range(len(existing))]:raise ValueError('Inspect incomplete frame transfer before resume')
    cursor=0;checks=[]
    while cursor<len(existing):
        receipt=read(folder/('transfer-'+str(cursor)+'.json'))
        mapping=render_mapping(cursor,n,receipt['mapping']['native_count'])
        if receipt['spec_sha']!=r['spec_sha'] or receipt['mapping']!=mapping:raise ValueError('Resume binding mismatch')
        for name,digest in receipt['frames'].items():
            checks.append((frames/name,digest))
        if receipt.get('inherited_source'):
            _,proof=inherited_guided(r,mapping)
            if proof!=receipt['inherited_source']:raise ValueError('Inherited frame lineage changed')
        cursor+=mapping['logical_count'];chunks.append(receipt)
    if cursor!=len(existing):raise ValueError('Incomplete native transfer')
    verify_frame_files(checks)
    while cursor<total:
        current(folder)
        if available_memory()<2**30:raise RuntimeError('Below user reserve')
        m=render_mapping(cursor,n,batch_size);part=folder/('chunk-'+str(cursor)+'-'+str(time.time_ns()))
        inherit=inherit_accepted and m['segment']=='GUIDED_LOCATE';proof=None
        if not inherit:part.mkdir()
        code="""(function(){if(app.project.renderQueue.rendering)throw Error('Busy');var cp=AEMCP.compById(COMP),meta=JSON.parse(cp.comment);if((meta.integration_spec_sha||meta.spec_sha)!==SPEC)throw Error('Wrong composition');for(var i=1;i<=app.project.renderQueue.numItems;i++){var old=app.project.renderQueue.item(i);if(old.render&&old.status===RQItemStatus.QUEUED)throw Error('Other queued render');}app.purge(PurgeTarget.ALL_CACHES);var q=app.project.renderQueue.items.add(cp),o=q.outputModule(1),preset=null;for(var j=0;j<o.templates.length;j++)if(o.templates[j].indexOf('TIFF')!==-1){preset=o.templates[j];break;}if(!preset)throw Error('TIFF unavailable');o.applyTemplate(preset);o.file=new File(DEST);q.timeSpanStart=START;q.timeSpanDuration=COUNT/24;app.setMultiFrameRenderingConfig(false,100);app.project.renderQueue.render();app.project.save();return JSON.stringify({done:q.status===RQItemStatus.DONE,start:START,count:COUNT,comp_id:cp.id});})();"""
        for k,v in {'COMP':str(m['comp']),'SPEC':json.dumps(r['spec_sha']),'DEST':json.dumps((part/'FRAME_[#####].tif').as_posix()),'START':str(m['source_start']),'COUNT':str(m['native_count'])}.items():code=code.replace(k,v)
        attempt=str(cursor)+'-'+str(time.time_ns())
        if inherit:
            paths,proof=inherited_guided(r,m)
            chunk={'done':True,'count':len(paths),'origin':'accepted_native_guided','start':m['source_start'],'comp_id':m['comp']}
        else:
            with monitor_existing_render(pid,hwnd) as memory:result=mutation_call(c,'ae_exec',{'code':code,'checkpoint_label':'before-integrated-batch-'+str(cursor),'timeout_sec':600},folder,630)
            write(folder/('memory-'+attempt+'.json'),memory);write(folder/('render-'+attempt+'.json'),result)
            if memory.get('abort_requested') or memory.get('monitor_error'):raise RuntimeError('Inspect render memory stop')
            chunk=json.loads(result['content']);paths=sorted(part.glob('*.tif'))
        if not chunk['done'] or len(paths)!=m['native_count']:raise ValueError('Incomplete native batch')
        transferred={}
        for index in range(m['logical_count']):
            target=frames/('FRAME_'+str(cursor+index).zfill(5)+'.tif')
            if target.exists():raise FileExistsError('Never overwrite a frame')
            source=paths[0 if m['native_count']==1 else index]
            if m['native_count']==1 or inherit:shutil.copyfile(source,target)
            else:shutil.move(str(source),str(target))
            transferred[target.name]=file_sha(target)
        # Keep the native source of an explicit hold and its attempt receipt.
        if m['native_count']!=1 and not inherit:part.rmdir()
        receipt={'spec_sha':r['spec_sha'],'mapping':m,'native':chunk,'frames':transferred,
                 'hold_reason':'constant_source_time_0_original_question' if m['native_count']==1 else None,
                 'native_attempt':None if inherit else str(folder/('render-'+attempt+'.json')),
                 'inherited_source':proof}
        write(folder/('transfer-'+str(cursor)+'.json'),receipt);chunks.append(receipt);cursor+=m['logical_count']
        write(folder/'render-progress.json',{'frames':cursor,'total':total});print(json.dumps({'native_or_explicit_hold_completed':cursor,'total':total}),flush=True)
    current(folder);manifest={name:digest for receipt in chunks for name,digest in receipt['frames'].items()};write(folder/'native-frame-shas.json',manifest)
    c.call('ae_exec',{'code':"app.purge(PurgeTarget.ALL_CACHES);JSON.stringify({purged:true}); // "+str(time.time_ns())})
    movie=acquisition_ab.encode_frames(frames,0,total,folder/'Q33_COMPLETE_4K_PICTURE.mp4',3840,2160)
    receipt={'spec_sha':r['spec_sha'],'movie':movie,'project':r['project'],'project_sha':file_sha(r['project']),
             'frame_manifest_sha':sha(manifest),'chunks':len(chunks),'native_frames':sum(x['mapping']['native_count'] for x in chunks),
             'explicit_hold_frames':sum(x['mapping']['logical_count']-x['mapping']['native_count'] for x in chunks),
             'inherited_native_frames':sum(x['mapping']['native_count'] for x in chunks if x.get('inherited_source')),
             'new_native_frames':sum(x['mapping']['native_count'] for x in chunks if not x.get('inherited_source')),
             'render_route':'direct_original_source_except_replay_entry','human_full_film_review':'PENDING','strict_two_method_relay':'HOLD','public_render_ready':False}
    write(folder/'render-receipt.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('prepare','build','render'));p.add_argument('folder');p.add_argument('--pid',type=int);p.add_argument('--hwnd',type=int);p.add_argument('--recovery-id');p.add_argument('--cue-manifest');p.add_argument('--batch-size',type=int,default=4);p.add_argument('--inherit-accepted-guided',action='store_true');a=p.parse_args()
    folder=local(a.folder);result=render(folder,a.pid,a.hwnd,a.batch_size,a.inherit_accepted_guided) if a.operation=='render' else build(folder,a.recovery_id) if a.operation=='build' else prepare(folder,a.cue_manifest)
    print(json.dumps({'operation':a.operation,'folder':str(folder)},ensure_ascii=False))
