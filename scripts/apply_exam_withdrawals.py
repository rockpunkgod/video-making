"""Execute explicit negative post-reveal review findings against frozen inputs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.review_withdrawal import withdraw_review
from scripts.collect_exam_cases import host_items,material_equal
from scripts.ingest_exam_sources import ROOT,freeze_json,sha

def apply(dataset,exam_id,finding_path):
    root=Path(dataset); raw=Path(finding_path).read_bytes(); document=json.loads(raw)
    if set(document)!={'exam_id','host_prediction_sha256','semantic_review_sha256','finding'} or document['exam_id']!=exam_id:
        raise ValueError('Withdrawal document exam identity/fields mismatch')
    host_bytes=(root/'predictions'/exam_id/'reviewed-blind.json').read_bytes()
    audit_bytes=(root/'semantic-reviews'/(exam_id+'.json')).read_bytes()
    if document['host_prediction_sha256']!=sha(host_bytes) or document['semantic_review_sha256']!=sha(audit_bytes):
        raise ValueError('Withdrawal must bind actual host prediction and semantic review')
    audit=json.loads(audit_bytes); host=json.loads(host_bytes); finding=document['finding']
    if audit['question_id']!=finding['question_id'] or audit['exam_id']!=exam_id:
        raise ValueError('Withdrawal borrows a different semantic review')
    audit_binding=audit.get('reviewed_prediction_sha256',audit.get('blind_prediction_sha256'))
    audit_stage=audit.get('stage',audit.get('review_stage',audit.get('review_timing','')))
    if audit_binding!=sha(host_bytes) or not audit_stage.startswith('post_reveal'):
        raise ValueError('Semantic audit is not bound to this post-reveal host review')
    selected=[(q,a) for q,a in host_items(host) if q['question_id']==finding['question_id']]
    if len(selected)!=1: raise ValueError('Withdrawal must select one frozen host question')
    mechanical_bytes=(root/'predictions'/exam_id/'blind.json').read_bytes(); mechanical=json.loads(mechanical_bytes)
    if (mechanical.get('exam_id')!=exam_id or mechanical.get('pass')!='blind' or host.get('exam_id')!=exam_id
        or host.get('mechanical_prediction_sha256',host.get('source_prediction_sha256'))!=sha(mechanical_bytes)):
        raise ValueError('Withdrawal host no longer binds original mechanical paper')
    paper=deepcopy(mechanical['inputs']); q,a=selected[0]
    positions=[i for i,x in enumerate(paper['questions']) if x['question_id']==q['question_id']]
    if len(positions)!=1: raise ValueError('Question absent from original paper')
    material_equal(paper['questions'][positions[0]],q)
    engine=QuestionAnalyzer(); out=withdraw_review(q,a,finding,engine)
    paper['questions'][positions[0]]=out['input']; aggregate=PaperAnalyzer(engine).analyze(paper)
    result={'exam_id':exam_id,'stage':'post_reveal_negative_review_execution','finding_sha256':sha(raw),
        'host_prediction_sha256':sha(host_bytes),'semantic_review_sha256':sha(audit_bytes),
        **out,'paper_analysis':aggregate,'new_blind_prediction':False,'registry_updates':0,
        'semantic_certification':'not_certified','learner_validation':'pending_real_participant_validation'}
    freeze_json(root/'case-review'/exam_id/'withdrawal.json',result)
    return metadata(result)

def metadata(result):
    return {'exam_id':result['exam_id'],'stage':result['stage'],
        'finding_sha256':result['finding_sha256'],'host_prediction_sha256':result['host_prediction_sha256'],
        'semantic_review_sha256':result['semantic_review_sha256'],
        'question_id':result['analysis']['question_id'],'answer_withheld':result['analysis']['answer'] is None,
        'content_eligible':result['analysis']['content_eligible'],
        'effective_relation_indexes':result['withdrawal']['effective_relation_indexes'],
        'effective_execution_ids':result['withdrawal']['effective_execution_ids'],
        'failure_categories':result['withdrawal']['failure_categories'],
        'recommendations':result['paper_analysis']['recommendations'],
        'case_candidates':result['paper_analysis']['case_candidates'],
        'new_blind_prediction':False,'registry_updates':0,'semantic_certification':'not_certified'}

def load_metadata(dataset,exam_id):
    root=Path(dataset); path=root/'case-review'/exam_id/'withdrawal.json'
    if not path.is_file(): return None
    result=json.loads(path.read_bytes())
    host_bytes=(root/'predictions'/exam_id/'reviewed-blind.json').read_bytes()
    audit_bytes=(root/'semantic-reviews'/(exam_id+'.json')).read_bytes()
    if result['exam_id']!=exam_id or result['host_prediction_sha256']!=sha(host_bytes) or result['semantic_review_sha256']!=sha(audit_bytes):
        raise ValueError('Withdrawal metadata no longer binds frozen sources')
    return metadata(result)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('exam_id'); parser.add_argument('finding')
    parser.add_argument('--dataset',default=str(ROOT/'local-data/exams-2020-2025'))
    args=parser.parse_args(); print(json.dumps(apply(args.dataset,args.exam_id,args.finding),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
