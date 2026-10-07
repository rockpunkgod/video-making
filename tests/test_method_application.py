"""Program-only fixtures; no invented real teaching reviews or questions."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import unittest

from core.registry import Registry
from core.analyzer import QuestionAnalyzer
from answer_engine.frozen_export import FrozenAssetExporter
from answer_engine.method_application_export import FrozenMethodApplicationExporter
from video_contracts import sha, seal
from video_contracts.method_application import require_current_application
from tests.test_execution import fixture
from creative_os.semantic_text_layout import layout_words, bind_words


class MethodApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r=Registry();q=fixture();a=QuestionAnalyzer(r).analyze(q)
        request=dict(question=q,analysis=a,methods=[deepcopy(r.methods[mid]) for mid in a['method_versions']],
            reviews=[dict(question_id=q['question_id'],input_sha256=sha(q),analysis_sha256=sha(a),
                reviewer='SYNTHETIC PROGRAM ONLY',reviewer_kind='AI',evaluation_phase='post_reveal')],
            withdrawals=[],evaluation_phase='post_reveal',source=dict(usage_status='internal_only',
                redistribution_status='unconfirmed',source_reference='SYNTHETIC',attribution_text='SYNTHETIC'))
        cls.b=FrozenAssetExporter().export(request);cls.st=FrozenAssetExporter().status(request)
        cls.annotation=dict(action_index=1,review_indices=[0],source_region=a['execution_trace'][1]['evidence'][0],
            spans=[dict(span_id='whole',field='passage',start=0,end=16,quote='alpha beta gamma',semantic_role='core',
                assertion=dict(field='concrete_action',quote='program-only observable action meaning'))],
            reduced_span_ids=['whole'],deferred_span_ids=[],protected_span_ids=['whole'],relations=[])

    def export(self, annotation=None, status=None):
        return FrozenMethodApplicationExporter().export(self.b,self.st if status is None else status,
                                                      self.annotation if annotation is None else annotation,'one')

    def test_readonly_replay_and_ai_credential(self):
        before=sha([self.b,self.st,self.annotation])
        with patch.object(QuestionAnalyzer,'analyze',side_effect=AssertionError('must not solve')):
            a=self.export();b=FrozenMethodApplicationExporter().export(self.b,self.st,self.annotation,'two')
        self.assertEqual(before,sha([self.b,self.st,self.annotation]))
        self.assertEqual(a['semantic_binding_sha'],b['semantic_binding_sha'])
        self.assertNotEqual(a['envelope_sha'],b['envelope_sha'])
        self.assertEqual(a['semantic_review']['level'],'ai_reviewed')
        self.assertFalse(a['semantic_review']['independent_human_certified'])
        self.assertFalse(a['public_render_ready'])
        self.assertEqual(a['payload']['actual_action'],self.b['analysis']['execution_trace'][1])

    def test_current_status_and_withdrawal(self):
        for state in ('WITHDRAWN','SUPERSEDED','STALE','BLOCKED','INCOMPLETE'):
            s=seal(dict(self.st,effective_status=state))
            with self.assertRaises(ValueError):self.export(status=s)
        with self.assertRaises(ValueError):require_current_application(self.export(),self.b,None)

    def test_tamper_and_borrowed_method_assertion(self):
        a=deepcopy(self.annotation);a['spans'][0]['assertion']['quote']='program-only observable action loc'
        with self.assertRaisesRegex(ValueError,'own existing action assertion'):self.export(a)
        a=deepcopy(self.annotation);a['action_index']=2
        with self.assertRaisesRegex(ValueError,'auxiliary'):self.export(a)
        result=self.export();result['payload']['method']['primary_role']='decider';result=seal(result)
        with self.assertRaises(ValueError):require_current_application(result,self.b,self.st)

    def test_full_partition_and_protected_conditions(self):
        a=deepcopy(self.annotation);a['spans'][0].update(end=5,quote='alpha')
        with self.assertRaisesRegex(ValueError,'drops source'):self.export(a)
        a=deepcopy(self.annotation);a['spans'][0]['quote']='wrong'
        with self.assertRaisesRegex(ValueError,'partition'):self.export(a)
        a=deepcopy(self.annotation);a['deferred_span_ids']=['whole']
        with self.assertRaisesRegex(ValueError,'reversible'):self.export(a)
        a=deepcopy(self.annotation);a['spans'][0]['semantic_role']='condition'
        a['spans'].append(dict(a['spans'][0],span_id='tail',start=6,end=16,quote='beta gamma',semantic_role='core'))
        a['spans'][0].update(end=6,quote='alpha ')
        a.update(reduced_span_ids=['tail'],protected_span_ids=['tail'],deferred_span_ids=['whole'])
        with self.assertRaisesRegex(ValueError,'conditions'):self.export(a)

    def test_dangling_review_or_relation(self):
        a=deepcopy(self.annotation);a['review_indices']=[99]
        with self.assertRaisesRegex(ValueError,'review'):self.export(a)
        a=deepcopy(self.annotation);a['relations']=[dict(from_span_id='other',to_span_ids=['whole'],
            assertion=dict(field='concrete_action',quote='program-only'))]
        with self.assertRaisesRegex(ValueError,'Relation'):self.export(a)

    def test_layout_offsets_and_ambiguous_span_boundary(self):
        font=Path('C:/Windows/Fonts/georgia.ttf')
        if not font.exists():font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        if not font.exists():self.skipTest('No local measurement font')
        text='alpha beta\ngamma';words=layout_words(text,str(font),30,120)
        self.assertEqual([text[w['start']:w['end']] for w in words],['alpha','beta','gamma'])
        self.assertGreater(words[-1]['line'],words[0]['line'])
        with self.assertRaisesRegex(ValueError,'Partially'):
            bind_words(words,[dict(span_id='bad',start=1,end=5)])
