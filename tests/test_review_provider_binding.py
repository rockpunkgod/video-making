"""Provider transport tests, not new exam questions or learner observations."""
from copy import deepcopy
import unittest
from jsonschema import ValidationError
from core.analyzer import QuestionAnalyzer,PaperAnalyzer
from core.registry import Registry
from tests.test_engine import grammar_review


class ReviewProviderBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=Registry()

    def test_provider_cannot_replace_identity_or_existing_material(self):
        q=grammar_review()
        q.update(passage=q['stem'],options={'A':'protection'},student_text=q['stem'],
                 continuation_starters=['first','second'],student_symptoms=['不会变词'])
        changes={'question_id':'different','question_type':'阅读理解','stem':'different',
                 'passage':'different','options':{'A':'different'},'given_word':'different',
                 'student_text':'different','continuation_starters':['changed','second'],
                 'student_symptoms':['changed']}
        for field,value in changes.items():
            analyzer=QuestionAnalyzer(self.registry,lambda row,r,f=field,v=value:{**row,f:v})
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'original question material: '+field):
                analyzer.analyze(q)

    def test_in_place_changes_do_not_modify_caller_or_bypass_snapshot(self):
        q=grammar_review(); before=deepcopy(q)
        def provider(row,registry):
            row['question_id']='changed'; return row
        with self.assertRaisesRegex(ValueError,'question_id'):
            QuestionAnalyzer(self.registry,provider).analyze(q)
        self.assertEqual(q,before)
        q['options']={'A':'protection'}; before=deepcopy(q)
        def nested_provider(row,registry):
            row['options']['A']='changed'; return row
        with self.assertRaisesRegex(ValueError,'options'):
            QuestionAnalyzer(self.registry,nested_provider).analyze(q)
        self.assertEqual(q,before)

    def test_optional_material_cannot_be_added_or_removed(self):
        q=grammar_review()
        for field,value in [('passage',q['stem']),('options',{'A':'protection'}),
                            ('student_text',q['stem']),('continuation_starters',['one','two']),
                            ('student_symptoms',[]),('original_images',[])]:
            with self.subTest(add=field),self.assertRaisesRegex(ValueError,field):
                QuestionAnalyzer(self.registry,lambda row,r,f=field,v=value:{**row,f:v}).analyze(q)
        for field in ('given_word','student_symptoms','original_images'):
            material={**q,'student_symptoms':[],'original_images':[]}
            def remove(row,registry):
                row.pop(field); return row
            with self.subTest(remove=field),self.assertRaisesRegex(ValueError,field):
                QuestionAnalyzer(self.registry,remove).analyze(material)

    def test_provider_can_add_review_annotations_and_labels(self):
        reviewed=grammar_review(); raw={k:v for k,v in reviewed.items() if k not in {'observations','relations'}}
        before=deepcopy(raw)
        def provider(row,registry):
            row.update(observations=deepcopy(reviewed['observations']),
                       relations=deepcopy(reviewed['relations']),difficulty='medium')
            return row
        out=QuestionAnalyzer(self.registry,provider).analyze(raw)
        self.assertEqual(out['answer'],'protection')
        self.assertEqual(out['question_id'],raw['question_id'])
        self.assertEqual(out['difficulty'],'medium'); self.assertEqual(raw,before)

    def test_invalid_original_input_cannot_be_laundered_by_provider(self):
        q={**grammar_review(),'answer_key':'protection'}; calls=[]
        def provider(row,registry):
            calls.append(True); row.pop('answer_key'); return row
        with self.assertRaises(ValidationError): QuestionAnalyzer(self.registry,provider).analyze(q)
        self.assertEqual(calls,[])

    def test_paper_cannot_recommend_replaced_question_identity(self):
        analyzer=QuestionAnalyzer(self.registry,lambda row,r:{**row,'question_id':'replaced'})
        with self.assertRaisesRegex(ValueError,'question_id'):
            PaperAnalyzer(analyzer).analyze({'paper_id':'provider-binding-program-test','questions':[grammar_review()]})


if __name__=='__main__': unittest.main()
