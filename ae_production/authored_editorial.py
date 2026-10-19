"""Bind host-authored editorial decisions to the one existing AV timeline.

This is a bounded adapter for the current authored film. Legacy 0.4 generators
keep their own readiness and execution limits. No teaching facts are inferred.
"""
from copy import deepcopy
from pathlib import Path

from video_contracts import read,sha,pointer
from scripts.voice_delivery import sha256
from pedagogy import compile_plan,copy_projection,motion_projection
from student_pov import realize
from content_os.course_mapping import action_visual_intent
from method_choreography.registry import registry


def validate_editorial(author,bundles):
    e=author['editorial']
    if set(e)!={'schema','manifest','sha256'} or e['schema']!='authored-editorial/v1':
        raise ValueError('Explicit authored editorial contract required')
    if sha256(e['manifest'])!=e['sha256']:
        raise ValueError('Agent editorial input changed; author a new revision')
    m=read(e['manifest'])
    if m['authority']!='internal_ai_editorial_only' or m['human_approved'] is not False:
        raise ValueError('Internal author cannot certify human approval')
    for path,digest in m['source_files'].items():
        if sha256(path)!=digest:raise ValueError('Editorial source changed: '+path)
    by_id={s['id']:s for s in author['scenes']}
    if set(m['scenes'])!=set(by_id):raise ValueError('Every actual scene needs a viewing decision')
    for sid,d in m['scenes'].items():
        s=by_id[sid]
        if not d['viewer_task'].strip() or not d['withheld_information'].strip():
            raise ValueError('A viewing task and explicit disclosure choice are required')
        if d['consumed_decisions']!={k:deepcopy(s[k]) for k in d['consumed_decisions']}:
            raise ValueError('An editorial decision was ignored: '+sid)
        if ('comparison_background_policy' in s
                and d['consumed_decisions'].get('comparison_background_policy')!=s['comparison_background_policy']):
            raise ValueError('Comparison background policy needs its actual editorial decision: '+sid)
        if d['source_refs']!=s['source_refs']:raise ValueError('Viewer objects lost their source: '+sid)
    expected=list(dict.fromkeys(s['world'] for s in author['scenes']))
    if m['world_order']!=expected:raise ValueError('Selection/order was not consumed')
    if m['method_naming']!='point_of_use':raise ValueError('Keep the current point-of-use method naming')
    if m['contract_version'] not in ('0.3.0','0.4.0'):raise ValueError('Explicit Pedagogy contract required')
    if set(m['teaching_selection'])!=set(bundles):raise ValueError('Pedagogy must cover every selected question')
    from ae_production.authored_episode import validate_replay_policy
    validate_replay_policy(author)
    replays=[s['id'] for s in author['scenes'] if s['kind']=='replay']
    expected_replay=replays[0] if replays else None
    if 'replay_scene' not in m or m['replay_scene']!=expected_replay:
        raise ValueError('The actual local replay or explicit user omission was not consumed')
    if 'audience_hook' in author:
        if m.get('audience_hook')!={'decision_sha':sha(author['audience_hook']),
                'consumer':'Audience Engagement -> compile_clock -> authored_native',
                'creative_authority':'explicit_user_instruction_only'}:
            raise ValueError('Audience opening decision needs its exact director handoff')
    return m


