"""Replay frozen host evidence into local Case Review candidates, not releases.

No reference answer is read. Paper aggregation occurs after reveal and is never
relabeled blind. Text and graphs remain in the ignored dataset directory.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from core.analyzer import QuestionAnalyzer, PaperAnalyzer
from core.evidence import validate_graph
from core.execution import validate_execution_trace
from core.registry import Registry, validate_schema
from scripts.ingest_exam_sources import ROOT, freeze_json, sha

MATERIAL_FIELDS=('question_id','question_type','stem','passage','options','given_word',
                 'student_text','continuation_starters','original_images','student_symptoms')

def host_items(document):
    if document.get('pass')!='host_reviewed_blind':
        raise ValueError('Not a frozen host-reviewed prediction')
    if 'questions' in document:
        return [(item['input'],item['analysis']) for item in document['questions']]
    if 'question' in document:
        return [(document['question'],document['analysis'])]
    return [(document['reviewed_input'],document['prediction'])]

def material_equal(original,reviewed):
    for field in MATERIAL_FIELDS:
        if (field in original)!=(field in reviewed) or original.get(field)!=reviewed.get(field):
            raise ValueError('Frozen host changed original material: '+field)

def own_candidates(question,analysis,registry):
    """Keep actual artifacts/relations; do not credit merely suggested methods."""
    if not analysis['content_eligible']:
        return []
    stopped={x['method_id'] for x in analysis['execution_trace'] if x['state']=='stopped'}
    candidates=[]
    for match in analysis['method_matches']:
        mid=match['method_id']
        if not match['trigger_verified'] or mid in stopped:
            continue
        actions=[x for x in analysis['execution_trace'] if x['method_id']==mid and x['state']=='produced']
        decisions=[x for x in analysis['candidate_analysis'] if x['method_id']==mid and x['effect'] in {'retain','eliminate'}]
        if not actions and not decisions:
            continue
        method=registry.methods[mid]
        candidates.append({'candidate_id':question['question_id']+'-'+mid,'question_id':question['question_id'],
            'method_id':mid,'method_version':method['version'],'question_type':question['question_type'],
            'primary_role':method['primary_role'],'output_role':method['output_type'],
            'own_trigger':[x for x in question.get('observations',[]) if x['method_id']==mid and x['reviewed']],
            'own_produced_actions':deepcopy(actions),'own_reviewed_decisions':deepcopy(decisions),
            'observable_action_recorded':bool(actions),'candidate_status':'pending_case_review' if actions else 'needs_action_recording',
            'case_type':None,'case_type_reason':None,'original_question':deepcopy(question),
            'evidence_graph':deepcopy(analysis['evidence_graph']),
            'stop_rule':method['stop_rule'],'course_section_ids':list(method['section_ids']),
            'answer_scope':'Whole-question closure does not certify this method or its case type.',
            'registry_registration':'not_registered','source_rights':'local_research_only; redistribution_not_verified',
            'learner_validation':'pending_real_participant_validation'})
    return candidates

def collect(dataset,exam_id):
    root=Path(dataset); predictions=root/'predictions'/exam_id
    mechanical_bytes=(predictions/'blind.json').read_bytes()
    host_bytes=(predictions/'reviewed-blind.json').read_bytes()
    mechanical=json.loads(mechanical_bytes); host=json.loads(host_bytes)
    if mechanical.get('exam_id')!=exam_id or mechanical.get('pass')!='blind' or host.get('exam_id')!=exam_id:
        raise ValueError('Wrong exam or frozen pass')
    binding=host.get('mechanical_prediction_sha256',host.get('source_prediction_sha256'))
    if binding!=sha(mechanical_bytes):
        raise ValueError('Host prediction does not bind frozen mechanical prediction')
    originals={q['question_id']:q for q in mechanical['inputs']['questions']}
    paper=deepcopy(mechanical['inputs']); positions={q['question_id']:i for i,q in enumerate(paper['questions'])}
    registry=Registry(); registry.validate(); analyzer=QuestionAnalyzer(registry)
    cases=[]; reviewed_ids=set()
    for question,frozen in host_items(host):
        qid=question['question_id']
        if qid not in originals or qid in reviewed_ids:
            raise ValueError('Unknown or duplicate reviewed question')
        if frozen['question_id']!=qid or frozen['question_type']!=question['question_type']:
            raise ValueError('Frozen analysis identity differs from original question')
        material_equal(originals[qid],question)
        validate_schema('question-input',question); validate_schema('question-analysis',frozen)
        validate_graph(frozen['evidence_graph'],question); validate_execution_trace(frozen,registry)
        replay=analyzer.analyze(deepcopy(question))
        if replay!=frozen:
            raise ValueError('Current engine differs from frozen review; explicit regression review required')
        reviewed_ids.add(qid); paper['questions'][positions[qid]]=deepcopy(question)
        cases.extend(own_candidates(question,frozen,registry))
    # Replay the full original paper, overlaying ONLY unchanged pre-reveal input
    # annotations. This is post-reveal aggregation, not a newly blind analysis.
    aggregate=PaperAnalyzer(analyzer).analyze(paper)
    for item in cases:
        if item['question_id'] not in aggregate['method_coverage'][item['method_id']]['case_candidate_question_ids']:
            raise ValueError('Candidate missing own Paper Analyzer eligibility')
    report={'schema_version':'1.0.0','exam_id':exam_id,'stage':'post_reveal_aggregation_of_frozen_pre_reveal_annotations',
        'mechanical_prediction_sha256':sha(mechanical_bytes),'host_prediction_sha256':sha(host_bytes),
        'written_question_count':len(paper['questions']),'reviewed_question_ids':sorted(reviewed_ids),
        'case_candidates':cases,'paper_analysis':aggregate,
        'registry_updates':0,'case_slots_filled':0,'semantic_certification':'not_certified',
        'limitations':['Method eligibility is structural, not proof of English semantics or case-type suitability.',
            'Actionless reviewed decisions require actual action recording before a complete real Case.',
            'No answer key is read; no frozen prediction or Registry is rewritten.']}
    freeze_json(root/'case-review'/exam_id/'candidates.json',report)
    return public_metadata(report)

def public_metadata(report):
    return {'exam_id':report['exam_id'],'stage':report['stage'],'written_question_count':report['written_question_count'],
        'reviewed_question_ids':report['reviewed_question_ids'],'host_prediction_sha256':report['host_prediction_sha256'],
        'case_candidate_count':len(report['case_candidates']),
        'candidates':[{key:x[key] for key in ('candidate_id','question_id','method_id','method_version',
            'primary_role','output_role','observable_action_recorded','candidate_status','case_type','registry_registration')}
            for x in report['case_candidates']],
        'registry_updates':0,'case_slots_filled':0,'semantic_certification':'not_certified'}

def review_summary(dataset,exam_id):
    """Bind AI audit to its actual frozen candidate; export no teaching payload."""
    root=Path(dataset); candidate_path=root/'case-review'/exam_id/'candidates.json'
    if not candidate_path.is_file(): return None
    report=json.loads(candidate_path.read_bytes()); result=public_metadata(report)
    host_hash=sha((root/'predictions'/exam_id/'reviewed-blind.json').read_bytes())
    if report['exam_id']!=exam_id or report['host_prediction_sha256']!=host_hash:
        raise ValueError('Case candidate frozen review binding mismatch')
    review_path=root/'semantic-reviews'/(exam_id+'.json')
    if not review_path.is_file():
        result['semantic_review_status']='pending'; return result
    raw=review_path.read_bytes(); review=json.loads(raw)
    binding=review.get('reviewed_prediction_sha256',review.get('blind_prediction_sha256'))
    stage=review.get('stage',review.get('review_stage',review.get('review_timing','')))
    if review.get('exam_id')!=exam_id or review.get('question_id') not in report['reviewed_question_ids'] or binding!=host_hash or not stage.startswith('post_reveal'):
        raise ValueError('Semantic review does not bind the actual post-reveal candidate')
    methods={x['method_id']:x for x in review.get('method_reviews',review.get('methods',[]))}
    known={x['method_id']:x for x in report['case_candidates']}
    if set(methods)-set(known): raise ValueError('Semantic audit borrows unproduced method credit')
    recommendations=[review.get('single_case_type_recommendation',{}),review.get('best_single_case_type',{})]
    for candidate in result['candidates']:
        mid=candidate['method_id']; item=methods.get(mid,{})
        version=item.get('method_version',review.get('method_versions',{}).get(mid))
        if item and version!=candidate['method_version']: raise ValueError('Semantic review method version mismatch')
        proposed=item.get('unique_case_type_candidate')
        if not proposed:
            proposed=next((x.get('case_type') for x in recommendations if x.get('method_id')==mid),None)
        if proposed not in {None,'canonical','counterexample','boundary','transfer','hard'}:
            raise ValueError('Unknown proposed case type')
        candidate['proposed_case_type']=proposed
        candidate['case_type']=None  # Recommendation is not an approved type/slot.
        candidate['ai_semantic_result']=item.get('semantic_result',item.get('own_output',{}).get('status',
            review.get('overall',{}).get('method_attribution','AI_reviewed_not_certified')))
        candidate['semantic_review_status']='AI_post_reveal_reviewed_not_independently_certified' if item else 'pending'
    result.update({'semantic_review_status':'AI_post_reveal_reviewed_not_independently_certified',
        'semantic_review_sha256':sha(raw),'semantic_review_question_id':review['question_id'],
        'failure_category':review.get('failure_category'),
        'method_attribution_status':review.get('overall',{}).get('method_attribution',review.get('overall_status')),
        'registry_updates':0,'case_slots_filled':0})
    freeze_json(root/'case-review'/exam_id/'review-index.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('exam_id')
    parser.add_argument('--dataset',default=str(ROOT/'local-data/exams-2020-2025'))
    args=parser.parse_args(); print(json.dumps(collect(args.dataset,args.exam_id),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
