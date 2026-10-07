"""Program-only passage/CLI/overload integration, not semantic certification."""
from copy import deepcopy
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.analyzer import QuestionAnalyzer
from core.registry import Registry
from answer_engine.frozen_export import FrozenAssetExporter
from tests.test_execution import seven_chain_fixture
from tests import test_pedagogy as fixture_module
from video_contracts import sha, seal, read, write
from video_contracts import passage
from pedagogy import compile_plan, validate_plan, copy_projection, validate_handoff
from pedagogy.__main__ import main


def frozen_passage():
    """Explicitly synthetic assertions; no invented actual exam or human review."""
    quote = {'field': 'passage', 'start': 0, 'end': 16, 'quote': 'alpha beta gamma'}
    method = {'method_id': 'R02', 'version': '1.0.0', 'primary_role': 'interpreter',
        'brand_name': 'SYNTHETIC relation operation', 'core_action': 'SYNTHETIC first action',
        'decision_rule': 'SYNTHETIC local check', 'stop_rule': 'SYNTHETIC stop here',
        'trigger_cues': ['SYNTHETIC signal'], 'student_symptoms': ['SYNTHETIC symptom'],
        'four_step_card': {'start': 'SYNTHETIC signal', 'first_cut': 'SYNTHETIC first action',
                           'judge': 'SYNTHETIC local check', 'stop': 'SYNTHETIC stop here'},
        'compact': {'line': 'SYNTHETIC executable memory phrase'}, 'status': 'candidate'}
    packet = {'lesson_id': 'SYNTHETIC-PROGRAM-ONLY', 'passage': quote['quote'],
        'questions': [{'question_id': 'synthetic-q', 'number': 1, 'stem': 'SYNTHETIC original question',
                       'options': {'A': 'alpha', 'B': 'beta'}}], 'methods': [method],
        'source': {'usage_status': 'internal_only', 'redistribution_status': 'unconfirmed',
                   'source_reference': 'SYNTHETIC', 'attribution_text': 'SYNTHETIC'},
        'review': {'reviewer': 'SYNTHETIC AI HOST ONLY', 'reviewer_kind': 'ai_host',
            'status': 'reviewed', 'evaluation_phase': 'post_reveal', 'material_sha': '0' * 64,
            'decisions': [{'question_id': 'synthetic-q', 'candidate': c, 'effect': effect,
                'basis': 'direct_text_review', 'method_id': None, 'rationale': 'SYNTHETIC comparison',
                'evidence': [quote]} for c, effect in [('A', 'retain'), ('B', 'eliminate')]],
            'method_actions': [{'action_id': 'synthetic-action', 'question_id': 'synthetic-q',
                'method_id': 'R02', 'method_version': '1.0.0', 'role': 'interpreter',
                'output': 'SYNTHETIC actual local output', 'evidence': [quote],
                'stop_rule': 'SYNTHETIC stop here', 'answer': None}],
            'order': ['synthetic-q'], 'order_rationale': 'SYNTHETIC single question',
            'segments': []}}
    for sid, kind, refs in [('synthetic-action-segment', 'action', []),
                            ('synthetic-closure-segment', 'closure', [0, 1]),
                            ('synthetic-stop-segment', 'boundary', [])]:
        packet['review']['segments'].append({'segment_id': sid, 'question_id': 'synthetic-q',
            'kind': kind, 'text': 'SYNTHETIC narration', 'screen_text': 'SYNTHETIC screen',
            'evidence': [quote], 'action_refs': ['synthetic-action'], 'decision_refs': refs,
            'fidelity_reviewed': True})
    packet['review']['material_sha'] = sha(passage.material(packet))
    bundle = passage.export_bundle(packet, 'synthetic')
    return bundle, passage.status_manifest(bundle, 'synthetic'), {'method_id': 'R02', 'action_ids': ['synthetic-action']}


