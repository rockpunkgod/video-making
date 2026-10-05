"""Freeze post-reveal own action artifacts, never whole-question success.

This lane deliberately does not read answer keys, change blind predictions,
register Cases, or promote methods. Full source text stays in local-data.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from core.analyzer import QuestionAnalyzer
from core.registry import Registry, validate_schema
from core.evidence import validate_graph
from core.execution import validate_execution_trace
from core.review_withdrawal import withdraw_review
from renderers import render
from scripts.collect_exam_cases import material_equal
from scripts.ingest_exam_sources import ROOT, freeze_json, sha

STAGE = 'post_reveal_action_review'
BOUNDED_STAGE = 'post_reveal_bounded_action_review'
FIELDS = {'exam_id', 'stage', 'reviewer', 'reviewer_kind', 'method_id',
          'mechanical_prediction_sha256', 'question', 'semantic_review'}
REVIEW_FIELDS = {'trigger', 'action', 'evidence', 'output', 'stop', 'transfer',
                 'practical_benefit', 'limitations', 'proposed_case_type'}
ANNOTATIONS = {'requested_chain', 'observations', 'action_executions'}
HELPER_KINDS = {'located_evidence', 'interpretation', 'candidate_partition',
                'framework_card', 'text_groups', 'route_selection'}


def nonempty(value):
    """Require actual review payload, without imposing another teaching Schema."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and any(nonempty(v) for v in value.values())
    if isinstance(value, list):
        return bool(value) and any(nonempty(v) for v in value)
    return False


def identifier(value):
    if not isinstance(value, str) or not value or any(c not in
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in value):
        raise ValueError('Unsafe artifact identifier')
    return value


def review_action(request, mechanical, analyzer=None):
    """Validate supplied annotations and replay real artifacts, not solve English."""
    if set(request) not in (FIELDS,FIELDS|{'supersedes_action_review_sha256'}) or request['stage'] not in {STAGE,BOUNDED_STAGE}:
        raise ValueError('Explicit post-reveal action stage required')
    if request['reviewer_kind'] not in {'AI', 'human'} or not isinstance(request['reviewer'], str) or not request['reviewer'].strip():
        raise ValueError('Explicit external reviewer required')
    semantic = request['semantic_review']
    if not isinstance(semantic, dict) or set(semantic) != REVIEW_FIELDS:
        raise ValueError('Own role review fields required')
    for key in REVIEW_FIELDS - {'proposed_case_type'}:
        if not nonempty(semantic[key]):
            raise ValueError('Nonempty own role review required: ' + key)
    proposal = semantic['proposed_case_type']
    if isinstance(proposal, dict):
        if proposal.get('method_id') != request['method_id'] or proposal.get('registered') is not False or proposal.get('promotion_allowed') is not False:
            raise ValueError('Case proposal cannot register or promote a method')
        proposal = proposal.get('case_type')
    if proposal not in {None, 'canonical', 'counterexample', 'boundary', 'transfer', 'hard'}:
        raise ValueError('Unknown proposed case type')
    exam = identifier(request['exam_id']); mid = identifier(request['method_id'])
    if mechanical.get('exam_id') != exam or mechanical.get('pass') != 'blind':
        raise ValueError('Wrong frozen source prediction')
    question = request['question']; qid = identifier(question['question_id'])
    originals = [q for q in mechanical['inputs']['questions'] if q['question_id'] == qid]
    if len(originals) != 1:
        raise ValueError('Unknown or duplicate original question')
    original = originals[0]
    material_equal(original, question)
    bounded=request['stage']==BOUNDED_STAGE
    annotations=ANNOTATIONS|({'relations'} if bounded else set())
    # Nothing beyond supported annotation fields may be added,
    # removed or replaced, including task type and preexisting source metadata.
    if {k: v for k, v in original.items() if k not in annotations} != {
            k: v for k, v in question.items() if k not in annotations}:
        raise ValueError('Action review changed frozen question fields')
    if question.get('word_answer') or (not bounded and question.get('relations')):
        raise ValueError('Helper action lane cannot assert answers or candidate effects')
    analyzer = analyzer or QuestionAnalyzer(Registry())
    if mid not in analyzer.registry.methods:
        raise ValueError('Unknown reviewed method')
    method = analyzer.registry.methods[mid]
    if bounded and method['primary_role']!='decider':
        raise ValueError('Bounded action lane requires its own primary decider')
    if not bounded and method['primary_role'] not in {'locator', 'interpreter', 'reducer', 'framework'}:
        raise ValueError('Helper lane cannot claim a decision or verification role')
    validate_schema('question-input', question)
    analysis = analyzer.analyze(deepcopy(question))
    validate_schema('question-analysis', analysis)
    validate_graph(analysis['evidence_graph'], question)
    registry = analyzer.registry
    validate_execution_trace(analysis, registry)
    actions = analysis['execution_trace']
    kinds={'candidate_decision'} if bounded else HELPER_KINDS
    if not actions or any(x['method_id'] != mid or x['role'] != method['primary_role'] or
            x['state'] != 'produced' or x['output']['kind'] not in kinds for x in actions):
        raise ValueError('Requires actual own reviewed action artifacts only')
    if bounded:
        relations=question.get('relations',[])
        if any(x['method_id']!=mid for x in relations) or sorted(
                x['output']['relation_index'] for x in actions)!=list(range(len(relations))):
            raise ValueError('Every bounded relation requires exactly one own typed decision')
        if len({x['output']['candidate'] for x in actions})!=len(actions):
            raise ValueError('Bounded decisions cannot duplicate a candidate')
    if analysis['answer'] is not None or analysis['content_eligible'] or (not bounded and analysis['candidate_analysis']):
        raise ValueError('Own action review must not assert whole-question closure')
    for kind in ('structured', 'content-export', 'student', 'legacy-wechat'):
        render(analysis, kind, registry)
    report={'exam_id': exam, 'question_id': qid, 'method_id': mid,
            'method_version': method['version'], 'primary_role': method['primary_role'],
            'output_role': method['output_type'], 'stage': request['stage'],
            'reviewer': request['reviewer'], 'reviewer_kind': request['reviewer_kind'],
            'mechanical_prediction_sha256': request['mechanical_prediction_sha256'],
            'question': deepcopy(question), 'analysis': analysis, 'semantic_review': deepcopy(semantic),
            'candidate_status': 'pending_independent_case_review', 'case_type': None,
            'registry_updates': 0, 'case_slots_filled': 0,
            'learner_validation': 'pending_real_participant_validation',
            'semantic_certification': 'external_action_review_not_certified',
            'source_rights': 'local_research_only; redistribution_not_verified'}
    if 'supersedes_action_review_sha256' in request:
        if not bounded: raise ValueError('Only explicitly withdrawn bounded actions may be replaced')
        report['supersedes_action_review_sha256']=request['supersedes_action_review_sha256']
    return report


