"""Bind externally reviewed single-question spoken delivery to core evidence.

This checks transport, method/candidate coverage and source spans, not English
semantics, a lecturer's identity, or full-paper course ordering.
"""
from copy import deepcopy
import re
from .evidence import check_span
from .execution import covered_by
from .question_verification import validate_question_verification_projection
from video_contracts.answer_consistency import artifact_fingerprint
from video_contracts.objective_images import segment_image_ids, validate_image_lesson

TYPES={'阅读理解','七选五','完形填空','语法填空'}
DELIVERY_PATH='gaokao-english/references/delivery-contract.md'


def check_spoken_text(text,evidence):
    # English source punctuation is preserved inside exact source quotes.
    protected=text
    for s in sorted(evidence,key=lambda s:len(s['quote']),reverse=True):
        if re.search('[A-Za-z]',s['quote']): protected=protected.replace(s['quote'],'SOURCE')
    if any(c in protected for c in ':：;；!！“”‘’"\'`<>[]{}|#*、（）()—→=≠') or re.search(r'https?://|\n\s*(?:[-+]|\d+[.)、])',protected):
        raise ValueError('Spoken lesson must be natural plain text, not headings/lists/quoted/internal formatting')
    if any(word in protected for word in ['同学','置信度','证据编号','审阅','路由','来源台账','已核对','review_status','method_id','图片里','截图上','图中','如图所示','你发的图','作为老师','老师讲过这道题']):
        raise ValueError('Spoken lesson exposes internal metadata or fabricated delivery persona')


def terminal_targets(segment,analysis,used_methods):
    """Bind a non-branded spoken comparison to actual complete-question proof."""
    terminal=analysis.get('question_verification')
    if not terminal or terminal['state']!='reviewed' or not analysis['answer_verification']['closed']:
        raise ValueError('Spoken terminal comparison requires a reviewed closed question')
    if segment['terminal_review_id']!=terminal['review']['review_id']:
        raise ValueError('Spoken comparison must name its own terminal review')
    trace={x['execution_id']:x for x in analysis['execution_trace']}
    consumed={trace[x['execution_id']]['method_id'] for x in terminal['consumed_artifacts']}
    if not consumed<=used_methods:
        raise ValueError('Spoken terminal comparison must follow its actual supporting method actions')
    checks={c['candidate']:c for c in terminal['review']['candidate_checks']}
    bindings={b['candidate']:b for b in terminal['candidate_bindings']}
    ids=segment['candidate_ids']
    if len(ids)!=len(set(ids)) or not set(ids)<=set(checks):
        raise ValueError('Unknown or repeated spoken terminal candidate')
    if not any(s['field']=='passage' and s['quote'] in segment['text'] for s in segment['evidence']):
        raise ValueError('Spoken terminal comparison must show current source words')
    targets=[]
    for cid in ids:
        c=checks[cid]; b=bindings[cid]
        if b['effect']=='undetermined' or c['backfill_verdict']!='supports' or not b['verification_node_id']:
            raise ValueError('Spoken comparison cannot turn an unresolved terminal check into a decision')
        if cid not in segment['text'] or not all(covered_by(s,segment['evidence']) for s in c['evidence']):
            raise ValueError('Spoken terminal comparison lacks its own candidate and decisive evidence')
        targets.append(b['verification_node_id'])
    return targets


def check_lesson_sources(kind,source_ids,registry):
    if kind not in TYPES:
        raise ValueError('Spoken lesson source requires a supported objective question')
    if not any(sid in registry.sources['sections'] and registry.sources['sections'][sid]['path']==DELIVERY_PATH for sid in source_ids):
        raise ValueError('Spoken lesson must bind the frozen student delivery contract')
    allowed_paths={DELIVERY_PATH,'gaokao-english/references/course-evidence.md','gaokao-english/references/'+{'阅读理解':'reading-comprehension.md','七选五':'seven-five.md','完形填空':'cloze.md','语法填空':'course-evidence.md'}[kind]}
    if kind=='语法填空': allowed_paths.update({'gaokao-grammar-fill/SKILL.md','gaokao-grammar-fill/references/grammar-fill.md','gaokao-grammar-fill/references/course-evidence.md'})
    if len(source_ids)!=len(set(source_ids)) or any(sid not in registry.sources['sections'] or registry.sources['sections'][sid]['path'] not in allowed_paths for sid in source_ids):
        raise ValueError('Spoken lesson source is unknown, duplicated or from another module')


