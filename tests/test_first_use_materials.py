"""Synthetic export controls, not student or English semantic evaluation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.registry import Registry
from scripts.prepare_first_use_materials import prepare, question_fingerprint, read_question, verify, render_question


class FirstUseMaterialsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=Registry()

    def setUp(self):
        self.temporary=TemporaryDirectory()
        self.root=Path(self.temporary.name)
        self.demo=self.root/'demo.json'; self.transfer=self.root/'transfer.json'
        self.walkthrough=self.root/'walkthrough.json'
        for path, qid, passage in [(self.demo,'synthetic-demo','synthetic source one'),
                                  (self.transfer,'synthetic-transfer','synthetic source two')]:
            self.save(path,{'question':{'question_id':qid,'question_type':'七选五','stem':'synthetic blank',
                      'passage':passage,'options':{key:'synthetic candidate '+key for key in 'ABCDEFG'},'answer':'SECRET-ANSWER',
                      'observations':[{'expected_group':'SECRET-GROUP'}]},'analysis':{'answer':'SECRET-ANSWER'}})
        self.save(self.walkthrough,{'method_id':'F01','method_version':self.registry.methods['F01']['version'],
                      'source_commit':self.registry.index['source_baseline']['commit'],
                      'question_id':'synthetic-demo',
                      'demonstration_question_sha256':question_fingerprint(read_question(self.demo)[0]),
                      'first_action':'synthetic action',
                      'evidence':'synthetic evidence','output':'synthetic output','stop':'synthetic stop',
                      'review_scope':'ai_authored_draft_not_learner_validation'})
        self.patch=patch('scripts.prepare_first_use_materials.ROOT',self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop(); self.temporary.cleanup()

    def save(self,path,value): path.write_text(json.dumps(value),encoding='utf-8')

    def run_export(self,output=None):
        return prepare('F01',self.demo,self.transfer,self.walkthrough,
                       output or self.root/'local-data/kit',self.registry)

    def test_answer_free_and_no_manufactured_observations(self):
        result=self.run_export(); output=Path(result['output'])
        text=(output/'student-material.md').read_text(encoding='utf-8')
        self.assertNotIn('SECRET',text)
        self.assertNotIn('synthetic evidence',text.split('## 第二道题')[1])
        facilitator=json.loads((output/'facilitator.json').read_text(encoding='utf-8'))
        self.assertTrue(all(value is None for value in facilitator['first_use_test'].values()))
        self.assertFalse(facilitator['collection_allowed'])
        self.assertEqual(facilitator['new_blind_sample_count'],0)

    def test_public_output_rejected(self):
        with self.assertRaisesRegex(ValueError,'private local-data'): self.run_export(self.root/'public')

    def test_existing_kit_not_overwritten(self):
        self.run_export()
        with self.assertRaisesRegex(ValueError,'overwrite'): self.run_export()

    def test_duplicate_original_question_rejected_even_with_new_id(self):
        data=json.loads(self.demo.read_text()); data['question']['question_id']='new-id'
        self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'different original'): self.run_export()

    def test_stale_demo_version_rejected(self):
        data=json.loads(self.walkthrough.read_text()); data['method_version']='0.0.0'
        self.save(self.walkthrough,data)
        with self.assertRaisesRegex(ValueError,'current method'): self.run_export()

    def test_another_blank_in_same_passage_is_not_unfamiliar_transfer(self):
        data=json.loads(self.transfer.read_text()); data['question']['passage']='synthetic source one'
        data['question']['stem']='another blank'; self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'different passage'): self.run_export()

    def test_wrong_type_or_incomplete_text_rejected(self):
        data=json.loads(self.transfer.read_text()); data['question']['question_type']='阅读理解'
        self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'type does not match'): self.run_export()
        del data['question']['passage']; self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'Incomplete question'): self.run_export()

    def test_same_id_cannot_rebind_demonstration_to_changed_original_text(self):
        data=json.loads(self.demo.read_text()); data['question']['options']['G']='changed source'
        self.save(self.demo,data)
        with self.assertRaisesRegex(ValueError,'current method'): self.run_export()

    def test_missing_or_blank_choice_rejected_without_creating_output(self):
        data=json.loads(self.transfer.read_text()); del data['question']['options']['G']
        self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'choice set'): self.run_export()
        self.assertFalse((self.root/'local-data/kit').exists())
        data['question']['options']['G']='   '; self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'choice set'): self.run_export()

    def test_nontext_original_fields_are_not_silently_stringified(self):
        data=json.loads(self.transfer.read_text()); data['question']['passage']=['source']
        self.save(self.transfer,data)
        with self.assertRaisesRegex(ValueError,'Incomplete question'): self.run_export()

    def test_private_export_bindings_verify_without_granting_study_approval(self):
        result=self.run_export()
        checked=verify(result['output'],self.registry)
        self.assertEqual(checked['binding_check'],'PASS')
        self.assertFalse(checked['collection_allowed'])

    def test_changed_student_copy_and_original_source_are_detected(self):
        result=self.run_export(); output=Path(result['output'])
        material=output/'student-material.md'; original=material.read_bytes()
        material.write_bytes(original+b'changed')
        with self.assertRaisesRegex(ValueError,'Student material changed'): verify(output,self.registry)
        material.write_bytes(original)
        self.transfer.write_bytes(self.transfer.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'source artifact changed'): verify(output,self.registry)

    def test_same_version_changed_teaching_and_fabricated_results_rejected(self):
        result=self.run_export(); output=Path(result['output'])
        with patch.dict(self.registry.methods['F01']['four_step_card'],{'first_cut':'another action'}):
            with self.assertRaisesRegex(ValueError,'stale'): verify(output,self.registry)
        meta_path=output/'facilitator.json'; meta=json.loads(meta_path.read_text())
        meta['first_use_test']['action_success']=True; self.save(meta_path,meta)
        with self.assertRaisesRegex(ValueError,'observations'): verify(output,self.registry)

    def test_original_letter_prefix_not_duplicated_in_student_display(self):
        text=render_question({'question_type':'七选五','passage':'source','stem':'task','options':{'A':'A.The key is consistency.'}})
        self.assertIn('A.The key',text)
        self.assertNotIn('A. A.',text)

    def grammar_export(self,given_word='solid'):
        for path,qid,passage in [(self.demo,'synthetic-demo','synthetic grammar one'),
                                 (self.transfer,'synthetic-transfer','synthetic grammar two')]:
            self.save(path,{'question':{'question_id':qid,'question_type':'语法填空',
                                      'stem':'synthetic blank','passage':passage,'given_word':given_word}})
        method=self.registry.methods['G01']
        self.save(self.walkthrough,{'method_id':'G01','method_version':method['version'],
                  'source_commit':self.registry.index['source_baseline']['commit'],
                  'question_id':'synthetic-demo',
                  'demonstration_question_sha256':question_fingerprint(read_question(self.demo)[0]),
                  'first_action':'synthetic action','evidence':'synthetic evidence',
                  'output':'synthetic node','stop':'synthetic stop',
                  'review_scope':'ai_authored_draft_not_learner_validation'})
        return prepare('G01',self.demo,self.transfer,self.walkthrough,
                       self.root/'local-data/grammar-kit',self.registry)

    def test_grammar_preserves_repository_hint_and_renders_current_tree(self):
        result=self.grammar_export(); output=Path(result['output'])
        text=(output/'student-material.md').read_text(encoding='utf-8')
        self.assertIn('本空提示词：solid',text)
        self.assertIn(self.registry.methods['G01']['visual_formula'],text)
        self.assertEqual(read_question(self.demo)[0]['given_word'],'solid')
        self.assertEqual(verify(output,self.registry)['binding_check'],'PASS')

    def test_no_hint_is_explicit_not_silently_inferred(self):
        result=self.grammar_export(None); output=Path(result['output'])
        self.assertIn('本空无提示词',(output/'student-material.md').read_text(encoding='utf-8'))
        from scripts.prepare_first_use_materials import grammar_hint
        with self.assertRaisesRegex(ValueError,'Missing explicit'): grammar_hint({'question_type':'语法填空'})
        with self.assertRaisesRegex(ValueError,'Conflicting'): grammar_hint({'given_word':'solid','hint_word':'describe'})
        with self.assertRaisesRegex(ValueError,'text or explicit null'): grammar_hint({'given_word':42})

    def test_changed_hint_cannot_reuse_old_demonstration_and_tree_is_bound(self):
        result=self.grammar_export(); output=Path(result['output'])
        with patch.dict(self.registry.methods['G01'],{'visual_formula':'changed tree'}):
            with self.assertRaisesRegex(ValueError,'stale'): verify(output,self.registry)
        data=json.loads(self.demo.read_text()); data['question']['given_word']='other'
        self.save(self.demo,data)
        with self.assertRaisesRegex(ValueError,'current method'):
            prepare('G01',self.demo,self.transfer,self.walkthrough,self.root/'local-data/new-kit',self.registry)

    def test_original_paper_question_selection_preserves_binding_without_copying_answers(self):
        questions=[json.loads(path.read_text())['question'] for path in (self.demo,self.transfer)]
        paper=self.root/'existing-frozen-paper.json'
        self.save(paper,{'inputs':{'questions':questions},'predictions':{'answer':'SECRET-ANSWER'}})
        result=prepare('F01',paper,paper,self.walkthrough,self.root/'local-data/selected-kit',self.registry,
                       demonstration_id='synthetic-demo',transfer_id='synthetic-transfer')
        output=Path(result['output']); self.assertEqual(verify(output,self.registry)['binding_check'],'PASS')
        self.assertNotIn('SECRET',(output/'student-material.md').read_text(encoding='utf-8'))
        meta=json.loads((output/'facilitator.json').read_text(encoding='utf-8'))
        self.assertEqual(meta['source_refs'][1]['question_selector'],'synthetic-transfer')
        meta['question_ids'][1]='other-question'; self.save(output/'facilitator.json',meta)
        with self.assertRaisesRegex(ValueError,'Study question IDs'): verify(output,self.registry)

    def test_selection_never_guesses_missing_id_or_chooses_one_duplicate(self):
        question=json.loads(self.demo.read_text())['question']; paper=self.root/'paper.json'
        self.save(paper,{'inputs':{'questions':[question,question]}})
        for qid in ('missing','synthetic-demo'):
            with self.assertRaisesRegex(ValueError,'missing or duplicated'): read_question(paper,qid)


if __name__=='__main__': unittest.main()
