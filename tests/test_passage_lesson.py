"""Whole-passage structure fixtures, not real exams or learner results."""
from copy import deepcopy
import json
import unittest
from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from core.passage_lesson import PassageLessonAnalyzer,validate_order
from renderers.passage import render_passage
from test_lesson_feedback import fixture as single_fixture

def seven_question(registry):
    q=single_fixture(registry); s=q['observations'][0]['evidence'][0]
    q.update(question_type='七选五',options={c:'program-only option '+c for c in 'ABCDEFG'},requested_chain=['F01','F11'],observations=[{'method_id':m,'reviewed':True,'evidence':[s]} for m in ['F01','F11']])
    q['relations']=[{**deepcopy(q['relations'][0]),'method_id':'F11','candidate':c,'effect':'retain' if c=='A' else 'eliminate'} for c in 'ABCDEFG']
    source=[next(sid for sid in registry.methods[m]['section_ids'] if registry.sources['sections'][sid]['path']=='gaokao-english/references/seven-five.md') for m in ['F01','F11']]
    review=q['lesson_review']; review.update(question_type='七选五',source_section_ids=list(dict.fromkeys([review['source_section_ids'][0]]+source)))
    def segment(i,mid,function,text,refs=None): return {'segment_id':str(i),'method_id':mid,'function':function,'text':text,'evidence':[s],'relation_indices':refs or []}
    review['segments']=[segment(0,'F01','action','先用选项三分，先分组，再拼回去。'),segment(1,'F01','evidence','回到alpha beta gamma核本空的内容。'),segment(2,'F01','stop','分组不能定案。'),segment(3,'F11','action','再用正文闭环核本空关系。')]
    review['segments'] += [segment(i+4,'F11','comparison',c+'回到alpha beta gamma，核这个候选的决定性关系。',[i]) for i,c in enumerate('ABCDEFG')]
    review['segments'].append(segment(20,'F11','stop','本空关系不足就先停，不能只看剩余项。'))
    q['action_executions']=[{'execution_id':axis,'method_id':'F01','method_version':'1.1.0','role':'reducer','input_artifact_ids':[],'concrete_action':'program-only grouping','evidence':[s],'decision_rule_check':'program partition','stop_rule_check':'program reduce only','stop_applied':False,'reviewer':'synthetic-program-fixture','review_status':'reviewed','output':{'kind':'candidate_partition','axis':axis,'groups':[{'label':'没有可观察区别','candidates':list('ABCDEFG')}]}} for axis in ['sentence','actor','time']]
    return q


def packet(registry):
    questions=[]
    for number,task in [(31,'detail'),(32,'vocabulary'),(33,'main_idea')]:
        q=single_fixture(registry); q.update(question_id='program-'+str(number),task_type=task)
        questions.append({'number':number,'question':q})
    sid=next(s for s,v in registry.sources['sections'].items() if v['path']=='gaokao-english/references/delivery-contract.md' and v['heading']=='做题顺序')
    s=questions[0]['question']['observations'][0]['evidence'][0]
    return {'lesson_id':'synthetic-program-whole-passage-not-real-exam','question_type':'阅读理解','passage':'alpha beta gamma','material_complete':True,'questions':questions,
            'review':{'reviewer':'synthetic-program-fixture-not-participant','review_status':'reviewed','source_section_ids':[sid],'reading_mode':'central_task','steps':[{'question_id':'program-'+str(n),'pass':1,'outcome':'solved','transition':'先回到alpha beta gamma，核第'+str(n)+'题本身的任务和关系。','evidence':[s],'execution_ids':[]} for n in [33,31,32]]}}


class PassageLessonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.a=PassageLessonAnalyzer(QuestionAnalyzer(cls.r))

    def test_central_task_order_and_original_number_summary_are_separate(self):
        out=self.a.analyze(packet(self.r)); self.assertEqual(out['scope'],'whole_passage_delivery')
        body=render_passage(out,'legacy-wechat',self.r)
        self.assertEqual(body.count('同学'),1)
        self.assertLess(body.index('核第33题'),body.index('核第31题')); self.assertLess(body.index('核第31题'),body.index('核第32题'))
        self.assertTrue(body.endswith('最后按原题号汇总，第31题选A，第32题选A，第33题选A。'))
        self.assertIn('先把全文中心任务的题做掉',body); self.assertIn('猜词放最后',body)
        self.assertNotIn('最后这一题',body); self.assertNotIn('外部审阅',body)
        self.assertEqual(json.loads(render_passage(out,'content-export',self.r)),out)

    def test_original_order_mode_is_not_inferred_from_passage_letter(self):
        p=packet(self.r); p['review']['reading_mode']='original_order'; p['review']['steps'].sort(key=lambda s:s['question_id'])
        self.assertEqual(self.a.analyze(p)['scope'],'whole_passage_delivery')
        p['review']['reading_mode']='central_task'
        with self.assertRaisesRegex(ValueError,'course task order'): self.a.analyze(p)

    def test_missing_material_or_one_own_lesson_withholds_whole_message(self):
        for missing in ['material','lesson','review']:
            p=packet(self.r)
            if missing=='material': p['material_complete']=False
            elif missing=='lesson': p['questions'][1]['question'].pop('lesson_review')
            else: p['review']['review_status']='unreviewed'
            out=self.a.analyze(p); self.assertEqual(out['scope'],'partial_delivery'); self.assertEqual(out['answer_summary'],[]); self.assertEqual(out['review']['steps'],[])
            self.assertNotIn('第31题选A',render_passage(out,'student',self.r))

    def test_duplicate_numbers_cross_type_and_foreign_passage_rejected(self):
        for change in ['number','type','passage']:
            p=packet(self.r)
            if change=='number': p['questions'][1]['number']=31
            elif change=='type': p['questions'][1]['question']['question_type']='七选五'
            else: p['questions'][1]['question']['passage']='different program text'
            with self.subTest(change=change),self.assertRaises(ValueError): self.a.analyze(p)

    def test_missing_step_unknown_task_and_unquoted_order_reason_rejected(self):
        for change in ['step','task','reason','source']:
            p=packet(self.r)
            if change=='step': p['review']['steps'].pop()
            elif change=='task': p['questions'][0]['question']['task_type']='unknown'
            elif change=='reason': p['review']['steps'][0]['transition']='这题最简单，先做它。'
            else: p['review']['source_section_ids']=self.r.methods['R01']['section_ids'][:1]
            with self.subTest(change=change),self.assertRaises(ValueError): self.a.analyze(p)

    def test_projection_rechecks_order_answer_and_source_span(self):
        out=self.a.analyze(packet(self.r))
        for change in ['order','summary','source','scope']:
            bad=deepcopy(out)
            if change=='order': bad['review']['steps'].reverse()
            elif change=='summary': bad['answer_summary'][0]['answer']='B'
            elif change=='source': bad['questions'][0]['question']['passage']='foreign text'
            else: bad['scope']='partial_delivery'
            with self.subTest(change=change),self.assertRaises(ValueError): render_passage(bad,'legacy-wechat',self.r)

    def test_grammar_no_hint_then_hint_each_in_original_order(self):
        # Metadata branch test only, not English questions or learner records.
        items={str(n):{'number':n,'question':{'question_id':str(n),'stem':'program','given_word':hint}} for n,hint in [(41,'x'),(42,None),(43,'y'),(44,None)]}
        s={'field':'stem','start':0,'end':7,'quote':'program'}
        review={'reading_mode':None,'steps':[{'question_id':str(n),'pass':1,'outcome':'solved','transition':'先核program的当前空位。','evidence':[s],'execution_ids':[]} for n in [42,44,41,43]]}
        analyses={qid:{'execution_trace':[]} for qid in items}
        validate_order('语法填空',items,review,analyses)
        review['steps'][0],review['steps'][1]=review['steps'][1],review['steps'][0]
        with self.assertRaisesRegex(ValueError,'course task order'): validate_order('语法填空',items,review,analyses)
        items['42']['question'].pop('given_word')
        with self.assertRaisesRegex(ValueError,'explicit hint'): validate_order('语法填空',items,review,analyses)

    def test_cloze_two_passes_need_observed_stop_and_exact_recovery(self):
        items={str(n):{'number':n,'question':{'question_id':str(n),'stem':'program'}} for n in [21,22,23]}
        s={'field':'stem','start':0,'end':7,'quote':'program'}
        def step(n,p,outcome): return {'question_id':str(n),'pass':p,'outcome':outcome,'transition':'回到program，先暂留再核本空证据。','evidence':[s],'execution_ids':['stop'] if outcome=='deferred' else []}
        review={'reading_mode':None,'steps':[step(21,1,'deferred'),step(22,1,'solved'),step(23,1,'deferred'),step(21,2,'solved'),step(23,2,'solved')]}
        analyses={qid:{'execution_trace':[{'execution_id':'stop','state':'stopped'}]} for qid in items}
        validate_order('完形填空',items,review,analyses)
        for change in ['recovery','interleave','stop']:
            bad=deepcopy(review); a=deepcopy(analyses)
            if change=='recovery': bad['steps'][-2:]=list(reversed(bad['steps'][-2:]))
            elif change=='interleave': bad['steps'][1],bad['steps'][3]=bad['steps'][3],bad['steps'][1]
            else: a['21']['execution_trace'][0]['state']='produced'
            with self.subTest(change=change),self.assertRaises(ValueError): validate_order('完形填空',items,bad,a)

    def test_whole_seven_grouping_precedes_breakthrough_and_is_never_rebuilt(self):
        p=packet(self.r); p['question_type']='七选五'; p['review']['reading_mode']=None; p['questions']=[]
        for number in [36,37]:
            q=seven_question(self.r); q['question_id']='program-'+str(number); p['questions'].append({'number':number,'question':q})
        s=p['questions'][0]['question']['observations'][0]['evidence'][0]
        p['review']['steps']=[{'question_id':'program-'+str(n),'pass':1,'outcome':'solved','transition':'从alpha beta gamma的本空关系找第'+str(n)+'题的突破口。','evidence':[s],'execution_ids':[]} for n in [37,36]]
        out=self.a.analyze(p); body=render_passage(out,'legacy-wechat',self.r)
        for name in ['句型','主角','时间']: self.assertEqual(body.count('按'+name+'先分'),1)
        self.assertLess(body.index('按时间先分'),body.index('第37题的突破口'))
        self.assertTrue(body.endswith('最后按原题号汇总，第36题选A，第37题选A。'))
        p['questions'][1]['question']['action_executions'][0]['output']['groups'][0]['label']='重新编组'
        with self.assertRaisesRegex(ValueError,'cannot be rebuilt'): self.a.analyze(p)

    def test_cloze_whole_message_does_not_deliver_deferred_answer_early(self):
        p=packet(self.r); p['question_type']='完形填空'; p['review']['reading_mode']=None; p['questions']=p['questions'][:2]
        source=next(sid for sid in self.r.methods['C01']['section_ids'] if self.r.sources['sections'][sid]['path']=='gaokao-english/references/cloze.md')
        for row in p['questions']:
            q=row['question']; q.update(question_type='完形填空',requested_chain=['C01'])
            q['observations'][0]['method_id']='C01'
            for rel in q['relations']: rel.update(method_id='C01',execution_role='decider')
            q['lesson_review'].update(question_type='完形填空',source_section_ids=[q['lesson_review']['source_section_ids'][0],source])
            for seg in q['lesson_review']['segments']: seg.update(method_id='C01',text=seg['text'].replace('选项加戏','语篇线索链'))
        s=p['questions'][0]['question']['observations'][0]['evidence'][0]
        p['questions'][0]['question']['action_executions']=[{'execution_id':'stop','method_id':'C01','method_version':'1.1.0','role':'framework','input_artifact_ids':[],'concrete_action':'program-only first pass stopped action','evidence':[s],'decision_rule_check':'program first-pass gap','stop_rule_check':'program gap observed','stop_applied':True,'reviewer':'synthetic-program-fixture','review_status':'reviewed','output':None}]
        def step(n,pass_no,outcome,text,refs=None): return {'question_id':'program-'+str(n),'pass':pass_no,'outcome':outcome,'transition':text,'evidence':[s],'execution_ids':refs or []}
        p['review']['steps']=[step(31,1,'deferred','第31题回到alpha beta gamma还不足，先留着。',['stop']),step(32,1,'solved','先核第32题的alpha beta gamma关系。'),step(31,2,'solved','再回到第31题的alpha beta gamma，核本空回收依据。')]
        body=render_passage(self.a.analyze(p),'legacy-wechat',self.r)
        self.assertLess(body.index('先留着'),body.index('先核第32题')); self.assertLess(body.index('先核第32题'),body.index('再回到第31题'))
        self.assertNotIn('第31题选A',body[:body.index('最后按原题号')])

    def test_partial_diagnostic_identifies_exact_unfinished_question(self):
        p=packet(self.r); p['questions'][1]['question'].pop('lesson_review')
        out=self.a.analyze(p); self.assertEqual(out['incomplete_question_ids'],['program-32'])
        self.assertIn('第32题',render_passage(out,'student',self.r))


if __name__=='__main__': unittest.main()
