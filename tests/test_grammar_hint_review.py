"""Synthetic hint-absence controls, not learner or English-effect results."""
from copy import deepcopy
import unittest

from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from core.grammar_navigation import hint_branch, navigate_grammar
from core.real_cases import material
from renderers import render
from tests.test_execution import action


class HintReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def question(self):
        passage='program ____61____ item'
        span={'field':'passage','start':0,'end':len(passage),'quote':passage}
        return {'question_id':'synthetic-no-hint','question_type':'语法填空',
                'stem':'____61____','passage':passage,
                'grammar_hint_review': {'state':'without_hint','target_marker':'____61____',
                    'evidence':[span],'reviewer':'synthetic-program-reviewer',
                    'review_status':'reviewed','review_notes':'Program-only target metadata check.'}}

    def test_missing_field_remains_unknown_without_review(self):
        q=self.question(); q.pop('grammar_hint_review')
        self.assertEqual(hint_branch(q),'unknown')

    def test_review_routes_without_inserting_null_or_choosing_a_function(self):
        q=self.question(); before=deepcopy(q)
        nav=navigate_grammar(q,self.registry)
        self.assertEqual(nav['hint_branch'],'without_hint')
        self.assertEqual(nav['status'],'needs_function_confirmation')
        self.assertEqual(nav['paths'],[])
        self.assertEqual(q,before)
        self.assertNotIn('given_word',q)

    def test_route_requires_separate_function_and_trigger_reviews(self):
        q=self.question(); span=q['grammar_hint_review']['evidence'][0]
        q['observations']=[{'method_id':mid,'evidence':[span],'reviewed':True}
                           for mid in ['G01','G03']]
        q['requested_chain']=['G01']
        q['action_executions']=[action('route','G01','framework',
            {'kind':'route_selection','node_ids':['entry','hint','without_hint','article']},
            evidence=[span])]
        result=QuestionAnalyzer(self.registry).analyze(q)
        self.assertEqual(result['execution_trace'][0]['state'],'produced')
        self.assertIsNone(result['answer'])
        self.assertEqual(result['grammar_navigation']['paths'][0][-1],'article')
        for mode in ['structured','student','legacy-wechat','content-export']:
            self.assertTrue(render(result,mode,self.registry))
        q['observations']=q['observations'][:1]
        with self.assertRaisesRegex(ValueError,'separately reviewed function'):
            QuestionAnalyzer(self.registry).analyze(q)

    def test_unreviewed_absence_is_not_confirmed(self):
        q=self.question(); q['grammar_hint_review']['review_status']='unreviewed'
        self.assertEqual(hint_branch(q),'unknown')
        self.assertIn('尚未审阅',navigate_grammar(q,self.registry)['limitations'][-1])

    def test_connector_family_is_not_rendered_as_a_clause_assertion(self):
        q=self.question(); span=q['grammar_hint_review']['evidence'][0]
        q['observations']=[{'method_id':mid,'evidence':[span],'reviewed':True}
                           for mid in ['G01','G06']]
        q['requested_chain']=['G01']
        q['action_executions']=[action('connector-route','G01','framework',
            {'kind':'route_selection','node_ids':['entry','hint','without_hint','clause']},
            evidence=[span])]
        result=QuestionAnalyzer(self.registry).analyze(q)
        self.assertEqual(result['grammar_navigation']['paths'][0][-1],'clause')
        self.assertIn('逐步讲解还没齐',render(result,'student',self.registry))
        self.assertNotIn('连接/关系词',render(result,'student',self.registry))
        self.assertNotIn('从句缺口',render(result,'student',self.registry))

    def test_supplied_word_cannot_be_overridden(self):
        q=self.question(); q['given_word']='item'
        with self.assertRaisesRegex(ValueError,'contradicts'):
            hint_branch(q)

    def test_bracketed_prompt_and_unresolved_parenthesis_block_absence(self):
        for suffix in ['(item) other','（item） other','(unreadable','[item] other','【item】 other']:
            q=self.question(); q['passage']='program ____61____'+suffix
            quote=q['passage']; q['grammar_hint_review']['evidence']=[
                {'field':'passage','start':0,'end':len(quote),'quote':quote}]
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError,'bracketed prompt'):
                hint_branch(q)

    def test_wrong_blank_or_repeated_marker_is_not_accepted(self):
        q=self.question(); q['grammar_hint_review']['target_marker']='____60____'
        with self.assertRaisesRegex(ValueError,'exact requested blank'):
            hint_branch(q)
        q=self.question(); q['passage']+=' ____61____ other'
        with self.assertRaisesRegex(ValueError,'exact requested blank'):
            hint_branch(q)

    def test_blank_only_quote_cannot_prove_hint_absence(self):
        q=self.question(); marker=q['stem']; start=q['passage'].index(marker)
        q['grammar_hint_review']['evidence']=[{'field':'passage','start':start,
                                             'end':start+len(marker),'quote':marker}]
        with self.assertRaisesRegex(ValueError,'following printed text'):
            hint_branch(q)

    def test_cropped_passage_and_foreign_quote_are_rejected(self):
        q=self.question(); q['passage']='program ____61____'
        quote=q['passage']; q['grammar_hint_review']['evidence']=[
            {'field':'passage','start':0,'end':len(quote),'quote':quote}]
        with self.assertRaisesRegex(ValueError,'cropped blank'):
            hint_branch(q)
        q=self.question(); q['grammar_hint_review']['evidence'][0]['quote']='made up'
        with self.assertRaises(ValueError): hint_branch(q)

    def test_full_single_blank_sentence_in_stem_is_supported(self):
        q=self.question(); q['stem']=q.pop('passage')
        q['grammar_hint_review']['evidence'][0]['field']='stem'
        self.assertEqual(hint_branch(q),'without_hint')

    def test_generic_stem_can_bind_a_unique_single_blank_but_not_a_whole_multi_blank_passage(self):
        q=self.question(); q['stem']='program-only single blank request'
        self.assertEqual(hint_branch(q),'without_hint')
        q['passage']+=' ____62____ other'
        with self.assertRaisesRegex(ValueError,'exact requested blank'):
            hint_branch(q)

    def test_other_source_field_cannot_hide_a_bracketed_prompt(self):
        q=self.question(); q['stem']='____61____(item)'
        with self.assertRaisesRegex(ValueError,'bracketed prompt'):
            hint_branch(q)

    def test_nonblank_target_and_whitespace_identity_are_rejected(self):
        q=self.question(); q['grammar_hint_review']['target_marker']='program'
        with self.assertRaisesRegex(ValueError,'printed blank marker'):
            hint_branch(q)
        q=self.question(); q['grammar_hint_review']['reviewer']=' '
        with self.assertRaisesRegex(ValueError,'named reviewer'):
            hint_branch(q)

    def test_non_grammar_annotation_is_not_silently_ignored(self):
        q=self.question(); q['question_type']='阅读理解'
        with self.assertRaisesRegex(ValueError,'grammar question'):
            navigate_grammar(q,self.registry)

    def test_original_material_fingerprint_excludes_annotation_not_hint_field(self):
        q=self.question(); original=material(q)
        q.pop('grammar_hint_review')
        self.assertEqual(material(q),original)
        q['given_word']=None
        self.assertNotEqual(material(q),original)


if __name__=='__main__': unittest.main()