def public_metadata(report):
    # Do not expose reviewer prose, English text, graph, quotes, or option groups.
    result = {k: report[k] for k in ('exam_id', 'question_id', 'method_id', 'method_version',
              'primary_role', 'output_role', 'stage', 'reviewer_kind',
              'mechanical_prediction_sha256', 'candidate_status', 'case_type',
              'registry_updates', 'case_slots_filled', 'learner_validation', 'semantic_certification')}
    result.update({'produced_action_count': len(report['analysis']['execution_trace']),
                   'artifact_kinds': [x['output']['kind'] for x in report['analysis']['execution_trace']],
                   'answer_withheld': report['analysis']['answer'] is None,
                   'whole_question_content_eligible': report['analysis']['content_eligible']})
    if 'supersedes_action_review_sha256' in report:
        result['supersedes_action_review_sha256']=report['supersedes_action_review_sha256']
    return result


def collect(dataset, request_path,revision=None):
    root = Path(dataset).resolve(); path = Path(request_path).resolve()
    if not path.is_relative_to(root / 'action-reviews'):
        raise ValueError('Action requests must stay in private action-reviews directory')
    raw = path.read_bytes(); request = json.loads(raw)
    exam = identifier(request['exam_id'])
    if not path.is_relative_to(root / 'action-reviews' / exam):
        raise ValueError('Action request must stay in its own exam directory')
    # Timing is explicitly after an existing reveal; never label this blind.
    if not list((root / 'results' / exam).glob('reveal*.json')):
        raise ValueError('Post-reveal lane requires existing reveal artifact')
    mechanical_raw = (root / 'predictions' / exam / 'blind.json').read_bytes()
    if request['mechanical_prediction_sha256'] != sha(mechanical_raw):
        raise ValueError('Frozen mechanical prediction binding mismatch')
    report = review_action(request, json.loads(mechanical_raw))
    report['request_sha256'] = sha(raw)
    report['request_artifact'] = path.relative_to(root).as_posix()
    suffix='-'+identifier(revision) if revision else ''
    if 'supersedes_action_review_sha256' in report:
        if not revision: raise ValueError('Replacement must be separately named; never overwrite history')
        check_supersession(root,report)
    elif revision: raise ValueError('Action revision requires explicit withdrawn predecessor')
    output = root / 'action-reviews' / exam / (report['method_id'] + '-' + report['question_id'] + suffix + '.review.json')
    if 'supersedes_action_review_sha256' in report:
        for prior_path in (root/'action-reviews'/exam).glob('*.review.json'):
            prior=json.loads(prior_path.read_bytes())
            if prior_path!=output and prior.get('supersedes_action_review_sha256')==report['supersedes_action_review_sha256']:
                raise ValueError('Predecessor already superseded; withdraw the current review before another revision')
    freeze_json(output, report)
    return public_metadata(report)


