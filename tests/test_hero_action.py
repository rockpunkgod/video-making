"""Synthetic data only: visual continuity cannot change teaching ownership."""
from copy import deepcopy
import unittest

from creative_os.delivery import copy_sha, screen_sha
from creative_os.hero import build_contract, validate_contract
from creative_os.hero_action import make_action_hero
from tests import test_hero_narratives
from video_contracts import sha, seal


class ActionHeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_hero_narratives.NarrativeTests.setUpClass()

    def setUp(self):
        fixture = test_hero_narratives.NarrativeTests(); fixture.setUp()
        self.f = fixture.f
        nodes = [n for n in fixture.base['nodes'] if n['node_id'] != 'METHOD_ID']
        ids = {n['unit_id'] for n in nodes}
        self.excerpt = deepcopy(fixture.excerpt)
        self.excerpt['units'] = [u for u in self.excerpt['units'] if u['unit_id'] in ids]
        self.excerpt['delivery_copy_sha'] = copy_sha(self.excerpt)
        self.excerpt['screen_copy_sha'] = screen_sha(self.excerpt)
        f = self.f
        self.base = build_contract(f.package, f.manifest, f.statuses, f.full,
            self.excerpt, {}, nodes, [{'start':0, 'end':14.75, 'phase':'HOLD'}], 14.75)

    def build(self, statuses=None):
        f = self.f
        return make_action_hero(self.base, f.package, f.manifest,
            f.statuses if statuses is None else statuses, f.full, self.excerpt, 12)

    def test_replay_preserves_copy_ownership_and_inputs(self):
        before = sha([self.base, self.f.package, self.excerpt])
        result = self.build()
        self.assertEqual(result, self.build())
        self.assertEqual(before, sha([self.base, self.f.package, self.excerpt]))
        projection = lambda c: [(n['text'], n['unit_id']) for n in c['nodes'] if n['kind']=='text']
        self.assertEqual(projection(result), projection(self.base))
        self.assertEqual(result['copy_lock'], self.base['copy_lock'])
        self.assertFalse(result['public_render_ready'])

    def test_source_remains_fixed_through_all_judgments(self):
        result = self.build(); nodes = {n['node_id']: n for n in result['nodes']}
        for key, node in nodes.items():
            if key.startswith('EVIDENCE_'):
                self.assertEqual((node['in_point'],node['out_point']), (0,14.75))
                self.assertFalse(node.get('tracks'))
        annotations = [n for n in nodes.values() if 'annotation_refs' in n]
        self.assertTrue(annotations)
        for node in annotations:
            self.assertTrue(set(node['annotation_refs']) <= set(nodes))
        self.assertTrue(any('width' in n.get('tracks',{}) for n in annotations))
        # Full contract validation checks both declared holds, not just key counts.
        f = self.f
        validate_contract(result, f.package, f.manifest, f.statuses, f.full, self.excerpt)

    def test_withdrawn_source_and_unexpected_role_fail_closed(self):
        statuses = deepcopy(self.f.statuses)
        for key, value in statuses.items():
            value['effective_status'] = 'WITHDRAWN'; statuses[key] = seal(value)
        with self.assertRaises(ValueError): self.build(statuses)
        self.base['nodes'][0]['node_id'] = 'UNKNOWN'
        self.base.pop('render_contract_sha'); self.base['render_contract_sha'] = sha(self.base)
        with self.assertRaisesRegex(ValueError, 'exact consumer Hero roles'): self.build()
