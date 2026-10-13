"""Export private, answer-free first-use materials; do not manufacture results.

Inputs are two existing question artifacts and an explicitly authored demonstration.
Historical artifacts supply immutable question text only, not current evaluation credit.
"""
import argparse
import hashlib
import json
from pathlib import Path

from core.registry import ROOT, Registry
from scripts.audit_student_entries import PRIORITY

FIELDS = ('question_id','question_type','task_type','stem','passage','options',
          'hint_word','student_draft','continuation_starters')


def read_question(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    artifact = json.loads(data)
    raw = artifact.get('question', artifact)
    if not isinstance(raw, dict):
        raise ValueError('An existing structured question is required')
    question = {key: raw[key] for key in FIELDS if key in raw}
    if not all(question.get(key) for key in ('question_id','question_type','stem','passage')):
        raise ValueError('Incomplete question text; do not fill missing source material')
    return question, {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
                      'question_text_only': True, 'historical_review_reused': False}


def render_question(question):
    parts = [question['passage'], question['stem']]
    if question.get('options'):
        parts += [f'{key}. {value}' for key, value in question['options'].items()]
    if question.get('hint_word'):
        parts.append('提示词：'+question['hint_word'])
    if question.get('student_draft'):
        parts.append(question['student_draft'])
    if question.get('continuation_starters'):
        parts += question['continuation_starters']
    return '\n\n'.join(parts)


def prepare(method_id, demonstration_path, transfer_path, walkthrough_path, output, registry=None):
    registry = registry or Registry()
    registry.validate()
    if registry.is_historical or method_id not in PRIORITY:
        raise ValueError('Use the current Registry and one priority method')
    method = registry.methods[method_id]
    demo, demo_ref = read_question(demonstration_path)
    transfer, transfer_ref = read_question(transfer_path)
    if demo['question_type'] != method['question_type'] or transfer['question_type'] != method['question_type']:
        raise ValueError('Question type does not match the teaching method')
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
            or walkthrough.get('question_id')!=demo['question_id']):
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
        '## 示范题', render_question(demo),
        '先做：'+walkthrough['first_action'], '看到的证据：'+walkthrough['evidence'],
        '只得到：'+walkthrough['output'], '这里要刹车：'+walkthrough['stop'],
        '## 第二道题', render_question(transfer),
        '先不要报答案。判断是否该启动，写出第一刀和你看的词句；说明得到什么、还缺什么，以及是否需要停。',
    ])+'\n'
    # Evaluation prompts do not reveal any expected groups, answers or evidence.
    facilitator = {
        'method_id': method_id, 'method_version': method['version'],
        'source_commit': registry.index['source_baseline']['commit'],
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
    (output/'facilitator.json').write_text(json.dumps(facilitator,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'method_id':method_id,'output':str(output),'status':facilitator['status'],
            'new_case_count':0,'new_blind_sample_count':0,'collection_allowed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method',required=True,choices=PRIORITY)
    parser.add_argument('--demonstration',required=True,type=Path)
    parser.add_argument('--transfer',required=True,type=Path)
    parser.add_argument('--walkthrough',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare(args.method,args.demonstration,args.transfer,args.walkthrough,args.output),ensure_ascii=False))