def load_metadata(dataset, exam_id):
    root = Path(dataset); exam = identifier(exam_id); results = []; reports=[]
    for path in sorted((root / 'action-reviews' / exam).glob('*.review.json')):
        report = json.loads(path.read_bytes())
        if report['exam_id'] != exam or report['stage'] not in {STAGE,BOUNDED_STAGE}:
            raise ValueError('Wrong action review identity')
        raw = (root / 'predictions' / exam / 'blind.json').read_bytes()
        if report['mechanical_prediction_sha256'] != sha(raw):
            raise ValueError('Action review source binding mismatch')
        request_path = (root / report['request_artifact']).resolve()
        if not request_path.is_relative_to((root / 'action-reviews' / exam).resolve()):
            raise ValueError('Action request binding escapes private review directory')
        request_raw = request_path.read_bytes()
        if sha(request_raw) != report['request_sha256']:
            raise ValueError('Action review request binding mismatch')
        expected = review_action(json.loads(request_raw), json.loads(raw))
        expected.update({'request_sha256': sha(request_raw), 'request_artifact': report['request_artifact']})
        if expected != report:
            raise ValueError('Action replay drift requires explicit regression review')
        reports.append((report,sha(path.read_bytes()),path))
    superseded=set()
    for report,_,_ in reports:
        if 'supersedes_action_review_sha256' in report:
            check_supersession(root,report)
            superseded.add(report['supersedes_action_review_sha256'])
    active=set()
    for report,digest,path in reports:
        if digest in superseded: continue
        identity=(report['question_id'],report['method_id'])
        if identity in active: raise ValueError('Multiple active own action reviews need explicit supersession')
        active.add(identity)
        withdrawal=path.with_name(path.stem+'-withdrawal.json')
        if withdrawal.is_file():
            result=load_withdrawal(root,path)
            metadata=public_metadata(report)
            produced=[x for x in result['analysis']['execution_trace'] if x['state']=='produced']
            metadata.update(produced_action_count=len(produced),artifact_kinds=[x['output']['kind'] for x in produced],
                candidate_status='partially_withdrawn_pending_new_review' if produced else 'withdrawn_pending_new_review',
                withdrawal_applied=True)
            results.append(metadata)
        else: results.append(public_metadata(report))
    return results


