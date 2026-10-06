"""Explicit reviewed-passage transport. No solver, Registry or teaching imports.

Direct text judgments are upstream host assertions, never method achievements.
This additive contract does not relabel an incomplete QuestionAnalysis as closed.
"""
from copy import deepcopy
import re
from . import sha, seal, verify_seal, declared_review_level,ROOT,_validator

VERSION = '1.0.0'


def material(packet):
    return {k:packet[k] for k in ('lesson_id','passage','questions','methods')}


def validate_review(packet):
    schema=ROOT/'schemas/reviewed-passage-export.json'
    from jsonschema import ValidationError
    try: _validator(str(schema),schema.stat().st_mtime_ns).validate(packet)
    except ValidationError as error: raise ValueError('Invalid reviewed-passage schema: '+error.message) from error
    review = packet['review']
    if (review['material_sha'] != sha(material(packet)) or review['status'] != 'reviewed'
            or review['evaluation_phase'] != 'post_reveal'
            or declared_review_level(review) == 'unreviewed'):
        raise ValueError('Explicit bound reviewed credential required')
    qs = packet['questions']; ids = [q['question_id'] for q in qs]
    if not qs or len(set(ids)) != len(ids) or len({q['number'] for q in qs}) != len(qs):
        raise ValueError('Unique complete question set required')
    if any(not q['stem'] or len(q['options']) < 2 or any(not v for v in q['options'].values()) for q in qs):
        raise ValueError('Question material incomplete')
    questions = {q['question_id']:q for q in qs}
    methods = {m['method_id']:m for m in packet['methods']}
    if len(methods) != len(packet['methods']): raise ValueError('Duplicate frozen method')
    def evidence(qid, spans):
        if not spans or not any(s['field']=='passage' for s in spans):
            raise ValueError('Own passage evidence required')
        for s in spans:
            field=s['field']; q=questions[qid]
            text=packet['passage'] if field=='passage' else q['stem'] if field=='stem' else q['options'].get(field.removeprefix('options.'),'') if field.startswith('options.') else ''
            if not 0 <= s['start'] < s['end'] <= len(text) or text[s['start']:s['end']] != s['quote']:
                raise ValueError('Evidence span mismatch')
    decisions = review['decisions']; keys=[(d['question_id'],d['candidate']) for d in decisions]
    expected={(q['question_id'],k) for q in qs for k in q['options']}
    if set(keys)!=expected or len(keys)!=len(set(keys)):
        raise ValueError('Every candidate needs its own reviewed comparison')
    for d in decisions:
        if d['basis']!='direct_text_review' or d.get('method_id') is not None:
            raise ValueError('Direct judgment cannot claim method credit')
        if not d['rationale'] or d['effect'] not in ('retain','eliminate'):
            raise ValueError('Incomplete candidate judgment')
        evidence(d['question_id'], d['evidence'])
    for qid in ids:
        if sum(d['effect']=='retain' for d in decisions if d['question_id']==qid)!=1:
            raise ValueError('Unique supported candidate required')
    actions=review['method_actions']; action_ids=[a['action_id'] for a in actions]
    if len(action_ids)!=len(set(action_ids)): raise ValueError('Duplicate action')
    for a in actions:
        m=methods[a['method_id']]
        if a['method_version']!=m['version'] or a['role']!=m['primary_role']:
            raise ValueError('Method role/version drift')
        if a['role'] not in ('locator','interpreter','framework') or a.get('answer') is not None:
            raise ValueError('This lesson lane only attributes auxiliary method actions')
        if not a['output'] or not a['stop_rule']: raise ValueError('Actual output and Stop required')
        evidence(a['question_id'],a['evidence'])
    segments=review['segments']; segment_ids=[s['segment_id'] for s in segments]
    if len(segment_ids)!=len(set(segment_ids)) or not segments:
        raise ValueError('Unique complete narration required')
    by_action={a['action_id']:a for a in actions}
    covered=set()
    for s in segments:
        qid=s['question_id']; evidence(qid,s['evidence'])
        if not s['text'] or not s['screen_text'] or not s['fidelity_reviewed']:
            raise ValueError('Unreviewed narration')
        for index in s['decision_refs']:
            if type(index) is not int or not 0<=index<len(decisions) or decisions[index]['question_id']!=qid:
                raise ValueError('Cross-question or dangling decision reference')
            covered.add(index)
        if any(by_action[aid]['question_id']!=qid for aid in s['action_refs']):
            raise ValueError('Cross-question action reference')
        if s['kind'] not in ('action','evidence','comparison','closure','boundary'):
            raise ValueError('Unknown segment function')
        if s.get('summary_refs'):
            retained={i for i,d in enumerate(decisions) if d['effect']=='retain'}
            if s is not segments[-1] or set(s['summary_refs'])!=retained or len(s['summary_refs'])!=len(retained):
                raise ValueError('Final summary must bind every own retained decision')
            expected_summary=''.join(str(q['number'])+next(d['candidate'] for d in decisions
                if d['question_id']==q['question_id'] and d['effect']=='retain')
                for q in sorted(qs,key=lambda q:q['number']))
            if expected_summary not in re.sub(r'\s','',s['screen_text']):
                raise ValueError('Visible answer summary differs from upstream judgments')
    if covered != set(range(len(decisions))): raise ValueError('Narration omits candidate comparisons')
    if set(review['order'])!=set(ids) or len(review['order'])!=len(ids) or not review['order_rationale']:
        raise ValueError('Reviewed whole-passage order required')
    groups=[]
    for s in segments:
        if not groups or groups[-1]!=s['question_id']: groups.append(s['question_id'])
    if groups!=review['order']: raise ValueError('Narration differs from reviewed question order')
    for qid in ids:
        own=[s for s in segments if s['question_id']==qid]
        if not any(s['kind']=='closure' for s in own) or not any(s['kind']=='boundary' for s in own):
            raise ValueError('Every question needs closure and boundary')
    CODE_PATTERN = re.compile(r'(?<![A-Za-z0-9])[RFG]\d{2}(?![A-Za-z0-9])', re.IGNORECASE)
    if any(CODE_PATTERN.search(s[k]) for s in segments for k in ('text','screen_text')):
        raise ValueError('Internal method code on consumer surface')


