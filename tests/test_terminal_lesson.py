"""Synthetic transport controls; not student comprehension or English trials."""
from copy import deepcopy
import json
import unittest
from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from core.lesson_feedback import DELIVERY_PATH
from core.question_verification import material_fingerprint
from core.passage_lesson import PassageLessonAnalyzer
from renderers import render
from renderers.passage import render_passage
from tests import test_question_verification as question_fixture
from tests.test_execution import action


class TerminalLessonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=Registry(); cls.engine=QuestionAnalyzer(cls.registry)

    def question(self):
        factory=question_fixture.QuestionVerificationTests(); factory.registry=self.registry
        q=factory.question(); span=q['observations'][0]['evidence'][0]
        delivery=next(sid for sid,s in self.registry.sources['sections'].items() if s['path']==DELIVERY_PATH)
        def method_segment(sid,function,text):
            return {'segment_id':sid,'method_id':'R03','function':function,'text':text,'evidence':[span],'relation_indices':[]}
        q['lesson_review']={'schema_version':'1.1.0','question_type':'阅读理解','reviewer':'synthetic-transport-reviewer',
            'review_status':'reviewed','source_section_ids':[delivery,*self.registry.methods['R03']['section_ids']],
            'segments':[method_segment('action','action','这里先用同源替换，圈出当前对象与要解释的完整表达，再比真实语境。'),
                        method_segment('evidence','evidence','先读alpha beta gamma，这里形成的是语境解释，还不能只凭对应词选答案。'),
                        {'segment_id':'terminal','segment_scope':'whole_question','function':'comparison',
                         'terminal_review_id':q['question_verification_review']['review_id'],
                         'candidate_ids':['A','B','C'],'evidence':[span],
                         'text':'再把A和B及C的完整含义分别放回alpha beta gamma，A得到正向依据，B和C各有不合的内容，才能核清整题。'},
                        method_segment('stop','stop','如果候选含义仍不能区分，就停在语境缺口，不由剩余项自动选。')]}
        return q

    def test_plain_lesson_connects_actual_interpretation_to_non_branded_terminal(self):
        q=self.question(); result=self.engine.analyze(q)
        self.assertEqual(result['lesson_feedback']['scope'],'single_question_lesson')
        self.assertEqual(result['candidate_analysis'],[])
        self.assertEqual(result['method_chain'][0]['role'],'interpreter')
        for mode in ('student','legacy-wechat'):
            text=render(result,mode,self.registry)
            self.assertTrue(text.startswith('同学，我们来分析一下。'))
            self.assertTrue(text.endswith('最后这一题选A。'))
            self.assertEqual(text.count('同学'),1)
            for word in ('审阅','职责产物','method_id','终判接口','置信度'): self.assertNotIn(word,text)
        for mode in ('structured','content-export'):
            exported=json.loads(render(result,mode,self.registry))
            self.assertEqual(exported['question_verification'],result['question_verification'])
            self.assertEqual(exported['lesson_feedback'],result['lesson_feedback'])

    def test_legacy_version_cannot_silently_change_segment_semantics(self):
        q=self.question(); q['lesson_review']['schema_version']='1.0.0'
        with self.assertRaisesRegex(ValueError,'1.1.0'): self.engine.analyze(q)

    def test_terminal_segment_cannot_claim_an_interpreter_method_id(self):
        q=self.question(); q['lesson_review']['segments'][2]['method_id']='R03'
        with self.assertRaises(Exception): self.engine.analyze(q)

    def test_missing_candidate_or_stop_withholds_full_delivery(self):
        for choice in ('candidate','stop'):
            q=self.question()
            if choice=='candidate':
                q['lesson_review']['segments'][2]['candidate_ids']=['A','B']
            else: q['lesson_review']['segments'].pop()
            result=self.engine.analyze(q)
            self.assertEqual(result['lesson_feedback']['scope'],'partial_delivery')
            self.assertEqual(result['lesson_feedback']['review']['segments'],[])
            self.assertNotIn('最后这一题选A',render(result,'student',self.registry))

    def test_terminal_comparison_cannot_precede_supporting_method_action(self):
        q=self.question(); segments=q['lesson_review']['segments']
        segments.insert(0,segments.pop(2))
        with self.assertRaisesRegex(ValueError,'supporting method actions'): self.engine.analyze(q)

    def test_foreign_candidate_review_id_or_missing_decisive_quote_is_rejected(self):
        for field,value in [('candidate_ids',['X']),('terminal_review_id','other'),('text','只比较A和B及C而不展示正文词语。')]:
            q=self.question(); q['lesson_review']['segments'][2][field]=value
            with self.assertRaises(ValueError): self.engine.analyze(q)

    def test_terminal_reference_requires_its_own_passage_span_coverage(self):
        q=self.question(); q['lesson_review']['segments'][2]['evidence']=[
            {'field':'passage','start':0,'end':5,'quote':'alpha'}]
        with self.assertRaisesRegex(ValueError,'decisive evidence'): self.engine.analyze(q)

    def test_unresolved_backfill_cannot_be_closed_by_a_fluent_script(self):
        q=self.question(); q['question_verification_review']['candidate_checks'][1]['backfill_verdict']='unresolved'
        with self.assertRaisesRegex(ValueError,'closed question'): self.engine.analyze(q)

    def test_unreviewed_script_remains_withheld(self):
        q=self.question(); q['lesson_review']['review_status']='unreviewed'
        result=self.engine.analyze(q)
        self.assertEqual(result['lesson_feedback']['scope'],'unreviewed')
        self.assertEqual(result['lesson_feedback']['review']['segments'],[])

    def test_renderer_rechecks_terminal_candidate_proof_edge(self):
        result=self.engine.analyze(self.question())
        binding=next(b for b in result['lesson_feedback']['segment_bindings'] if b['segment_id']=='terminal')
        target=result['question_verification']['candidate_bindings'][0]['verification_node_id']
        result['evidence_graph']['edges']=[e for e in result['evidence_graph']['edges']
            if not (e['from']==target and e['to']==binding['relation_node_id'])]
        for mode in ('structured','student','legacy-wechat','content-export'):
            with self.assertRaisesRegex(ValueError,'own candidate proof'): render(result,mode,self.registry)

    def test_renderer_rechecks_candidate_and_source_coverage(self):
        result=self.engine.analyze(self.question())
        changed=deepcopy(result)
        changed['lesson_feedback']['review']['segments'][2]['candidate_ids']=['A','B']
        with self.assertRaisesRegex(ValueError,'candidate coverage'): render(changed,'student',self.registry)
        changed=deepcopy(result)
        changed['lesson_feedback']['review']['segments'][2]['evidence'][0]['quote']='fabricated'
        with self.assertRaises(ValueError): render(changed,'student',self.registry)

    def test_renderer_rechecks_delivery_contract_and_source_module(self):
        result=self.engine.analyze(self.question())
        refs=result['lesson_feedback']['review']['source_section_ids']
        foreign=next(sid for sid,s in self.registry.sources['sections'].items() if s['path']=='gaokao-english/references/seven-five.md')
        for sources in ([*self.registry.methods['R03']['section_ids']],refs+[refs[0]],refs+['unknown'],refs+[foreign]):
            changed=deepcopy(result); changed['lesson_feedback']['review']['source_section_ids']=sources
            for mode in ('structured','student','legacy-wechat','content-export'):
                with self.assertRaisesRegex(ValueError,'delivery contract|unknown, duplicated'): render(changed,mode,self.registry)

    def test_whole_seven_delivery_keeps_grouping_once_with_non_branded_terminal_segments(self):
        from tests.test_passage_lesson import seven_question
        q=seven_question(self.registry); q['task_type']='cohesion'
        q['requested_chain']=['F01','F05']; q['observations'][1]['method_id']='F05'; q.pop('relations')
        span=q['observations'][0]['evidence'][0]
        q['action_executions'].append(action('meaning','F05','interpreter',
            {'kind':'interpretation','parts':[{'name':'program-only scope','value':'synthetic content scope','evidence':[span]}]},
            inputs=['sentence','actor','time'],evidence=[span]))
        review=deepcopy(self.question()['question_verification_review'])
        review.update(question_id=q['question_id'],task_type=q['task_type'],material_sha256=material_fingerprint(q),
                      input_artifact_ids=['meaning'],source_section_ids=self.registry.methods['F05']['section_ids'])
        review['candidate_checks']=[{**deepcopy(review['candidate_checks'][0]),'candidate':cid,
            'claim':text,'effect':'retain' if cid=='A' else 'eliminate'} for cid,text in q['options'].items()]
        q['question_verification_review']=review
        lesson=q['lesson_review']; lesson['schema_version']='1.1.0'
        lesson['source_section_ids']=list(dict.fromkeys([lesson['source_section_ids'][0],
            *self.registry.methods['F01']['section_ids'],*self.registry.methods['F05']['section_ids']]))
        lesson['segments']=lesson['segments'][:3]
        for sid,function,text in [('content','action','这里用'+self.registry.methods['F05']['brand_name']+'，先圈实际管辖内容。'),
                                  ('content-evidence','evidence','回到alpha beta gamma核当前内容范围。')]:
            lesson['segments'].append({'segment_id':sid,'method_id':'F05','function':function,'text':text,'evidence':[span],'relation_indices':[]})
        lesson['segments'].append({'segment_id':'terminal','segment_scope':'whole_question','function':'comparison',
            'terminal_review_id':review['review_id'],'candidate_ids':list('ABCDEFG'),'evidence':[span],
            'text':'再分别回填A和B及C和D及E和F及G，用alpha beta gamma核每项内容，A有支持，其他项各有不合。'})
        lesson['segments'].append({'segment_id':'content-stop','method_id':'F05','function':'stop',
            'text':'只概括而不能接上实际展开时停止，不用剩余项定案。','evidence':[span],'relation_indices':[]})
        packet={'lesson_id':'synthetic-seven-terminal-not-real-trial','question_type':'七选五','passage':q['passage'],
                'material_complete':True,'questions':[{'number':36,'question':q}],
                'review':{'reviewer':'synthetic-program-reviewer','review_status':'reviewed',
                    'source_section_ids':[next(sid for sid,s in self.registry.sources['sections'].items()
                        if s['path']==DELIVERY_PATH and s['heading']=='做题顺序')],
                    'reading_mode':None,'steps':[{'question_id':q['question_id'],'pass':1,'outcome':'solved',
                        'transition':'先按alpha beta gamma找到第36题的内容突破口。','evidence':[span],'execution_ids':[]}]}}
        result=PassageLessonAnalyzer(self.engine).analyze(packet)
        self.assertEqual(result['scope'],'whole_passage_delivery')
        for mode in ('student','legacy-wechat'):
            body=render_passage(result,mode,self.registry)
            self.assertIn('再分别回填A',body)
            for label in ('句型','主角','时间'): self.assertEqual(body.count('按'+label+'先分'),1)


if __name__=='__main__': unittest.main()
