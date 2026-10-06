"""Synthetic-only checks for changing visual grammar without changing facts."""
from copy import deepcopy
import unittest

from creative_os.delivery import make_delivery, attach_fidelity_review, CHECKS
from creative_os.hero import build_contract
from creative_os.hero_narratives import DIRECTIONS, make_narrative
from tests import test_hero_identity
from video_contracts import sha, seal


class NarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_hero_identity.HeroTests.setUpClass()

    def setUp(self):
        f = test_hero_identity.HeroTests(); f.setUp(); self.f = f
        roles = ['HOOK','EVIDENCE_PREFIX','EVIDENCE_FOLLOW','EVIDENCE_YOUR',
                 'EVIDENCE_BLANK','EVIDENCE_GUIDE','EVIDENCE_TIME','FUNCTION','NOUN_NODE',
                 'STOP_EVENT','METHOD_STAMP','METHOD_ID','BOUNDARY_FORM','BOUNDARY_GERUND',
                 'BOUNDARY_G09','BOUNDARY_G09_ITEMS','BOUNDARY_HINT']
        specs = []
        for i, role in enumerate(roles):
            original = f.full['units'][i % len(f.full['units'])]
            specs.append(dict(unit_id=f'narrative-{i}', scene_id=original['scene_id'],
                              source_claim_refs=original['source_claim_refs'], intent='synthetic',
                              spoken_copy='当前动作，不定答案。', on_screen_copy=f'合成示例{i} 不定答案',
                              protected_terms=['不定答案']))
        self.excerpt = make_delivery(f.package,f.manifest,f.statuses,specs)
        for unit in self.excerpt['units']:
            self.excerpt = attach_fidelity_review(self.excerpt,unit['unit_id'],'SYNTHETIC HOST',
                                                  {k:'Synthetic fixture only.' for k in CHECKS})
        nodes = [dict(node_id=role,kind='text',unit_id=unit['unit_id'],text=unit['on_screen_copy'],
                      position=[128,128],font='NotoSansSC-Regular',size=40,color='#20211F')
                 for role,unit in zip(roles,self.excerpt['units'])]
        self.base = build_contract(f.package,f.manifest,f.statuses,f.full,self.excerpt,{},nodes,
                                   [{'start':0,'end':14.75,'phase':'HOLD'}],14.75)

    def variants(self, statuses=None):
        f=self.f
        return [make_narrative(self.base,d,f.package,f.manifest,statuses or f.statuses,
                               f.full,self.excerpt,10) for d in DIRECTIONS]

    def test_replay_and_ownership_survive_distinct_spatial_narratives(self):
        before=sha(self.base); results=self.variants()
        self.assertEqual(results,self.variants()); self.assertEqual(before,sha(self.base))
        self.assertEqual(len({r['design']['motion_grammar'] for r in results}),3)
        texts=lambda r:[(n['text'],n['unit_id']) for n in r['nodes'] if n['kind']=='text']
        for result in results:
            self.assertEqual(texts(result),texts(self.base))
            self.assertEqual(result['copy_lock'],self.base['copy_lock'])
            self.assertEqual(result['scope'],self.base['scope'])
            self.assertFalse(result['public_render_ready'])
            self.assertNotIn('motion_identity',result['design'])
        source_end=lambda r:next(n['out_point'] for n in r['nodes'] if n['node_id']=='EVIDENCE_BLANK')
        self.assertEqual([source_end(r) for r in results],[14.75,5.25,14.75])

    def test_withdrawal_still_blocks_every_narrative(self):
        statuses=deepcopy(self.f.statuses)
        for key,value in statuses.items():
            value['effective_status']='WITHDRAWN'; statuses[key]=seal(value)
        with self.assertRaises(ValueError):self.variants(statuses)

    def test_unknown_roles_cannot_silently_drop_protected_text(self):
        self.base['nodes'][0]['node_id']='UNKNOWN'
        # Reseal the otherwise valid base to reach the explicit role gate.
        self.base.pop('render_contract_sha'); self.base['render_contract_sha']=sha(self.base)
        with self.assertRaisesRegex(ValueError,'exact validated Hero text roles'):self.variants()