def lesson_feedback(question,analysis,registry,graph,trigger_nodes,relation_nodes):
    supplied=question.get('lesson_review')
    if supplied is None: return None
    if question['question_type'] not in TYPES or supplied['question_type']!=question['question_type']:
        raise ValueError('Spoken lesson question type mismatch')
    review=deepcopy(supplied); source_ids=review['source_section_ids']
    check_lesson_sources(question['question_type'],source_ids,registry)
    matched={x['method_id'] for x in analysis['method_matches']}; used=set(); actions=set(); evidenced=set(); compared=set(); stopped=set(); ids=set(); evidence_ids=[]; bindings=[]
    visual_candidates={c['candidate'] for c in analysis.get('question_verification',{}).get('review',{}).get('candidate_checks',[]) if c.get('image_evidence')}
    image_compared=set()
    spoken_image_edges=set()
    for segment in review['segments']:
        sid=segment['segment_id']; function=segment['function']
        if sid in ids: raise ValueError('Duplicate spoken segment id')
        ids.add(sid)
        if segment.get('segment_scope')=='whole_question':
            if review['schema_version'] not in {'1.1.0','1.2.0'}:
                raise ValueError('Whole-question spoken segments require lesson-review 1.1.0 or 1.2.0')
            spans=[check_span(question,s) for s in segment['evidence']]
            check_spoken_text(segment['text'],spans)
            targets=terminal_targets(segment,analysis,actions)
            image_ids=[]
            if review['review_status']=='reviewed':
                if set(segment['candidate_ids']) & visual_candidates and review['schema_version']!='1.2.0':
                    raise ValueError('Image-dependent spoken comparisons require lesson-review 1.2.0')
                image_ids=segment_image_ids(segment,analysis)
                image_compared.update(set(segment['candidate_ids']) & visual_candidates)
            compared.update(segment['candidate_ids'])
            if review['review_status']=='reviewed':
                claim=graph.node('candidate_claim',segment['text'],candidate='spoken_segment:'+sid)
                extra={'artifact_fingerprint':artifact_fingerprint(segment)} if review['schema_version']=='1.2.0' else {}
                relation=graph.node('relation','整题候选口播记录',review_id=segment['terminal_review_id'],reviewed=True,**extra)
                graph.edge(claim,relation,'supports')
                for target in targets: graph.edge(target,relation,'supports')
                for nid in image_ids:
                    graph.edge(nid,relation,'supports')
                    spoken_image_edges.add((nid,relation))
                own_ids=[]
                for s in spans:
                    nid=graph.node('source_evidence',s['quote'],span=s)
                    evidence_ids.append(nid); own_ids.append(nid); graph.edge(nid,relation,'supports')
                bindings.append({'segment_id':sid,'claim_node_id':claim,'relation_node_id':relation,'evidence_ids':own_ids})
                if review['schema_version']=='1.2.0': bindings[-1]['image_evidence_ids']=image_ids
            continue
        mid=segment['method_id']
        if mid not in matched or mid not in {x['method_id'] for x in analysis['method_chain']}:
            raise ValueError('Spoken lesson invokes an unmatched/unplanned method')
        method=registry.methods[mid]
        if not set(method['section_ids']).intersection(source_ids): raise ValueError('Spoken method needs its own course source')
        spans=[check_span(question,s) for s in segment['evidence']]
        if not any(s['field'] in {'passage','stem'} for s in spans): raise ValueError('Spoken lesson cannot use candidate wording as its only evidence')
        if question['question_type']!='语法填空' and not any(s['field']=='passage' for s in spans): raise ValueError('Objective lesson requires current passage evidence')
        check_spoken_text(segment['text'],spans)
        if mid not in used:
            aliases=[method['brand_name'],method['source_name']]+method['aliases']
            if function!='action' or not any(alias in segment['text'] for alias in aliases):
                raise ValueError('First use must name the method inside its actual action, not a separate method summary')
            used.add(mid)
        if function=='action': actions.add(mid)
        if function in {'evidence','comparison'}:
            if mid not in actions or not any(s['quote'] in segment['text'] for s in spans): raise ValueError('Spoken evidence must follow action and show a current source quote')
            evidenced.add(mid)
        if function=='stop': stopped.add(mid)
        refs=segment['relation_indices']
        if len(refs)!=len(set(refs)): raise ValueError('Repeated spoken candidate relation')
        if function=='comparison' and not refs: raise ValueError('Candidate comparison requires its own reviewed relations')
        for index in refs:
            relations=question.get('relations',[])
            if index>=len(relations): raise ValueError('Unknown spoken candidate relation')
            rel=relations[index]
            if rel['method_id']!=mid or rel['review_status']!='reviewed' or rel['effect']=='undetermined': raise ValueError('Spoken candidate comparison cannot borrow an unrelated or unreviewed decision')
            if not all(any(s['field']==r['field'] and s['start']<=r['start'] and r['end']<=s['end'] for s in spans) for r in rel['evidence']):
                raise ValueError('Spoken comparison lacks its own decisive relation evidence')
            if rel['candidate'] not in segment['text']: raise ValueError('Spoken comparison must identify its actual candidate')
            if function=='comparison': compared.add(rel['candidate'])
        if review['review_status']=='reviewed':
            if not trigger_nodes.get(mid): raise ValueError('Spoken lesson requires independently reviewed method triggers')
            claim=graph.node('candidate_claim',segment['text'],candidate='spoken_segment:'+sid)
            extra={'artifact_fingerprint':artifact_fingerprint(segment)} if review['schema_version']=='1.2.0' else {}
            relation=graph.node('relation','外部单题口播记录',method_id=mid,reviewed=True,**extra)
            graph.edge(claim,relation,'supports')
            own_ids=[]
            for signal in trigger_nodes[mid]: graph.edge(signal,relation,'supports')
            for s in spans:
                nid=graph.node('source_evidence',s['quote'],span=s); evidence_ids.append(nid); own_ids.append(nid); graph.edge(nid,relation,'supports')
            for index in refs: graph.edge(relation_nodes[index],relation,'supports')
            bindings.append({'segment_id':sid,'claim_node_id':claim,'relation_node_id':relation,'evidence_ids':own_ids})
    complete=bool(analysis['answer_verification']['closed'] and used and used<=actions and used<=evidenced and used<=stopped
                  and set(analysis['answer_verification']['retained_candidates']+analysis['answer_verification']['eliminated_candidates'])<=compared
                  and visual_candidates<=image_compared)
    grouping_ids=[]
    if question['question_type']=='七选五':
        partitions=[x for x in analysis['execution_trace'] if x['state']=='produced' and x['method_id']=='F01' and x['output']['kind']=='candidate_partition']
        by_axis={axis:[x for x in partitions if x['output']['axis']==axis] for axis in ['sentence','actor','time']}
        grouping_ok='F01' in used and review['segments'][0].get('method_id')=='F01' and review['segments'][0]['function']=='action' and set(question.get('options',{}))==set('ABCDEFG') and all(len(values)==1 for values in by_axis.values())
        complete=complete and grouping_ok
        if grouping_ok:
            grouping_ids=[by_axis[axis][0]['execution_id'] for axis in ['sentence','actor','time']]
            for x in partitions:
                for group in x['output']['groups']: check_spoken_text(group['label'],x['evidence'])
    scope='unreviewed' if review['review_status']!='reviewed' else 'single_question_lesson' if complete else 'partial_delivery'
    limitations=['单题口播为外部审阅输送，引用与覆盖检查不认证英语语义、文字忠实性、审阅身份或旧宿主表现。','仅单题入口，不证明整篇分组、阅读主旨优先或完形两遍等完整讲题顺序。']
    if scope!='single_question_lesson':
        if spoken_image_edges:
            graph.graph['edges']=[e for e in graph.graph['edges'] if (e['from'],e['to']) not in spoken_image_edges]
        review['segments']=[]
        bindings=[]
        grouping_ids=[]
        limitations.append('口播尚未覆盖实际动作、短引文、候选核验、刹车或最终闭合，实际扣留完整口播，不冒充已完成讲题。')
    return {'review':review,'scope':scope,'evidence_ids':evidence_ids,'segment_bindings':bindings,'grouping_execution_ids':grouping_ids,'limitations':limitations}