def export_bundle(packet, generated_at):
    validate_review(packet)
    payload=deepcopy({k:packet[k] for k in ('lesson_id','passage','questions','methods','review','source')})
    binding=sha(payload)
    return seal({'schema_version':VERSION,'kind':'frozen_reviewed_passage',
        'asset_id':'passage:'+binding,'semantic_binding_sha':binding,'payload':payload,
        'semantic_review':{'level':declared_review_level(packet['review']),
            'independent_human_certified':False,'status':'usable_for_engineering_pilot'},
        'generated_at':generated_at,'public_render_ready':False})


def status_manifest(bundle, generated_at, effective_status='ACTIVE'):
    verify_bundle(bundle)
    if effective_status not in ('ACTIVE','WITHDRAWN','SUPERSEDED','STALE','BLOCKED'):
        raise ValueError('Unknown upstream state')
    return seal({'kind':'reviewed_passage_status','asset_id':bundle['asset_id'],
        'semantic_binding_sha':bundle['semantic_binding_sha'],'source_sha':sha(bundle['payload']['source']),
        'effective_status':effective_status,'generated_at':generated_at})


def verify_bundle(bundle):
    verify_seal(bundle)
    if bundle['schema_version']!=VERSION or bundle['kind']!='frozen_reviewed_passage':
        raise ValueError('Wrong lesson transport version')
    validate_review(bundle['payload'])
    if (sha(bundle['payload'])!=bundle['semantic_binding_sha'] or
        bundle['asset_id']!='passage:'+bundle['semantic_binding_sha'] or
        bundle['semantic_review']!={'level':declared_review_level(bundle['payload']['review']),
            'independent_human_certified':False,'status':'usable_for_engineering_pilot'} or
        bundle['public_render_ready'] is not False):
        raise ValueError('Lesson binding or review level drift')


def require_current(bundle, status):
    verify_bundle(bundle)
    if status is None: raise ValueError('Current upstream status source required')
    verify_seal(status)
    if (status['kind']!='reviewed_passage_status' or status['asset_id']!=bundle['asset_id']
            or status['semantic_binding_sha']!=bundle['semantic_binding_sha']
            or status['source_sha']!=sha(bundle['payload']['source'])
            or status['effective_status']!='ACTIVE'):
        raise ValueError('Upstream lesson or source is invalid')
    if bundle['payload']['source']['usage_status'] not in ('internal_only','permitted'):
        raise ValueError('Source does not allow internal production')
