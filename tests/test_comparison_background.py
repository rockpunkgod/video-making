"""Isolation must preserve necessary reading and remain inside its own scene."""
from copy import deepcopy
import unittest

from ae_production.authored_native import background_isolation_rows


def specimen():
    return {
        'excerpts':{'chosen':{'world':'w','block_ids':['needed']}},
        'worlds':{'w':{'blocks':[
            {'id':'background','start':0,'end':40,'visible':True},
            {'id':'needed','start':40,'end':90,'visible':True}]}},
        'scenes':[{'id':'comparison','kind':'compare',
            'motion_treatment':'critical_comparison',
            'comparison_background_policy':'isolate_selected_passage',
            'candidate_reading_policy':'quiet_source_until_read',
            'excerpt':'chosen','source_refs':[{'world':'w','pointer':'/passage','start':40,'end':90}],
            'start':0,'candidate_arrive':2,'settled':7,'return_start':10,'end':12,
            'reading_events':[{'start':0,'end':30,'arrival':2.5,'end_time':3},
                              {'start':45,'end':85,'arrival':4,'end_time':5}]}]}


class ComparisonBackground(unittest.TestCase):
    def test_earlier_necessary_source_is_read_before_it_can_be_hidden(self):
        row=background_isolation_rows(specimen())[0]
        self.assertEqual(row['hidden'],['background'])
        self.assertEqual(row['readings'][0],{'time':2.75,'layers':['background']})
        self.assertGreater(row['fade_start'],row['readings'][0]['time'])
        self.assertEqual(row['quiet_at'],5)
        self.assertAlmostEqual(row['restore_at'],11.65)

    def test_last_necessary_reading_cannot_be_hidden(self):
        p=specimen();p['scenes'][0]['reading_events'][-1]['start']=30
        with self.assertRaisesRegex(ValueError,'hide necessary reading'):
            background_isolation_rows(p)

    def test_return_boundary_cannot_escape_its_scene(self):
        p=specimen();p['scenes'][0]['return_start']=12
        with self.assertRaisesRegex(ValueError,'inside its comparison scene'):
            background_isolation_rows(p)

    def test_no_legacy_or_unknown_scene_is_silently_isolated(self):
        for key,value in [('kind','locate'),('candidate_reading_policy','unknown'),
                          ('motion_treatment','unknown')]:
            p=specimen();p['scenes'][0][key]=value
            with self.assertRaisesRegex(ValueError,'explicit comparison reading path'):
                background_isolation_rows(p)
        p=specimen();p['scenes'][0].pop('comparison_background_policy')
        self.assertEqual(background_isolation_rows(p),[])

    def test_light_isolation_preserves_every_required_reading_block(self):
        p=specimen();s=p['scenes'][0];s['motion_treatment']='in_place_check'
        with self.assertRaisesRegex(ValueError,'required reading block'):
            background_isolation_rows(p)
        s['reading_events']=[{'start':45,'end':85,'depart':2,'arrival':4,'end_time':5}]
        row=background_isolation_rows(p)[0]
        self.assertEqual((row['fade_start'],row['quiet_at'],row['restore_at']),(2,4,10))

    def test_explicit_replay_isolation_preserves_candidate_policy_and_adds_no_decision(self):
        p=specimen();p['scenes'][0].update(kind='replay',candidate_reading_policy='visible')
        before=deepcopy(p)
        row=background_isolation_rows(p)[0]
        self.assertEqual(row['hidden'],['background'])
        self.assertEqual(p,before)
        self.assertNotIn('event',p['scenes'][0])


if __name__=='__main__':unittest.main()