def action_withdrawal(dataset,finding_path):
    """Execute a negative finding on an own frozen action, not its old host."""
    root=Path(dataset).resolve(); path=Path(finding_path).resolve()
    if not path.is_relative_to(root/'action-reviews'): raise ValueError('Private action finding required')
    raw=path.read_bytes(); request=json.loads(raw)
    if set(request)!={'exam_id','method_id','source_action_review_sha256','finding'}:
        raise ValueError('Own action withdrawal fields required')
    exam=identifier(request['exam_id']); mid=identifier(request['method_id'])
    if not path.is_relative_to(root/'action-reviews'/exam): raise ValueError('Own exam finding required')
    candidates=[p for p in (root/'action-reviews'/exam).glob('*.review.json')
                if sha(p.read_bytes())==request['source_action_review_sha256']]
    if len(candidates)!=1: raise ValueError('Finding must bind exactly one frozen action review')
    source=candidates[0]; report=json.loads(source.read_bytes())
    if report['exam_id']!=exam or report['method_id']!=mid: raise ValueError('Own action finding identity mismatch')
    # Current requests/sources are checked before withdrawing; no backfit.
    source_request=(root/report['request_artifact']).resolve()
    if not source_request.is_relative_to(root/'action-reviews'/exam): raise ValueError('Source request escape')
    original=source_request.read_bytes()
    mechanical=(root/'predictions'/exam/'blind.json').read_bytes()
    if sha(original)!=report['request_sha256'] or sha(mechanical)!=report['mechanical_prediction_sha256']:
        raise ValueError('Own withdrawal source binding mismatch')
    replay=review_action(json.loads(original),json.loads(mechanical))
    replay.update(request_sha256=sha(original),request_artifact=report['request_artifact'])
    if replay!=report: raise ValueError('Own withdrawal source replay drift')
    out=withdraw_review(report['question'],report['analysis'],request['finding'])
    registry=Registry()
    for kind in ('structured','student','legacy-wechat','content-export'): render(out['analysis'],kind,registry)
    return {'exam_id':exam,'method_id':mid,'stage':'post_reveal_own_action_withdrawal',
        'source_action_review_sha256':sha(source.read_bytes()),'request_sha256':sha(raw),
        'request_artifact':path.relative_to(root).as_posix(),**out,
        'new_blind_prediction':False,'registry_updates':0,'case_slots_filled':0}


def collect_withdrawal(dataset,finding_path):
    result=action_withdrawal(dataset,finding_path)
    root=Path(dataset)
    source=next(p for p in (root/'action-reviews'/result['exam_id']).glob('*.review.json')
                if sha(p.read_bytes())==result['source_action_review_sha256'])
    freeze_json(source.with_name(source.stem+'-withdrawal.json'),result)
    return {k:result[k] for k in ('exam_id','method_id','stage','source_action_review_sha256',
                                'new_blind_prediction','registry_updates','case_slots_filled')}


def load_withdrawal(root,source):
    result=json.loads(source.with_name(source.stem+'-withdrawal.json').read_bytes())
    if result['source_action_review_sha256']!=sha(source.read_bytes()):
        raise ValueError('Withdrawal must belong to this exact source action report')
    request=(Path(root)/result['request_artifact']).resolve()
    if action_withdrawal(root,request)!=result: raise ValueError('Own action withdrawal replay drift')
    return result


def check_supersession(root,report):
    paths=[p for p in (Path(root)/'action-reviews'/report['exam_id']).glob('*.review.json')
           if sha(p.read_bytes())==report['supersedes_action_review_sha256']]
    if len(paths)!=1: raise ValueError('Replacement must bind its exact frozen predecessor')
    parent=json.loads(paths[0].read_bytes())
    if any(parent[k]!=report[k] for k in ('exam_id','question_id','method_id','method_version','mechanical_prediction_sha256')):
        raise ValueError('Replacement cannot change source, question, method or version')
    material_equal(parent['question'],report['question'])
    withdrawn=load_withdrawal(root,paths[0])
    old_ids={x['execution_id'] for x in parent['analysis']['execution_trace']}
    if old_ids!=set(withdrawn['withdrawal']['effective_execution_ids']):
        raise ValueError('Replacement requires explicit withdrawal of every old own action')


