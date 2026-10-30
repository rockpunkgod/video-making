"""Synthetic export controls, not student or English semantic evaluation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.registry import Registry
from scripts.prepare_first_use_materials import prepare, question_fingerprint, read_question, verify, render_question
from tests import test_grammar_hint_review as hint_fixtures


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

    def test_answer_free_hint_review_can_preserve_missing_field_in_original_material(self):
        q=hint_fixtures.HintReviewTests().question()
        q['grammar_hint_review']['review_notes']='SECRET-REVIEW-NOTES'
        self.save(self.demo,{'question':q,'analysis':{'answer':'SECRET-ANSWER'}})
        selected,ref=read_question(self.demo)
        self.assertNotIn('given_word',selected)
        self.assertTrue(ref['factual_hint_review_retained'])
        self.assertFalse(ref['historical_review_reused'])
        text=render_question(selected)
        self.assertIn('本空无提示词',text)
        self.assertNotIn('SECRET',text)
        self.assertNotIn('given_word',selected)

    def test_missing_hint_is_not_inferred_from_an_unreviewed_annotation(self):
        q=hint_fixtures.HintReviewTests().question()
        q['grammar_hint_review']['review_status']='unreviewed'
        with self.assertRaisesRegex(ValueError,'Missing explicit hint state'):
            render_question(q)

    def test_alias_word_cannot_conflict_with_no_hint_review(self):
        q=hint_fixtures.HintReviewTests().question(); q['hint_word']='word'
        with self.assertRaisesRegex(ValueError,'contradicts'):
            render_question(q)

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

    def test_layout_only_changes_do_not_make_a_passage_unfamiliar(self):
        variants=['synthetic\nsource\tone','synthetic\u00a0source one',
                  'ｓｙｎｔｈｅｔｉｃ source one','synthetic\u200b source one']
        for index,passage in enumerate(variants):
            with self.subTest(passage=passage):
                data=json.loads(self.transfer.read_text())
                data['question'].update(passage=passage,stem='another synthetic blank')
                self.save(self.transfer,data)
                output=self.root/'local-data'/('format-'+str(index))
                with self.assertRaisesRegex(ValueError,'different passage'): self.run_export(output)
                self.assertFalse(output.exists())

    def test_layout_identity_preserves_original_text_and_question_fingerprint(self):
        from scripts.prepare_first_use_materials import passage_identity
        data=json.loads(self.transfer.read_text())
        data['question']['passage']='ｓｙｎｔｈｅｔｉｃ\u00a0source\n two'
        self.save(self.transfer,data)
        question,binding=read_question(self.transfer); original_bytes=self.transfer.read_bytes()
        self.assertEqual(passage_identity(question['passage']),'synthetic source two')
        result=self.run_export(); verify(result['output'],self.registry)
        self.assertEqual(self.transfer.read_bytes(),original_bytes)
        self.assertEqual(question_fingerprint(read_question(self.transfer)[0]),binding['question_sha256'])
        self.assertIn(question['passage'],(Path(result['output'])/'student-material.md').read_text(encoding='utf-8'))

    def test_layout_identity_does_not_remove_negation_or_numeric_conditions(self):
        from scripts.prepare_first_use_materials import passage_identity
        self.assertNotEqual(passage_identity('synthetic source can act'),
                            passage_identity('synthetic source cannot act'))
        self.assertNotEqual(passage_identity('synthetic result 10 units'),
                            passage_identity('synthetic result 100 units'))
        self.assertNotEqual(passage_identity('synthetic result -10 units'),
                            passage_identity('synthetic result 10 units'))

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

    def test_optional_nontext_fields_rejected_before_export(self):
        from copy import deepcopy
        original=json.loads(self.transfer.read_text())
        for index,(field,value,message) in enumerate([
                ('student_draft',['synthetic text'],'student draft'),
                ('continuation_starters','synthetic text','continuation starters'),
                ('continuation_starters',[1],'continuation starters')]):
            with self.subTest(field=field,value=value):
                data=deepcopy(original);data['question'][field]=value;self.save(self.transfer,data)
                output=self.root/'local-data'/('optional-'+str(index))
                with self.assertRaisesRegex(ValueError,message):self.run_export(output)
                self.assertFalse(output.exists())

    def test_private_export_bindings_verify_without_granting_study_approval(self):
        result=self.run_export()
        checked=verify(result['output'],self.registry)
        self.assertEqual(checked['binding_check'],'PASS')
        self.assertFalse(checked['collection_allowed'])

    def test_verify_rechecks_walkthrough_identity_even_with_matching_file_hash(self):
        import hashlib
        output=Path(self.run_export()['output'])
        data=json.loads(self.walkthrough.read_text()); data['method_id']='R09'
        self.save(self.walkthrough,data)
        meta_path=output/'facilitator.json'; meta=json.loads(meta_path.read_text())
        meta['source_refs'][2]['sha256']=hashlib.sha256(self.walkthrough.read_bytes()).hexdigest()
        self.save(meta_path,meta)
        with self.assertRaisesRegex(ValueError,'Demonstration must bind'): verify(output,self.registry)

    def test_verify_rechecks_student_projection_not_just_declared_hash(self):
        import hashlib
        output=Path(self.run_export()['output'])
        student=output/'student-material.md'; student.write_text('synthetic unrelated lesson and answer')
        meta_path=output/'facilitator.json'; meta=json.loads(meta_path.read_text())
        meta['student_material_sha256']=hashlib.sha256(student.read_bytes()).hexdigest()
        self.save(meta_path,meta)
        with self.assertRaisesRegex(ValueError,'Student material.*projection'): verify(output,self.registry)

    def test_verify_rechecks_passage_independence_even_with_matching_source_hashes(self):
        import hashlib
        output=Path(self.run_export()['output'])
        data=json.loads(self.transfer.read_text()); data['question']['passage']='synthetic\nsource one'
        self.save(self.transfer,data)
        meta_path=output/'facilitator.json'; meta=json.loads(meta_path.read_text())
        meta['source_refs'][1]['sha256']=hashlib.sha256(self.transfer.read_bytes()).hexdigest()
        meta['source_refs'][1]['question_sha256']=question_fingerprint(read_question(self.transfer)[0])
        self.save(meta_path,meta)
        with self.assertRaisesRegex(ValueError,'different passage'): verify(output,self.registry)

    def test_verify_requires_complete_null_observations_and_pending_draft_markers(self):
        from copy import deepcopy
        output=Path(self.run_export()['output']); meta_path=output/'facilitator.json'
        original=json.loads(meta_path.read_text())
        changes=[('first_use_test',{}),('first_use_test',{'unknown_result':None}),
                 ('learner_validation','validated_real_participant'),
                 ('review_scope','independently_validated'),('prior_exposure','verified_unfamiliar'),
                 ('study_order','blind_before_communication'),('required_before_collection',[]),
                 ('origin','real_student_result'),('new_case_count',False)]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                meta=deepcopy(original);meta[key]=value;self.save(meta_path,meta)
                with self.assertRaisesRegex(ValueError,'approval or observations'):verify(output,self.registry)
        self.save(meta_path,original)
        self.assertFalse(verify(output,self.registry)['collection_allowed'])

    def test_verify_and_prepare_share_priority_method_scope(self):
        import hashlib
        from scripts.prepare_first_use_materials import teaching_fingerprint,render_student_material
        output=Path(self.run_export()['output']); method=self.registry.methods['F05']
        walkthrough=json.loads(self.walkthrough.read_text())
        walkthrough.update(method_id='F05',method_version=method['version'])
        self.save(self.walkthrough,walkthrough)
        meta_path=output/'facilitator.json';meta=json.loads(meta_path.read_text())
        meta.update(method_id='F05',method_version=method['version'],teaching_card_sha256=teaching_fingerprint(method))
        meta['source_refs'][2]['sha256']=hashlib.sha256(self.walkthrough.read_bytes()).hexdigest()
        student=output/'student-material.md'
        student.write_text(render_student_material(method,read_question(self.demo)[0],read_question(self.transfer)[0],walkthrough),encoding='utf-8',newline='')
        meta['student_material_sha256']=hashlib.sha256(student.read_bytes()).hexdigest();self.save(meta_path,meta)
        with self.assertRaisesRegex(ValueError,'not current-bound'):verify(output,self.registry)
        with self.assertRaisesRegex(ValueError,'priority method'):
            prepare('F05',self.demo,self.transfer,self.walkthrough,self.root/'local-data/unsupported',self.registry)

    def test_valid_line_endings_verify_without_expanding_original_CRLF(self):
        import hashlib
        from scripts.prepare_first_use_materials import render_student_material,normalized_newlines
        data=json.loads(self.transfer.read_text());data['question']['passage']='synthetic source\r\ntwo'
        self.save(self.transfer,data);source_bytes=self.transfer.read_bytes()
        output=Path(self.run_export()['output']);student=output/'student-material.md'
        expected=render_student_material(self.registry.methods['F01'],read_question(self.demo)[0],read_question(self.transfer)[0],json.loads(self.walkthrough.read_text()))
        self.assertEqual(student.read_bytes(),expected.encode('utf-8'))
        self.assertNotIn(b'\r\r\n',student.read_bytes())
        meta_path=output/'facilitator.json';meta=json.loads(meta_path.read_text())
        for text in [expected,normalized_newlines(expected),normalized_newlines(expected).replace('\n','\r\n')]:
            student.write_bytes(text.encode('utf-8'))
            meta['student_material_sha256']=hashlib.sha256(student.read_bytes()).hexdigest();self.save(meta_path,meta)
            self.assertEqual(verify(output,self.registry)['binding_check'],'PASS')
        self.assertEqual(self.transfer.read_bytes(),source_bytes)

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

    def test_same_version_challenge_changes_invalidate_study_material(self):
        result=self.run_export()
        with patch.dict(self.registry.methods['F01'],{'challenge_prompt':'changed task at same version'}):
            with self.assertRaisesRegex(ValueError,'stale'): verify(result['output'],self.registry)

    def test_legacy_material_without_challenge_binding_cannot_be_current(self):
        result=self.run_export(); output=Path(result['output']); meta_path=output/'facilitator.json'
        meta=json.loads(meta_path.read_text()); del meta['teaching_binding_scope']; self.save(meta_path,meta)
        with self.assertRaisesRegex(ValueError,'stale'): verify(output,self.registry)

    def test_no_forced_absent_dimension_in_current_f01_instruction(self):
        method=self.registry.methods['F01']
        self.assertIn('若某一维没有区别',method['challenge_prompt'])
        self.assertIn('若某一维没有区别',method['compact']['90s'])
        self.assertNotIn('说出哪一维没有区分度',method['challenge_prompt'])
        self.assertNotIn('指出一个无区分度',method['compact']['90s'])

    def test_batch_refresh_preserves_old_drafts_and_rejects_collected_values(self):
        from scripts.refresh_first_use_drafts import refresh
        result=self.run_export(); old=Path(result['output']); original=(old/'student-material.md').read_bytes()
        index=old.parent/'CURRENT_DRAFTS.json'
        self.save(index,{'source_commit':self.registry.index['source_baseline']['commit'],
                         'current_kits':{'F01':old.name}})
        with patch('scripts.refresh_first_use_drafts.ROOT',self.root):
            updated=refresh(index,'test-v2',self.registry)
            self.assertFalse(updated['collection_allowed'])
            self.assertEqual((old/'student-material.md').read_bytes(),original)
            self.assertEqual(verify(old.with_name(old.name+'-test-v2'),self.registry)['binding_check'],'PASS')
            with self.assertRaisesRegex(ValueError,'index already exists'): refresh(index,'test-v2',self.registry)
            meta_path=old/'facilitator.json'; meta=json.loads(meta_path.read_text())
            meta['first_use_test']['action_success']=False; self.save(meta_path,meta)
            with self.assertRaisesRegex(ValueError,'collected'): refresh(index,'test-v3',self.registry)

    def assert_invalid_batch_preflight(self,change,message):
        import hashlib
        from scripts.refresh_first_use_drafts import refresh
        old=Path(self.run_export()['output'])
        gdemo=self.root/'grammar-demo.json';gtransfer=self.root/'grammar-transfer.json';gwalk=self.root/'grammar-walkthrough.json'
        for path,qid,passage in [(gdemo,'synthetic-gdemo','synthetic grammar one'),(gtransfer,'synthetic-gtransfer','synthetic grammar two')]:
            self.save(path,{'question_id':qid,'question_type':'语法填空','stem':'synthetic grammar blank','passage':passage,'given_word':'solid'})
        self.save(gwalk,{'method_id':'G01','method_version':self.registry.methods['G01']['version'],
                        'source_commit':self.registry.index['source_baseline']['commit'],'question_id':'synthetic-gdemo',
                        'demonstration_question_sha256':question_fingerprint(read_question(gdemo)[0]),
                        'first_action':'synthetic action','evidence':'synthetic evidence','output':'synthetic output',
                        'stop':'synthetic stop','review_scope':'ai_authored_draft_not_learner_validation'})
        other=self.root/'local-data/grammar-kit'
        prepare('G01',gdemo,gtransfer,gwalk,other,self.registry)
        data=json.loads(gtransfer.read_text());data.update(change);self.save(gtransfer,data)
        meta_path=other/'facilitator.json';meta=json.loads(meta_path.read_text())
        meta['source_refs'][1]['sha256']=hashlib.sha256(gtransfer.read_bytes()).hexdigest()
        # Deliberately invalid raw fixture: do not validate it during setup.
        # The assertion below must reach the refresh batch preflight itself.
        meta['source_refs'][1]['question_sha256']=question_fingerprint(data);self.save(meta_path,meta)
        old_files={p:p.read_bytes() for kit in [old,other] for p in kit.iterdir()}
        index=old.parent/'CURRENT_DRAFTS.json'
        self.save(index,{'source_commit':self.registry.index['source_baseline']['commit'],'current_kits':{'F01':old.name,'G01':other.name}})
        with patch('scripts.refresh_first_use_drafts.ROOT',self.root):
            with self.assertRaisesRegex(ValueError,message):refresh(index,'preflight-v2',self.registry)
        self.assertFalse(old.with_name(old.name+'-preflight-v2').exists())
        self.assertFalse(other.with_name(other.name+'-preflight-v2').exists())
        self.assertFalse(index.with_name('CURRENT_DRAFTS-preflight-v2.json').exists())
        for p,raw in old_files.items():self.assertEqual(p.read_bytes(),raw)

    def test_batch_preflight_rejects_later_invalid_pair_before_any_new_kit(self):
        self.assert_invalid_batch_preflight({'passage':'synthetic\ngrammar one'},'different passage')

    def test_batch_preflight_rejects_later_render_failure_before_any_new_kit(self):
        self.assert_invalid_batch_preflight({'student_draft':['synthetic text']},'student draft')

    def test_f01_core_rules_unchanged_from_pre_revision_snapshot(self):
        from copy import deepcopy
        from core.registry import ROOT
        original=json.loads((ROOT/'provenance/student-entry-revisions/F01-1.2.0-before-conditional-challenge.json').read_text(encoding='utf-8'))['method']
        current=self.registry.methods['F01']
        for key in ('version','core_action','trigger_cues','decision_rule','stop_rule','primary_role','four_step_card'):
            self.assertEqual(current[key],original[key],key)
        history=Registry(snapshot_commit=original['source_alignment']['commit'])
        old_sections=[history.sources['sections'][sid] for sid in original['full']['section_ids']]
        new_sections=[self.registry.sources['sections'][sid] for sid in current['full']['section_ids']]
        self.assertEqual(len(new_sections),len(old_sections))
        for old,new in zip(old_sections,new_sections):
            self.assertEqual({key:new[key] for key in ('path','heading','content')},
                             {key:old[key] for key in ('path','heading','content')})
        expected_full=deepcopy(original['full'])
        expected_full['section_ids']=list(current['full']['section_ids'])
        if self.registry.index['source_baseline']['commit']=='70db6d6f0423bc8da95c591ca1feda883c2865b1':
            from scripts.align_answer_20261030 import NOTES
            expected_full['source_update_note']=NOTES['F']
        # Optional presentation support cannot change any existing full-card
        # rule, boundary or source binding. Check additions separately rather
        # than requiring the old full object to have no new optional fields.
        support_keys={'beginner_support','presentation_revision'}
        self.assertEqual({key:value for key,value in current['full'].items()
                          if key not in support_keys},expected_full)
        if 'beginner_support' in current['full']:
            self.assertEqual(current['full']['presentation_revision'],'2026-10-28.2')
            self.assertTrue(current['full']['beginner_support']['first_micro_action'])
            self.assertIn('无区分度',current['full']['beginner_support']['short_stop']+
                          current['compact']['30s'])
        self.assertNotEqual(current['challenge_prompt'],original['challenge_prompt'])

    def test_new_export_includes_bound_beginner_support_without_observations(self):
        result=self.run_export(); output=Path(result['output'])
        meta=json.loads((output/'facilitator.json').read_bytes())
        text=(output/'student-material.md').read_text(encoding='utf-8')
        support=self.registry.methods['F01']['full']['beginner_support']
        self.assertEqual(meta['teaching_binding_scope'],'first_use_card_challenge_and_support_v3')
        for key in ['first_micro_action','prerequisite','if_stuck','micro_action_is_not_completion']:
            self.assertIn(support[key],text)
        self.assertTrue(all(value is None for value in meta['first_use_test'].values()))
        self.assertFalse(meta['collection_allowed'])
        self.assertNotIn('SECRET',text)
        self.assertNotIn(support['first_micro_action'],text.split('## 第二道题')[1])

    def test_same_semantic_version_changed_support_invalidates_new_kit(self):
        result=self.run_export()
        support=self.registry.methods['F01']['full']['beginner_support']
        with patch.dict(support,{'first_micro_action':'synthetic changed first action'}):
            with self.assertRaisesRegex(ValueError,'stale'):
                verify(result['output'],self.registry)

    def test_absent_support_preserves_exact_v2_fingerprint_and_projection(self):
        from scripts.prepare_first_use_materials import teaching_fingerprint,teaching_binding_scope,render_student_material
        method=json.loads(json.dumps(self.registry.methods['F01']))
        method['full'].pop('beginner_support')
        method['full'].pop('presentation_revision')
        fields={key:method[key] for key in ('method_id','version','brand_name','student_symptoms',
                'four_step_card','primary_role','output_type','section_ids','challenge_prompt')}
        self.assertEqual(teaching_fingerprint(method),question_fingerprint(fields))
        self.assertEqual(teaching_binding_scope(method),'first_use_card_and_challenge_v2')
        demo,_=read_question(self.demo); transfer,_=read_question(self.transfer)
        walkthrough=json.loads(self.walkthrough.read_bytes())
        text=render_student_material(method,demo,transfer,walkthrough)
        self.assertNotIn('先做一小步',text)
        self.assertIn('第一刀：'+method['four_step_card']['first_cut'],text)

    def test_unused_example_does_not_rebind_first_use_material(self):
        from scripts.prepare_first_use_materials import teaching_fingerprint
        method=self.registry.methods['F01']
        before=teaching_fingerprint(method)
        with patch.dict(method['full']['beginner_support'],{'example':'unused synthetic illustration'}):
            self.assertEqual(teaching_fingerprint(method),before)

    def test_v2_scope_cannot_wrap_new_support_even_with_current_hash(self):
        result=self.run_export(); output=Path(result['output'])
        path=output/'facilitator.json'; meta=json.loads(path.read_bytes())
        meta['teaching_binding_scope']='first_use_card_and_challenge_v2'
        self.save(path,meta)
        with self.assertRaisesRegex(ValueError,'stale'):
            verify(output,self.registry)

    def test_incomplete_support_fails_before_new_kit_is_created(self):
        support=self.registry.methods['F01']['full']['beginner_support']
        output=self.root/'local-data/missing-support'
        with patch.dict(support,{'first_micro_action':''}):
            with self.assertRaisesRegex(ValueError,'Beginner support'):
                self.run_export(output)
        self.assertFalse(output.exists())


if __name__=='__main__': unittest.main()
