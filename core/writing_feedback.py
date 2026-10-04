"""Bind external writing reviews to current material and frozen course contracts.

This validates delivery completeness and references, never English semantics,
rubric judgement, reviewer identity, or the preservation of meaning in a rewrite.
"""
from copy import deepcopy
import hashlib
import json
from .evidence import check_span
from .image_evidence import image_manifest, check_image_region

ORDERS={
    '应用文':['overall','diagnostics','corrections','outline','revised_text','practice','materials'],
    '读后续写':['overall','diagnostics','anchors','emotion','corrections','outline','revised_text','practice'],
}

def check_handwriting(review, kind, registry, manifest, score, allow_withheld=False):
    visual=review.get('handwriting_review')
    if visual is None:
        if score and score['handwriting_applied']:
            raise ValueError('Handwriting judgement needs independently reviewed original-image evidence')
        return
    if review['schema_version']!='1.1.0':
        raise ValueError('Original-image review requires writing-review 1.1.0')
    if review['kind']!='correction':
        raise ValueError('Writing guidance cannot judge student handwriting')
    sid=visual['source_section_id']
    expected='15 分评分规范' if kind=='应用文' else '25 分评分规范'
    if sid not in review['source_section_ids'] or registry.sources['sections'][sid]['heading']!=expected:
        raise ValueError('Handwriting review requires its own module rubric')
    for region in visual['regions']: check_image_region(region,manifest)
    if len({json.dumps(r,sort_keys=True) for r in visual['regions']})!=len(visual['regions']):
        raise ValueError('Duplicate handwriting evidence region')
    applied=bool(score and score['handwriting_applied'])
    adjustment=visual['adjustment_kind']
    if not applied:
        if score is None and allow_withheld: return
        if adjustment!='none' or visual['band_before'] is not None or visual['deduction_points'] is not None or visual['score_before'] is not None:
            raise ValueError('Unapplied handwriting review cannot claim a grade adjustment')
        return
    if not (visual['review_status']=='reviewed' and review['review_status']=='reviewed' and visual['original_handwriting'] and visual['clear_image'] and visual['affects_communication'] is True):
        raise ValueError('Handwriting adjustment requires clear reviewed original-image communication impact')
    if score['original_handwriting_reference'] not in {r['image_id'] for r in visual['regions']}:
        raise ValueError('Handwriting score must name its reviewed original-image evidence')
    if score['source_section_id']!=sid:
        raise ValueError('Handwriting score and visual review rubric mismatch')
    if kind=='应用文':
        bands=['第五档','第四档','第三档','第二档','第一档','0 分档']
        before=visual['band_before']
        if adjustment!='lower_one_band' or before not in bands[:-1] or score['band']!=bands[bands.index(before)+1] or visual['deduction_points'] is not None or visual['score_before'] is not None:
            raise ValueError('Application handwriting rule lowers one band, not arbitrary points')
    else:
        before=visual['score_before']; points=visual['deduction_points']
        if adjustment!='discretionary_deduction' or points is None or before is None or visual['band_before'] is not None:
            raise ValueError('Continuation handwriting rule requires explicit discretionary deduction')
        if not 0<=before['lower']<=before['upper']<=25 or before['lower']-points!=score['lower'] or before['upper']-points!=score['upper']:
            raise ValueError('Continuation handwriting deduction must match before/after proposal')


def visual_fingerprint(feedback):
    payload={k:feedback[k] for k in ['image_manifest','student_text_sha256']}
    payload.update(handwriting_review=feedback['review'].get('handwriting_review'),score=feedback['review']['proposed_score'])
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def validate_writing_projection(analysis,registry):
    feedback=analysis['writing_feedback']
    if feedback is None: return
    review=feedback['review']; manifest=feedback['image_manifest']
    if len({a['image_id'] for a in manifest})!=len(manifest): raise ValueError('Duplicate original image manifest')
    check_handwriting(review,analysis['question_type'],registry,manifest,review['proposed_score'],allow_withheld=feedback['scope']!='full_correction')
    visual=review.get('handwriting_review'); ids=feedback['image_evidence_ids']
    if not visual:
        if ids: raise ValueError('Image evidence without visual review')
        return
    if visual['student_text_sha256']!=feedback['student_text_sha256']:
        raise ValueError('Original-image review belongs to another student draft')
    nodes={n['id']:n for n in analysis['evidence_graph']['nodes']}
    if len(ids)!=len(visual['regions']) or len(set(ids))!=len(ids):
        raise ValueError('Handwriting evidence projection is incomplete')
    fingerprint=visual_fingerprint(feedback)
    for nid,region in zip(ids,visual['regions']):
        n=nodes.get(nid)
        if n is None or n['type']!='image_evidence' or n.get('image_ref')!={k:region[k] for k in ['image_id','sha256','box']} or n['label']!=region['observed'] or n.get('artifact_fingerprint')!=fingerprint:
            raise ValueError('Handwriting review changed after image evidence binding')
    if feedback['scope']!='full_correction' and review['proposed_score'] is not None:
        raise ValueError('Partial handwriting correction cannot expose full score')
    score=review['proposed_score']
    if score and score['handwriting_applied']:
        relations={n['id'] for n in nodes.values() if n['type']=='relation' and n.get('reviewed') and n.get('method_id')==('A09' if analysis['question_type']=='应用文' else 'W15') and n['label']=='外部写作审阅：'+score['rationale']}
        if not relations or any(not any(e['from']==nid and e['to'] in relations and e['type']=='supports' for e in analysis['evidence_graph']['edges']) for nid in ids):
            raise ValueError('Handwriting score lost its original-image evidence path')

