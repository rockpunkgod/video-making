"""Synthetic explicit-numbering contracts; not English or printed-source certification."""
from copy import deepcopy
import unittest
from core.registry import Registry,validate_schema
from core.grammar_navigation import hint_branch,navigate_grammar
from core.analyzer import QuestionAnalyzer
from core.real_cases import material
from renderers import render
from tests.test_execution import action

class NumericHintReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.registry=Registry()

    def question(self):
        text='Synthetic item    61    their sample. Other item    62    (word).'
        start=text.index('61')
        target={'field':'passage','start':start,'end':start+2,'quote':'61'}
        span={'field':'passage','start':0,'end':len(text),'quote':text}
        return {'question_id':'synthetic-Q61','question_type':'语法填空','stem':'61','passage':text,
            'grammar_hint_review':{'state':'without_hint','target_marker':'61','evidence':[span],
                'reviewer':'synthetic-source-reviewer','review_status':'reviewed',
                'review_notes':'Synthetic annotation, no actual original paper or learner.',
                'numeric_marker_binding':{'question_id':'synthetic-Q61','question_number':61,
                    'target_span':target,'printed_blank_confirmed':True,
                    'source_review_note':'Synthetic printed-numbering declaration; not source authentication.'}}}

    def test_explicit_review_keeps_original_material_and_does_not_choose_function(self):
        q=self.question();before=deepcopy(q);frozen=material(q)
        validate_schema('question-input',q)
        nav=navigate_grammar(q,self.registry)
        self.assertEqual(nav['hint_branch'],'without_hint')
        self.assertEqual(nav['status'],'needs_function_confirmation')
        self.assertEqual(nav['paths'],[]);self.assertEqual(q,before)
        self.assertNotIn('given_word',q)
        q.pop('grammar_hint_review');self.assertEqual(material(q),frozen)

    def test_missing_and_unreviewed_annotation_leave_digits_unknown(self):
        q=self.question();q.pop('grammar_hint_review');self.assertEqual(hint_branch(q),'unknown')
        q=self.question();q['grammar_hint_review']['review_status']='unreviewed'
        self.assertEqual(hint_branch(q),'unknown')

    def test_digit_marker_alone_cannot_enable_absence(self):
        q=self.question();q['grammar_hint_review'].pop('numeric_marker_binding')
        with self.assertRaisesRegex(ValueError,'explicit printed-source'):hint_branch(q)

    def test_binding_cannot_be_borrowed_from_another_question(self):
        for key,value in [('question_id','synthetic-Q62'),('question_number',62)]:
            q=self.question();q['grammar_hint_review']['numeric_marker_binding'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'exact requested'):hint_branch(q)

    def test_stem_must_request_only_this_number(self):
        for stem in ['62','61 62','generic request','___61___','61 (word)']:
            q=self.question();q['stem']=stem
            with self.subTest(stem=stem),self.assertRaisesRegex(ValueError,'exact requested'):hint_branch(q)

    def test_year_and_zero_padded_marker_are_not_numbered_blank_route(self):
        for marker in ['2026','061','0','-61','61.0']:
            q=self.question();q['grammar_hint_review']['target_marker']=marker
            with self.subTest(marker=marker),self.assertRaises(ValueError):hint_branch(q)

    def test_boolean_number_false_typography_and_blank_note_are_rejected(self):
        for key,value in [('question_number',True),('printed_blank_confirmed',False),('source_review_note',' ')]:
            q=self.question();q['grammar_hint_review']['numeric_marker_binding'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):hint_branch(q)

    def test_target_span_is_marker_not_borrowed_context_or_stem(self):
        q=self.question();binding=q['grammar_hint_review']['numeric_marker_binding']
        binding['target_span']=q['grammar_hint_review']['evidence'][0]
        with self.assertRaisesRegex(ValueError,'marker itself'):hint_branch(q)
        q=self.question();q['grammar_hint_review']['numeric_marker_binding']['target_span']={
            'field':'stem','start':0,'end':2,'quote':'61'}
        with self.assertRaisesRegex(ValueError,'passage marker'):hint_branch(q)

    def test_inexact_span_and_repeated_number_are_rejected(self):
        q=self.question();q['grammar_hint_review']['numeric_marker_binding']['target_span']['quote']='62'
        with self.assertRaises(ValueError):hint_branch(q)
        q=self.question();q['passage']+=' quantity 61.'
        with self.assertRaisesRegex(ValueError,'one exact target'):hint_branch(q)

    def test_embedded_digits_cannot_be_a_target(self):
        for replacement in ['161','x61','61x','_61_']:
            q=self.question();text=q['passage'].replace('61',replacement,1);q['passage']=text
            start=text.index('61');q['grammar_hint_review']['numeric_marker_binding']['target_span'].update(start=start,end=start+2)
            q['grammar_hint_review']['evidence']=[{'field':'passage','start':0,'end':len(text),'quote':text}]
            with self.subTest(replacement=replacement),self.assertRaisesRegex(ValueError,'one exact target'):hint_branch(q)

    def test_bracketed_prompt_blocks_absence_in_actual_target_suffix(self):
        for suffix in ['(word)','（word）','[word]','【word】','{word}','｛word｝','(unreadable']:
            q=self.question();text=q['passage'].replace('their sample.',suffix+' their sample.');q['passage']=text
            q['grammar_hint_review']['evidence']=[{'field':'passage','start':0,'end':len(text),'quote':text}]
            with self.subTest(suffix=suffix),self.assertRaisesRegex(ValueError,'bracketed prompt'):hint_branch(q)

    def test_blank_only_one_letter_and_foreign_evidence_do_not_prove_absence(self):
        for end_extra in [0,4,5]:
            q=self.question();t=q['grammar_hint_review']['numeric_marker_binding']['target_span']
            end=t['end']+end_extra;text=q['passage']
            q['grammar_hint_review']['evidence']=[{'field':'passage','start':t['start'],'end':end,'quote':text[t['start']:end]}]
            with self.subTest(end_extra=end_extra),self.assertRaisesRegex(ValueError,'complete following'):hint_branch(q)
        q=self.question();q['grammar_hint_review']['evidence'][0]['quote']='made up'
        with self.assertRaises(ValueError):hint_branch(q)

    def test_cropped_end_and_supplied_hint_cannot_be_overridden(self):
        q=self.question();t=q['grammar_hint_review']['numeric_marker_binding']['target_span']
        q['passage']=q['passage'][:t['end']];text=q['passage']
        q['grammar_hint_review']['evidence']=[{'field':'passage','start':0,'end':len(text),'quote':text}]
        with self.assertRaisesRegex(ValueError,'cropped blank'):hint_branch(q)
        q=self.question();q['given_word']='word'
        with self.assertRaisesRegex(ValueError,'contradicts'):hint_branch(q)

    def test_numeric_annotation_cannot_be_attached_to_underscore_route(self):
        q=self.question();q['grammar_hint_review']['target_marker']='____61____'
        with self.assertRaisesRegex(ValueError,'different marker format'):hint_branch(q)

    def test_schema_rejects_missing_binding_fields_and_unknown_properties(self):
        q=self.question();q['grammar_hint_review']['numeric_marker_binding'].pop('target_span')
        with self.assertRaises(Exception):validate_schema('question-input',q)
        q=self.question();q['grammar_hint_review']['numeric_marker_binding']['invented']=True
        with self.assertRaises(Exception):validate_schema('question-input',q)

    def test_function_and_actual_route_still_require_separate_actions(self):
        q=self.question();span=q['grammar_hint_review']['evidence'][0]
        q['observations']=[{'method_id':mid,'evidence':[span],'reviewed':True} for mid in ['G01','G03']]
        q['requested_chain']=['G01']
        q['action_executions']=[action('route','G01','framework',
            {'kind':'route_selection','node_ids':['entry','hint','without_hint','article']},evidence=[span])]
        a=QuestionAnalyzer(self.registry).analyze(q)
        self.assertIsNone(a['answer']);self.assertEqual(a['execution_trace'][0]['state'],'produced')
        for mode in ['student','legacy-wechat','structured','content-export']:self.assertTrue(render(a,mode,self.registry))
        q['observations']=q['observations'][:1]
        with self.assertRaisesRegex(ValueError,'separately reviewed function'):QuestionAnalyzer(self.registry).analyze(q)

if __name__=='__main__':unittest.main()
