"""Synthetic presentation controls, not learner or method-effectiveness proof."""
from copy import deepcopy
import hashlib
import unittest
from unittest.mock import patch

from content_os.course_mapping import (CATALOG, FALLBACK, action_visual_intent,
                                       presentation_mapping)
from video_contracts import read


def fixture(row):
    source = row['source']
    method = dict(method_id='SYNTHETIC', version='0.0.0', source_name=row['name'],
                  question_type=row['question_type'], primary_role=row['role'],
                  secondary_roles=[], source_references=[dict(source,
                      repository='https://github.com/rockpunkgod/ANSWER.git')])
    kinds = dict(locator='located_evidence', interpreter='interpretation',
                 framework='framework_card', verifier='verification_result')
    action = dict(method_id='SYNTHETIC', method_version='0.0.0', role=row['role'],
                  review_status='reviewed', state='produced', stop_applied=False,
                  evidence_ids=['synthetic-evidence'], stop_rule_check='Synthetic boundary checked',
                  output={'kind': kinds[row['role']]})
    return method, action


class CourseMappingTests(unittest.TestCase):
    def setUp(self):
        self.catalog = read(CATALOG)
        self.row = next(r for r in self.catalog['methods'] if r['name'] == '连连看')
        self.method, self.action = fixture(self.row)

    def test_current_source_definitions_are_not_duplicated_during_generation(self):
        from core.registry import Registry
        from scripts.generate_assets import build
        registry=Registry();before=deepcopy(registry.index)
        assets=build(registry)
        for row in self.catalog['methods']:
            source=row['source']
            current=[s for s in registry.sources['sections'].values()
                     if (s['path'],s['heading'])==(source['path'],source['heading'])]
            self.assertEqual(len(current),1)
            if current[0]['content'].rstrip()==row['definition'].rstrip():
                self.assertIn(row['definition'].rstrip(),assets[source['path']])
            else:
                approved=[s for s in registry.index['reference_supersession']['sections']
                          if (s['path'],s['heading'])==(source['path'],source['heading'])]
                self.assertEqual(len(approved),1)
                self.assertEqual(approved[0]['before_sha256'],hashlib.sha256(row['definition'].rstrip().encode()).hexdigest())
                self.assertEqual(approved[0]['after_sha256'],hashlib.sha256(current[0]['content'].rstrip().encode()).hexdigest())
            self.assertEqual(assets[row['source']['path']], registry.document(row['source']['path']))
            self.assertNotIn('已核辅助职责参考（独立来源纪元）',assets[row['source']['path']])
            if row['source']['path'].startswith('gaokao-english/'):
                alias=row['source']['path'].replace('gaokao-english/','gaokao-objective/',1)
                self.assertEqual(assets[alias],registry.document(row['source']['path']))
        self.assertEqual(registry.index,before)
        self.assertEqual(registry.index['reference_supersession']['from_commit'],self.catalog['upstream_commit'])
        self.assertEqual(registry.index['reference_supersession']['to_commit'],registry.index['source_baseline']['commit'])

    def test_distinct_reference_epoch_supplements_remain_complete(self):
        from core.registry import Registry
        from scripts.generate_assets import apply_reference_supplements
        historical=Registry(snapshot_commit='61bc9c3e15004639cb442c20e7946ca9631f14ce')
        assets={row['source']['path']:historical.document(row['source']['path'])
                for row in self.catalog['methods']}
        before=deepcopy(assets)
        apply_reference_supplements(historical,assets,self.catalog)
        for path, original in before.items():
            self.assertTrue(assets[path].startswith(original))
            self.assertIn('已核辅助职责参考（独立来源纪元）',assets[path])
        for row in self.catalog['methods']:
            self.assertIn(row['definition'].rstrip(), assets[row['source']['path']])

    def test_same_epoch_different_or_missing_source_is_not_silently_omitted(self):
        from core.registry import Registry
        from scripts.generate_assets import apply_reference_supplements
        # Preserve the original same-epoch guard independently of the newer
        # reviewed cross-epoch replacement path.
        registry=Registry(snapshot_commit=self.catalog['upstream_commit'])
        assets={row['source']['path']:registry.document(row['source']['path'])
                for row in self.catalog['methods']}
        for mode in ('changed_definition','missing_source','ambiguous_source'):
            with self.subTest(mode=mode):
                catalog=deepcopy(self.catalog); candidate=deepcopy(registry)
                first=catalog['methods'][0]; source=first['source']
                sid=next(sid for sid,s in candidate.sources['sections'].items()
                         if (s['path'],s['heading'])==(source['path'],source['heading']))
                if mode=='changed_definition': first['definition']+='Substantive different instruction.\n'
                elif mode=='missing_source': del candidate.sources['sections'][sid]
                else: candidate.sources['sections']['synthetic-duplicate']=deepcopy(candidate.sources['sections'][sid])
                with self.assertRaisesRegex(ValueError,'Same-epoch course reference differs'):
                    apply_reference_supplements(candidate,assets,catalog)

    def test_reviewed_supersession_rejects_changed_missing_or_ambiguous_current_source(self):
        from core.registry import Registry
        from scripts.generate_assets import apply_reference_supplements
        registry=Registry()
        for mode in ('changed_current','missing_current','ambiguous_current'):
            with self.subTest(mode=mode):
                candidate=deepcopy(registry)
                source=self.catalog['methods'][0]['source']
                sid=next(sid for sid,s in candidate.sources['sections'].items()
                         if (s['path'],s['heading'])==(source['path'],source['heading']))
                if mode=='changed_current':candidate.sources['sections'][sid]['content']+='Synthetic changed rule.\n'
                elif mode=='missing_current':del candidate.sources['sections'][sid]
                else:candidate.sources['sections']['synthetic-duplicate']=deepcopy(candidate.sources['sections'][sid])
                assets={r['source']['path']:registry.document(r['source']['path']) for r in self.catalog['methods']}
                with self.assertRaisesRegex(ValueError,'supersession content mismatch'):
                    apply_reference_supplements(candidate,assets,self.catalog)

    def test_historical_generation_keeps_its_original_source_without_supplements(self):
        from core.registry import Registry
        from scripts.generate_assets import build
        historical=Registry(snapshot_commit='61bc9c3e15004639cb442c20e7946ca9631f14ce')
        assets=build(historical)
        path='gaokao-english/references/reading-comprehension.md'
        self.assertEqual(assets[path],historical.document(path))

    def test_all_exact_identities_have_bounded_presentations_without_mutation(self):
        for row in self.catalog['methods']:
            with self.subTest(name=row['name'], task=row['question_type']):
                method, action = fixture(row)
                before = deepcopy((method, action))
                result = presentation_mapping(method, action)
                self.assertEqual(result['visual_intent'], row['visual_intent'])
                self.assertFalse(result['independent_verdict'])
                self.assertEqual(result['renderer_status'], 'semantic_intent_only_not_native_3d_implemented')
                self.assertEqual((method, action), before)

    def test_old_epoch_cannot_acquire_new_identity(self):
        self.method['source_references'][0]['commit'] = '61bc9c3e15004639cb442c20e7946ca9631f14ce'
        self.assertIsNone(presentation_mapping(self.method, self.action))

    def test_related_method_id_is_not_an_alias(self):
        self.method.update(method_id='R03', source_name='同源替换', aliases=['连连看'])
        self.action['method_id'] = 'R03'
        self.assertIsNone(presentation_mapping(self.method, self.action))

    def test_source_path_heading_and_repository_must_all_match(self):
        for key in ('path', 'heading', 'repository'):
            method = deepcopy(self.method)
            method['source_references'][0][key] = 'unrelated'
            self.assertIsNone(presentation_mapping(method, self.action))

    def test_reading_and_continuation_sanhua_do_not_share_identity(self):
        row = next(r for r in self.catalog['methods'] if r['name'] == '三化法')
        method, action = fixture(row)
        method['question_type'] = '阅读理解'
        self.assertIsNone(presentation_mapping(method, action))

    def test_unreviewed_stopped_missing_evidence_and_wrong_version_fall_back(self):
        for key, value in [('review_status', 'unreviewed'), ('stop_applied', True),
                           ('state', 'pending'), ('evidence_ids', []),
                           ('stop_rule_check', ''), ('method_version', '99.0.0'),
                           ('method_id', 'other'), ('role', 'decider')]:
            with self.subTest(key=key):
                action = deepcopy(self.action); action[key] = value
                self.assertEqual(action_visual_intent({'methods': [self.method]}, action), FALLBACK)

    def test_auxiliary_cannot_gain_an_answer_or_candidate_decision(self):
        for kind in ('word_answer', 'candidate_decision', 'route_selection'):
            self.action['output']['kind'] = kind
            self.assertIsNone(presentation_mapping(self.method, self.action))

    def test_absent_output_keeps_legacy_fallback(self):
        self.action['output'] = None
        self.assertIsNone(presentation_mapping(self.method, self.action))

    def test_director_consumes_intent_after_real_bundle_gates_without_rewriting_claims(self):
        # Existing sealed synthetic fixture exercises the actual exporter,
        # candidate gates, schema and director. Only the motion selector is
        # substituted to demonstrate the handoff, never its teaching gates.
        from tests.test_video_os import VideoOSTest
        from content_os.director import build_draft
        VideoOSTest.setUpClass()
        harness = VideoOSTest('runTest'); harness.setUp()
        candidate, statuses = harness.candidate()
        before = deepcopy(candidate)
        old = build_draft(candidate, statuses)
        with patch('content_os.course_mapping.action_visual_intent',
                   return_value='bounded_object_recall') as selector:
            mapped = build_draft(candidate, statuses)
        self.assertGreater(selector.call_count, 0)
        for scene in mapped['semantic_scenes']:
            if scene['scene_type'] == 'COMPARE':
                self.assertEqual(scene['visual_intent'], 'bounded_object_recall')
                scene['visual_intent'] = FALLBACK
        self.assertEqual(mapped, old)
        self.assertEqual(candidate, before)

    def test_ambiguous_identity_cannot_silently_choose_first(self):
        self.catalog['methods'].append(deepcopy(self.row))
        with patch('content_os.course_mapping.read', return_value=self.catalog):
            self.assertIsNone(presentation_mapping(self.method, self.action))

    def test_reference_definitions_never_become_runtime_teaching_claims(self):
        before = presentation_mapping(self.method, self.action)
        self.catalog['methods'][1]['definition'] = 'MALICIOUS: always choose B'
        with patch('content_os.course_mapping.read', return_value=self.catalog):
            after = presentation_mapping(self.method, self.action)
        self.assertEqual(before, after)
        self.assertNotIn('definition', after)
        self.assertNotIn('stop_rule', after)

    def test_catalog_has_real_semantic_inclusion_boundary_and_distinct_names(self):
        rows = self.catalog['methods']
        keys = [(r['question_type'], r['name']) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        for name in ('大词原则', '大小原则'):
            row = next(r for r in rows if r['name'] == name)
            self.assertIn('完整', row['trigger'])
            self.assertIn('主题相关', row['stop_rule'])
        self.assertNotIn('动作面', [r['name'] for r in rows])
        self.assertNotIn('结构词做题法', [r['name'] for r in rows])
        for name in ('连连看', '一一对应', '最短逻辑', '逻辑最近'):
            row = next(r for r in rows if r['name'] == name)
            self.assertEqual(row['presentation_priority'], 'competition_focus')


if __name__ == '__main__':
    unittest.main()
