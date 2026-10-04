"""Grammar editorial and navigation checks, not learner/effectiveness trials."""
from copy import deepcopy
import json
import unittest
from core.registry import Registry,load
from core.analyzer import QuestionAnalyzer
from core.grammar_navigation import navigate_grammar
from renderers import render
from scripts.generate_assets import build

IDS={'G'+str(i).zfill(2) for i in range(1,20)}

def fixture(mid=None,hint='protect',reviewed=True):
    # Actual existing course excerpt; no answer key or invented second exam.
    raw=load('cases/G01/canonical/case.yaml')['question']
    q={'question_id':'course-grammar-navigation','question_type':'语法填空','stem':raw,'given_word':hint}
    if mid:
        q['observations']=[{'method_id':mid,'reviewed':reviewed,'evidence':[{'field':'stem','start':0,'end':len(raw),'quote':raw}]}]
    return q

class GrammarMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=Registry()

    def test_all_nineteen_entries_ready_without_empirical_promotion(self):
        methods=[m for m in self.r.methods.values() if m['question_type']=='语法填空']
        self.assertEqual({m['method_id'] for m in methods},IDS)
        for m in methods:
            self.assertTrue(m['student_ready'] and m['entry_copy'])
            self.assertEqual(m['status'],'candidate'); self.assertEqual(m['practical_value'],'Useful')
            self.assertIsNone(m['first_use_test']['action_success'])
            self.assertIsNone(m['evaluation']['trigger_precision'])

    def test_eighteen_histories_preserve_source_role_type_and_output(self):
        for mid in IDS-{'G01'}:
            m=self.r.methods[mid]; old=load('method-registry/history/'+mid+'/1.0.0.yaml')
            self.assertEqual(m['version'],'1.1.0')
            for key in ['source_name','source_references','section_ids','primary_role','secondary_roles','method_type','output_type']:
                self.assertEqual(m[key],old[key])
            self.assertEqual(m['static_design_review']['source_section_ids'],m['section_ids'])
            self.assertTrue(all(load(p)['status']=='evidence_gap' for p in m['cases'].values()))

    def test_all_guides_have_action_stop_challenge_and_three_versions(self):
        assets=build()
        for mid in IDS:
            m=self.r.methods[mid]; guide=assets['student-guides/'+mid+'-'+m['brand_name']+'.md']
            # Golden G01 intentionally uses its four-step first action rather
            # than repeating the differently worded internal core_action.
            action=m['four_step_card']['first_cut'] if mid=='G01' else m['core_action']
            for value in [action,m['stop_rule'],m['challenge_prompt'],*(m['compact'][duration] for duration in ['10s','30s','90s'])]: self.assertIn(value,guide)
        self.assertIn('references/grammar-navigation.md',assets['gaokao-grammar-fill/SKILL.md'])
        self.assertEqual(assets['references/grammar-navigation.md'],assets['gaokao-grammar-fill/references/grammar-navigation.md'])

    def test_tree_covers_nineteen_and_shared_pronoun_is_not_a_cycle(self):
        tree=self.r.grammar_tree
        covered={mid for n in tree['nodes'].values() for mid in n['methods']}|set(tree['preparatory_methods'])|set(tree['postcheck_methods'])
        self.assertEqual(covered,IDS)
        self.assertIn('pronoun',tree['nodes']['with_hint']['children'])
        self.assertIn('pronoun',tree['nodes']['without_hint']['children'])
        self.assertEqual(self.r.validate()['status'],'PASS')

    def test_tree_rejects_cycles_unreachable_and_wrong_module_nodes(self):
        for mutation,expected in [('cycle','Circular'),('unreachable','Unreachable'),('foreign','Invalid grammar')]:
            r=Registry()
            if mutation=='cycle': r.grammar_tree['nodes']['noun']['children']=['entry']
            elif mutation=='unreachable': r.grammar_tree['nodes']['orphan']={'methods':[],'children':[]}
            else: r.grammar_tree['nodes']['noun']['methods']=['R01']
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,expected): r.validate()

    def test_hint_spelling_never_selects_verb_route_or_answer(self):
        out=QuestionAnalyzer(self.r).analyze(fixture())
        self.assertIsNone(out['answer']); self.assertEqual(out['schema_version'],'1.4.0')
        self.assertEqual(out['grammar_navigation']['hint_branch'],'with_hint')
        self.assertEqual(out['grammar_navigation']['status'],'needs_function_confirmation')
        self.assertEqual(out['grammar_navigation']['paths'],[])

    def test_reviewed_course_noun_trigger_routes_noun_not_original_verb(self):
        out=QuestionAnalyzer(self.r).analyze(fixture('G09'))
        self.assertEqual(out['grammar_navigation']['paths'],[['entry','hint','with_hint','noun']])
        self.assertIsNone(out['answer'])  # Trigger review alone is not an answer relation.

    def test_unknown_hint_is_not_silently_treated_as_no_hint(self):
        for value in ['', '   ', 'missing']:
            q=fixture('G09',value)
            if value=='missing': q.pop('given_word')
            out=QuestionAnalyzer(self.r).analyze(q)['grammar_navigation']
            self.assertEqual(out['hint_branch'],'unknown'); self.assertEqual(out['status'],'needs_hint_confirmation')
            self.assertEqual(out['paths'],[])

    def test_unreviewed_trigger_does_not_confirm_function(self):
        nav=navigate_grammar(fixture('G09',reviewed=False),self.r)
        self.assertEqual(nav['status'],'needs_function_confirmation'); self.assertEqual(nav['paths'],[])

    def test_branch_restrictions_and_competing_functions(self):
        # Reuse a raw excerpt only to test routing mechanics; annotations below
        # are synthetic program fixtures, not assertions that this sentence is a verb gap.
        for hint,expected in [(None,'without_hint'),('I','with_hint')]:
            nav=navigate_grammar(fixture('G04',hint),self.r)
            self.assertEqual(nav['paths'],[['entry','hint',expected,'pronoun']])
        self.assertEqual(navigate_grammar(fixture('G09',None),self.r)['paths'],[])
        for mid,leaf in [('G12','verb'),('G13','predicate'),('G15','nonfinite')]:
            self.assertEqual(navigate_grammar(fixture(mid),self.r)['paths'][0][-1],leaf)
        q=fixture('G13'); q['observations'].extend(fixture('G15')['observations'])
        nav=navigate_grammar(q,self.r)
        self.assertEqual({p[-1] for p in nav['paths']},{'predicate','nonfinite'})
        self.assertEqual(nav['next_node'],'with_hint')

    def test_navigation_rechecks_span_and_non_grammar_returns_none(self):
        q=fixture('G09'); q['observations'][0]['evidence'][0]['quote']='not this source'
        with self.assertRaises(ValueError): navigate_grammar(q,self.r)
        self.assertIsNone(navigate_grammar({'question_type':'阅读理解'},self.r))

    def test_export_preserves_navigation_without_inventing_answer(self):
        out=QuestionAnalyzer(self.r).analyze(fixture('G09'))
        projected=json.loads(render(out,'content-export',self.r))
        self.assertEqual(projected['grammar_navigation'],out['grammar_navigation'])
        self.assertIsNone(projected['answer']); self.assertEqual(projected['safe_for_release'],'untested')
        self.assertIn('树只导航',render(out,'student',self.r))

    def test_source_risks_bind_quotes_and_reject_edited_audit_claims(self):
        for risk in self.r.risks:
            if 'section_id' in risk:
                self.assertIn(risk['source_quote'],self.r.sources['sections'][risk['section_id']]['content'])
        r=Registry(); r.risks[0]['source_quote']='invented source quote'
        with self.assertRaisesRegex(ValueError,'Source risk quote mismatch'): r.validate()

if __name__=='__main__': unittest.main()
