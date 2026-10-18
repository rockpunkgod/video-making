"""Make a new editorial revision from the two already frozen showcase questions.

This is an explicit, asset-specific editing decision, not automatic solving or
automatic student-difficulty inference. Original author, media and takes stay put.
"""
import argparse
from copy import deepcopy
from pathlib import Path

from ae_production.authored_episode import AUTHOR, checked_author, delivery_path
from creative_os.teaching_focus import VERSION, validate_focus
from video_contracts import read, write, sha
from scripts.voice_delivery import sha256


def author_revision(source, destination):
    a,bundles=checked_author(source)
    if set(bundles)!={'fitbit','camp'} or 'creative writing camp' not in bundles['camp']['source_snapshot']['stem']:
        raise ValueError('This editorial demonstration is bound to the existing Fitbit/camp assets')
    if destination.exists():raise FileExistsError('Preserve the prior editorial revision')
    before=deepcopy(a);by_id={s['id']:s for s in a['scenes']}
    expected={'SC03':('fitbit','A'),'SC04':('fitbit','B'),'SC05':('fitbit','C'),
              'SC06':('fitbit','D'),'SC10':('camp','A'),'SC11':('camp','D'),
              'SC12':('camp','B'),'SC13':('camp','C')}
    for sid,pair in expected.items():
        s=by_id[sid]
        if (s['world'],s.get('candidate'))!=pair:raise ValueError('Source scene identity changed')
    focus={'version':VERSION,'questions':{}}
    def unit(ident,world,candidates,scene_ids,challenge,change,ratings):
        refs=[]
        for sid in scene_ids:
            for r in by_id[sid]['source_refs']:
                if r['world']==world and r['pointer']=='/passage' and r not in refs:refs.append(deepcopy(r))
        return {'id':ident,'candidates':candidates,'difficulty_basis':'EDITORIAL_HYPOTHESIS',
                'challenge':challenge,'judgement_change':change,
                'method_action_ref':deepcopy(by_id[scene_ids[0]]['action_refs'][0]),
                'decisive_source_refs':refs,'ratings':dict(zip(('difficulty','method_value','visual_payoff'),ratings))}
    focus['questions']['fitbit']={'units':[unit('same-price-relation','fitbit',['A'],['SC03'],
        'those options 的比较对象要接回前文；more affordable 与 cheaper 是否仍在比较同一对象的价格？',
        '接回 Whoop/Oura，再把 cheaper 与 more affordable 对齐，支持 A；不把方法解释当整题终审。',(3,3,3))]}
    focus['questions']['camp']={'units':[
        unit('activity-versus-role','camp',['A','D'],['SC10','SC11'],
             'workshops 同词命中不保证动作一致；literary forms 没有逐字照抄却可能概括原文。',
             '参加不能换成主持，A 排除；小说、诗歌等与多种文学形式对应，D 留下。',(3,3,3)),
        unit('whose-work-which-action','camp',['B'],['SC12'],
             '介绍出版、展示作品与编往届文集，是否支持当前学生发表自己的旧作？',
             '保留作品归属和编辑动作，B 的完整主张无支持；这一项不能因节奏要求直接略过。',(2,2,2))]}
    treatments={'fitbit':{'A':('focus','价格比较的指代与等值概括是本题方法回报'),
                         'B':('quick','without app 与 all data processed in app 直接相冲突'),
                         'C':('quick','free 与 additional monthly fee 直接相冲突'),
                         'D':('brief','保留完整范围核验，一句指出原文没有数据量比较')},
                'camp':{'A':('focus','同词下的动作角色差异'),
                        'B':('focus','作品归属及动作需跨段核验，不冒充显然错误'),
                        'C':('brief','嘉宾分享与往届文集均不支持采访；保留两处原文阅读'),
                        'D':('focus','具体体裁到上位概括，与 A 的同词错配形成对照')}}
    for world,options in treatments.items():
        checks=bundles[world]['analysis']['question_verification']['review']['candidate_checks']
        focus['questions'][world]['options']={}
        for candidate,(treatment,rationale) in options.items():
            index=next(i for i,c in enumerate(checks) if c['candidate']==candidate)
            focus['questions'][world]['options'][candidate]={'treatment':treatment,'rationale':rationale,
                'verification_ref':{'pointer':f'/question_verification/review/candidate_checks/{index}','sha':sha(checks[index])}}
    a['teaching_focus']=focus;a['revision']=destination.name
    a['copy_review']='PENDING independent user review of the entire reordered copy'
    a['voice_inputs']=[str(delivery_path(source,before))];a['voice_delivery']='voice/delivery.json'
    order=['SC01','SC02','SC05','SC04','SC06','SC03','SC07','SC08','SC09','SC09L','SC13','SC12','SC10','SC11','SC14','SC15']
    if set(order)!=set(by_id):raise ValueError('Unexpected source scenes; explicit new editing needed')
    removed={'SC04_1a','SC05_1a','SC06_1a','SC12_1a','SC13_1a'}
    a['voices']=[v for v in a['voices'] if v['id'] not in removed]
    voices={v['id']:v['text'] for v in a['voices']}
    for s in a['scenes']:
        s['voice_ids']=[v for v in s['voice_ids'] if v not in removed]
        s['voice_placements']={k:v for k,v in s.get('voice_placements',{}).items() if k not in removed}
        copy=''.join(voices[v] for v in s['voice_ids'])
        s['attention']=[x for x in s.get('attention',[]) if x['anchor'] in copy]
        if s.get('event') in ('eliminate','supported'):
            treatment=focus['questions'][s['world']]['options'][s['candidate']]['treatment']
            s['audience_intent']=focus['questions'][s['world']]['options'][s['candidate']]['rationale']
            if treatment!='focus':
                s['voice_placements']={v:'comparison' for v in s['voice_ids']}
    a['scenes']=[by_id[sid] for sid in order]
    # Actual AE composed-line inspection found 24 phrase chunks in this source
    # overview. The inherited 2.2 s cannot show their sequential handoffs.
    by_id['SC02']['reading_path'][4]['read_seconds']=max(8.,by_id['SC02']['reading_path'][4]['read_seconds'])
    validate_focus(a,bundles)
    destination.mkdir(parents=True);write(destination/AUTHOR,a)
    write(destination/'FOCUS_SOURCE_BINDING.json',{'source_revision':str(source),'before_author_sha':sha(before),
        'frozen_bundle_sha':{w:sha(b) for w,b in bundles.items()},'removed_redundant_prompt_takes':sorted(removed),
        'new_teaching_facts':False,'student_measurement':False,'human_review':'PENDING'})
    return a


