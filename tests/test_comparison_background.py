"""Isolation must preserve necessary reading and remain inside its own scene."""
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

    def test_no_legacy_or_unquiet_scene_is_silently_isolated(self):
        for key,value in [('kind','locate'),('candidate_reading_policy','visible'),
                          ('motion_treatment','in_place_check')]:
            p=specimen();p['scenes'][0][key]=value
            with self.assertRaisesRegex(ValueError,'quiet comparison reading path'):
                background_isolation_rows(p)
        p=specimen();p['scenes'][0].pop('comparison_background_policy')
        self.assertEqual(background_isolation_rows(p),[])


if __name__=='__main__':unittest.main()