class PedagogyWorkflowTests(unittest.TestCase):
    def test_reviewed_passage_projects_one_bound_action_without_method_answer_credit(self):
        b, s, selection = frozen_passage()
        before = sha([b, s])
        p = compile_plan(b, s, selection, mode='worked_example')
        self.assertEqual(p['availability']['status'], 'READY')
        self.assertEqual(p['input_binding']['transport'], 'reviewed_passage')
        self.assertEqual(p['answer_scope']['upstream_answer'], 'A')
        self.assertIsNone(p['answer_scope']['answer'])
        self.assertEqual(p['role'], 'interpreter')
        self.assertEqual([x['kind'] for x in p['student_steps']],
                         ['question', 'observation', 'action', 'evidence', 'judgment', 'stop'])
        self.assertTrue(validate_plan(p, b, s)['consumption_allowed'])
        self.assertEqual(before, sha([b, s]))
        cp = copy_projection(p, b, s)
        validate_handoff(cp, p, b, s)
        with self.assertRaises(ValueError):
            validate_handoff(cp, p, b, passage.status_manifest(b, 'withdrawn', 'WITHDRAWN'))

    def test_raw_original_question_and_evidence_are_not_rewritten(self):
        b, s, selection = frozen_passage()
        p = compile_plan(b, s, selection, mode='worked_example')
        question = next(x['item'] for x in p['student_steps'] if x['kind'] == 'question')
        evidence = next(x['item'] for x in p['student_steps'] if x['kind'] == 'evidence')
        self.assertEqual(question['text'], b['payload']['questions'][0]['stem'])
        self.assertEqual(evidence['text'], b['payload']['passage'])
        self.assertEqual(evidence['projection_operation'], 'literal_source_v1')

    def test_four_actions_are_overload_even_if_all_actions_exist(self):
        registry = Registry()
        q = seven_chain_fixture()
        extra = deepcopy(q['action_executions'][0]); extra['execution_id'] = 'group-extra'
        q['action_executions'].insert(3, extra)
        for a in q['action_executions']:
            if a['method_id'] == 'F01':
                a['stop_rule_check'] = registry.methods['F01']['stop_rule']
        a = QuestionAnalyzer(registry).analyze(q)
        request = {'question': q, 'analysis': a,
            'methods': [deepcopy(registry.methods[mid]) for mid in a['method_versions']],
            'reviews': [{'question_id': q['question_id'], 'input_sha256': sha(q), 'analysis_sha256': sha(a),
                'reviewer': 'SYNTHETIC ONLY', 'reviewer_kind': 'AI', 'evaluation_phase': 'post_reveal'}],
            'withdrawals': [], 'evaluation_phase': 'post_reveal',
            'source': {'usage_status': 'internal_only', 'redistribution_status': 'unconfirmed',
                       'source_reference': 'SYNTHETIC', 'attribution_text': 'SYNTHETIC'}}
        exp = FrozenAssetExporter(); b, s = exp.export(request), exp.status(request)
        p = compile_plan(b, s, {'method_id': 'F01',
            'action_ids': ['group-sentence', 'group-actor', 'group-time', 'group-extra']})
        self.assertEqual(p['availability']['status'], 'HOLD')
        self.assertIn('core_actions', p['cognitive_load']['exceeded'])
        self.assertIn('primary_evidence_cluster', p['cognitive_load']['exceeded'])
        with self.assertRaises(ValueError):
            copy_projection(p, b, s)

    def test_status_lifecycle_and_method_versions_are_rechecked(self):
        helper = fixture_module.PedagogyTests(); helper.registry = Registry(); helper.engine = QuestionAnalyzer(helper.registry)
        b, s, selection = helper.assets('G01')
        p = compile_plan(b, s, selection, mode='worked_example')
        for field in ('action', 'review', 'method'):
            st = deepcopy(s)
            if field == 'action':
                st['lifecycle']['actions'][0]['status'] = 'withdrawn'
            elif field == 'review':
                st['lifecycle']['reviews'][0]['status'] = 'withdrawn'
            else:
                st['method_versions']['G01'] = '99.0.0'
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_plan(p, b, seal(st))

    def test_cli_compile_reload_handoff_and_no_history_overwrite(self):
        b, s, selection = frozen_passage()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / 'bundle.json', b); write(root / 'status.json', s)
            request = {'bundle': 'bundle.json', 'status': 'status.json', 'selection': selection,
                       'mode': 'worked_example', 'output': 'plan.json'}
            write(root / 'compile-request.json', request)
            with patch('sys.argv', ['pedagogy', 'compile', str(root / 'compile-request.json')]), contextlib.redirect_stdout(io.StringIO()):
                main()
            self.assertTrue((root / 'plan.json').exists())
            with patch('sys.argv', ['pedagogy', 'compile', str(root / 'compile-request.json')]), self.assertRaises(ValueError):
                main()
            write(root / 'handoff-request.json', {'bundle': 'bundle.json', 'status': 'status.json',
                'plan': 'plan.json', 'copy_output': 'copy.json', 'motion_output': 'motion.json'})
            with patch('sys.argv', ['pedagogy', 'handoff', str(root / 'handoff-request.json')]), contextlib.redirect_stdout(io.StringIO()):
                main()
            self.assertTrue((root / 'copy.json').exists() and (root / 'motion.json').exists())
            cp = read(root / 'copy.json')
            validate_handoff(cp, read(root / 'plan.json'), b, s)
            write(root / 'status.json', passage.status_manifest(b, 'withdrawn', 'WITHDRAWN'))
            with patch('sys.argv', ['pedagogy', 'handoff', str(root / 'handoff-request.json')]), self.assertRaises(ValueError):
                main()


if __name__ == '__main__':
    unittest.main()