def compile_editorial(author,clock,bundles):
    """Recompute valid projections and prove their downstream author decisions.

    A held Student POV result is consumed as a limitation, never upgraded to a
    READY 0.4 experience or a claim of reduced student work.
    """
    m=validate_editorial(author,bundles);pedagogy={};mapping={}
    for world,b in bundles.items():
        status=read(author['sources'][world]['status'])
        p=compile_plan(b,status,m['teaching_selection'][world],mode='worked_example',
                       contract_version=m['contract_version'],duration_target=480,generated_at='authored-v1')
        if p['availability']['status']!='READY':raise ValueError('Current Pedagogy cannot authorize author input')
        cp=copy_projection(p,b,status);mp=motion_projection(p,b,status)
        pov=realize(cp,p,b,status,contract_version=m['contract_version'],
                    **({'motion_projection':mp} if m['contract_version']=='0.4.0' else {}))
        pedagogy[world]={'plan_sha':p['plan_sha'],'copy_projection_sha':sha(cp),
            'motion_projection_sha':sha(mp),'student_pov_status':pov['availability'],
            'student_pov_consumer':'author-disclosure-and-no-unsupported-work-reduction',
            'consumed_scene_ids':[s['id'] for s in author['scenes'] if s['world']==world],
            'source_role':p['role'],'independent_human_certified':False}
        mapping[world]=[{ 'execution_id':x['execution_id'],'intent':action_visual_intent(b,x)}
                        for x in b['analysis']['execution_trace'] if x['state']=='produced']
        for sid,d in m['scenes'].items():
            if d['world']==world and d['pedagogy_plan_sha']!=p['plan_sha']:
                raise ValueError('Author did not use the current Pedagogy selection: '+sid)
    _,recipes,identity=registry()
    rows=[];states={w:{} for w in bundles}
    for s in clock['scenes']:
        d=m['scenes'][s['id']];w=s['world'];options=bundles[w]['source_snapshot']['options']
        before={c:states[w].get(c,'unchecked') for c in options}
        reading=[{'source_object':f'{w}:{x["start"]}:{x["end"]}',
                  'source_span':[x['start'],x['end']],'range':[x['arrival'],x['end_time']],
                  'mode':x['mode']} for x in s.get('reading_events',[])]
        if s.get('event')=='final' and set(states[w])!=set(options):
            raise ValueError('Viewer final answer must retain the full actual candidate prefix')
        if s.get('event') in ('eliminate','supported'):states[w][s['candidate']]=s['event']
        rows.append({'scene':s['id'],'world':w,'viewer_task':d['viewer_task'],
            'withheld_information':d['withheld_information'],'source_refs':s['source_refs'],
            'candidate_states_before':before,'candidate_states_after':deepcopy(states[w]),
            'observation_range':[s['start'],s['settled']], 'reading_windows':reading,
            'decision':{'range':[s['event_time'],s.get('decision_end',s['event_time'])],
                        'candidate':s['candidate'],'kind':s['event']} if s.get('event') else None,
            'confirmation_range':[s['return_start'],s['end']],
            'choreography':s['choreography'],'attention':s.get('attention_events',[]),
            'candidate_reading_policy':s.get('candidate_reading_policy','visible')})
        # Opt in through the actual author decision. Historical manifests keep
        # their exact output so a new consumer cannot invalidate saved films.
        for key in ('screen_title','comparison_background_policy','extraction_policy'):
            if key in d['consumed_decisions']:
                rows[-1][key]=deepcopy(s[key])
    transitions=[]
    for prev,nxt in zip(m['world_order'],m['world_order'][1:]):
        t=next(t for t in m['transitions'] if t['from']==prev and t['to']==nxt)
        if not all(t[k].strip() for k in ('earned_payoff','new_obstacle','new_information')):
            raise ValueError('Adjacent questions require a real payoff/obstacle/information change')
        if not any(s['world']==prev and s.get('event')=='final' for s in clock['scenes']):
            raise ValueError('Transition before the preceding question closes')
        transitions.append(deepcopy(t))
    result = {'schema':'authored-editorial-consumption/v1','manifest_sha256':author['editorial']['sha256'],
        'pedagogy':pedagogy,'method_mapping':mapping,'motion_identity':identity,
        'choreography_adapter':'source-bound-authored-parameters/v1',
        'legacy_v04_runtime':'NOT_INVOKED_R03_UNIMPLEMENTED','execution_allowed':False,
        'execution_consumer':'authored_native.Host; one author and clock',
        'rows':rows,'transitions':transitions,'research_choices':m['research_choices'],
        'actual_media_mapping':'PENDING_FINAL_EXPORT','public_render_ready':False}
    if 'audience_hook' in author:
        from creative_os.audience_engagement import validate_authored_hook
        result['audience_hook']={**validate_authored_hook(author,bundles),
            'actual_consumer':'authored_native shared template',
            'clock':deepcopy(clock['audience_hook'])}
    return result