def writing_feedback(question,registry,graph=None,triggers=None):
    supplied=question.get('writing_review')
    if supplied is None: return None
    kind=question['question_type']
    if kind not in ORDERS or supplied['question_type']!=kind:
        raise ValueError('Writing review question type mismatch')
    review=deepcopy(supplied)
    manifest=image_manifest(question)
    check_handwriting(review,kind,registry,manifest,review['proposed_score'])
    if review.get('handwriting_review') and review['handwriting_review']['student_text_sha256']!=hashlib.sha256(question.get('student_text','').encode()).hexdigest():
        raise ValueError('Original-image review belongs to another student draft')
    if not review['sections'] and not review['corrections']: raise ValueError('Empty writing review')
    filename='application-writing-and-correction.md' if kind=='应用文' else 'continuation-writing-and-correction.md'
    path='gaokao-writing/references/'+filename
    for sid in review['source_section_ids']:
        if sid not in registry.sources['sections'] or registry.sources['sections'][sid]['path']!=path:
            raise ValueError('Writing review source belongs to another course module')
    keys=[s['key'] for s in review['sections']]
    if len(keys)!=len(set(keys)): raise ValueError('Duplicate writing feedback section')
    if set(keys)-set(ORDERS[kind]): raise ValueError('Writing feedback section is from another module')
    for section in review['sections']:
        for s in section['evidence']: check_span(question,s)
        if section['key'] in {'overall','diagnostics','anchors','emotion'} and not section['evidence']:
            raise ValueError('Writing diagnosis needs current material evidence')
        if review['kind']=='correction' and section['key']=='overall' and not any(s['field']=='student_text' for s in section['evidence']):
            raise ValueError('Correction cannot praise or diagnose an unseen student draft')
    occupied=[]
    for correction in review['corrections']:
        s=check_span(question,correction['original'])
        if s['field']!='student_text': raise ValueError('Correction must identify actual student text')
        if any(s['start']<end and start<s['end'] for start,end in occupied):
            raise ValueError('Overlapping corrections require one explicit reviewed replacement')
        occupied.append((s['start'],s['end']))
    covered=set()
    for s in review['reviewed_student_spans']:
        check_span(question,s)
        if s['field']!='student_text': raise ValueError('Language coverage must refer to student text')
        covered.update(range(s['start'],s['end']))
    student=question.get('student_text','')
    language_complete=bool(student.strip()) and all(i in covered for i,c in enumerate(student) if not c.isspace())
    materials_complete=bool(question['stem'].strip())
    if kind=='读后续写':
        starters=question.get('continuation_starters',[])
        materials_complete=materials_complete and bool(question.get('passage','').strip()) and len(starters)==2 and all(s.strip() for s in starters)
    order=ORDERS[kind]
    required=set(order)-{'corrections','materials'}
    mid=('A01' if kind=='应用文' else 'W01') if review['kind']=='guidance' else ('A09' if kind=='应用文' else 'W15')
    independent_trigger=bool((triggers or {}).get(mid))
    cited={s['field'] for section in review['sections'] for s in section['evidence']}
    required_fields={'stem','student_text'} if kind=='应用文' else {'passage','student_text','continuation_starters:0','continuation_starters:1'}
    full=materials_complete and required_fields<=cited and review['student_text_complete'] and language_complete and required<=set(keys) and independent_trigger
    if kind=='读后续写': full=full and review['student_text_excludes_given_starters']
    limitations=['外部审阅意见已绑定题面与原稿；结构/引用检查不认证英语判断、改写保真、评分正确或审阅者身份。']
    if review['kind']=='guidance':
        if review['corrections'] or review['proposed_score'] is not None:
            raise ValueError('Writing guidance cannot invent corrections or grades')
        scope='guidance' if materials_complete else 'partial_feedback'
    else:
        scope='full_correction' if full else 'partial_feedback'
        if not full: limitations.append('批改材料、语言审阅覆盖、独立方法触发或原交付功能不完整，只交付有依据的局部反馈；不得称完整批改。')
    score_status='not_requested'
    score=review['proposed_score']
    if score is not None:
        scale=15 if kind=='应用文' else 25
        if score['scale']!=scale or not 0<=score['lower']<=score['upper']<=scale:
            raise ValueError('Writing score scale or range mismatch')
        sid=score['source_section_id']
        if sid not in review['source_section_ids'] or registry.sources['sections'][sid]['heading']!=f'{scale} 分评分规范':
            raise ValueError('Writing score requires the correct frozen rubric section')
        rubric=registry.sources['sections'][sid]['content']
        bands={line.split('|')[1].strip() for line in rubric.splitlines() if line.startswith('|') and (line.split('|')[1].strip().startswith('第') or line.split('|')[1].strip()=='0 分档')}
        if score['band'] not in bands: raise ValueError('Unknown course score band')
        for s in score['evidence']: check_span(question,s)
        if not any(s['field']=='student_text' for s in score['evidence']):
            raise ValueError('Score requires actual student evidence')
        if not full or review['kind']!='correction' or review['review_status']!='reviewed':
            review['proposed_score']=None; score_status='withheld'
            limitations.append('不完整或未审阅批改的完整分数已扣留。')
        else: score_status='external_proposal_not_certified'
    if review['review_status']!='reviewed':
        scope='unreviewed'; review['proposed_score']=None
        limitations.append('未审阅稿仅保留机器数据，不向学生交付其诊断或改稿。')
    elif not materials_complete:
        review['sections']=[]
        limitations.append('缺题目/原文/首句时只保留逐处现有语言修改；完整框架诊断、主题判断及整篇修改稿已扣留。')
    elif scope=='partial_feedback':
        review['sections']=[s for s in review['sections'] if s['key']!='revised_text']
        limitations.append('局部批改不交付冒充完整稿的整篇修改稿。')
    evidence_ids=[]; image_ids=[]
    feedback={'review':review,'scope':scope,'score_status':score_status,'source_document':path,'section_order':order,'evidence_ids':evidence_ids,'image_manifest':manifest,'image_evidence_ids':image_ids,'student_text_sha256':hashlib.sha256(student.encode()).hexdigest(),'limitations':limitations}
    visual=review.get('handwriting_review')
    if visual:
        limitations.append('原图字节、尺寸、区域和原稿指纹已绑定；原稿身份、清晰度及交际影响仍是外部审阅声明，不是自动视觉评分。')
    if graph is not None:
        if visual:
            for region in visual['regions']:
                image_ids.append(graph.node('image_evidence',region['observed'],image_ref={k:region[k] for k in ['image_id','sha256','box']},artifact_fingerprint=visual_fingerprint(feedback)))
        # These nodes trace the host's assertions, not an automatic judgement.
        # Independent method triggers still come from the ordinary observations.
        entries=[(s['text'],s['evidence']) for s in review['sections']]
        entries += [(c['replacement']+'；'+c['reason'],[c['original']]) for c in review['corrections']]
        if review['proposed_score'] is not None:
            entries.append((review['proposed_score']['rationale'],review['proposed_score']['evidence']))
        for claim,spans in entries:
            reviewed=review['review_status']=='reviewed' and independent_trigger and bool(spans)
            candidate=graph.node('candidate_claim',claim,candidate='student_draft')
            rel=graph.node('relation','外部写作审阅：'+claim,method_id=mid,reviewed=reviewed)
            graph.edge(candidate,rel,'supports')
            if review['proposed_score'] is not None and claim==review['proposed_score']['rationale'] and review['proposed_score']['handwriting_applied']:
                for nid in image_ids: graph.edge(nid,rel,'supports')
            for span in spans:
                nid=graph.node('source_evidence',span['quote'],span=span)
                graph.edge(nid,rel,'supports'); evidence_ids.append(nid)
            for trigger in (triggers or {}).get(mid,[]): graph.edge(trigger,rel,'supports')
            if reviewed and review['kind']=='correction':
                action=graph.node('method_action',registry.methods[mid]['core_action'],method_id=mid)
                graph.edge(rel,action,'supports')
                verification=graph.node('verification','外部建议，非自动语义认证：'+claim,method_id=mid,candidate='student_draft')
                graph.edge(action,verification,'verifies')
    return feedback
