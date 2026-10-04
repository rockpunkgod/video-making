"""Synthetic spoken-transport fixtures, never real exam or learner outcomes."""
from copy import deepcopy
import json
import unittest
from core.analyzer import QuestionAnalyzer
from core.registry import Registry,validate_schema
from core.lesson_feedback import DELIVERY_PATH
from renderers import render


def fixture(registry):
    raw='alpha beta gamma'; span={'field':'passage','start':0,'end':len(raw),'quote':raw}
    mids=registry.methods['R01']['section_ids']
    source=next(s for s in mids if registry.sources['sections'][s]['path']=='gaokao-english/references/reading-comprehension.md')
    delivery=next(s for s,v in registry.sources['sections'].items() if v['path']==DELIVERY_PATH)
    q={'question_id':'synthetic-spoken-program-only','question_type':'阅读理解','task_type':'detail','stem':'program-only, not an English exam','passage':raw,'options':{'A':'alpha','B':'beta'},'requested_chain':['R01'],
       'observations':[{'method_id':'R01','reviewed':True,'evidence':[span]}],
       'relations':[{'method_id':'R01','candidate':c,'effect':effect,'claim':'program-only candidate '+c,'evidence':[span],'decision_rule_check':'program relation, not teaching evidence','stop_rule_check':'program stop check','verification':'program verification','reviewer':'synthetic-parser-fixture','review_status':'reviewed'} for c,effect in [('A','retain'),('B','eliminate')]]}
    def segment(i,function,text,refs=None): return {'segment_id':str(i),'function':function,'method_id':'R01','text':text,'evidence':[span],'relation_indices':refs or []}
    q['lesson_review']={'schema_version':'1.0.0','question_type':'阅读理解','review_status':'reviewed','reviewer':'synthetic-program-fixture-not-a-teacher-study','source_section_ids':[delivery,source],
       'segments':[segment(1,'action','这里先用选项加戏，把候选拆出后来多说的部分，先只查这一截。'),
                   segment(2,'evidence','先回到原文alpha beta gamma，这一截是当前核验的起点。'),
                   segment(3,'comparison','A的断言回到alpha beta gamma能得到支持，先保留。',[0]),
                   segment(4,'comparison','B的断言回到alpha beta gamma不能得到支持，在这一截排除。',[1]),
                   segment(5,'stop','新增部分有直接或间接文本支持时，就不能仅因没有原词而排除。')]}
    return q


class SpokenLessonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry(); cls.a=QuestionAnalyzer(cls.r)

    def test_legacy_plain_spoken_delivery_preserves_order_and_one_final_answer(self):
        q=fixture(self.r); out=self.a.analyze(q); validate_schema('question-analysis',out)
        self.assertEqual(out['lesson_feedback']['scope'],'single_question_lesson')
        body=render(out,'legacy-wechat',self.r)
        self.assertTrue(body.startswith('同学，我们来分析一下。'))
        self.assertEqual(body.count('同学'),1); self.assertTrue(body.endswith('最后这一题选A。'))
        positions=[body.index(s['text']) for s in q['lesson_review']['segments']]
        self.assertEqual(positions,sorted(positions))
        for leaked in ['职责产物','外部审阅','置信度','source','method_id','# ','1. ']: self.assertNotIn(leaked,body)

    def test_full_machine_and_content_exports_preserve_delivery_graph(self):
        out=self.a.analyze(fixture(self.r))
        for kind in ['structured','content-export']:
            exported=json.loads(render(out,kind,self.r))
            self.assertEqual(exported['lesson_feedback'],out['lesson_feedback']); self.assertEqual(exported['evidence_graph'],out['evidence_graph'])
        self.assertEqual(out['review_scope'],'external_single_question_lesson')

    def test_missing_stop_or_candidate_coverage_withholds_lesson(self):
        for index in [3,4]:
            q=fixture(self.r); q['lesson_review']['segments'].pop(index)
            out=self.a.analyze(q)
            self.assertEqual(out['lesson_feedback']['scope'],'partial_delivery'); self.assertEqual(out['lesson_feedback']['review']['segments'],[])
            self.assertNotIn('最后这一题选A',render(out,'legacy-wechat',self.r))

    def test_evidence_can_be_embedded_in_comparison_without_separate_heading(self):
        q=fixture(self.r); q['lesson_review']['segments'].pop(1)
        out=self.a.analyze(q)
        self.assertEqual(out['lesson_feedback']['scope'],'single_question_lesson')
        self.assertIn('alpha beta gamma',render(out,'legacy-wechat',self.r))

    def test_unreviewed_delivery_is_really_withheld(self):
        q=fixture(self.r); q['lesson_review']['review_status']='unreviewed'
        out=self.a.analyze(q)
        self.assertEqual(out['lesson_feedback']['scope'],'unreviewed'); self.assertEqual(out['lesson_feedback']['review']['segments'],[])
        self.assertNotIn(q['lesson_review']['segments'][0]['text'],render(out,'student',self.r))

    def test_unclosed_candidate_cannot_be_promoted_by_spoken_text(self):
        q=fixture(self.r); q['relations'].pop(); q['lesson_review']['segments'].pop(3)
        out=self.a.analyze(q); self.assertIsNone(out['answer'])
        self.assertEqual(out['lesson_feedback']['scope'],'partial_delivery')

    def test_unreviewed_trigger_is_not_replaced_by_confident_delivery(self):
        q=fixture(self.r); q['observations'][0]['reviewed']=False; q['relations']=[]
        q['lesson_review']['segments']=[q['lesson_review']['segments'][0]]
        with self.assertRaisesRegex(ValueError,'independently reviewed'): self.a.analyze(q)

    def test_first_method_use_is_named_inside_action_not_a_catalogue(self):
        for change in ['name','function']:
            q=fixture(self.r)
            if change=='name': q['lesson_review']['segments'][0]['text']='先看看逻辑。'
            else: q['lesson_review']['segments'][0]['function']='evidence'
            with self.assertRaisesRegex(ValueError,'First use'): self.a.analyze(q)

    def test_fabricated_quote_or_hidden_evidence_is_rejected(self):
        q=fixture(self.r); q['lesson_review']['segments'][1]['evidence'][0]['quote']='foreign words'
        with self.assertRaisesRegex(ValueError,'fabricated'): self.a.analyze(q)
        q=fixture(self.r); q['lesson_review']['segments'][1]['text']='所以这句话有依据。'
        with self.assertRaisesRegex(ValueError,'show a current source quote'): self.a.analyze(q)

    def test_candidate_comparison_requires_own_reviewed_evidence(self):
        for change in ['index','candidate','evidence','unreviewed']:
            q=fixture(self.r); segment=q['lesson_review']['segments'][2]
            if change=='index': segment['relation_indices']=[20]
            elif change=='candidate': segment['text']=segment['text'].replace('A','C')
            elif change=='evidence': segment['evidence']=[{'field':'passage','start':0,'end':5,'quote':'alpha'}]
            else: q['relations'][0]['review_status']='unreviewed'
            with self.subTest(change=change),self.assertRaises(ValueError): self.a.analyze(q)

    def test_contract_source_and_course_module_are_not_interchangeable(self):
        q=fixture(self.r); q['lesson_review']['source_section_ids'].pop(0)
        with self.assertRaisesRegex(ValueError,'delivery contract'): self.a.analyze(q)
        q=fixture(self.r); q['lesson_review']['source_section_ids'].append(self.r.methods['W15']['section_ids'][0])
        with self.assertRaisesRegex(ValueError,'another module'): self.a.analyze(q)

    def test_markdown_internal_metadata_and_second_greeting_are_rejected(self):
        for text in ['这里先用选项加戏，置信度为高。','同学，先用选项加戏。','# 选项加戏','选项加戏。\n1. 查证据','选项加戏，图片里可以看到。','选项加戏，老师讲过这道题。']:
            q=fixture(self.r); q['lesson_review']['segments'][0]['text']=text
            with self.subTest(text=text),self.assertRaises(ValueError): self.a.analyze(q)

    def test_original_english_punctuation_is_preserved_inside_current_quotes(self):
        q=fixture(self.r); raw='alpha, beta; gamma!'
        q['passage']=raw; s={'field':'passage','start':0,'end':len(raw),'quote':raw}
        for obs in q['observations']: obs['evidence']=[s]
        for rel in q['relations']: rel['evidence']=[s]
        for segment in q['lesson_review']['segments']:
            segment['evidence']=[s]; segment['text']=segment['text'].replace('alpha beta gamma',raw)
        body=render(self.a.analyze(q),'legacy-wechat',self.r)
        self.assertIn(raw,body)

    def test_projection_cannot_detach_text_graph_or_answer_state(self):
        out=self.a.analyze(fixture(self.r))
        for change in ['text','evidence','bindings','answer','scope','wrong_answer','trigger','candidate_relation']:
            bad=deepcopy(out); f=bad['lesson_feedback']
            if change=='text': f['review']['segments'][1]['text']+='新的无来源断言。'
            elif change=='evidence': f['segment_bindings'][0]['evidence_ids']=f['segment_bindings'][1]['evidence_ids']
            elif change=='bindings': f['segment_bindings'].pop()
            elif change=='answer': bad['answer_verification']['closed']=False
            elif change=='scope': f['scope']='partial_delivery'
            elif change=='wrong_answer': bad['answer']='B'
            else:
                target=f['segment_bindings'][2]['relation_node_id']
                kinds={'question_signal'} if change=='trigger' else {'relation'}
                blocked={n['id'] for n in bad['evidence_graph']['nodes'] if n['type'] in kinds}
                bad['evidence_graph']['edges']=[e for e in bad['evidence_graph']['edges'] if not(e['to']==target and e['from'] in blocked)]
            with self.subTest(change=change),self.assertRaises(ValueError): render(bad,'legacy-wechat',self.r)

    def test_seven_five_requires_three_actual_groups_and_displays_once(self):
        q=fixture(self.r); s=q['observations'][0]['evidence'][0]
        q.update(question_type='七选五',options={c:'program-only option '+c for c in 'ABCDEFG'},requested_chain=['F01','F11'],observations=[{'method_id':m,'reviewed':True,'evidence':[s]} for m in ['F01','F11']])
        q['relations']=[{**deepcopy(q['relations'][0]),'method_id':'F11','candidate':c,'effect':'retain' if c=='A' else 'eliminate'} for c in 'ABCDEFG']
        delivery=q['lesson_review']['source_section_ids'][0]
        source_ids=[next(sid for sid in self.r.methods[m]['section_ids'] if self.r.sources['sections'][sid]['path']=='gaokao-english/references/seven-five.md') for m in ['F01','F11']]
        review=q['lesson_review']; review.update(question_type='七选五',source_section_ids=list(dict.fromkeys([delivery]+source_ids)))
        def segment(i,mid,function,text,refs=None): return {'segment_id':str(i),'method_id':mid,'function':function,'text':text,'evidence':[s],'relation_indices':refs or []}
        review['segments']=[segment(0,'F01','action','先用选项三分，先分组，再拼回去。'),segment(1,'F01','evidence','分组以后回到alpha beta gamma，继续核本空关系。'),segment(2,'F01','stop','分组只是缩范围，不能拿它定答案。'),segment(3,'F11','action','再用'+self.r.methods['F11']['brand_name']+'，逐项核本空决定性内容。')]
        review['segments'] += [segment(i+4,'F11','comparison',c+'回到alpha beta gamma才核这个候选的具体关系。',[i]) for i,c in enumerate('ABCDEFG')]
        review['segments'].append(segment(20,'F11','stop','本空关系不足时先停，不因为选项占用或剩一项就定案。'))
        q['action_executions']=[{'execution_id':axis,'method_id':'F01','method_version':'1.1.0','role':'reducer','input_artifact_ids':[],'concrete_action':'program-only grouping action','evidence':[s],'decision_rule_check':'program partition completeness','stop_rule_check':'program reduce only','stop_applied':False,'reviewer':'synthetic-program-fixture','review_status':'reviewed','output':{'kind':'candidate_partition','axis':axis,'groups':[{'label':'本维没有可观察区别','candidates':list('ABCDEFG')}]}} for axis in ['sentence','actor','time']]
        out=self.a.analyze(q); self.assertEqual(out['lesson_feedback']['scope'],'single_question_lesson')
        body=render(out,'legacy-wechat',self.r)
        for name in ['句型','主角','时间']: self.assertEqual(body.count('按'+name+'先分'),1)
        self.assertIn('A和B和C和D和E和F和G',body)
        self.assertLess(body.index('按时间先分'),body.index('逐项核本空决定性内容'))
        missing=deepcopy(q); missing['action_executions'].pop()
        self.assertEqual(self.a.analyze(missing)['lesson_feedback']['scope'],'partial_delivery')
        reordered=deepcopy(q); reordered['lesson_review']['segments']=review['segments'][3:]+review['segments'][:3]
        self.assertEqual(self.a.analyze(reordered)['lesson_feedback']['scope'],'partial_delivery')


if __name__=='__main__': unittest.main()