def chain_report(dataset, request_path):
    """Compose frozen helper actions with separate passage decisions/verification.

    This is an explicitly post-reveal external review, never a replacement blind
    prediction. Its upstream partitions are immutable and confer no answer truth.
    """
    root=Path(dataset).resolve(); path=Path(request_path).resolve()
    if not path.is_relative_to(root/'chain-reviews'):
        raise ValueError('Chain request must stay in private chain-reviews directory')
    raw=path.read_bytes(); request=json.loads(raw)
    fields={'exam_id','stage','reviewer','reviewer_kind','mechanical_prediction_sha256',
            'upstream_action_review_sha256','question','semantic_review'}
    if set(request)!=fields or request['stage']!='post_reveal_chain_review':
        raise ValueError('Explicit post-reveal chain review required')
    exam=identifier(request['exam_id']); question=request['question']; qid=identifier(question['question_id'])
    if not path.is_relative_to(root/'chain-reviews'/exam):
        raise ValueError('Chain request must stay in its own exam directory')
    if request['reviewer_kind'] not in {'AI','human'} or not isinstance(request['reviewer'],str) or not request['reviewer'].strip() or not isinstance(request['semantic_review'],dict):
        raise ValueError('Chain review needs external reviewer and semantic limits')
    if not list((root/'results'/exam).glob('reveal*.json')):
        raise ValueError('Chain review requires existing reveal artifact')
    mechanical_raw=(root/'predictions'/exam/'blind.json').read_bytes(); mechanical=json.loads(mechanical_raw)
    if mechanical.get('exam_id')!=exam or mechanical.get('pass')!='blind' or request['mechanical_prediction_sha256']!=sha(mechanical_raw):
        raise ValueError('Chain review source binding mismatch')
    originals=[q for q in mechanical['inputs']['questions'] if q['question_id']==qid]
    if len(originals)!=1: raise ValueError('Unknown chain question')
    material_equal(originals[0],question)
    annotations=ANNOTATIONS|{'relations'}
    if {k:v for k,v in originals[0].items() if k not in annotations}!={k:v for k,v in question.items() if k not in annotations}:
        raise ValueError('Chain review changed frozen question fields')
    # This first audited composition uses the existing complete seven-five lane;
    # do not silently expand it to another type or borrow another question's work.
    expected=['F01','F05','F11','F06']
    if question['question_type']!='七选五' or question.get('requested_chain')!=expected:
        raise ValueError('Chain review requires grouping, scope, own decision, verification')
    parent_path=root/'action-reviews'/exam/('F01-'+qid+'.review.json')
    parent_raw=parent_path.read_bytes(); parent=json.loads(parent_raw)
    # Revalidate the original request and engine, not just its recorded output.
    active=load_metadata(root,exam)
    own=[x for x in active if x['question_id']==qid and x['method_id']=='F01']
    if len(own)!=1 or own[0].get('withdrawal_applied') or own[0].get('supersedes_action_review_sha256'):
        raise ValueError('Chain cannot consume withdrawn or superseded original grouping')
    if sha(parent_raw)!=request['upstream_action_review_sha256'] or parent['question_id']!=qid or parent['method_id']!='F01':
        raise ValueError('Chain review upstream binding mismatch')
    parent_actions=parent['question']['action_executions']; actions=question.get('action_executions',[])
    own_groups=[x for x in actions if x['method_id']=='F01']
    if own_groups!=parent_actions or actions[:len(parent_actions)]!=parent_actions:
        raise ValueError('Chain review must preserve frozen grouping actions first')
    parent_triggers=[x for x in parent['question']['observations'] if x['method_id']=='F01']
    if [x for x in question.get('observations',[]) if x['method_id']=='F01']!=parent_triggers:
        raise ValueError('Chain review changed frozen grouping trigger')
    registry=Registry(); analyzer=QuestionAnalyzer(registry)
    semantic=request['semantic_review']
    versions={m:registry.methods[m]['version'] for m in expected}
    if semantic.get('method_chain')!=expected or semantic.get('method_versions')!=versions or not nonempty(semantic.get('scope')):
        raise ValueError('Chain semantic review must bind its own current methods and scope')
    for mid in expected:
        own=semantic.get(mid)
        if not isinstance(own,dict) or own.get('role')!=registry.methods[mid]['primary_role'] or any(not nonempty(own.get(k)) for k in ('action','stop')):
            raise ValueError('Chain review needs each own role, action and stop: '+mid)
    validate_schema('question-input',question); analysis=analyzer.analyze(deepcopy(question))
    validate_schema('question-analysis',analysis)
    validate_graph(analysis['evidence_graph'],question); validate_execution_trace(analysis,registry)
    produced=[x for x in analysis['execution_trace'] if x['state']=='produced']
    if {x['method_id'] for x in produced}!=set(expected):
        raise ValueError('Chain review lacks one own produced stage')
    group_ids={x['execution_id'] for x in parent_actions}
    scopes=[x for x in produced if x['method_id']=='F05' and x['output']['kind']=='interpretation']
    if not scopes or any(not group_ids<=set(x['input_artifact_ids']) for x in scopes):
        raise ValueError('Scope must consume all frozen grouping artifacts')
    scope_ids={x['execution_id'] for x in scopes}
    decisions=[x for x in produced if x['method_id']=='F11' and x['output']['kind']=='candidate_decision']
    if not decisions or any(not scope_ids.intersection(x['input_artifact_ids']) for x in decisions):
        raise ValueError('Decisions need their scope interpretation and own relations')
    if sorted(x['output']['candidate'] for x in decisions)!=sorted(question['options']):
        raise ValueError('Chain decisions must cover every candidate exactly once; legacy relations cannot replace own actions')
    decision_ids={x['execution_id'] for x in decisions}
    checks=[x for x in produced if x['method_id']=='F06' and x['output']['kind']=='verification_result']
    if not checks or any(not set(x['output']['target_execution_ids'])<=decision_ids for x in checks):
        raise ValueError('Backfill must verify own same-candidate decisions')
    for kind in ['structured','content-export','student','legacy-wechat']: render(analysis,kind,registry)
    return {'exam_id':exam,'question_id':qid,'stage':request['stage'],'reviewer_kind':request['reviewer_kind'],
        'reviewer':request['reviewer'],'mechanical_prediction_sha256':sha(mechanical_raw),
        'upstream_action_review_sha256':sha(parent_raw),'request_sha256':sha(raw),
        'request_artifact':path.relative_to(root).as_posix(),'question':deepcopy(question),
        'analysis':analysis,'semantic_review':deepcopy(request['semantic_review']),
        'method_ids':expected,'method_versions':{m:registry.methods[m]['version'] for m in expected},
        'semantic_certification':'external_AI_or_human_review_not_authenticated',
        'learner_validation':'pending_real_participant_validation','registry_updates':0,'case_slots_filled':0}


