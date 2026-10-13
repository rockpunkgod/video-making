"""Export private, answer-free first-use materials; do not manufacture results.

Inputs are two existing question artifacts and an explicitly authored demonstration.
Historical artifacts supply immutable question text only, not current evaluation credit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from core.registry import ROOT, Registry
from scripts.audit_student_entries import PRIORITY

FIELDS = ('question_id','question_type','task_type','stem','passage','options',
          'given_word','hint_word','student_draft','continuation_starters')


def question_fingerprint(question):
    return hashlib.sha256(json.dumps(question,ensure_ascii=False,sort_keys=True,
                                     separators=(',',':')).encode('utf-8')).hexdigest()


def teaching_fingerprint(method):
    fields={key:method[key] for key in (
        'method_id','version','brand_name','student_symptoms','four_step_card',
        'primary_role','output_type','section_ids')}
    if method['method_id']=='G01':
        fields['visual_formula']=method['visual_formula']
    return question_fingerprint(fields)


def read_question(path, question_id=None):
    path = Path(path).resolve()
    data = path.read_bytes()
    artifact = json.loads(data)
    if not isinstance(artifact,dict):
        raise ValueError('An existing structured question is required')
    if question_id is not None:
        inputs=artifact.get('inputs')
        questions=inputs.get('questions') if isinstance(inputs,dict) else None
        if not isinstance(questions,list):
            raise ValueError('Question selection requires existing frozen paper inputs')
        matches=[q for q in questions if isinstance(q,dict) and q.get('question_id')==question_id]
        if len(matches)!=1:
            raise ValueError('Original question ID is missing or duplicated in paper inputs')
        raw=matches[0]
    else:
        raw = artifact.get('question', artifact)
    if not isinstance(raw, dict):
        raise ValueError('An existing structured question is required')
    question = {key: raw[key] for key in FIELDS if key in raw}
    if not all(isinstance(question.get(key),str) and question[key].strip()
               for key in ('question_id','question_type','stem','passage')):
        raise ValueError('Incomplete question text; do not fill missing source material')
    return question, {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
                      'question_sha256':question_fingerprint(question),
                      'question_selector':question_id,
                      'question_text_only': True, 'historical_review_reused': False}


def check_choices(question):
    expected = {'七选五':set('ABCDEFG'),'阅读理解':set('ABCD')}.get(question['question_type'])
    if expected is not None:
        options = question.get('options')
        if (not isinstance(options,dict) or set(options)!=expected or
                any(not isinstance(value,str) or not value.strip() for value in options.values())):
            raise ValueError('Incomplete or invalid original choice set; do not invent missing options')


def grammar_hint(question):
    keys=[key for key in ('given_word','hint_word') if key in question]
    if not keys:
        raise ValueError('Missing explicit hint state for this grammar blank')
    if any(question[key] is not None and not isinstance(question[key],str) for key in keys):
        raise ValueError('Grammar hint must be text or explicit null')
    values=[(question[key] or '').strip() for key in keys]
    if len(set(values))!=1:
        raise ValueError('Conflicting original grammar hint fields')
    return values[0] or None


def render_question(question):
    parts = [question['passage'], question['stem']]
    if question.get('options'):
        parts += [value if re.match(r'^\s*'+re.escape(key)+r'[.．、]',value)
                  else f'{key}. {value}' for key, value in question['options'].items()]
    if question['question_type']=='语法填空':
        hint=grammar_hint(question)
        parts.append('本空提示词：'+hint if hint else '本空无提示词。')
    if question.get('student_draft'):
        parts.append(question['student_draft'])
    if question.get('continuation_starters'):
        parts += question['continuation_starters']
    return '\n\n'.join(parts)


def prepare(method_id, demonstration_path, transfer_path, walkthrough_path, output, registry=None,
            demonstration_id=None, transfer_id=None):
    registry = registry or Registry()
    registry.validate()
    if registry.is_historical or method_id not in PRIORITY:
        raise ValueError('Use the current Registry and one priority method')
    method = registry.methods[method_id]
    demo, demo_ref = read_question(demonstration_path,demonstration_id)
    transfer, transfer_ref = read_question(transfer_path,transfer_id)
    if demo['question_type'] != method['question_type'] or transfer['question_type'] != method['question_type']:
        raise ValueError('Question type does not match the teaching method')
    check_choices(demo); check_choices(transfer)
    if method_id=='G01':
        grammar_hint(demo); grammar_hint(transfer)
    identity = lambda question: {key: value for key, value in question.items() if key!='question_id'}
    if demo['question_id']==transfer['question_id'] or identity(demo)==identity(transfer):
        raise ValueError('The second task must use different original question material')
    if demo['passage'].strip()==transfer['passage'].strip():
        raise ValueError('A different passage is required for the unfamiliar transfer task')
    walkthrough_path = Path(walkthrough_path).resolve()
    walkthrough_bytes = walkthrough_path.read_bytes()
    walkthrough = json.loads(walkthrough_bytes)
    if (walkthrough.get('method_id')!=method_id or walkthrough.get('method_version')!=method['version']
            or walkthrough.get('source_commit')!=registry.index['source_baseline']['commit']
            or walkthrough.get('question_id')!=demo['question_id']
            or walkthrough.get('demonstration_question_sha256')!=question_fingerprint(demo)):
        raise ValueError('Demonstration must bind the current method, source and exact example')
    if not all(isinstance(walkthrough.get(key),str) and walkthrough[key].strip()
               for key in ('first_action','evidence','output','stop')):
        raise ValueError('Demonstration requires explicit action, evidence, output and stop')
    if walkthrough.get('review_scope')!='ai_authored_draft_not_learner_validation':
        raise ValueError('Do not claim independent or learner acceptance for this draft')
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT/'local-data').resolve()):
        raise ValueError('Real question materials must remain in private local-data')
    if output.exists():
        raise ValueError('Refuse to overwrite a frozen or existing study kit')
    card = method['four_step_card']
    learner = '\n\n'.join([
        '# '+method['brand_name'],
        '你可能遇到：'+method['student_symptoms'][0],
        '什么时候启动：'+card['start'], '第一刀：'+card['first_cut'],
        '怎么判：'+card['judge'], '什么时候停：'+card['stop'],
        *(['```text\n'+method['visual_formula']+'\n```'] if method_id=='G01' else []),
        '## 示范题', render_question(demo),
        '先做：'+walkthrough['first_action'], '看到的证据：'+walkthrough['evidence'],
        '只得到：'+walkthrough['output'], '这里要刹车：'+walkthrough['stop'],
        '## 第二道题', render_question(transfer),
        '先不要报答案。'+method['challenge_prompt'],
        '再说明是否该启动，你看的词句是什么，动作得到什么、还缺什么，以及是否需要停。',
    ])+'\n'
    # Evaluation prompts do not reveal any expected groups, answers or evidence.
    facilitator = {
        'method_id': method_id, 'method_version': method['version'],
        'source_commit': registry.index['source_baseline']['commit'],
        'teaching_card_sha256':teaching_fingerprint(method),
        'status': 'draft_materials_not_study_approval',
        'review_scope': walkthrough['review_scope'],
        'question_ids': [demo['question_id'],transfer['question_id']],
        'origin': 'existing_real_question_artifacts_not_new_cases',
        'source_refs': [demo_ref,transfer_ref,{'path':str(walkthrough_path),
                        'sha256':hashlib.sha256(walkthrough_bytes).hexdigest()}],
        'prior_exposure': 'must_check_with_each_participant_before_collection',
        'study_order': 'communication_then_freeze_then_practicality_then_first_use',
        'collection_allowed': False,
        'required_before_collection': [
            'independent current-source review of demonstration and transfer scoring evidence',
            'communication acceptance and frozen teaching version',
            'practicality gate, participant unfamiliarity check and frozen study plan',
        ],
        'first_use_test': dict.fromkeys(('trigger_success','action_success','evidence_success',
                           'stop_rule_success','no_answer_backfit','final_result','failure_type')),
        'learner_validation': 'pending_real_participant_validation',
        'new_case_count': 0, 'new_blind_sample_count': 0,
    }
    output.mkdir(parents=True)
    (output/'student-material.md').write_text(learner,encoding='utf-8')
    facilitator['student_material_sha256']=hashlib.sha256((output/'student-material.md').read_bytes()).hexdigest()
    (output/'facilitator.json').write_text(json.dumps(facilitator,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'method_id':method_id,'output':str(output),'status':facilitator['status'],
            'new_case_count':0,'new_blind_sample_count':0,'collection_allowed':False}


def verify(output, registry=None):
    """Check current bindings, not authenticity, teaching validity or study approval."""
    registry=registry or Registry()
    registry.validate()
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'local-data').resolve()):
        raise ValueError('Real question materials must remain in private local-data')
    meta=json.loads((output/'facilitator.json').read_text(encoding='utf-8'))
    method=registry.methods.get(meta.get('method_id'))
    if (registry.is_historical or method is None or
            meta.get('method_version')!=method['version'] or
            meta.get('source_commit')!=registry.index['source_baseline']['commit'] or
            meta.get('teaching_card_sha256')!=teaching_fingerprint(method)):
        raise ValueError('Study kit teaching card is stale or not current-bound')
    if (meta.get('status')!='draft_materials_not_study_approval' or
            meta.get('collection_allowed') is not False or
            meta.get('new_case_count')!=0 or meta.get('new_blind_sample_count')!=0 or
            not isinstance(meta.get('first_use_test'),dict) or
            any(value is not None for value in meta['first_use_test'].values())):
        raise ValueError('A material draft cannot claim study approval or observations')
    material=(output/'student-material.md').read_bytes()
    if hashlib.sha256(material).hexdigest()!=meta.get('student_material_sha256'):
        raise ValueError('Student material changed after export')
    refs=meta.get('source_refs',[])
    if len(refs)!=3:
        raise ValueError('Missing original question or walkthrough bindings')
    for ref in refs:
        if hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()!=ref['sha256']:
            raise ValueError('Original source artifact changed after export')
    bound_question_ids=[]
    for ref in refs[:2]:
        question,_=read_question(ref['path'],ref.get('question_selector'))
        if question_fingerprint(question)!=ref.get('question_sha256'):
            raise ValueError('Original question binding mismatch')
        bound_question_ids.append(question['question_id'])
    if bound_question_ids!=meta.get('question_ids'):
        raise ValueError('Study question IDs do not match selected source questions')
    return {'method_id':method['method_id'],'binding_check':'PASS',
            'status':'draft_materials_not_study_approval','collection_allowed':False,
            'scope':'consistency only; not semantic, source authenticity or learner acceptance'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',type=Path)
    parser.add_argument('--method',choices=PRIORITY)
    parser.add_argument('--demonstration',type=Path)
    parser.add_argument('--demonstration-id')
    parser.add_argument('--transfer',type=Path)
    parser.add_argument('--transfer-id')
    parser.add_argument('--walkthrough',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.verify:
        if any((args.method,args.demonstration,args.demonstration_id,args.transfer,args.transfer_id,args.walkthrough,args.output)):
            parser.error('--verify cannot be combined with export arguments')
        result=verify(args.verify)
    else:
        if not all((args.method,args.demonstration,args.transfer,args.walkthrough,args.output)):
            parser.error('Export requires --method, --demonstration, --transfer, --walkthrough and --output')
        result=prepare(args.method,args.demonstration,args.transfer,args.walkthrough,args.output,
                       demonstration_id=args.demonstration_id,transfer_id=args.transfer_id)
    print(json.dumps(result,ensure_ascii=False))
