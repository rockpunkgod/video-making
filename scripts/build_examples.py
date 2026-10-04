"""Runnable course examples and explicitly synthetic harness fixtures, never fake exams."""
import json
import subprocess
from pathlib import Path
from core.registry import ROOT,Registry,load
from evaluation.harness import evaluate

def write(relative,obj):
    p=ROOT/relative; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def build():
    raw=load('cases/G01/canonical/case.yaml')['question']
    q={'question_id':'course-protect','question_type':'语法填空','task_type':'word_form','stem':raw,'given_word':'protect','student_symptoms':['有提示词不知道怎么变']}
    write('examples/question-course.json',q)
    evidence={'field':'stem','start':0,'end':len(raw),'quote':raw}
    reviewed={**q,'observations':[{'method_id':'G09','evidence':[evidence],'reviewed':True}],'relations':[{'method_id':'G09','candidate':'protection','effect':'retain','claim':'environmental 修饰宾语中心，空位需要名词','evidence':[evidence],'decision_rule_check':'名词性宾语中心与形容词修饰位置均成立','stop_rule_check':'提示动词不代表动词位置，停用谓语/非谓语分支','verification':'回填 environmental protection，核 promote 宾语与派生形式','reviewer':'engineering-course-fixture-not-participant','review_status':'reviewed'}]}
    write('examples/question-reviewed-course.json',reviewed)
    write('examples/paper-course.json',{'paper_id':'course-excerpts-not-complete-exam','questions':[q,{**reviewed,'question_id':'course-protect-reviewed'}]})
    # Synthetic RECORDS only; no invented exam text is passed off as a course case.
    rows=[]
    kinds=['positive_trigger','negative_trigger','counterexample','boundary','transfer']
    for v in ['10s','30s','90s']:
        for i,kind in enumerate(kinds):
            positive=kind in {'positive_trigger','transfer'}; stop=kind in {'counterexample','boundary'}
            measure={'accuracy':True,'time_seconds':20,'candidates_remaining':2,'evidence_span':3,'hesitation_count':1,'unresolved':False}
            rows.append({'record_id':v+'-'+kind,'participant_id':'synthetic-'+v,'method_id':'R01','method_version':'1.1.0','question_id':'synthetic-contract-'+str(i),'dataset_id':'synthetic-contract-only','origin':'synthetic','phase':'blind','compact_version':v,'case_type':kind,'applicable':positive,'triggered':positive,'action_success':True,'evidence_success':True,'stop_required':stop,'stopped':stop,'boundary_detected':stop,'observed_first_action':'synthetic 程序分支记录','observed_evidence':'synthetic 程序分支记录','stop_rule_observation':'synthetic 程序分支记录','participant_restatement':'synthetic，不是学生原话','notes':'程序契约测试，不是真题、参与者或实效结果','resolved':positive,'standalone':positive,'assisted':False,'role_overclaim':False,'answer_backfit':False,'execution_breakdown':False,'recall_success':True,'natural_restatement':True,'baseline':measure,'method':dict(measure),'communication_freeze_id':'synthetic-not-study','assignment':'uncontrolled','evaluator_id':'synthetic-fixture'})
    for row in rows:
        row.update(declared_primary_role='decider',observed_actual_role='decider')
    write('evaluation/datasets/synthetic-observations.json',rows)
    write('evaluation/datasets/real-observations.pending.json',[])
    write('evaluation/results/synthetic-contract-result.json',evaluate(rows))
    write('evaluation/results/real-validation.pending.json',evaluate([]))
    write('evaluation/plan.example.json',{'method_id':'R01','method_version':'1.1.0','dataset_id':'REPLACE_WITH_FROZEN_DATASET','communication_freeze_id':'REPLACE_WITH_COMMUNICATION_FREEZE','minimum_participants_per_version':10,'max_false_trigger_delta':0.02,'min_boundary_accuracy':0.95,'max_boundary_drop':0.02,'max_stop_failure_delta':0.02,'min_recall_rate':0.9,'min_restatement_rate':0.9,'minimum_efficiency_gain':{'time_seconds':3,'candidates_remaining':1,'evidence_span':1,'hesitation_count':1,'unresolved':0.05},'frozen_before_data_collection':False,'rationale':'示例阈值不是通用门槛，须按误用风险、样本与效应量制定并在采集前冻结；本模板默认不可用于发布。'})
    # Resolve existing short case references against frozen source text, not invented prose.
    p=ROOT/'provenance/case-source-excerpts.json'
    if True:
        records=json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
        for corpus in ['24c4e1bcbc7f','ce31f1ee2a89','0957ffbfe1d4']:
            sourcepath='kaiming-english-qa/references/corpus/'+corpus+'.txt'
            if any(x['path']==sourcepath for x in records): continue
            result=subprocess.run(['git','-C',str(ROOT.parent/'ANSWER-readonly'),'show','b04ebc26:'+sourcepath],capture_output=True,encoding='utf-8',check=True)
            lines=result.stdout.splitlines()
            selected=lines[:108] if corpus=='24c4e1bcbc7f' else lines[:94] if corpus=='ce31f1ee2a89' else [line for line in lines if 'exhibition' in line or '【PDF第6页】' in line]
            records.append({'path':sourcepath,'commit':'b04ebc26d7fa096404111a0bb12f6c77cc8525b9','scope':'existing case source extract, includes OCR/filled-key text; NOT analyzer input','lines':selected})
        write('provenance/case-source-excerpts.json',records)

if __name__=='__main__': build()
