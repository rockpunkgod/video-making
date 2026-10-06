"""Internal provenance must not leak into student-facing presentation."""
from copy import deepcopy
import unittest

from creative_os.consumer_copy import require_consumer_copy, project_consumer_contract
from creative_os.hero import validate_contract
from tests import test_hero_identity


class ConsumerCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_hero_identity.HeroTests.setUpClass()

    def setUp(self):
        self.f = test_hero_identity.HeroTests(); self.f.setUp()
        self.base = self.f.build()

    def project(self, edits):
        f=self.f
        return project_consumer_contract(self.base,f.package,f.manifest,f.statuses,
                                         f.full,f.excerpt,f.full,f.excerpt,edits,2)

    def test_metadata_retained_and_old_contract_unchanged(self):
        before=deepcopy(self.base); result=self.project({})
        self.assertEqual(self.base,before)
        for key in ('scope','package_sha','excerpt_sha','full_delivery_sha','copy_lock'):
            self.assertEqual(result[key],self.base[key])
        self.assertEqual(result['design']['audience'],'consumer')
        self.assertFalse(result['public_render_ready'])
        # IDs in metadata are allowed and remain available for audit.
        d=deepcopy(self.f.excerpt); d['units'][0]['method_id']='G01'
        require_consumer_copy(d,result['nodes'])

    def test_all_visible_and_spoken_surfaces_reject_codes(self):
        for code in ('G01','G09','F01','R02'):
            for key in ('spoken_copy','on_screen_copy'):
                d=deepcopy(self.f.excerpt); d['units'][0][key]+=' '+code
                with self.assertRaisesRegex(ValueError,'Internal method code'):
                    require_consumer_copy(d,self.base['nodes'])
            nodes=deepcopy(self.base['nodes']); nodes[0]['text']=code
            with self.assertRaises(ValueError):require_consumer_copy(self.f.excerpt,nodes)
        d=deepcopy(self.f.excerpt); d['units'][0]['visual_excerpts']=[{'text':'G09 待核'}]
        with self.assertRaises(ValueError):require_consumer_copy(d,self.base['nodes'])

    def test_removing_protected_teaching_copy_is_not_label_cleanup(self):
        with self.assertRaisesRegex(ValueError,'projection'):
            self.project({self.base['nodes'][0]['node_id']:None})

    def test_new_wording_requires_a_matching_reviewed_delivery(self):
        with self.assertRaisesRegex(ValueError,'bound unit'):
            self.project({self.base['nodes'][0]['node_id']:'新的教学结论'})

    def test_consumer_contract_revalidation_repeats_policy(self):
        result=self.project({}); result['nodes'][0]['text']='G01'
        f=self.f
        with self.assertRaisesRegex(ValueError,'Internal method code'):
            validate_contract(result,f.package,f.manifest,f.statuses,f.full,f.excerpt)