def compare_revisions(source, destination):
    a,_=checked_author(destination);old,_=checked_author(source)
    before=read(source/'AV_PLAN.json');after=read(destination/'AV_PLAN.json')
    events=lambda p:sorted([(e['world'],e['candidate'],e['kind'],e['refs']) for e in p['candidate_events']],key=lambda e:e[:3])
    if events(before)!=events(after):raise ValueError('Final answer or candidate authority changed')
    for k in ('sources','input_files','excerpts'):
        if old[k]!=a[k]:raise ValueError('Frozen inputs changed')
    oldscenes={s['id']:s for s in old['scenes']}
    for s in a['scenes']:
        for k in ('source_refs','action_refs','terminal_refs'):
            if s.get(k)!=oldscenes[s['id']].get(k):raise ValueError('Evidence or reading path changed')
        previous=oldscenes[s['id']].get('reading_path',[]);current=s.get('reading_path',[])
        if len(previous)!=len(current):raise ValueError('Reading evidence omitted')
        for x,y in zip(previous,current):
            if y['read_seconds']<x['read_seconds']:
                raise ValueError('Reading was accelerated')
            if {k:v for k,v in x.items() if k!='read_seconds'}!={k:v for k,v in y.items() if k!='read_seconds'}:
                raise ValueError('Original reading span or path changed')
    oldvoices={s['id']:s for s in before['segments']}
    for s in after['segments']:
        if s['voice']['audio_sha256']!=oldvoices[s['id']]['voice']['audio_sha256'] or s['text']!=oldvoices[s['id']]['text']:
            raise ValueError('Voice reuse claim is not byte-identical')
    report={'before_plan':str(source/'AV_PLAN.json'),'before_sha256':sha256(source/'AV_PLAN.json'),
        'after_plan':str(destination/'AV_PLAN.json'),'after_sha256':sha256(destination/'AV_PLAN.json'),
        'before_seconds':before['duration'],'after_seconds':after['duration'],
        'removed_seconds':before['duration']-after['duration'],'before_takes':len(before['segments']),
        'after_takes':len(after['segments']),'all_8_option_checks_identical':True,
        'all_reading_spans_and_routes_identical':True,'reading_never_accelerated':True,'all_remaining_takes_byte_identical':True,
        'all_frozen_sources_identical':True,'new_native_render':'PENDING','human_review':'PENDING','questions':[]}
    for world in a['sources']:
        rows=[]
        for s in after['scenes']:
            if s['world']!=world or s['kind'] not in ('compare','replay'):continue
            prev=next(x for x in before['scenes'] if x['id']==s['id'])
            if s['choreography']['source_read_seconds']!=prev['choreography']['source_read_seconds']:
                raise ValueError('Source reading hold was shortened')
            rows.append({'scene':s['id'],'candidate':s['candidate'],'treatment':s['teaching_treatment'],
                         'before_seconds':prev['end']-prev['start'],'after_seconds':s['end']-s['start']})
        shares={k:sum(r[k] for r in rows if r['treatment']=='focus')/sum(r[k] for r in rows)
                for k in ('before_seconds','after_seconds')}
        report['questions'].append({'world':world,'rows':rows,'critical_share_before':shares['before_seconds'],
                                    'critical_share_after':shares['after_seconds']})
    report['source_read_holds_identical']=True
    write(destination/'BEFORE_AFTER.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--compare-only',action='store_true')
    args=p.parse_args()
    (compare_revisions if args.compare_only else author_revision)(args.source.resolve(),args.destination.resolve())