def chain_metadata(report):
    result={k:report[k] for k in ['exam_id','question_id','stage','reviewer_kind','method_ids','method_versions',
        'mechanical_prediction_sha256','upstream_action_review_sha256','semantic_certification',
        'learner_validation','registry_updates','case_slots_filled']}
    result.update(produced_action_count=sum(x['state']=='produced' for x in report['analysis']['execution_trace']),
        answer_withheld=report['analysis']['answer'] is None,
        structural_closure=report['analysis']['answer_verification']['closed'],
        superseded_artifact_count=0)
    return result


def collect_chain(dataset,request_path,revision=None):
    report=chain_report(dataset,request_path)
    suffix='-'+identifier(revision) if revision else ''
    target=Path(dataset)/'chain-reviews'/report['exam_id']/(report['question_id']+suffix+'.review.json')
    freeze_json(target,report)
    return chain_metadata(report)


def load_chain_metadata(dataset,exam_id):
    root=Path(dataset).resolve(); exam=identifier(exam_id); results=[]; grouped={}
    for path in sorted((root/'chain-reviews'/exam).glob('*.review.json')):
        report=json.loads(path.read_bytes())
        if report['exam_id']!=exam or report['stage']!='post_reveal_chain_review':
            raise ValueError('Wrong chain review identity')
        request=(root/report['request_artifact']).resolve()
        if not request.is_relative_to(root/'chain-reviews'/exam): raise ValueError('Chain request path escape')
        if sha(request.read_bytes())!=report['request_sha256']:
            raise ValueError('Frozen chain review drift: request binding mismatch')
        grouped.setdefault(report['question_id'],[]).append((report,request))
    registry=Registry()
    for reports in grouped.values():
        current=[(r,p) for r,p in reports if r['method_versions']=={
            m:registry.methods[m]['version'] for m in r['method_ids']}]
        if len(current)!=1:
            raise ValueError('Exactly one current chain review required; preserve history and explicitly re-review version drift')
        report,request=current[0]
        if chain_report(root,request)!=report: raise ValueError('Frozen chain review drift requires explicit audit')
        metadata=chain_metadata(report); metadata['superseded_artifact_count']=len(reports)-1
        results.append(metadata)
    return results


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('request')
    parser.add_argument('--chain',action='store_true',help='post-reveal composition of frozen helper actions')
    parser.add_argument('--revision',help='explicit immutable revision suffix; own actions also require a withdrawn predecessor')
    parser.add_argument('--withdraw-action',action='store_true',help='apply bound negative finding to an own action review')
    parser.add_argument('--dataset', default=str(ROOT / 'local-data/exams-2020-2025'))
    args = parser.parse_args()
    if args.withdraw_action and (args.chain or args.revision): parser.error('withdrawal cannot also collect a revision')
    result=collect_withdrawal(args.dataset,args.request) if args.withdraw_action else (
        collect_chain(args.dataset,args.request,args.revision) if args.chain else collect(args.dataset,args.request,args.revision))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
