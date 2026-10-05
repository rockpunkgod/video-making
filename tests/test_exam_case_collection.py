"""Invented controls only, not real Case or learner certification."""
import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
from scripts.collect_exam_cases import material_equal,host_items,own_candidates,public_metadata,review_summary
from scripts.ingest_exam_sources import freeze_json,sha

class ExamCaseCollectionTest(unittest.TestCase):
    def test_host_pass_and_immutable_material_gate(self):
        with self.assertRaisesRegex(ValueError,'Not a frozen'): host_items({'pass':'reveal'})
        original={'question_id':'CONTROL','passage':'PROGRAM ONLY'}
        material_equal(original,{**original,'observations':[]})
        for changed in [{**original,'passage':'changed'},{**original,'options':{}},{'question_id':'CONTROL'}]:
            with self.subTest(changed=changed),self.assertRaisesRegex(ValueError,'original material'):
                material_equal(original,changed)

    def fixture(self):
        registry=SimpleNamespace(methods={'M':{'version':'CONTROL','question_type':'阅读理解',
            'primary_role':'decider','output_type':'decide','stop_rule':'PROGRAM STOP','section_ids':['CONTROL']}})
        question={'question_id':'CONTROL','question_type':'阅读理解','passage':'DO NOT EXPORT BODY',
            'observations':[{'method_id':'M','reviewed':True,'evidence':[]}]}
        analysis={'content_eligible':True,'execution_trace':[],
            'method_matches':[{'method_id':'M','trigger_verified':True}],
            'candidate_analysis':[{'method_id':'M','candidate':'A','effect':'eliminate'}],
            'evidence_graph':{'DO NOT EXPORT GRAPH':True}}
        return registry,question,analysis

    def test_decision_without_observable_action_is_not_complete_case(self):
        r,q,a=self.fixture(); rows=own_candidates(q,a,r)
        self.assertEqual(rows[0]['candidate_status'],'needs_action_recording')
        self.assertFalse(rows[0]['observable_action_recorded'])
        self.assertIsNone(rows[0]['case_type'])

    def test_no_borrowed_answer_or_suggestion_or_stopped_action_credit(self):
        r,q,a=self.fixture()
        for change in [{'content_eligible':False},{'candidate_analysis':[]},
                       {'method_matches':[{'method_id':'M','trigger_verified':False}]},
                       {'execution_trace':[{'method_id':'M','state':'stopped'}]}]:
            with self.subTest(change=change): self.assertEqual(own_candidates(q,{**a,**change},r),[])

    def test_observable_produced_action_enters_review_not_registry(self):
        r,q,a=self.fixture(); a['execution_trace']=[{'method_id':'M','state':'produced','concrete_action':'PROGRAM ONLY'}]
        rows=own_candidates(q,a,r)
        self.assertEqual(rows[0]['candidate_status'],'pending_case_review')
        self.assertEqual(rows[0]['registry_registration'],'not_registered')

    def test_public_metadata_does_not_export_body_graph_or_claim_success(self):
        r,q,a=self.fixture()
        report={'exam_id':'CONTROL','stage':'CONTROL','written_question_count':1,
                'reviewed_question_ids':['CONTROL'],'host_prediction_sha256':'CONTROL',
                'case_candidates':own_candidates(q,a,r)}
        value=public_metadata(report)
        self.assertNotIn('DO NOT EXPORT',str(value))
        self.assertEqual(value['case_slots_filled'],0)
        self.assertEqual(value['semantic_certification'],'not_certified')

    def test_post_reveal_review_hash_timing_and_question_bindings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); exam='CONTROL'; r,q,a=self.fixture()
            host=root/'predictions'/exam/'reviewed-blind.json'; freeze_json(host,{'PROGRAM ONLY':True})
            report={'exam_id':exam,'stage':'post_reveal','written_question_count':1,
                'reviewed_question_ids':['CONTROL'],'host_prediction_sha256':sha(host.read_bytes()),
                'case_candidates':own_candidates(q,a,r)}
            freeze_json(root/'case-review'/exam/'candidates.json',report)
            review_path=root/'semantic-reviews'/ (exam+'.json')
            for extra in [{'stage':'pre_reveal'},{'question_id':'foreign'},{'reviewed_prediction_sha256':'wrong'}]:
                review={'exam_id':exam,'question_id':'CONTROL','stage':'post_reveal',
                    'reviewed_prediction_sha256':report['host_prediction_sha256'],**extra}
                # Disposable test fixture; not a frozen real exam overwrite.
                review_path.parent.mkdir(parents=True,exist_ok=True)
                from unittest.mock import patch
                real=Path.read_bytes
                with patch.object(Path,'is_file',return_value=True),patch.object(Path,'read_bytes',autospec=True) as read:
                    read.side_effect=lambda p: json.dumps(review).encode() if p==review_path else real(p)
                    with self.subTest(extra=extra),self.assertRaisesRegex(ValueError,'actual post-reveal'):
                        review_summary(root,exam)

    def test_own_action_revision_does_not_rewrite_frozen_host_candidate_or_approve_type(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); exam='CONTROL'; r,q,a=self.fixture()
            host=root/'predictions'/exam/'reviewed-blind.json'; freeze_json(host,{'PROGRAM ONLY':True})
            report={'exam_id':exam,'stage':'post_reveal','written_question_count':1,
                'reviewed_question_ids':['CONTROL'],'host_prediction_sha256':sha(host.read_bytes()),
                'case_candidates':own_candidates(q,a,r)}
            candidate_path=root/'case-review'/exam/'candidates.json'; freeze_json(candidate_path,report)
            before=candidate_path.read_bytes()
            review={'exam_id':exam,'question_id':'CONTROL','stage':'post_reveal',
                'reviewed_prediction_sha256':report['host_prediction_sha256'],
                'method_reviews':[{'method_id':'M','method_version':'CONTROL','unique_case_type_candidate':'canonical'}]}
            freeze_json(root/'semantic-reviews'/(exam+'.json'),review)
            revision={'question_id':'CONTROL','method_id':'M','method_version':'CONTROL',
                'stage':'post_reveal_bounded_action_review','produced_action_count':1,
                'answer_withheld':True,'case_slots_filled':0}
            with patch('scripts.collect_action_reviews.load_metadata',return_value=[revision]):
                result=review_summary(root,exam)
                index=root/'case-review'/exam/'review-index.json'; frozen=index.read_bytes()
                self.assertEqual(review_summary(root,exam),result)
                self.assertEqual(index.read_bytes(),frozen)
            candidate=result['candidates'][0]
            self.assertFalse(candidate['observable_action_recorded'])  # Original host snapshot.
            self.assertEqual(candidate['post_reveal_own_action_revision'],revision)
            self.assertIsNone(candidate['case_type'])
            self.assertEqual(result['case_slots_filled'],0)
            self.assertEqual(candidate_path.read_bytes(),before)
            self.assertNotIn('post_reveal_own_action_revision',json.loads(frozen)['candidates'][0])
            wrong={**revision,'method_version':'different-version'}
            with patch('scripts.collect_action_reviews.load_metadata',return_value=[wrong]):
                self.assertNotIn('post_reveal_own_action_revision',review_summary(root,exam)['candidates'][0])