def validate_lesson_projection(analysis,registry):
    feedback=analysis['lesson_feedback']
    if feedback is None: return
    review=feedback['review']
    if review['question_type']!=analysis['question_type']:
        raise ValueError('Spoken lesson question type mismatch')
    check_lesson_sources(analysis['question_type'],review['source_section_ids'],registry)
    validate_image_lesson(analysis)
    if feedback['scope']!='single_question_lesson':
        if review['segments'] or feedback['segment_bindings'] or feedback['grouping_execution_ids']: raise ValueError('Partial/unreviewed lesson must withhold student delivery')
        return
    if not analysis['answer'] or not analysis['answer_verification']['closed'] or review['review_status']!='reviewed' or review['question_type']!=analysis['question_type']:
        raise ValueError('Complete spoken lesson requires a reviewed closed answer')
    retained={c['candidate'] for c in analysis['candidate_analysis'] if c['effect']=='retain'}
    eliminated={c['candidate'] for c in analysis['candidate_analysis'] if c['effect']=='eliminate'}
    if analysis.get('question_verification'):
        validate_question_verification_projection(analysis,registry)
        for c in analysis['question_verification']['candidate_bindings']:
            if c['effect']=='retain': retained.add(c['candidate'])
            if c['effect']=='eliminate': eliminated.add(c['candidate'])
    if retained!={analysis['answer']} or retained.intersection(eliminated) or analysis['answer_verification']['unresolved_candidates']:
        raise ValueError('Spoken final answer differs from its own candidate closure')
    nodes={n['id']:n for n in analysis['evidence_graph']['nodes']}; edges={(e['from'],e['to']) for e in analysis['evidence_graph']['edges']}
    bindings={b['segment_id']:b for b in feedback['segment_bindings']}
    if len(bindings)!=len(feedback['segment_bindings']) or set(bindings)!={s['segment_id'] for s in review['segments']}: raise ValueError('Spoken graph bindings differ from delivery segments')
    used=set(); actions=set(); evidenced=set(); stopped=set(); compared=set()
    for s in review['segments']:
        if s.get('segment_scope')=='whole_question':
            if review['schema_version'] not in {'1.1.0','1.2.0'}: raise ValueError('Whole-question spoken segments require lesson-review 1.1.0 or 1.2.0')
            check_spoken_text(s['text'],s['evidence'])
            targets=terminal_targets(s,analysis,actions)
            binding=bindings[s['segment_id']]
            claim=nodes.get(binding['claim_node_id'],{}); rel=nodes.get(binding['relation_node_id'],{})
            if (claim.get('label')!=s['text'] or claim.get('candidate')!='spoken_segment:'+s['segment_id']
                    or rel.get('method_id') or rel.get('review_id')!=s['terminal_review_id']
                    or not rel.get('reviewed') or (claim.get('id'),rel.get('id')) not in edges
                    or any((target,rel.get('id')) not in edges for target in targets)):
                raise ValueError('Spoken terminal text detached from its own candidate proof')
            evidence=[nodes.get(nid,{}) for nid in binding['evidence_ids']]
            if [n.get('span') for n in evidence]!=s['evidence'] or any((n.get('id'),rel.get('id')) not in edges for n in evidence):
                raise ValueError('Spoken terminal delivery evidence differs from graph')
            compared.update(s['candidate_ids'])
            continue
        mid=s['method_id']; method=registry.methods.get(mid); binding=bindings[s['segment_id']]
        if not method or method['version']!=analysis['method_versions'].get(mid) or not any(m['method_id']==mid and m['trigger_verified'] for m in analysis['method_matches']):
            raise ValueError('Spoken projection lacks current method and independent trigger')
        if not set(method['section_ids']).intersection(review['source_section_ids']): raise ValueError('Spoken projection lost its own course source')
        check_spoken_text(s['text'],s['evidence'])
        if mid not in used:
            if s['function']!='action' or not any(name in s['text'] for name in [method['brand_name'],method['source_name']]+method['aliases']): raise ValueError('Spoken projection must name method on first action')
            used.add(mid)
        if s['function']=='action': actions.add(mid)
        if s['function'] in {'evidence','comparison'}:
            if not any(span['quote'] in s['text'] for span in s['evidence']): raise ValueError('Spoken projection must show source evidence')
            evidenced.add(mid)
        if s['function']=='stop': stopped.add(mid)
        for index in s['relation_indices']:
            if index>=len(analysis['candidate_analysis']): raise ValueError('Unknown projected candidate relation')
            candidate=analysis['candidate_analysis'][index]
            if candidate['method_id']!=mid or candidate['effect']=='undetermined' or candidate['candidate'] not in s['text']: raise ValueError('Projected lesson changes candidate judgement')
            if s['function']=='comparison': compared.add(candidate['candidate'])
        claim=nodes.get(binding['claim_node_id'],{}); rel=nodes.get(binding['relation_node_id'],{})
        if claim.get('label')!=s['text'] or claim.get('candidate')!='spoken_segment:'+s['segment_id'] or rel.get('method_id')!=mid or not rel.get('reviewed') or (claim.get('id'),rel.get('id')) not in edges:
            raise ValueError('Spoken text is detached from its reviewed graph claim')
        if not any(n['type']=='question_signal' and n.get('method_id')==mid and n.get('reviewed') and (n['id'],rel.get('id')) in edges for n in nodes.values()):
            raise ValueError('Spoken graph lost its independent method trigger')
        evidence=[nodes.get(nid,{}) for nid in binding['evidence_ids']]
        if [n.get('span') for n in evidence]!=s['evidence'] or any((n.get('id'),rel.get('id')) not in edges for n in evidence):
            raise ValueError('Spoken delivery evidence differs from its graph')
        for index in s['relation_indices']:
            c=analysis['candidate_analysis'][index]
            if not any(n['type']=='relation' and n.get('method_id')==mid and n.get('candidate')==c['candidate'] and n.get('reviewed') and (n['id'],rel.get('id')) in edges for n in nodes.values()):
                raise ValueError('Spoken graph lost the current candidate relation')
    if not used<=actions or not used<=evidenced or not used<=stopped or not set(analysis['answer_verification']['retained_candidates']+analysis['answer_verification']['eliminated_candidates'])<=compared:
        raise ValueError('Complete spoken projection lost method/evidence/stop/candidate coverage')
    if analysis['question_type']=='七选五':
        executions={x['execution_id']:x for x in analysis['execution_trace']}; axes=[]
        for eid in feedback['grouping_execution_ids']:
            x=executions.get(eid)
            if not x or x['state']!='produced' or x['method_id']!='F01' or x['output']['kind']!='candidate_partition': raise ValueError('Spoken grouping needs reviewed F01 partitions')
            axes.append(x['output']['axis'])
            for group in x['output']['groups']: check_spoken_text(group['label'],x['evidence'])
        if axes!=['sentence','actor','time'] or 'F01' not in used: raise ValueError('Seven-five delivery must show all three grouping axes once')
    elif feedback['grouping_execution_ids']: raise ValueError('Do not apply seven-five grouping order to another question type')
